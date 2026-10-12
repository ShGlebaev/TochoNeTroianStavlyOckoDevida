#!/usr/bin/env bash
# ============================================================
# Сборка PaintLauncher для Linux (из корня проекта).
# Результат: dist/PaintLauncher/PaintLauncher
# ============================================================
set -e
cd "$(dirname "$0")"

echo "[1/4] Создание/обновление виртуального окружения..."
python3 -m venv .venv

echo "[2/4] Установка зависимостей..."
.venv/bin/pip install --upgrade pip -q
.venv/bin/pip install -r requirements.txt -q

echo "[3/4] Сборка PyInstaller..."
# Лёгкий бинарник без 3D: NO3D=1 ./build.sh
pyinstaller() { .venv/bin/pyinstaller "$@"; }
pyinstaller --clean --noconfirm PaintLauncher.spec

echo "[4/4] Готово!"
echo "Результат: dist/PaintLauncher/PaintLauncher"
echo "Для распространения запакуй папку dist/PaintLauncher."
