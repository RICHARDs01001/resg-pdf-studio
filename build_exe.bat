@echo off
rem ---------------------------------------------------------------
rem  RESG PDF Studio - generar dist\RESG-PDF-Studio.exe (Windows)
rem ---------------------------------------------------------------
cd /d "%~dp0"

echo === 1/4  Instalando dependencias ===
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install pyinstaller

echo === 2/4  Pruebas del backend ===
python tools\selftest.py
if errorlevel 1 (
    echo Las pruebas del backend han fallado. Se cancela el empaquetado.
    pause
    exit /b 1
)

echo === 3/4  Pruebas de interfaz ===
python tools\gui_smoke.py
if errorlevel 1 (
    echo Las pruebas de interfaz han fallado. Se cancela el empaquetado.
    pause
    exit /b 1
)

echo === 4/4  Generando el ejecutable ===
python -m PyInstaller resg_pdf_studio.spec --clean --noconfirm
if errorlevel 1 (
    echo No se pudo generar el ejecutable.
    pause
    exit /b 1
)

echo.
echo Listo: dist\RESG-PDF-Studio.exe
pause
