"""draw2d: JSON с операциями черчения -> DXF (2D, для КОМПАСа/AutoCAD).
  python draw2d.py part.json -o part        # создаст part.dxf (+ part_preview.png с --preview)
Схему JSON см. PROMPT.md (её же скармливаешь LLM вместе с картинкой).
Оси: X - вправо, Y - вверх (чертёжная СК). Все размеры в мм.
Поддерживаемые типы линий (lt): main, thin, dashed, center, dashdot,
thick, thick_dashed, thick_dashdot, dim.

API (как в draw3d.py):
  doc = build(spec)          # ezdxf документ со всем чертежом (лист, рамка, entities)
  export(doc, 'out.dxf')     # сохранить DXF
  preview('out.dxf', 'p.png')# PNG-превью
"""
import sys, json, math, argparse
import ezdxf
from ezdxf.enums import TextEntityAlignment as TA

LAYERS = {  # имя типа линии -> (толщина 1/100 мм, тип линии)
    'main': (70, 'CONTINUOUS'), 'thin': (25, 'CONTINUOUS'), 'dashed': (35, 'DASHED'),
    'center': (25, 'CENTER'), 'dashdot': (35, 'DASHDOT'), 'thick': (140, 'CONTINUOUS'),
    'thick_dashed': (140, 'DASHED'), 'thick_dashdot': (140, 'DASHDOT'), 'dim': (25, 'CONTINUOUS'),
}
ALIGN = {'left': TA.MIDDLE_LEFT, 'center': TA.MIDDLE_CENTER, 'right': TA.MIDDLE_RIGHT,
         'bl': TA.BOTTOM_LEFT, 'bc': TA.BOTTOM_CENTER, 'br': TA.BOTTOM_RIGHT}
SIZES = {'A4': (210, 297), 'A3': (297, 420), 'A2': (420, 594), 'A1': (594, 841)}

def fmt(v):
    return f'{v:.2f}'.rstrip('0').rstrip('.').replace('.', ',')

class TF:
    def __init__(s, scale=1.0, ox=0.0, oy=0.0, flip=False):
        s.s, s.ox, s.oy, s.f = scale, ox, oy, (-1 if flip else 1)
    def p(s, q): return (s.ox + s.s * q[0], s.oy + s.f * s.s * q[1])
    def a(s, ang): return ang if s.f == 1 else -ang
    def r(s, v): return v * s.s

