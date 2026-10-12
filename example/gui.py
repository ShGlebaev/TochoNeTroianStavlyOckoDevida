"""gui.py: графический интерфейс для draw2d.py / draw3d.py.
  python gui.py
Вкладки: 2D (JSON -> DXF), 3D (JSON -> STEP + виды). Внутри 2D - интерактивный
холст: рисование примитивов мышью, свойства в панели справа, генерация JSON.
"""
import sys, os, json, math, io, base64, traceback
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog

# Пути: в режиме PyInstaller (frozen) ресурсы лежат в _MEIPASS, а пользовательские
# файлы ищем/пишем рядом с исполняемым файлом.
if getattr(sys, 'frozen', False):
    APP_DIR = os.path.dirname(sys.executable)
    BUNDLE = getattr(sys, '_MEIPASS', APP_DIR)
else:
    APP_DIR = BUNDLE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BUNDLE)
import draw2d
try:
    import draw3d
    HAS_3D = True
except ImportError:
    HAS_3D = False   # cadquery не собран/не установлен — 3D-вкладка будет отключена

def res_path(name):
    """Файл примера: сначала рядом с приложением, потом в бандле."""
    p = os.path.join(APP_DIR, name)
    return p if os.path.exists(p) else os.path.join(BUNDLE, name)

EX = APP_DIR

# ======================================================================
# Общие утилиты
# ======================================================================
def log(msg, tag='info'):
    """Пишем в statusbar (если есть) и в stderr."""
    print(f'[{tag}] {msg}', file=sys.stderr)

class StatusBar(ttk.Frame):
    def __init__(self, master):
        super().__init__(master)
        self.lbl = ttk.Label(self, text='Готово', anchor='w')
        self.lbl.pack(fill='x', side='left', padx=4)
    def set(self, text): self.lbl.config(text=text)

