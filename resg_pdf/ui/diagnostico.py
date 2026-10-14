# -*- coding: utf-8 -*-
"""Estado del sistema: qué motores y conversores hay disponibles.

Ninguna herramienta de la app deja de funcionar por lo que falte aquí: lo
marcado como opcional solo añade funciones extra (fidelidad máxima de
conversión, OCR, PDF/A o traducción).
"""
from __future__ import annotations

import os

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (QApplication, QDialog, QFrame, QHBoxLayout,
                             QLabel, QPushButton, QScrollArea, QVBoxLayout,
                             QWidget)

from .. import __version__
from ..backend import tools as T


def informe():
    """Devuelve (filas, texto plano) con el estado de cada componente.

    Cada fila es ``(nombre, activo, detalle, ayuda, opcional)``.
    """
    env = T.estado_entorno()
    version = getattr(T.pymupdf, "__version__", "?")
    idiomas = T.idiomas_traduccion()
    filas = [
        ("Motor PDF (PyMuPDF)", True, f"versión {version}", "", False),
        ("PDF a Word (.docx)", bool(env["pdf2docx"]), "pdf2docx", "", False),
        ("PDF a PowerPoint (.pptx)", bool(env["python-pptx"]), "python-pptx",
         "", False),
        ("PDF a Excel (.xlsx)", bool(env["openpyxl"]), "openpyxl", "", False),
        ("Extracción de tablas", bool(env["pdfplumber"]), "pdfplumber",
         "", False),
        ("Escáner WIA (Windows)", bool(env["pywin32"]) and os.name == "nt",
         "pywin32", "pip install pywin32", True),
        ("Office a PDF con máxima fidelidad", bool(env["libreoffice"]),
         env["libreoffice"] or "LibreOffice no instalado",
         "https://es.libreoffice.org/descarga/", True),
        ("OCR (texto seleccionable)", bool(env["tesseract"]),
         env["tesseract"] or "Tesseract no instalado",
         "https://github.com/UB-Mannheim/tesseract/wiki", True),
        ("PDF/A (archivado)", bool(env["ghostscript"]),
         env["ghostscript"] or "Ghostscript no instalado",
         "https://www.ghostscript.com/releases/gsdnld.html", True),
        ("Traducción local", bool(env["argostranslate"]),
         ("argostranslate · " + ", ".join(idiomas)) if idiomas
         else ("argostranslate instalado" if env["argostranslate"]
               else "argostranslate no instalado"),
         "pip install argostranslate", True),
    ]
    lineas = [f"RESG PDF Studio v{__version__} · estado del sistema", ""]
    for nombre, activo, detalle, _ayuda, opcional in filas:
        estado = "OK " if activo else ("-- " if opcional else "NO ")
        lineas.append(f"[{estado}] {nombre} — {detalle}")
    return filas, "\n".join(lineas)


class DialogoEstado(QDialog):
    """Ventana compacta con el estado de cada componente."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Estado del sistema · RESG PDF Studio")
        self.setMinimumWidth(680)
        self._filas, self._texto = informe()

        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(20, 18, 20, 16)
        raiz.setSpacing(12)

        titulo = QLabel("Estado del sistema")
        titulo.setObjectName("pageTitulo")
        raiz.addWidget(titulo)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        cuerpo = QWidget()
        lista = QVBoxLayout(cuerpo)
        lista.setContentsMargins(0, 0, 6, 0)
        lista.setSpacing(8)
        for nombre, activo, detalle, ayuda, opcional in self._filas:
            lista.addWidget(self._fila(nombre, activo, detalle, ayuda, opcional))
        lista.addStretch(1)
        scroll.setWidget(cuerpo)
        raiz.addWidget(scroll, 1)

        botones = QHBoxLayout()
        btn_copiar = QPushButton("Copiar informe")
        btn_copiar.setObjectName("btnSecundario")
        btn_copiar.clicked.connect(self._copiar)
        botones.addWidget(btn_copiar)
        botones.addStretch(1)
        btn_cerrar = QPushButton("Cerrar")
        btn_cerrar.setObjectName("btnPrimario")
        btn_cerrar.clicked.connect(self.accept)
        botones.addWidget(btn_cerrar)
        raiz.addLayout(botones)

    def _fila(self, nombre, activo, detalle, ayuda, opcional):
        marco = QFrame()
        marco.setObjectName("filaEstado")
        lay = QHBoxLayout(marco)
        lay.setContentsMargins(14, 10, 12, 10)
        lay.setSpacing(12)

        etiqueta = QLabel(nombre)
        etiqueta.setObjectName("estadoNombre")
        etiqueta.setMinimumWidth(250)
        lay.addWidget(etiqueta)

        info = QLabel(detalle)
        info.setObjectName("estadoDetalle")
        info.setWordWrap(True)
        if ayuda and not activo:
            info.setText(f"{detalle} — <a href='{ayuda}'>cómo instalarlo</a>")
            info.setOpenExternalLinks(True)
            info.setTextFormat(Qt.TextFormat.RichText)
        lay.addWidget(info, 1)

        if activo:
            insignia = QLabel("Activo")
            insignia.setObjectName("badgeOk")
        elif opcional:
            insignia = QLabel("Opcional")
            insignia.setObjectName("badgeOpc")
        else:
            insignia = QLabel("No")
            insignia.setObjectName("badgeNo")
        lay.addWidget(insignia, 0, Qt.AlignmentFlag.AlignTop)
        return marco

    def _copiar(self):
        QApplication.clipboard().setText(self._texto)


def mostrar_estado(parent=None):
    DialogoEstado(parent).exec()