# ---------- лист ----------
def sheet(msp, doc, cfg):
    fmt_, ori = cfg.get('format', 'A4'), cfg.get('orientation', 'portrait')
    w, h = SIZES[fmt_]
    if ori == 'landscape': w, h = h, w
    def Pl(pts, lt='thin', close=False):
        msp.add_lwpolyline(pts, close=close, dxfattribs={'layer': lt})
    def Ln(a, b, lt='thin'): msp.add_line(a, b, dxfattribs={'layer': lt})
    def Tx(s, xy, hh=3.5, al='center'):
        t = msp.add_text(s, dxfattribs={'height': hh, 'layer': 'thin', 'style': 'GOST', 'oblique': 15})
        t.set_placement(xy, align=ALIGN[al])
    Pl([(0, 0), (w, 0), (w, h), (0, h)], 'thin', True)
    if cfg.get('frame', True): Pl([(20, 5), (w - 5, 5), (w - 5, h - 5), (20, h - 5)], 'main', True)
    tb = cfg.get('title_block') or {}
    form = tb.get('form')
    bh = {'1': 55, '2': 40, '2a': 15}.get(form, 0)
    if form:
        x0, y0, x1 = w - 5 - 185, 5, w - 5
        Pl([(x0, y0), (x1, y0), (x1, y0 + bh), (x0, y0 + bh)], 'main', True)
        for dx in (7, 17, 40, 55, 65): Ln((x0 + dx, y0), (x0 + dx, y0 + bh), 'main')
        for r in range(1, int(bh // 5)): Ln((x0, y0 + 5 * r), (x0 + 65, y0 + 5 * r))
        code, name = tb.get('code', ''), tb.get('name', '')
        if form == '2a':
            Ln((x0 + 175, y0), (x0 + 175, y0 + bh), 'main'); Ln((x0 + 175, y0 + 5), (x1, y0 + 5), 'main')
            Tx(code, (x0 + 120, y0 + 7.5), 7)
            Tx('Лист', (x0 + 180, y0 + 12.5), 2.5); Tx(str(tb.get('sheet', 1)), (x0 + 180, y0 + 2.5), 4)
        else:
            Ln((x0 + 65, y0 + 15), (x1, y0 + 15), 'main'); Ln((x0 + 135, y0), (x0 + 135, y0 + bh), 'main')
            Ln((x0 + 65, y0 + bh - 15), (x0 + 135, y0 + bh - 15), 'main')
            Ln((x0 + 135, y0 + bh - 15), (x1, y0 + bh - 15), 'main'); Ln((x0 + 135, y0 + bh - 30), (x1, y0 + bh - 30), 'main')
            Tx(code, (x0 + 100, y0 + bh - 7.5), 7); Tx(name, (x0 + 100, y0 + (bh - 15 + 15) / 2), 7)
            Tx(tb.get('group', ''), (x0 + 160, y0 + 7.5), 5)
            Tx('Разраб.', (x0 + 1, y0 + 12), 2.5, 'left'); Tx(tb.get('author', ''), (x0 + 18, y0 + 12), 2.5, 'left')
            Tx(tb.get('scale', '1:1'), (x0 + 175, y0 + bh - 22), 4)
        if form == '2a' and name: pass
        Tx('Формат ' + fmt_, (x1 - 5, 2.2), 2.5, 'right')
    return w, h, bh

# ---------- bbox для автоподгонки ----------
def bbox(ents):
    xs, ys = [], []
    def add(q): xs.append(q[0]); ys.append(q[1])
    for e in ents:
        t = e['type']
        if t == 'line': add(e['p1']); add(e['p2'])
        elif t in ('polyline', 'spline'): [add(q) for q in e['pts']]
        elif t in ('circle', 'arc'):
            add((e['c'][0] - e['r'], e['c'][1] - e['r'])); add((e['c'][0] + e['r'], e['c'][1] + e['r']))
        elif t == 'ellipse':
            m = max(e['rx'], e['ry']); add((e['c'][0] - m, e['c'][1] - m)); add((e['c'][0] + m, e['c'][1] + m))
        elif t == 'rect': add(e['p']); add((e['p'][0] + e['w'], e['p'][1] + e['h']))
        elif t == 'hatch': [add(q) for q in e['boundary']]
        elif t == 'text': add(e['p'])
    return (min(xs), max(xs), min(ys), max(ys)) if xs else (0, 1, 0, 1)

# ---------- главный рендер ----------
def build(spec):
    """Собрать ezdxf-документ из спецификации. Возвращает (doc, meta), где meta -
    размеры листа (W, H, bh) для возможной пост-обработки."""
    doc = ezdxf.new('R2010', setup=True)
    doc.header['$LTSCALE'] = 4
    if 'GOST' not in doc.styles: doc.styles.add('GOST', font='isocpeur.ttf')
    for n, (lw, lt) in LAYERS.items(): doc.layers.add(n, lineweight=lw, linetype=lt)
    msp = doc.modelspace()
    W, H, bh = sheet(msp, doc, spec.get('sheet', {}))
    ents = spec['entities']; view = spec.get('view', {})
    flip = view.get('y_down', False)
    fitmode = view.get('fit', 'none')
    if fitmode in ('auto', 'shrink'):
        x0, x1, y0, y1 = bbox(ents); m = view.get('dim_margin', 15)
        ax0, ax1, ay0, ay1 = 20 + m, W - 5 - m, 5 + bh + m, H - 5 - m
        sc = min((ax1 - ax0) / max(x1 - x0, 1e-9), (ay1 - ay0) / max(y1 - y0, 1e-9))
        if fitmode == 'shrink': sc = min(sc, 1.0)
        cx, cy = (ax0 + ax1) / 2, (ay0 + ay1) / 2
        f = -1 if flip else 1
        tf = TF(sc, cx - sc * (x0 + x1) / 2, cy - f * sc * (y0 + y1) / 2, flip)
    else:
        o = view.get('origin', [0, 0]); tf = TF(view.get('scale', 1.0), o[0], o[1], flip)
    sc = tf.s
    dstyle = {'dimtxt': 3.5, 'dimasz': 3, 'dimexe': 1.5, 'dimexo': 1, 'dimtxsty': 'GOST', 'dimgap': 1}
    def lay(e): return e.get('lt', 'main')
    for i, e in enumerate(ents):
        try:
            t = e['type']; at = {'layer': lay(e)}
            if t == 'line': msp.add_line(tf.p(e['p1']), tf.p(e['p2']), dxfattribs=at)
            elif t == 'rect':
                x, y = e['p']; pts = [(x, y), (x + e['w'], y), (x + e['w'], y + e['h']), (x, y + e['h'])]
                msp.add_lwpolyline([tf.p(q) for q in pts], close=True, dxfattribs=at)
            elif t == 'polyline': msp.add_lwpolyline([tf.p(q) for q in e['pts']], close=e.get('closed', False), dxfattribs=at)
            elif t == 'circle': msp.add_circle(tf.p(e['c']), tf.r(e['r']), dxfattribs=at)
            elif t == 'arc':
                a1, a2 = tf.a(e['a1']), tf.a(e['a2'])
                if tf.f == -1: a1, a2 = a2, a1
                msp.add_arc(tf.p(e['c']), tf.r(e['r']), a1, a2, dxfattribs=at)
            elif t == 'ellipse':
                rx, ry, rot = e['rx'], e['ry'], e.get('rot', 0)
                if ry > rx: rx, ry, rot = ry, rx, rot + 90
                rot = tf.a(rot); rr = math.radians(rot)
                s0, s1 = e.get('a1', 0), e.get('a2', 360)
                if tf.f == -1: s0, s1 = -s1, -s0
                msp.add_ellipse(tf.p(e['c']), major_axis=(tf.r(rx) * math.cos(rr), tf.r(rx) * math.sin(rr), 0),
                                ratio=ry / rx, start_param=math.radians(s0), end_param=math.radians(s1 if s1 - s0 < 360 else s0 + 360), dxfattribs=at)
            elif t == 'spline': msp.add_spline(fit_points=[(*tf.p(q), 0) for q in e['pts']], dxfattribs=at)
            elif t == 'text':
                h_ = e.get('h', 3.5)
                tx = msp.add_text(e['text'], dxfattribs={'height': h_, 'layer': e.get('lt', 'thin'), 'style': 'GOST',
                                                          'rotation': tf.a(e.get('rot', 0)), 'oblique': 15})
                tx.set_placement(tf.p(e['p']), align=ALIGN[e.get('align', 'left')])
            elif t == 'hatch':
                hh = msp.add_hatch(dxfattribs={'layer': 'thin'})
                hh.set_pattern_fill(e.get('pattern', 'ANSI31'), scale=e.get('scale', 1.0), angle=e.get('angle', 0))
                hh.paths.add_polyline_path([tf.p(q) for q in e['boundary']], is_closed=True)
                for hole in e.get('holes', []): hh.paths.add_polyline_path([tf.p(q) for q in hole], is_closed=True, flags=16)
            elif t == 'dim_linear':
                p1, p2 = e['p1'], e['p2']; o = e.get('offset', 10); k = e.get('orient', 'h')
                a, b = tf.p(p1), tf.p(p2)
                val = {'h': abs(p2[0] - p1[0]), 'v': abs(p2[1] - p1[1])}.get(k, math.dist(p1, p2))
                txt = e.get('text') or fmt(val)
                if k == 'h': d = msp.add_linear_dim(base=((a[0] + b[0]) / 2, a[1] + o), p1=a, p2=b, angle=0, text=txt, override=dstyle, dxfattribs={'layer': 'dim'})
                elif k == 'v': d = msp.add_linear_dim(base=(a[0] + o, (a[1] + b[1]) / 2), p1=a, p2=b, angle=90, text=txt, override=dstyle, dxfattribs={'layer': 'dim'})
                else: d = msp.add_aligned_dim(p1=a, p2=b, distance=o, text=txt, override=dstyle, dxfattribs={'layer': 'dim'})
                d.render()
            elif t in ('dim_radius', 'dim_diameter'):
                c = tf.p(e['c']); ang = tf.a(e.get('angle', 45)); r = e['r']
                if t == 'dim_radius': txt = e.get('text') or 'R' + fmt(r); d = msp.add_radius_dim(c, radius=tf.r(r), angle=ang, text=txt, override=dstyle, dxfattribs={'layer': 'dim'})
                else: txt = e.get('text') or 'Ø' + fmt(2 * r); d = msp.add_diameter_dim(c, radius=tf.r(r), angle=ang, text=txt, override=dstyle, dxfattribs={'layer': 'dim'})
                d.render()
            elif t == 'dim_angle':
                c, a, b = e['c'], e['p1'], e['p2']
                v1 = math.atan2(a[1] - c[1], a[0] - c[0]); v2 = math.atan2(b[1] - c[1], b[0] - c[0])
                val = abs(math.degrees(v2 - v1)) % 360; val = val if val <= 180 else 360 - val
                C, A, B = tf.p(c), tf.p(a), tf.p(b)
                d = msp.add_angular_dim_3p(base=tf.p((c[0] + e.get('r', 10) * 1, c[1] + e.get('r', 10))), center=C, p1=A, p2=B,
                                           text=e.get('text') or fmt(val) + '°', override=dstyle, dxfattribs={'layer': 'dim'})
                d.render()
            elif t == 'leader':  # выноска: pts[0] - остриё, последний - полка с текстом
                pts = [tf.p(q) for q in e['pts']]
                msp.add_lwpolyline(pts, dxfattribs={'layer': 'thin'})
                dx, dy = pts[0][0] - pts[1][0], pts[0][1] - pts[1][1]; n = math.hypot(dx, dy) or 1; dx, dy = dx / n, dy / n
                bx, by = pts[0][0] - dx * 3, pts[0][1] - dy * 3
                msp.add_solid([pts[0], (bx - dy * .9, by + dx * .9), (bx + dy * .9, by - dx * .9)], dxfattribs={'layer': 'thin'})
                sh = len(e['text']) * 2.2 + 2; s = 1 if pts[-1][0] >= pts[-2][0] else -1
                msp.add_line(pts[-1], (pts[-1][0] + s * sh, pts[-1][1]), dxfattribs={'layer': 'thin'})
                tx = msp.add_text(e['text'], dxfattribs={'height': e.get('h', 3.5), 'layer': 'thin', 'style': 'GOST', 'oblique': 15})
                tx.set_placement((pts[-1][0] + s * sh / 2, pts[-1][1] + 2.2), align=TA.MIDDLE_CENTER)
            elif t == 'table':  # p - левый верхний угол (в мм листа, без преобразования)
                x, y = e['p']; cw = e['col_w']; rh = e.get('row_h', 8); rows = e['rows']
                tw = sum(cw)
                for r_ in range(len(rows) + 1): msp.add_line((x, y - r_ * rh), (x + tw, y - r_ * rh), dxfattribs={'layer': 'main'})
                xx = x
                for c_ in range(len(cw) + 1):
                    msp.add_line((xx, y), (xx, y - len(rows) * rh), dxfattribs={'layer': 'main'}); xx += cw[c_] if c_ < len(cw) else 0
                for r_, row in enumerate(rows):
                    xx = x
                    for c_, cell in enumerate(row):
                        tx = msp.add_text(str(cell), dxfattribs={'height': 3.5, 'layer': 'thin', 'style': 'GOST', 'oblique': 15})
                        tx.set_placement((xx + cw[c_] / 2, y - r_ * rh - rh / 2), align=TA.MIDDLE_CENTER); xx += cw[c_]
            else: raise ValueError(f'неизвестный type: {t}')
        except Exception as ex:
            print(f'! entities[{i}] ({e.get("type")}): {type(ex).__name__}: {ex}', file=sys.stderr)
    return doc, (W, H, bh)

def export(doc, out):
    """Сохранить собранный документ в DXF."""
    doc.saveas(out)
    return out

def preview(dxf_path, png_path, size=None):
    """PNG-превью из готового DXF. size - (W, H) мм листа (для пропорций)."""
    import matplotlib; matplotlib.use('Agg')
    from ezdxf.addons.drawing import RenderContext, Frontend
    from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
    import matplotlib.pyplot as plt
    d = ezdxf.readfile(dxf_path)
    if size is None:
        ext = d.header.get('$EXTMAX', (297, 420, 0)); ext0 = d.header.get('$EXTMIN', (0, 0, 0))
        W = max(ext[0] - ext0[0], 1); H = max(ext[1] - ext0[1], 1)
    else:
        W, H = size
    fig = plt.figure(figsize=(8, 8 * H / W)); ax = fig.add_axes([0, 0, 1, 1])
    Frontend(RenderContext(d), MatplotlibBackend(ax)).draw_layout(d.modelspace())
    fig.savefig(png_path, dpi=110)
    plt.close(fig)
    return png_path

def render(spec, out, preview_png=None):
    """Собрать и сохранить: spec -> out (DXF), при preview_png - ещё и PNG."""
    doc, meta = build(spec)
    export(doc, out)
    if preview_png: preview(out, preview_png, size=(meta[0], meta[1]))
    return out

if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('spec'); ap.add_argument('-o', default='out.dxf'); ap.add_argument('--preview', action='store_true')
    a = ap.parse_args()
    base = a.o[:-4] if a.o.endswith('.dxf') else a.o
    render(json.load(open(a.spec, encoding='utf-8')), base + '.dxf',
           preview_png=base + '_preview.png' if a.preview else None)
    print('ok -> %s.dxf' % base)