# ======================================================================
# Вкладка 2D: JSON-редактор + превью
# ======================================================================
class Tab2DJSON(ttk.Frame):
    """Редактор JSON с валидацией и кнопкой сборки в DXF."""
    def __init__(self, master, status):
        super().__init__(master)
        self.status = status
        self.path = None

        top = ttk.Frame(self); top.pack(fill='x', padx=4, pady=2)
        ttk.Button(top, text='📂 Открыть JSON', command=self.open_json).pack(side='left')
        ttk.Button(top, text='💾 Сохранить JSON', command=self.save_json).pack(side='left', padx=2)
        ttk.Button(top, text='▶ Собрать DXF', command=self.build).pack(side='left', padx=2)
        ttk.Button(top, text='📋 Вставить пример', command=self.paste_example).pack(side='left', padx=2)
        self.sample_btn = ttk.Menubutton(top, text='📄 Загрузить пример')
        m = tk.Menu(self.sample_btn, tearoff=0)
        for fn in ('sample_2d.json', 'bracket_2d.json', 'gear_2d.json'):
            m.add_command(label=fn, command=lambda f=fn: self.load_sample(f))
        self.sample_btn.config(menu=m); self.sample_btn.pack(side='left', padx=2)

        self.txt = tk.Text(self, undo=True, wrap='none', font=('Consolas', 10))
        self.txt.pack(fill='both', expand=True, padx=4, pady=2)
        self.txt.bind('<<Modified>>', self._on_modified)

        bottom = ttk.Frame(self); bottom.pack(fill='x', padx=4, pady=2)
        ttk.Label(bottom, text='Выходной файл:').pack(side='left')
        self.out = tk.StringVar(value='out.dxf')
        ttk.Entry(bottom, textvariable=self.out, width=25).pack(side='left', padx=2)
        ttk.Checkbutton(bottom, text='PNG-превью', variable=tk.BooleanVar(value=True)).pack(side='left', padx=2)

    def _on_modified(self, _=None):
        if self.txt.edit_modified():
            self.txt.edit_modified(False)

    def open_json(self):
        p = filedialog.askopenfilename(filetypes=[('JSON', '*.json')], initialdir=EX)
        if not p: return
        self.txt.delete('1.0', 'end'); self.txt.insert('1.0', open(p, encoding='utf-8').read())
        self.path = p; self.status.set(f'Открыт {p}')

    def save_json(self):
        p = self.path or filedialog.asksaveasfilename(defaultextension='.json', filetypes=[('JSON', '*.json')], initialdir=EX)
        if not p: return
        open(p, 'w', encoding='utf-8').write(self.txt.get('1.0', 'end'))
        self.path = p; self.status.set(f'Сохранён {p}')

    def load_sample(self, name):
        p = res_path(name)
        if os.path.exists(p):
            self.txt.delete('1.0', 'end'); self.txt.insert('1.0', open(p, encoding='utf-8').read())
            self.path = p; self.status.set(f'Загружен пример {name}')
        else:
            self.status.set(f'Нет файла {p}')

    def paste_example(self):
        spec = {
            'sheet': {'format': 'A4', 'orientation': 'landscape', 'frame': True,
                      'title_block': {'form': '1', 'code': 'ПН.000', 'name': 'Деталь',
                                      'author': '', 'group': '', 'scale': '1:1'}},
            'view': {'fit': 'auto', 'dim_margin': 15},
            'entities': [
                {'type': 'rect', 'p': [0, 0], 'w': 120, 'h': 80, 'lt': 'main'},
                {'type': 'circle', 'c': [60, 40], 'r': 20, 'lt': 'main'},
                {'type': 'dim_linear', 'p1': [0, 0], 'p2': [120, 0], 'orient': 'h', 'offset': -12},
                {'type': 'dim_linear', 'p1': [0, 0], 'p2': [0, 80], 'orient': 'v', 'offset': -12},
                {'type': 'dim_radius', 'c': [60, 40], 'r': 20, 'angle': 45},
                {'type': 'text', 'p': [60, 100], 'text': 'Пример', 'h': 5, 'align': 'center', 'lt': 'thin'}
            ]
        }
        self.txt.delete('1.0', 'end'); self.txt.insert('1.0', json.dumps(spec, indent=2, ensure_ascii=False))
        self.status.set('Пример вставлен в редактор')

    def build(self):
        try:
            spec = json.loads(self.txt.get('1.0', 'end'))
        except Exception as ex:
            messagebox.showerror('JSON', f'Ошибка парсинга JSON:\n{ex}'); return
        base = self.out.get().strip() or 'out'
        if base.endswith('.dxf'): base = base[:-4]
        if not os.path.isabs(base): base = os.path.join(EX, base)
        try:
            doc, meta = draw2d.build(spec)
            draw2d.export(doc, base + '.dxf')
            draw2d.preview(base + '.dxf', base + '_preview.png', size=(meta[0], meta[1]))
            self.status.set(f'Собрано -> {base}.dxf (+preview.png)')
            messagebox.showinfo('OK', f'{base}.dxf\n{base}_preview.png')
        except Exception as ex:
            log(traceback.format_exc())
            messagebox.showerror('Сборка', f'Ошибка:\n{ex}')

# ======================================================================
# Вкладка 2D: интерактивный холст
# ======================================================================
TOOLS2D = {
    'select':  '⬚ Выбор',
    'line':    '─ Линия',
    'rect':    '▭ Прямоугольник',
    'circle':  '○ Окружность',
    'arc':     '◠ Дуга',
    'text':    'Т Текст',
    'dim_lin': '↔ Размер',
}

