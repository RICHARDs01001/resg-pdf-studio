@echo off
rem ---------------------------------------------------------------
rem  RESG PDF Studio - instalar dependencias (Windows)
rem ---------------------------------------------------------------
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
    echo No se encontro Python. Instalalo desde https://www.python.org
    pause
    exit /b 1
)

python -m pip install --upgrade pip
python -m pip install -r requirements.txt

echo.
echo Listo. Ya puedes ejecutar la aplicacion con run.bat
pause
