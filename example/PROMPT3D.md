# PROMPT3D.md — схема JSON для draw3d.py (3D-модель → STEP + виды в DXF)

Этот файл скармливай LLM вместе с описанием детали — она вернёт JSON,
который `draw3d.py` соберёт в STEP и три вида в DXF (для КОМПАСа).

## Запуск

```bash
python draw3d.py part.json -o part --preview   # part.step, part_views.dxf, part_preview.png
```

## Оси

X, Y — в плоскости листа/детали, Z — «вверх» (высота/толщина), если не указано иное.

## Структура JSON

```jsonc
{
  "ops": [ ... ]   // упорядоченный список операций; результат накапливается
}
```

Каждая операция — объект с полем `"op"`. Общие поля:
- `"cut": true` — вычитать из накопленного тела (по умолчанию объединение).

## Операции

| op | поля | описание |
|----|------|----------|
| `box` | `w`, `l`, `h`, `at` [x,y,z], `centered` (true), `rotate` [{axis,deg}], `cut` | параллелепипед |
| `cylinder` | `d`, `h`, `at`, `rotate`, `cut` | цилиндр |
| `extrude_sketch` | `pts` [[x,y],…], `h`, `plane` (XY…), `at`, `cut` | выдавливание эскиза |
| `revolve` | `profile` [[axial, radius],…], `axis` (X/Y/Z), `angle` (360), `move`, `cut` | вращение |
| `hole` | `d`, `center` [a,b], `axis` (Z), `through` (true) \| `depth` | одно отверстие |
| `hole_pattern_circular` | `d`, `count`, `bolt_circle_d`, `center`, `start_angle`, `axis` | отверстия по окружности |
| `hole_pattern_linear` | `d`, `count`, `pitch`, `center`, `dir` [u,v], `axis` | отверстия в ряд |
| `cut_prism_through` | `shape` (square/rect), `size` \| `w`,`l`, `center`, `axis`, `rot` | сквозной вырез призмой |
| `fillet` | `r`, `sel` | скругление рёбер |
| `chamfer` | `r`, `sel` | фаска |
| `mirror_union` | `plane` (XZ…) | зеркальное объединение |

### Селекторы рёбер (`sel` для fillet/chamfer)

`all` | `vertical` (|Z) | `horizontal` (#Z) | `top` (>Z) | `bottom` (<Z) | произвольный CQ-селектор строкой.

## Пример минимальной детали

```json
{
  "ops": [
    {"op": "box", "w": 80, "l": 60, "h": 20, "at": [-40, -30, 0]},
    {"op": "hole", "d": 10, "center": [-25, -15], "axis": "Z", "through": true},
    {"op": "hole", "d": 10, "center": [25, 15], "axis": "Z", "through": true},
    {"op": "fillet", "r": 5, "sel": "vertical"},
    {"op": "chamfer", "r": 1.5, "sel": "top"}
  ]
}
```

Готовые примеры: `sample_3d.json`, `bolt_3d.json`, `flange_3d.json`.

## Выход

- `part.step` — 3D-модель;
- `part_views.dxf` — три вида (спереди/сверху/слева, ГОСТ 2.305, первый угол),
  невидимые линии — штриховые, слои `vis`/`hid`/`ctr`;
- `part_preview.png` — при `--preview`.
