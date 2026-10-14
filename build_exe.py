# -*- coding: utf-8 -*-
"""Genera el .exe de RESG PDF Studio con un solo comando:

    python build_exe.py

Equivale a: pyinstaller resg_pdf_studio.spec --clean --noconfirm
El resultado queda en dist/RESG-PDF-Studio.exe
"""
import subprocess
import sys

subprocess.check_call([sys.executable, "-m", "pip", "install", "-r",
                       "requirements.txt"])
subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
subprocess.check_call([sys.executable, "-m", "PyInstaller",
                       "resg_pdf_studio.spec", "--clean", "--noconfirm"])
print("\nListo: dist/RESG-PDF-Studio.exe")
