@echo off
rem ---------------------------------------------------------------
rem  RESG PDF Studio - ejecutar desde el codigo fuente (Windows)
rem ---------------------------------------------------------------
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
    echo No se encontro Python. Instalalo desde https://www.python.org
    pause
    exit /b 1
)

python -c "import PyQt6" >nul 2>nul
if errorlevel 1 (
    echo Instalando dependencias por primera vez...
    python -m pip install --upgrade pip
    python -m pip install -r requirements.txt
)

python main.py
if errorlevel 1 pause
