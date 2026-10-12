@echo off
REM ============================================================
REM  Сборка PaintLauncher.exe для Windows (одной командой)
REM  Требуется: Python 3.10+ с pip. Запускать из корня проекта.
REM  Результат: dist\PaintLauncher\PaintLauncher.exe
REM ============================================================
setlocal enabledelayedexpansion

cd /d "%~dp0"

echo [1/4] Создание/обновление виртуального окружения...
if not exist ".venv-win" (
    python -m venv .venv-win || (echo ОШИБКА: не удалось создать venv. Установи Python с python.org && pause && exit /b 1)
)
call .venv-win\Scripts\activate.bat

echo [2/4] Установка зависимостей...
pip install --upgrade pip -q
pip install -r requirements.txt -q || (echo ОШИБКА: не удалось установить зависимости && pause && exit /b 1)

echo [3/4] Сборка PyInstaller...
REM Собрать лёгкий exe БЕЗ 3D (если нужен только 2D): set NO3D=1
pyinstaller --clean --noconfirm PaintLauncher.spec || (echo ОШИБКА: сборка не удалась && pause && exit /b 1)

echo [4/4] Готово!
echo.
echo Результат: dist\PaintLauncher\PaintLauncher.exe
echo Для распространения запакуй папку dist\PaintLauncher в zip.
echo.
pause
