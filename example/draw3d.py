"""draw3d: JSON с операциями моделирования -> STEP (3D) + три вида в DXF (2D, для КОМПАСа).
  python draw3d.py part.json -o part        # создаст part.step, part_views.dxf, part_preview.png
Схему JSON см. PROMPT3D.md.
Оси: X, Y - в плоскости листа/детали, Z - "вверх" (высота/толщина), если не указано иное.
"""
import sys, json, math, argparse
import cadquery as cq
from cadquery import exporters

def V(p, z=0.0):
    return (p[0], p[1], z) if len(p) == 2 else tuple(p)

def axis_vec(a):
    return {'X': (1, 0, 0), 'Y': (0, 1, 0), 'Z': (0, 0, 1)}[a.upper()]

AX_PLANE = {'Z': ('XY', False, (0, 0, -1)), 'X': ('YZ', False, (-1, 0, 0)), 'Y': ('ZX', True, (0, -1, 0))}

def _drill_wp(axis, a, b):
    """Рабочая плоскость для сверления/выреза вдоль axis; (a,b) - координаты
    по двум оставшимся глобальным осям в порядке X,Y,Z (без axis)."""
    plane, swap, backoff = AX_PLANE[axis.upper()]
    u, v = (b, a) if swap else (a, b)
    return cq.Workplane(plane).center(u, v), backoff

def sel_edges(res, which):
    if which in ('all', None): return res.edges()
    if which == 'vertical': return res.edges('|Z')
    if which == 'horizontal': return res.edges('#Z')
    if which == 'top': return res.faces('>Z').edges()
    if which == 'bottom': return res.faces('<Z').edges()
    return res.edges(which)  # произвольный CQ-селектор строкой

