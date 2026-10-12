# PaintLauncher — чертёжное приложение (2D + 3D)

Приложение для генерации чертежей и 3D-моделей из JSON-описаний.

## Состав

| Файл | Назначение |
|------|-----------|
| `draw2d.py` | JSON → DXF (2D-чертёж: лист, рамка, основная надпись, размеры, штриховки) |
| `draw3d.py` | JSON → STEP + три вида в DXF (3D-моделирование через CadQuery) |
| `gui.py` | GUI (Tkinter): редактор JSON, интерактивный холст 2D, вкладка 3D |
| `PROMPT.md` | Схема JSON для 2D (скармливать LLM со скриншотом чертежа) |
| `PROMPT3D.md` | Схема JSON для 3D (скармливать LLM с описанием детали) |
| `sample_*.json`, `bracket_2d.json`, `gear_2d.json`, `bolt_3d.json`, `flange_3d.json` | Готовые примеры |

## Установка

```bash
python3 -m venv .venv
.venv/bin/pip install ezdxf matplotlib cadquery
```

## Запуск

### GUI

```bash
.venv/bin/python example/gui.py
```

Три вкладки:
1. **2D · JSON → DXF** — редактор JSON с кнопками «Открыть/Сохранить/Собрать/Примеры».
2. **2D · Интерактивный холст** — рисование примитивов мышью (линия, прямоугольник,
   окружность, текст, размер), дерево объектов, кнопка «Собрать JSON → DXF».
3. **3D · JSON → STEP + виды** — редактор JSON, сборка в STEP и три вида DXF.

### Командная строка

```bash
# 2D
.venv/bin/python example/draw2d.py example/sample_2d.json -o out --preview

# 3D
.venv/bin/python example/draw3d.py example/sample_3d.json -o part --preview
```

## Как это работает

1. **Опиши чертёж/деталь** словами или картинкой → попроси LLM сгенерировать JSON
   по схеме из `PROMPT.md` (2D) или `PROMPT3D.md` (3D).
2. **Положи JSON** в `example/` и загрузи его в GUI (или передай в CLI).
3. **Собери** — получишь DXF (2D) или STEP + DXF видов (3D).
4. **Открой DXF** в КОМПАСе/AutoCAD, STEP — в любом CAD.

## API (для интеграции)

```python
import draw2d, draw3d

# 2D
doc, meta = draw2d.build(spec)          # ezdxf-документ
draw2d.export(doc, 'out.dxf')           # сохранить
draw2d.preview('out.dxf', 'out.png')    # PNG-превью

# 3D
res = draw3d.build(spec)                # cadquery Workplane
res.val().exportStep('part.step')
draw3d.export_views(res, 'part', preview='part_preview.png')
```
