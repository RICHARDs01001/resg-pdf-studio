# -*- coding: utf-8 -*-
"""Mide cuánto tarda cada etapa del arranque (para optimizar la apertura).

Uso:  python tools/medir_arranque.py
"""
import os
import sys
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

marcas = []
t0 = time.perf_counter()


def marca(nombre):
    marcas.append((nombre, (time.perf_counter() - t0) * 1000))


import PyQt6.QtWidgets  # noqa: E402
marca("PyQt6.QtWidgets")

from PyQt6.QtWidgets import QApplication  # noqa: E402
app = QApplication([])
marca("QApplication()")

import pymupdf  # noqa: E402
marca("pymupdf")

import resg_pdf.ui.styles  # noqa: E402
app.setStyleSheet(resg_pdf.ui.styles.QSS)
marca("styles + setStyleSheet")

import resg_pdf.ui.registry  # noqa: E402
marca("registry (backend tools)")

import resg_pdf.ui.pages  # noqa: E402
marca("pages (editor + preview)")

import resg_pdf.ui.main_window  # noqa: E402
marca("main_window")

ventana = resg_pdf.ui.main_window.MainWindow()
marca("MainWindow() construida")

ventana.show()
marca("show()")

anterior = 0.0
for nombre, ms in marcas:
    print(f"{nombre:28s} {ms - anterior:8.0f} ms   (acumulado {ms:7.0f} ms)")
    anterior = ms
print("-" * 58)
print(f"{'TOTAL hasta ver la ventana':28s} {marcas[-1][1]:8.0f} ms")