class Tab2DCanvas(ttk.Frame):
    """Интерактивный холст: рисуем примитивы мышью, генерируем entities JSON.
    Каждый примитив попадает в дерево объектов, там же его можно удалить или
    изменить тип линии. Кнопка 'JSON' собирает всё в draw2d.build()."""
    def __init__(self, master, status):
        super().__init__(master)
        self.status = status
        self.tool = tk.StringVar(value='line')
        self.lt = tk.StringVar(value='main')
        self.ents = []
        self.p0 = None          # первая точка (для line/rect/circle/arc)
        self.cur = None         # текущий объект при рисовании

        top = ttk.Frame(self); top.pack(fill='x', padx=4, pady=2)
        ttk.Label(top, text='Инструмент:').pack(side='left')
        cb = ttk.Combobox(top, textvariable=self.tool, values=list(TOOLS2D.keys()),
                          state='readonly', width=10)
        cb.pack(side='left', padx=2)
        cb.bind('<<ComboboxSelected>>', lambda e: self._cancel())
        ttk.Label(top, text='Линия:').pack(side='left', padx=(10, 0))
        ttk.Combobox(top, textvariable=self.lt, values=list(draw2d.LAYERS.keys()),
                     state='readonly', width=12).pack(side='left', padx=2)
        ttk.Button(top, text='✖ Очистить', command=self.clear).pack(side='right')
        ttk.Button(top, text='➡ Собрать JSON -> DXF', command=self.to_json).pack(side='right', padx=4)

        body = ttk.Frame(self); body.pack(fill='both', expand=True)
        self.tree = ttk.Treeview(body, columns=('lt',), show='tree headings', selectmode='extended')
        self.tree.heading('#0', text='Объекты'); self.tree.heading('lt', text='Тип линии')
        self.tree.column('lt', width=80)
        self.tree.pack(side='left', fill='y')
        self.tree.bind('<Delete>', lambda e: self.delete_sel())
        self.tree.bind('<Double-1>', self.edit_sel)

        cv = ttk.Frame(body); cv.pack(side='left', fill='both', expand=True)
        self.cv = tk.Canvas(cv, bg='white')
        self.cv.pack(fill='both', expand=True)
        self.cv.bind('<Button-1>', self.on_click)
        self.cv.bind('<B1-Motion>', self.on_drag)
        self.cv.bind('<ButtonRelease-1>', self.on_up)
        self.cv.bind('<Motion>', self.on_move)
        self.scale = 4.0; self.ox = 20; self.oy = 60   # px/mm, смещение (лист A4 297x210)
        self.paper = (297, 210)                        # mm (landscape A4)
        self.cv.config(width=int(self.paper[0]*self.scale)+40, height=int(self.paper[1]*self.scale)+40)
        self._draw_paper()
        self._redraw()

    def _draw_paper(self):
        w, h = self.paper
        self.cv.delete('paper')
        self.cv.create_rectangle(self.ox, self.oy - h*self.scale, self.ox + w*self.scale, self.oy,
                                 fill='white', outline='black', tags='paper')
        # рамка
        self.cv.create_rectangle(self.ox + 20*self.scale, self.oy - h*self.scale + 5*self.scale,
                                 self.ox + (w-5)*self.scale, self.oy - 5*self.scale,
                                 outline='black', width=1, tags='paper')

    def to_p(self, ev):
        return ((ev.x - self.ox)/self.scale, (self.oy - ev.y)/self.scale)

    def _redraw(self):
        self.cv.delete('ent')
        for i, e in enumerate(self.ents):
            t = e['type']
            try:
                if t == 'line':
                    self._ln(e['p1'], e['p2'], e.get('lt','main'), tags=('ent',))
                elif t == 'rect':
                    pts = [(e['p'][0], e['p'][1]), (e['p'][0]+e['w'], e['p'][1]),
                           (e['p'][0]+e['w'], e['p'][1]+e['h']), (e['p'][0], e['p'][1]+e['h'])]
                    self._ln(pts[0], pts[1], e.get('lt','main'), tags=('ent',))
                    self._ln(pts[1], pts[2], e.get('lt','main'), tags=('ent',))
                    self._ln(pts[2], pts[3], e.get('lt','main'), tags=('ent',))
                    self._ln(pts[3], pts[0], e.get('lt','main'), tags=('ent',))
                elif t == 'circle':
                    c = e['c']; r = e['r']
                    self.cv.create_oval(self._x(c[0]-r), self._y(c[1]+r), self._x(c[0]+r), self._y(c[1]-r),
                                        outline='blue', tags=('ent',))
                elif t == 'text':
                    self.cv.create_text(self._x(e['p'][0]), self._y(e['p'][1]), text=e.get('text',''),
                                        fill='black', anchor='s', tags=('ent',))
            except Exception:
                pass
        # текущий недорисованный
        if self.cur:
            try:
                if self.cur['type'] == 'line':
                    self._ln(self.cur['p1'], self.cur['p2'], self.cur.get('lt','main'), tags=('cur',))
                elif self.cur['type'] == 'rect':
                    x0, y0 = self.cur['p']; x1, y1 = self.cur['q']
                    self.cv.create_rectangle(self._x(x0), self._y(y0), self._x(x1), self._y(y1),
                                             outline='green', dash=(3, 3), tags=('cur',))
                elif self.cur['type'] == 'circle':
                    c, r = self.cur['c'], self.cur['r']
                    self.cv.create_oval(self._x(c[0]-r), self._y(c[1]+r), self._x(c[0]+r), self._y(c[1]-r),
                                        outline='green', dash=(3, 3), tags=('cur',))
            except Exception:
                pass
        # дерево
        self.tree.delete(*self.tree.get_children())
        for i, e in enumerate(self.ents):
            label = self._label(e)
            self.tree.insert('', 'end', iid=str(i), text=label, values=(e.get('lt','main'),))
        if self.cur:
            self.tree.insert('', 'end', iid='cur', text=self._label(self.cur) + ' (рисуется…)', values=(self.cur.get('lt','main'),))

    def _label(self, e):
        t = e['type']
        if t == 'line': return f"линия {self._fmt(e['p1'])}-{self._fmt(e['p2'])}"
        if t == 'rect': return f"прямоугольник {self._fmt(e['p'])} {e['w']}x{e['h']}"
        if t == 'circle': return f"окружность {self._fmt(e['c'])} r={e['r']}"
        if t == 'text': return f"текст '{e.get('text','')[:20]}'"
        if t == 'dim_linear': return f"размер {self._fmt(e['p1'])}-{self._fmt(e['p2'])} {e.get('orient','h')}"
        return t

    def _fmt(self, p): return f"({p[0]:.1f},{p[1]:.1f})"

    def _x(self, mm): return self.ox + mm*self.scale
    def _y(self, mm): return self.oy - mm*self.scale

    def _ln(self, a, b, lt, tags):
        col = {'main': 'black', 'thin': 'gray', 'dashed': 'gray', 'center': 'red',
               'dashdot': 'red', 'thick': 'black', 'thick_dashed': 'black', 'dim': 'blue'}.get(lt, 'black')
        dash = (5, 3) if lt in ('dashed','thick_dashed','center','dashdot') else None
        self.cv.create_line(self._x(a[0]), self._y(a[1]), self._x(b[0]), self._y(b[1]),
                            fill=col, dash=dash, width=2 if lt.startswith('thick') else 1, tags=tags)

    # ---- мышь ----
    def on_click(self, ev):
        p = self.to_p(ev)
        tool = self.tool.get()
        if tool == 'line':
            self.cur = {'type': 'line', 'p1': p, 'p2': p, 'lt': self.lt.get()}
        elif tool == 'rect':
            self.cur = {'type': 'rect', 'p': p, 'q': p, 'w': 0, 'h': 0, 'lt': self.lt.get()}
        elif tool == 'circle':
            self.cur = {'type': 'circle', 'c': p, 'r': 0, 'lt': self.lt.get()}
        elif tool == 'text':
            txt = simpledialog.askstring('Текст', 'Введите текст:')
            if txt:
                self.ents.append({'type': 'text', 'p': p, 'text': txt, 'h': 5, 'align': 'center', 'lt': self.lt.get()})
                self._redraw()
        elif tool == 'dim_lin':
            self.cur = {'type': 'dim_linear', 'p1': p, 'p2': p, 'orient': 'h', 'offset': -10}
        elif tool == 'select':
            self._cancel()
            # выбор ближайшего объекта
            best, bi = 20/self.scale, -1
            for i, e in enumerate(self.ents):
                if e['type'] in ('line','dim_linear'):
                    d = self._dist_to_line(p, e['p1'], e['p2'])
                    if d < best: best, bi = d, i
                elif e['type'] == 'circle':
                    if abs(math.dist(p, e['c']) - e['r']) < best: best, bi = abs(math.dist(p, e['c']) - e['r']), i
                elif e['type'] == 'rect':
                    x0, y0 = e['p']; x1, y1 = x0+e['w'], y0+e['h']
                    if x0 <= p[0] <= x1 and y0 <= p[1] <= y1: best, bi = 0, i
                elif e['type'] == 'text':
                    if math.dist(p, e['p']) < best: best, bi = math.dist(p, e['p']), i
            if bi >= 0:
                self.tree.selection_set((str(bi),))
                self.status.set(f'Выбран: {self._label(self.ents[bi])}')
            else:
                self.tree.selection_set(())

    def on_drag(self, ev):
        if not self.cur: return
        q = self.to_p(ev)
        t = self.cur['type']
        if t == 'line': self.cur['p2'] = q
        elif t == 'rect':
            x0, y0 = self.cur['p']; self.cur['w'] = q[0]-x0; self.cur['h'] = q[1]-y0; self.cur['q'] = q
        elif t == 'circle': self.cur['r'] = math.dist(q, self.cur['c'])
        elif t == 'dim_linear':
            dx, dy = q[0]-self.cur['p1'][0], q[1]-self.cur['p1'][1]
            self.cur['orient'] = 'h' if abs(dx) > abs(dy) else 'v'
            self.cur['p2'] = q
        self._redraw()

    def on_up(self, ev):
        if not self.cur: return
        t = self.cur['type']
        if t in ('line','circle') and (math.dist(self.cur['p1'] if t=='line' else self.cur['c'],
               self.cur['p2'] if t=='line' else self.to_p(ev)) < 1):
            self.cur = None; self._redraw(); return
        if t == 'rect' and (abs(self.cur['w']) < 1 or abs(self.cur['h']) < 1):
            self.cur = None; self._redraw(); return
        self.ents.append(self.cur); self.cur = None; self._redraw()
        self.status.set(f'{len(self.ents)} объектов на холсте')

    def on_move(self, ev):
        if self.cur: self._redraw()
        else: self.status.set(f"({self.to_p(ev)[0]:.1f}, {self.to_p(ev)[1]:.1f}) мм")

    def _cancel(self):
        if self.cur: self.cur = None; self._redraw()

    def _dist_to_line(self, p, a, b):
        ax, ay = a; bx, by = b; px, py = p
        dx, dy = bx-ax, by-ay
        if dx == dy == 0: return math.dist(p, a)
        t = max(0, min(1, ((px-ax)*dx + (py-ay)*dy)/(dx*dx+dy*dy)))
        return math.dist(p, (ax+t*dx, ay+t*dy))

    def clear(self):
        self.ents = []; self.cur = None; self._redraw(); self.status.set('Холст очищен')

    def delete_sel(self):
        ids = [int(i) for i in self.tree.selection() if i != 'cur']
        for i in sorted(set(ids), reverse=True):
            if 0 <= i < len(self.ents): del self.ents[i]
        self._redraw(); self.status.set(f'Удалено {len(ids)}')

    def edit_sel(self, _=None):
        iid = self.tree.focus()
        if not iid or iid == 'cur': return
        i = int(iid)
        if i >= len(self.ents): return
        e = self.ents[i]
        win = tk.Toplevel(self); win.title(f'Свойства #{i}')
        ttk.Label(win, text='Тип линии:').pack(anchor='w', padx=4)
        lt = ttk.Combobox(win, values=list(draw2d.LAYERS.keys()), state='readonly', textvariable=tk.StringVar(value=e.get('lt','main')))
        lt.pack(fill='x', padx=4)
        ttk.Label(win, text='Слой-алиас объекта:').pack(anchor='w', padx=4)
        ttk.Label(win, text=self._label(e)).pack(anchor='w', padx=4)
        def ok():
            e['lt'] = lt.get(); win.destroy(); self._redraw()
        ttk.Button(win, text='OK', command=ok).pack(pady=4)

    def to_json(self):
        if not self.ents:
            messagebox.showinfo('Пусто', 'Нет объектов — нарисуйте что-нибудь'); return
        spec = {
            'sheet': {'format': 'A4', 'orientation': 'landscape', 'frame': True,
                      'title_block': {'form': '1', 'code': 'ПН.000', 'name': 'Чертёж с холста',
                                      'author': '', 'group': '', 'scale': '1:1'}},
            'view': {'fit': 'auto', 'dim_margin': 15},
            'entities': self.ents,
        }
        base = os.path.join(EX, 'out_canvas')
        try:
            doc, meta = draw2d.build(spec)
            draw2d.export(doc, base + '.dxf')
            draw2d.preview(base + '.dxf', base + '_preview.png', size=(meta[0], meta[1]))
            self.status.set(f'Собрано -> {base}.dxf')
            messagebox.showinfo('OK', f'{base}.dxf\n{base}_preview.png')
        except Exception as ex:
            log(traceback.format_exc()); messagebox.showerror('Сборка', str(ex))

