# -*- coding: utf-8 -*-
"""Comprueba los arreglos sin abrir ventanas de verdad.

Uso:  python tools/verificar_arreglos.py
"""
import os
import sys
import tempfile
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

import pymupdf  # noqa: E402
from PyQt6.QtCore import QEvent, QEventLoop, QMimeData, QPoint, QPointF  # noqa: E402
from PyQt6.QtCore import Qt  # noqa: E402
from PyQt6.QtGui import QDropEvent, QMouseEvent, QWheelEvent  # noqa: E402
from PyQt6.QtWidgets import QApplication, QGraphicsItem  # noqa: E402

from resg_pdf.ui import widgets as W  # noqa: E402
from resg_pdf.ui.main_window import MainWindow  # noqa: E402
from resg_pdf.ui.styles import QSS  # noqa: E402

TMP = tempfile.mkdtemp(prefix="resg_verifica_")
BIEN, MAL = [], []


def log(nombre, correcto, extra=""):
    print(f"{'[ OK ]' if correcto else '[FALLO]'} {nombre:<42} {extra}",
          flush=True)
    (BIEN if correcto else MAL).append(nombre)


def pdf(ruta, texto, paginas=1):
    doc = pymupdf.open()
    for i in range(paginas):
        doc.new_page().insert_text((72, 96), f"{texto} {i + 1}", fontsize=16)
    doc.save(ruta)
    doc.close()
    return ruta


def bombear(app, ms=800):
    fin = time.time() + ms / 1000
    while time.time() < fin:
        app.processEvents(QEventLoop.ProcessEventsFlag.AllEvents, 20)
        time.sleep(0.01)


def soltar(punto):
    return QDropEvent(QPointF(punto), Qt.DropAction.MoveAction,
                      QMimeData(), Qt.MouseButton.LeftButton,
                      Qt.KeyboardModifier.NoModifier)


def main():                                                    # noqa: C901
    app = QApplication([])
    app.setStyleSheet(QSS)
    win = MainWindow()
    win.resize(1400, 900)
    win.show()
    app.processEvents()

    # --------------------------------------------- 1 · arranque diferido
    log("La parrilla se monta tras mostrar la ventana",
        len(win.home.tarjetas) > 0, f"{len(win.home.tarjetas)} tarjetas")

    # --------------------------------------------- 2 · caché de documentos
    a = pdf(os.path.join(TMP, "a.pdf"), "Documento A", 3)
    b = pdf(os.path.join(TMP, "b.pdf"), "Documento B", 1)
    log("El PDF se abre una sola vez (caché)",
        W._doc_de(a) is W._doc_de(a), "mismo objeto PyMuPDF")
    img = W._render_miniatura(a, 2, 0, 168, 224)
    log("La miniatura sale entera y sin recortes",
        not img.isNull() and img.width() <= 168 and img.height() <= 224,
        f"{img.width()}x{img.height()} px")

    # --------------------------------------------- 3 · arrastre con el ratón
    win.abrir_tool("unir")
    vista = win._paginas["unir"].archivos
    vista.add_files([a, b])
    bombear(app)
    lista = vista.lista
    lista.resize(1000, 620)
    bombear(app, 300)
    log("Se ven las 4 páginas de los 2 archivos",
        vista.paginas_totales() == 4, f"{vista.paginas_totales()} páginas")

    rect0 = lista.visualItemRect(lista.item(0))
    log("La lista está maquetada", rect0.isValid() and rect0.width() > 0,
        f"rect={rect0.x()},{rect0.y()},{rect0.width()}x{rect0.height()}")

    lista.clearSelection()
    lista.item(lista.count() - 1).setSelected(True)
    lista.dropEvent(soltar(lista.visualItemRect(lista.item(0)).center()))
    app.processEvents()
    log("Arrastrar la última la pone la primera",
        vista.plan() and vista.plan()[0]["file"] == b,
        os.path.basename(vista.plan()[0]["file"]))

    # --------------------------------------------- 4 · editor: ratón libre
    win.abrir_tool("editar")
    editor = win._paginas["editar"].editor
    log("El editor abre el PDF", editor.cargar(a) and editor.abierto(), "")
    bombear(app, 300)
    editor.anadir_texto()
    editor.anadir_forma("rectangulo")
    log("Se añaden elementos", len(editor.elementos()) == 2,
        f"{len(editor.elementos())} elementos")
    log("El texto no entra en modo edición al pulsarlo",
        editor._elementos[0]["item"].textInteractionFlags()
        == Qt.TextInteractionFlag.NoTextInteraction, "")
    log("El elemento se puede arrastrar con el ratón",
        bool(editor._elementos[0]["item"].flags()
             & QGraphicsItem.GraphicsItemFlag.ItemIsMovable), "")

    lienzo = editor.lienzo
    centro = QPointF(lienzo.viewport().rect().center())
    try:
        lienzo.wheelEvent(QWheelEvent(
            centro, QPointF(lienzo.viewport().mapToGlobal(centro.toPoint())),
            QPoint(0, 0), QPoint(0, 120), Qt.MouseButton.NoButton,
            Qt.KeyboardModifier.ControlModifier, Qt.ScrollPhase.NoScrollPhase,
            False))
        ok_zoom = lienzo._zoom > 1.0
    except Exception as e:  # noqa: BLE001
        ok_zoom = False
        print("   zoom:", type(e).__name__, e)
    log("Ctrl + rueda acerca la página", ok_zoom, f"zoom={lienzo._zoom:.2f}")

    try:
        lienzo.mousePressEvent(QMouseEvent(
            QEvent.Type.MouseButtonPress, QPointF(30, 30),
            Qt.MouseButton.MiddleButton, Qt.MouseButton.MiddleButton,
            Qt.KeyboardModifier.NoModifier))
        ok_pan = lienzo.dragMode().name == "ScrollHandDrag"
        lienzo.mouseReleaseEvent(QMouseEvent(
            QEvent.Type.MouseButtonRelease, QPointF(30, 30),
            Qt.MouseButton.MiddleButton, Qt.MouseButton.NoButton,
            Qt.KeyboardModifier.NoModifier))
        ok_pan = ok_pan and lienzo.dragMode().name == "RubberBandDrag"
    except Exception as e:  # noqa: BLE001
        ok_pan = False
        print("   pan:", type(e).__name__, e)
    log("El botón central arrastra y se restaura", ok_pan,
        lienzo.dragMode().name)

    editor.lienzo.resetear_zoom()
    log("Al cerrar el PDF el zoom vuelve a 1", lienzo._zoom == 1.0, "")

    print("-" * 60)
    print(f"CORRECTOS: {len(BIEN)}    FALLOS: {len(MAL)}")
    for nombre in MAL:
        print("  FALLO ->", nombre)
    win.close()          # detiene los hilos de miniaturas
    app.processEvents()
    return 1 if MAL else 0


if __name__ == "__main__":
    sys.exit(main())

