# PROMPT.md — схема JSON для draw2d.py (2D-чертёж → DXF)

Этот файл скармливай LLM вместе со скриншотом/описанием чертежа — она вернёт JSON,
который `draw2d.py` соберёт в DXF для КОМПАСа.

## Запуск

```bash
python draw2d.py part.json -o part --preview   # part.dxf + part_preview.png
```

## Структура JSON

```jsonc
{
  "sheet": {                       // лист (необязательно, по умолчанию A4 portrait)
    "format": "A4",                // A4 | A3 | A2 | A1
    "orientation": "landscape",    // portrait | landscape
    "frame": true,                 // рамка (20/5 мм)
    "title_block": {               // основная надпись
      "form": "1",                 // "1" | "2" | "2a" | null (без надписи)
      "code": "ПН.001", "name": "Деталь",
      "author": "Иванов", "group": "У", "scale": "1:1", "sheet": 1
    }
  },
  "view": {                        // как размещать entities на листе
    "fit": "auto",                 // "auto" (вписать) | "shrink" (вписать, но не увеличивать) | "none"
    "dim_margin": 15,              // отступ от рамки, мм (для fit)
    "y_down": false,               // true, если координаты Y вниз (экранная СК)
    "origin": [0, 0],              // смещение (для fit=none)
    "scale": 1.0                   // масштаб (для fit=none)
  },
  "entities": [ ... ]              // список примитивов (см. ниже)
}
```

## Типы линий (`lt`)

`main` (жирная сплошная), `thin` (тонкая), `dashed` (штриховая), `center` (осевая),
`dashdot` (штрихпунктир), `thick`, `thick_dashed`, `thick_dashdot`, `dim` (размерные).

## Примитивы (`entities`)

| type | поля | описание |
|------|------|----------|
| `line` | `p1`, `p2`, `lt` | отрезок |
| `rect` | `p` (левый-нижний), `w`, `h`, `lt` | прямоугольник |
| `polyline` | `pts` [[x,y],…], `closed`, `lt` | ломаная |
| `circle` | `c` (центр), `r`, `lt` | окружность |
| `arc` | `c`, `r`, `a1`, `a2` (град.), `lt` | дуга |
| `ellipse` | `c`, `rx`, `ry`, `rot`, `a1`, `a2`, `lt` | эллипс/дуга |
| `spline` | `pts`, `lt` | сплайн через точки |
| `text` | `p`, `text`, `h` (высота), `align` (left/center/right/bl/bc/br), `rot`, `lt` | надпись |
| `hatch` | `boundary` [[x,y],…], `holes`, `pattern` (ANSI31…), `scale`, `angle` | штриховка |
| `dim_linear` | `p1`, `p2`, `orient` (h/v/al), `offset`, `text` | линейный размер |
| `dim_radius` | `c`, `r`, `angle`, `text` | радиус R… |
| `dim_diameter` | `c`, `r`, `angle`, `text` | диаметр Ø… |
| `dim_angle` | `c`, `p1`, `p2`, `r`, `text` | угловой размер |
| `leader` | `pts` (остриё → полка), `text`, `h` | выноска |
| `table` | `p` (левый-верхний, **мм листа, без view-преобразования**), `col_w`, `row_h`, `rows` | таблица |

## Пример минимального чертежа

```json
{
  "sheet": {"format": "A4", "orientation": "landscape", "frame": true,
            "title_block": {"form": "1", "code": "ПН.001", "name": "Пластина"}},
  "view": {"fit": "auto"},
  "entities": [
    {"type": "rect", "p": [0,0], "w": 120, "h": 80, "lt": "main"},
    {"type": "circle", "c": [30,40], "r": 8, "lt": "main"},
    {"type": "dim_linear", "p1": [0,0], "p2": [120,0], "orient": "h", "offset": -12},
    {"type": "dim_diameter", "c": [30,40], "r": 8, "angle": 45}
  ]
}
```

Готовые примеры: `sample_2d.json`, `bracket_2d.json`, `gear_2d.json`.
