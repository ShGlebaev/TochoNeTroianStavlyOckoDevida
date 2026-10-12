# -*- mode: python ; coding: utf-8 -*-
# Спецификация PyInstaller для PaintLauncher.
# Режим onedir (папка, а не один файл) — антивирусы реагируют на него спокойнее.
# Сборка:  pyinstaller PaintLauncher.spec

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

datas = []
# Примеры JSON и инструкции кладём рядом с приложением
for f in ('sample_2d.json', 'bracket_2d.json', 'gear_2d.json',
          'sample_3d.json', 'bolt_3d.json', 'flange_3d.json',
          'PROMPT.md', 'PROMPT3D.md', 'README_INSTRUCTIONS.md'):
    datas.append(('example/' + f, '.'))

hiddenimports = ['draw2d', 'ezdxf', 'matplotlib']

# cadquery/OCP — по желанию. Если он установлен, включаем 3D-вкладку.
# ВНИМАНИЕ: OCP (OpenCascade) добавляет сотни МБ и часто ломает сборку.
# Для лёгкого exe собери с переменной NO3D=1 — GUI сам отключит 3D-вкладку.
import os
try:
    import cadquery  # noqa
    if os.environ.get('NO3D'):
        raise ImportError('NO3D')
    hiddenimports += collect_submodules('cadquery') + collect_submodules('OCP')
    datas += collect_data_files('cadquery')
    WITH_3D = True
except ImportError:
    WITH_3D = False

a = Analysis(
    ['example/gui.py'],
    pathex=['example'],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=['PyQt5', 'PyQt6', 'PySide2', 'PySide6', 'IPython', 'notebook',
              'pytest', 'sphinx', 'pandas', 'scipy', 'sympy'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='PaintLauncher',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,                 # без UPX — меньше ложных срабатываний антивирусов
    console=False,             # GUI-приложение без консоли
    icon=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name='PaintLauncher',
)
