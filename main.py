# -*- coding: utf-8 -*-
"""RESG PDF Studio — punto de entrada.

Ejecutar en desarrollo:   python main.py
"""
import os
import sys

from PyQt6.QtWidgets import QApplication

from resg_pdf.ui.main_window import MainWindow
from resg_pdf.ui.styles import QSS

# En el .exe empaquetado sin consola (console=False) sys.stdout y sys.stderr
# valen None. Algunas librerías (pdf2docx, pymupdf) escriben en ellos, por lo
# que se les da un sumidero para que nunca hagan fallar la aplicación.
for _nombre in ("stdout", "stderr"):
    if getattr(sys, _nombre, None) is None:
        try:
            setattr(sys, _nombre,
                    open(os.devnull, "w", encoding="utf-8"))
        except OSError:
            pass


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("RESG PDF Studio")
    app.setOrganizationName("RESG-tech")
    app.setStyleSheet(QSS)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
