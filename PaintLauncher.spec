# -*- mode: python ; coding: utf-8 -*-
# Спецификация PyInstaller для PaintLauncher.
# Режим onedir (папка, а не один файл) — антивирусы реагируют на него спокойнее.
# Сборка:  pyinstaller PaintLauncher.spec

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

datas = []
# Примеры JSON и инструкции кладём рядом с приложением.
# Путь относительно корня репозитория (где лежит .spec файл).
import glob, os as _os
for pat in ('example/*.json', 'example/*.md'):
    for f in glob.glob(pat):
        datas.append((f, '.'))

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