def build(spec):
    res = None
    for i, op in enumerate(spec['ops']):
        t = op['op']
        try:
            if t == 'revolve':
                ax = op.get('axis', 'X').upper()
                pts = op['profile']  # [[axial, radius], ...]
                plane = {'X': 'XZ', 'Y': 'YZ', 'Z': 'XY'}[ax]
                w = cq.Workplane(plane).polyline(pts).close()
                end = (1, 0, 0) if ax == 'X' else (0, 1, 0) if ax == 'Y' else (0, 0, 1)
                piece = w.revolve(op.get('angle', 360), (0, 0, 0), end)
                if op.get('move'): piece = piece.translate(V(op['move'], op.get('move', [0, 0, 0])[2] if len(op.get('move', [0,0,0]))>2 else 0))
                res = piece if res is None else (res.union(piece) if not op.get('cut') else res.cut(piece))

            elif t == 'box':
                w, l, h = op['w'], op['l'], op['h']
                piece = cq.Workplane('XY').box(w, l, h, centered=op.get('centered', True))
                mv = op.get('at', [0, 0, 0])
                if not op.get('centered', True): piece = cq.Workplane('XY').center(0,0).workplane(offset=0).box(w,l,h,centered=False)
                piece = piece.translate(tuple(mv))
                for r in op.get('rotate', []):
                    piece = piece.rotate((0,0,0), axis_vec(r['axis']), r['deg'])
                res = piece if res is None else (res.cut(piece) if op.get('cut') else res.union(piece))

            elif t == 'cylinder':
                d, h = op['d'], op['h']
                piece = cq.Workplane('XY').circle(d / 2).extrude(h)
                piece = piece.translate(tuple(op.get('at', [0, 0, 0])))
                for r in op.get('rotate', []): piece = piece.rotate((0,0,0), axis_vec(r['axis']), r['deg'])
                res = piece if res is None else (res.cut(piece) if op.get('cut') else res.union(piece))

            elif t == 'extrude_sketch':
                plane = op.get('plane', 'XY')
                w = cq.Workplane(plane).polyline(op['pts']).close().extrude(op['h'])
                w = w.translate(tuple(op.get('at', [0, 0, 0])))
                res = w if res is None else (res.cut(w) if op.get('cut') else res.union(w))

            elif t == 'hole':  # одно отверстие вдоль axis (через всё тело или на глубину)
                d = op['d']; ax = op.get('axis', 'Z'); a, b = op['center']
                wp, backoff = _drill_wp(ax, a, b)
                hgt = 2000 if op.get('through', True) else op['depth']
                off = tuple(x * (1000 if op.get('through', True) else 0) for x in backoff)
                piece = wp.circle(d / 2).extrude(hgt).translate(off)
                res = res.cut(piece)

            elif t == 'hole_pattern_circular':  # отверстия по окружности, ось - axis
                d = op['d']; n = op['count']; bc = op['bolt_circle_d'] / 2; ax = op.get('axis', 'Z')
                ca, cb = op.get('center', [0, 0]); a0 = op.get('start_angle', 90)
                piece = None
                for k in range(n):
                    ang = math.radians(a0 + 360 * k / n)
                    a, b = ca + bc * math.cos(ang), cb + bc * math.sin(ang)
                    wp, backoff = _drill_wp(ax, a, b)
                    off = tuple(x * 1000 for x in backoff)
                    c = wp.circle(d / 2).extrude(2000).translate(off)
                    piece = c if piece is None else piece.union(c)
                res = res.cut(piece)

            elif t == 'hole_pattern_linear':
                d = op['d']; n = op['count']; pitch = op['pitch']; ax = op.get('axis', 'Z')
                ca, cb = op['center']; dirv = op.get('dir', [1, 0])
                nrm = math.hypot(*dirv); ua, ub = dirv[0] / nrm, dirv[1] / nrm
                offc = -(n - 1) * pitch / 2
                piece = None
                for k in range(n):
                    a, b = ca + ua * (offc + k * pitch), cb + ub * (offc + k * pitch)
                    wp, backoff = _drill_wp(ax, a, b)
                    off = tuple(x * 1000 for x in backoff)
                    c = wp.circle(d / 2).extrude(2000).translate(off)
                    piece = c if piece is None else piece.union(c)
                res = res.cut(piece)

            elif t == 'cut_prism_through':  # вырез призмой насквозь вдоль axis
                size = op.get('size'); shape = op.get('shape', 'square'); rot = op.get('rot', 0)
                ax = op.get('axis', 'Z'); ca, cb = op.get('center', [0, 0])
                wp, backoff = _drill_wp(ax, ca, cb)
                sk = wp.rect(size, size) if shape == 'square' else wp.rect(op['w'], op['l'])
                off = tuple(x * 1000 for x in backoff)
                av = axis_vec(ax)
                piece = sk.extrude(2000).translate(off).rotate((ca, cb, 0) if ax != 'Z' else (0,0,0), av, rot) \
                    if False else sk.extrude(2000).translate(off)
                if rot:
                    piece = piece.rotate((0, 0, 0), av, rot)
                res = res.cut(piece)

            elif t == 'fillet':
                res = sel_edges(res, op.get('sel')).fillet(op['r'])
            elif t == 'chamfer':
                res = sel_edges(res, op.get('sel')).chamfer(op['r'])
            elif t == 'mirror_union':
                plane = op.get('plane', 'XZ')
                res = res.union(res.mirror(plane))
            else:
                raise ValueError(f'неизвестная op: {t}')
        except Exception as ex:
            raise RuntimeError(f'ops[{i}] ({t}): {type(ex).__name__}: {ex}') from ex
    return res

def _hlr_edges(shape, normal, xdir):
    """Возвращает (видимые, невидимые) рёбра как списки полилиний [(x,y),...]
    в 2D-координатах плоскости вида (normal = направление взгляда, xdir = ось X вида)."""
    from OCP.gp import gp_Ax2, gp_Pnt, gp_Dir
    from OCP.BRepLib import BRepLib
    from OCP.HLRBRep import HLRBRep_Algo, HLRBRep_HLRToShape
    from OCP.HLRAlgo import HLRAlgo_Projector
    from OCP.GCPnts import GCPnts_QuasiUniformDeflection
    from cadquery.occ_impl.shapes import Shape, Compound, TOLERANCE

    hlr = HLRBRep_Algo(); hlr.Add(shape.wrapped)
    ax2 = gp_Ax2(gp_Pnt(0, 0, 0), gp_Dir(*normal), gp_Dir(*xdir))
    hlr.Projector(HLRAlgo_Projector(ax2)); hlr.Update(); hlr.Hide()
    hs = HLRBRep_HLRToShape(hlr)
    vis_c, hid_c = [], []
    for c in (hs.VCompound(), hs.Rg1LineVCompound(), hs.OutLineVCompound()):
        if not c.IsNull(): vis_c.append(c)
    for c in (hs.HCompound(), hs.OutLineHCompound()):
        if not c.IsNull(): hid_c.append(c)
    for c in vis_c + hid_c: BRepLib.BuildCurves3d_s(c, TOLERANCE)

    def edges_of(comps):
        out = []
        for comp in comps:
            for e in Shape(comp).Edges():
                curve = e._geomAdaptor()
                pts = GCPnts_QuasiUniformDeflection(curve, 1e-3, curve.FirstParameter(), curve.LastParameter())
                if pts.IsDone():
                    out.append([(pts.Value(i + 1).X(), pts.Value(i + 1).Y()) for i in range(pts.NbPoints())])
        return out
    return edges_of(vis_c), edges_of(hid_c)