# ======================================================================
# Вкладка 3D: JSON -> STEP + виды
# ======================================================================
class Tab3D(ttk.Frame):
    def __init__(self, master, status):
        super().__init__(master)
        self.status = status
        top = ttk.Frame(self); top.pack(fill='x', padx=4, pady=2)
        ttk.Button(top, text='📂 Открыть JSON', command=self.open_json).pack(side='left')
        ttk.Button(top, text='💾 Сохранить', command=self.save_json).pack(side='left', padx=2)
        ttk.Button(top, text='▶ Собрать STEP + DXF', command=self.build).pack(side='left', padx=2)
        self.sample_btn = ttk.Menubutton(top, text='📄 Загрузить пример')
        m = tk.Menu(self.sample_btn, tearoff=0)
        for fn in ('sample_3d.json', 'bolt_3d.json', 'flange_3d.json'):
            m.add_command(label=fn, command=lambda f=fn: self.load_sample(f))
        self.sample_btn.config(menu=m); self.sample_btn.pack(side='left', padx=2)

        self.txt = tk.Text(self, undo=True, wrap='none', font=('Consolas', 10))
        self.txt.pack(fill='both', expand=True, padx=4, pady=2)
        bottom = ttk.Frame(self); bottom.pack(fill='x', padx=4, pady=2)
        ttk.Label(bottom, text='Выходной файл:').pack(side='left')
        self.out = tk.StringVar(value='part')
        ttk.Entry(bottom, textvariable=self.out, width=25).pack(side='left', padx=2)
        ttk.Checkbutton(bottom, text='PNG-превью видов', variable=tk.BooleanVar(value=True)).pack(side='left', padx=2)

    def open_json(self):
        p = filedialog.askopenfilename(filetypes=[('JSON', '*.json')], initialdir=EX)
        if not p: return
        self.txt.delete('1.0', 'end'); self.txt.insert('1.0', open(p, encoding='utf-8').read())
        self.status.set(f'Открыт {p}')

    def save_json(self):
        p = filedialog.asksaveasfilename(defaultextension='.json', filetypes=[('JSON', '*.json')], initialdir=EX)
        if not p: return
        open(p, 'w', encoding='utf-8').write(self.txt.get('1.0', 'end'))
        self.status.set(f'Сохранён {p}')

    def load_sample(self, name):
        p = res_path(name)
        if os.path.exists(p):
            self.txt.delete('1.0', 'end'); self.txt.insert('1.0', open(p, encoding='utf-8').read())
            self.status.set(f'Загружен пример {name}')
        else:
            self.status.set(f'Нет файла {p}')

    def build(self):
        try:
            spec = json.loads(self.txt.get('1.0', 'end'))
        except Exception as ex:
            messagebox.showerror('JSON', f'Ошибка парсинга JSON:\n{ex}'); return
        base = self.out.get().strip() or 'part'
        if not os.path.isabs(base): base = os.path.join(EX, base)
        try:
            res = draw3d.build(spec)
            res.val().exportStep(base + '.step')
            draw3d.export_views(res, base, preview=base + '_preview.png' if True else None)
            self.status.set(f'Собрано -> {base}.step, {base}_views.dxf')
            messagebox.showinfo('OK', f'{base}.step\n{base}_views.dxf')
        except Exception as ex:
            log(traceback.format_exc()); messagebox.showerror('Сборка', str(ex))

# ======================================================================
# Окно
# ======================================================================
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('PaintLauncher — 2D/3D чертёжное приложение')
        self.geometry('1100x700')
        self.status = StatusBar(self); self.status.pack(side='bottom', fill='x')

        nb = ttk.Notebook(self); nb.pack(fill='both', expand=True)
        nb.add(Tab2DJSON(nb, self.status), text='2D · JSON -> DXF')
        nb.add(Tab2DCanvas(nb, self.status), text='2D · Интерактивный холст')
        if HAS_3D:
            nb.add(Tab3D(nb, self.status), text='3D · JSON -> STEP + виды')
        else:
            f = ttk.Frame(nb)
            ttk.Label(f, text='3D-вкладка недоступна: не установлен пакет cadquery.\n'
                              'Установите его:  pip install cadquery',
                      justify='center', font=('', 11)).pack(expand=True)
            nb.add(f, text='3D · недоступно')

if __name__ == '__main__':
    App().mainloop()
