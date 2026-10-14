# -*- mode: python ; coding: utf-8 -*-
"""Spec de PyInstaller para RESG PDF Studio (un solo .exe).

Generar el ejecutable:
    pip install pyinstaller
    pyinstaller resg_pdf_studio.spec
El .exe queda en dist/RESG-PDF-Studio.exe
"""

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=[],
    datas=[("assets", "assets")],
    hiddenimports=[
        "pymupdf",
        "pypdf",
        "pdf2docx",
        "pdfplumber",
        "pptx",
        "openpyxl",
        "PIL",
        "numpy",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "PyQt5", "PySide2", "PySide6"],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="RESG-PDF-Studio",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    runtime_tmpdir=None,
    console=False,                 # aplicación de ventana, sin consola
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="assets/icono.ico",
)