def export_views(res, base, preview=None):
    """Три вида (спереди/сверху/слева, ГОСТ 2.305 первый угол) с удалением
    невидимых линий -> один DXF. Главный вид сверху-слева, сверху — вид сверху
    под ним, справа — вид слева, выровненный по высоте с главным."""
    import ezdxf
    doc = ezdxf.new('R2010', setup=True)
    for n, (lw, lt) in {'vis': (50, 'CONTINUOUS'), 'hid': (25, 'DASHED'), 'ctr': (25, 'CENTER')}.items():
        doc.layers.add(n, lineweight=lw, linetype=lt)
    msp = doc.modelspace()
    shape = res.val()

    # front: смотрим с -Y (видим XZ), top: смотрим с +Z сверху (видим XY, X вправо),
    # left: смотрим с -X (видим YZ) -> разворачиваем в стандартную раскладку ГОСТ
    front_v, front_h = _hlr_edges(shape, (0, -1, 0), (1, 0, 0))     # x=X, y=Z
    top_v, top_h = _hlr_edges(shape, (0, 0, -1), (1, 0, 0))         # x=X, y=-Y (смотрим сверху вниз)
    left_v, left_h = _hlr_edges(shape, (1, 0, 0), (0, -1, 0))       # x=-Y, y=Z (вид слева направо)

    def bb(polys):
        xs = [p[0] for pl in polys for p in pl]; ys = [p[1] for pl in polys for p in pl]
        return (min(xs), max(xs), min(ys), max(ys)) if xs else (0, 1, 0, 1)

    fx0, fx1, fy0, fy1 = bb(front_v + front_h)
    tx0, tx1, ty0, ty1 = bb(top_v + top_h)
    lx0, lx1, ly0, ly1 = bb(left_v + left_h)
    gap = 20
    fo = (-fx0, -fy0)                                        # низ-лево главного вида в (0,0)
    to = (-fx0 - tx0, -(ty1 - ty0) - gap - fy0)               # вид сверху под главным, выровнен по X
    lo = (fx1 - fx0 + gap - lx0, -fy0)                        # вид слева справа, выровнен по высоте (Y)

    def draw(polys, off, layer):
        for pl in polys:
            msp.add_lwpolyline([(x + off[0], y + off[1]) for x, y in pl], dxfattribs={'layer': layer})
    draw(front_v, fo, 'vis'); draw(front_h, fo, 'hid')
    draw(top_v, to, 'vis'); draw(top_h, to, 'hid')
    draw(left_v, lo, 'vis'); draw(left_h, lo, 'hid')
    doc.saveas(base + '_views.dxf')

    if preview:
        import matplotlib; matplotlib.use('Agg')
        from ezdxf.addons.drawing import RenderContext, Frontend
        from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
        import matplotlib.pyplot as plt
        fig = plt.figure(figsize=(10, 8)); ax = fig.add_axes([0, 0, 1, 1])
        Frontend(RenderContext(doc), MatplotlibBackend(ax)).draw_layout(msp)
        fig.savefig(preview, dpi=110)

if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('spec'); ap.add_argument('-o', default='part')
    ap.add_argument('--preview', action='store_true')
    a = ap.parse_args()
    spec = json.load(open(a.spec, encoding='utf-8'))
    res = build(spec)
    res.val().exportStep(a.o + '.step')
    export_views(res, a.o, preview=(a.o + '_preview.png') if a.preview else None)
    print('ok -> %s.step, %s_views.dxf  |  объём: %.1f мм3' % (a.o, a.o, res.val().Volume()))
