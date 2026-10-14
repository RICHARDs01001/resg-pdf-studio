# Cómo compilar y publicar

## Requisitos

- Python 3.10 o superior (probado con 3.12/3.13).
- Windows para generar el `.exe` (en Linux/macOS se puede desarrollar y probar,
  pero el ejecutable de Windows se crea en Windows).

```bash
pip install -r requirements-dev.txt
```

## Generar el ejecutable

```bash
python build_exe.py
```

Equivale a:

```bash
python -m pip install -r requirements.txt
python -m pip install pyinstaller
python -m PyInstaller resg_pdf_studio.spec --clean --noconfirm
```

El resultado es **un único archivo**: `dist/RESG-PDF-Studio.exe`
(≈ 205 MB porque incluye Python y los motores de conversión, OCR y comparación).

En Windows también existe `build_exe.bat`, que además ejecuta las pruebas antes
de empaquetar.

## Probar el ejecutable sin pantalla

```bash
set QT_QPA_PLATFORM=offscreen
dist\RESG-PDF-Studio.exe
```

Si arranca y se mantiene vivo unos segundos sin errores, el empaquetado está
correcto (incluye los recursos y el plugin «offscreen» de Qt).

## ¿Se puede reducir el tamaño?

Sí. En `resg_pdf_studio.spec` se pueden descartar paquetes que se cuelan como
dependencias de `pdf2docx`/`pdfplumber`:

```python
excludes=["tkinter", "PyQt5", "PySide2", "PySide6",
          "pygame", "matplotlib", "scipy", "pandas", "pytest"],
```

Mantén **OpenCV** (`cv2`): `pdf2docx` lo necesita. Después de cualquier cambio
en el `.spec`, vuelve a ejecutar las pruebas y arranca el `.exe` una vez para
comprobar que todo sigue funcionando.

## Publicar una versión

1. Actualiza `__version__` en `resg_pdf/__init__.py` y apunta los cambios en
   `CHANGELOG.md`.
2. Ejecuta las pruebas (`tools/selftest.py` y `tools/gui_smoke.py`).
3. Etiqueta la versión:

   ```bash
   git tag v1.1.0
   git push origin v1.1.0
   ```

4. El flujo de trabajo `.github/workflows/build.yml` compila el `.exe`, lo
   adjunta a la release de GitHub y publica también los artefactos.

## Crear la carpeta limpia para GitHub

```bash
python tools/preparar_github.py
```

Copia el proyecto sin `build/`, `dist/`, registros ni archivos temporales a
`..\RESG-PDF-Studio-GitHub`, listo para `git init` y `git push`.

## Iconos

Los iconos de las herramientas se generan por código:

```bash
python tools/generate_icons.py            # todos (96x96)
python tools/generate_icons.py --nuevos   # solo los que falten
```

Funciona en Linux, Windows y macOS (busca la fuente disponible en el sistema).
