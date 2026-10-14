# -*- coding: utf-8 -*-
"""Vista de miniaturas de las páginas con reorganización libre.

Es la pieza que permite «ver» los archivos al subirlos y decidir su orden:
las páginas se arrastran con el ratón a la posición que quieras, se pueden
girar, duplicar, marcar y quitar. No hay límite de páginas ni de archivos.
"""
from __future__ import annotations

import os

import pymupdf
from PyQt6.QtCore import QSize, Qt, pyqtSignal
from PyQt6.QtGui import QIcon, QPixmap, QTransform
from PyQt6.QtWidgets import (QFileDialog, QHBoxLayout, QLabel, QListWidget,
                             QListWidgetItem, QPushButton, QVBoxLayout,
                             QWidget)

from .widgets import CargadorMiniaturas, ZonaSoltar, cerrar_documentos

# Roles de datos guardados en cada miniatura
ROL_RUTA = Qt.ItemDataRole.UserRole
ROL_PAGINA = Qt.ItemDataRole.UserRole + 1
ROL_ROT = Qt.ItemDataRole.UserRole + 2
ROL_CLAVE = Qt.ItemDataRole.UserRole + 3
ROL_TIPO = Qt.ItemDataRole.UserRole + 4

LOTE = 300          # páginas que se dibujan de golpe (el resto, a un clic)

# Tamaño de las miniaturas: más grandes = se ve la página completa y nítida.
ANCHO_MINI = 168
ALTO_MINI = 224


def _paginas_de(ruta):
    """Número de páginas de un PDF o 1 si es una imagen."""
    doc = pymupdf.open(ruta)
    try:
        return max(1, doc.page_count)
    finally:
        doc.close()


class VistaMiniaturas(QListWidget):
    """Lista en modo icono que permite mover las páginas arrastrándolas."""

    reordenado = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("thumbList")
        self.setViewMode(QListWidget.ViewMode.IconMode)
        self.setMovement(QListWidget.Movement.Snap)
        self.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.setFlow(QListWidget.Flow.LeftToRight)
        self.setWrapping(True)
        self.setSpacing(2)
        self.setIconSize(QSize(ANCHO_MINI, ALTO_MINI))
        self.setGridSize(QSize(ANCHO_MINI + 28, ALTO_MINI + 42))
        # False: fijándolo, las páginas con otra proporción se recortaban y no
        # se veían enteras en la miniatura.
        self.setUniformItemSizes(False)
        self.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setDragDropMode(QListWidget.DragDropMode.InternalMove)
        self.setVerticalScrollMode(QListWidget.ScrollMode.ScrollPerPixel)
        self.setAutoScroll(True)
        self.setAutoScrollMargin(48)

    def dropEvent(self, evento):
        """Reordena las miniaturas moviéndolas a la posición donde se sueltan."""
        punto = evento.position().toPoint()
        indice = self.indexAt(punto)
        if indice.isValid():
            caja = self.visualRect(indice)
            # Soltando en la mitad derecha se coloca DESPUÉS de esa página;
            # soltando en la mitad izquierda, justo antes.
            destino = indice.row() + (1 if punto.x() > caja.center().x() else 0)
        else:
            destino = self.count()
        if not self.mover_seleccion_a(destino):
            evento.ignore()
            return
        evento.acceptProposedAction()

    def mover_seleccion_a(self, destino):
        """Mueve las miniaturas seleccionadas a la posición ``destino``.

        Devuelve True si se movió algo. Es la lógica que usa el arrastre con el
        ratón (el usuario arrastra las páginas para cambiar el orden).
        """
        origen = sorted(i.row() for i in self.selectedIndexes())
        if not origen:
            return False
        destino = max(0, min(self.count(), int(destino)))
        items = [self.takeItem(fila) for fila in reversed(origen)]
        items.reverse()
        destino -= sum(1 for fila in origen if fila < destino)
        for item in items:
            self.insertItem(max(0, destino), item)
            item.setSelected(True)
            destino += 1
        self.reordenado.emit()
        return True

    def sumar_seleccion(self, delta):
        """Mueve la selección ``delta`` posiciones (atajos de teclado)."""
        filas = sorted(i.row() for i in self.selectedIndexes())
        if not filas:
            return
        if delta > 0:
            for fila in reversed(filas):
                if fila + 1 < self.count():
                    item = self.takeItem(fila)
                    self.insertItem(fila + 1, item)
                    item.setSelected(True)
        else:
            for fila in filas:
                if fila - 1 >= 0:
                    item = self.takeItem(fila)
                    self.insertItem(fila - 1, item)
                    item.setSelected(True)
        self.reordenado.emit()


class VistaPrevia(QWidget):
    """Miniaturas de las páginas + herramientas para organizarlas.

    Mantiene la misma interfaz que ``FileListWidget`` (``add_files``,
    ``files``, ``changed`` y ``clear``) para que las páginas de herramienta
    puedan usar una u otra sin cambiar nada.
    """

    changed = pyqtSignal()

    def __init__(self, filtro, multiple, parent=None):
        super().__init__(parent)
        self.filtro, self.multiple = filtro, multiple
        self._pendientes = []
        self._por_clave = {}
        self._item_mas = None
        self._silencioso = False
        self.setAcceptDrops(True)

        self._cargador = CargadorMiniaturas(ANCHO_MINI, ALTO_MINI, self)
        self._cargador.listo.connect(self._miniatura_lista)
        self._cargador.start()

        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(0, 0, 0, 0)
        raiz.setSpacing(10)

        raiz.addWidget(self._construir_barra())

        self.zona = ZonaSoltar(filtro, multiple)
        self.zona.archivos.connect(self.add_files)
        raiz.addWidget(self.zona)

        self.lista = VistaMiniaturas()
        self.lista.setVisible(False)
        self.lista.reordenado.connect(self._tras_reordenar)
        self.lista.itemClicked.connect(self._al_pulsar_item)
        self.lista.itemChanged.connect(self._item_cambiado)
        raiz.addWidget(self.lista, 1)
        self._mostrar_lista(False)

    # ----------------------------------------------------------- barra
    def _construir_barra(self):
        barra = QWidget()
        lay = QVBoxLayout(barra)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)

        fila1 = QHBoxLayout()
        fila1.setSpacing(8)
        self.btn_add = QPushButton("Añadir archivos")
        self.btn_add.setObjectName("btnSecundario")
        self.btn_add.clicked.connect(self._elegir)
        fila1.addWidget(self.btn_add)

        self.btn_todo = QPushButton("Quitar todo")
        self.btn_todo.setObjectName("btnSecundario")
        self.btn_todo.clicked.connect(self.clear)
        fila1.addWidget(self.btn_todo)
        fila1.addStretch(1)

        self.lbl_cuenta = QLabel("")
        self.lbl_cuenta.setObjectName("estado")
        fila1.addWidget(self.lbl_cuenta)
        lay.addLayout(fila1)

        fila2 = QHBoxLayout()
        fila2.setSpacing(6)
        acciones = (
            ("↺  Girar izq.", lambda: self.girar(-90),
             "Gira 90° a la izquierda las páginas seleccionadas"),
            ("↻  Girar der.", lambda: self.girar(90),
             "Gira 90° a la derecha las páginas seleccionadas"),
            ("Duplicar", self.duplicar_seleccion,
             "Copia las páginas seleccionadas justo después"),
            ("◀  Mover", lambda: self.lista.sumar_seleccion(-1),
             "Mueve las páginas seleccionadas una posición a la izquierda"),
            ("▶  Mover", lambda: self.lista.sumar_seleccion(1),
             "Mueve las páginas seleccionadas una posición a la derecha"),
            ("Quitar", self.quitar_seleccion,
             "Elimina las páginas seleccionadas de la lista"),
            ("Marcar todo", lambda: self.marcar_todo(True),
             "Incluye todas las páginas en el resultado"),
            ("Desmarcar todo", lambda: self.marcar_todo(False),
             "Excluye todas las páginas (útil con «Extraer» o «Eliminar»)"),
        )
        for texto, accion, ayuda in acciones:
            btn = QPushButton(texto)
            btn.setObjectName("btnMini")
            btn.setToolTip(ayuda)
            btn.clicked.connect(lambda _=False, a=accion: a())
            fila2.addWidget(btn)
        fila2.addStretch(1)
        lay.addLayout(fila2)
        return barra

    # --------------------------------------------------------- API pública
    def add_files(self, rutas):
        rutas = [r for r in rutas if r and os.path.isfile(r)]
        if not rutas:
            return
        if not self.multiple:
            self.clear()
            rutas = rutas[:1]
        for ruta in rutas:
            try:
                total = _paginas_de(ruta)
            except Exception:  # noqa: BLE001 - archivo ilegible: se ignora
                continue
            for pagina in range(total):
                self._pendientes.append({"ruta": ruta, "page": pagina, "rot": 0})
        self._volcar_lote()
        self.changed.emit()

    def files(self):
        """Rutas de las páginas marcadas (las que se van a procesar)."""
        vistos = []
        for datos in self.plan():
            if datos["file"] not in vistos:
                vistos.append(datos["file"])
        return vistos

    def clear(self):
        self._silencioso = True
        self.lista.clear()
        self._silencioso = False
        self._pendientes = []
        self._por_clave = {}
        self._item_mas = None
        self._mostrar_lista(False)
        self._actualizar_barra()
        self.changed.emit()

    def plan(self):
        """Lista ordenada de páginas (archivo, número y giro) marcadas."""
        pasos = []
        for i in range(self.lista.count()):
            item = self.lista.item(i)
            if item.data(ROL_TIPO) == "mas":
                continue
            if item.checkState() != Qt.CheckState.Checked:
                continue
            pasos.append({"file": item.data(ROL_RUTA),
                          "page": int(item.data(ROL_PAGINA) or 0),
                          "rot": int(item.data(ROL_ROT) or 0) % 360})
        return pasos

    def paginas_totales(self):
        return sum(1 for i in range(self.lista.count())
                   if self.lista.item(i).data(ROL_TIPO) != "mas")

    def paginas_marcadas(self):
        return len(self.plan())

    def resumen(self):
        archivos = len(self.files())
        return (f"{self.paginas_marcadas()} de {self.paginas_totales()} páginas · "
                f"{archivos} " + ("archivo" if archivos == 1 else "archivos"))

    # ------------------------------------------------------------ llenado
    def _volcar_lote(self):
        self._quitar_item_mas()
        for datos in self._pendientes[:LOTE]:
            item = QListWidgetItem()
            item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
                          | Qt.ItemFlag.ItemIsDragEnabled
                          | Qt.ItemFlag.ItemIsDropEnabled
                          | Qt.ItemFlag.ItemIsUserCheckable)
            item.setData(ROL_RUTA, datos["ruta"])
            item.setData(ROL_PAGINA, datos["page"])
            item.setData(ROL_ROT, datos["rot"])
            item.setCheckState(Qt.CheckState.Checked)
            item.setTextAlignment(Qt.AlignmentFlag.AlignHCenter)
            self._silencioso = True
            self.lista.addItem(item)
            self._silencioso = False
            self._pedir(item)
        del self._pendientes[:LOTE]
        if self._pendientes:
            self._anadir_item_mas()
        self._renumerar()
        self._mostrar_lista(True)
        self._actualizar_barra()

    def _anadir_item_mas(self):
        item = QListWidgetItem("+  Mostrar más páginas")
        item.setData(ROL_TIPO, "mas")
        item.setFlags(Qt.ItemFlag.ItemIsEnabled)
        item.setTextAlignment(Qt.AlignmentFlag.AlignHCenter)
        item.setToolTip(f"Quedan {len(self._pendientes)} páginas por dibujar")
        self.lista.addItem(item)
        self._item_mas = item

    def _quitar_item_mas(self):
        if self._item_mas is None:
            return
        fila = self.lista.row(self._item_mas)
        if fila >= 0:
            self.lista.takeItem(fila)
        self._item_mas = None

    def _pedir(self, item, girar_icono=None):
        """Pide la miniatura al cargador y la asocia a esta página."""
        clave = self._cargador.pedir(item.data(ROL_RUTA),
                                     int(item.data(ROL_PAGINA) or 0),
                                     int(item.data(ROL_ROT) or 0))
        item.setData(ROL_CLAVE, clave)
        self._por_clave.setdefault(clave, []).append(item)
        if girar_icono:
            pix = item.icon().pixmap(ANCHO_MINI, ALTO_MINI)
            if not pix.isNull():
                item.setIcon(QIcon(pix.transformed(
                    QTransform().rotate(girar_icono),
                    Qt.TransformationMode.SmoothTransformation)))

    def _miniatura_lista(self, clave, imagen):
        for item in self._por_clave.get(clave, []):
            if item.listWidget() is self.lista:
                item.setIcon(QIcon(QPixmap.fromImage(imagen)))

    def _renumerar(self):
        numero = 0
        self._silencioso = True
        for i in range(self.lista.count()):
            item = self.lista.item(i)
            if item.data(ROL_TIPO) == "mas":
                continue
            numero += 1
            pagina = int(item.data(ROL_PAGINA) or 0) + 1
            item.setText(f"{numero}  ·  p.{pagina}")
            item.setToolTip(f"{os.path.basename(item.data(ROL_RUTA))} "
                            f"— página {pagina}")
        self._silencioso = False

    def _mostrar_lista(self, hay_paginas):
        self.lista.setVisible(hay_paginas)
        self.zona.setVisible(not hay_paginas)

    def _actualizar_barra(self):
        total = self.paginas_totales()
        if total:
            archivos = len(self.files())
            plural = "archivo" if archivos == 1 else "archivos"
            self.lbl_cuenta.setText(f"{self.paginas_marcadas()} de {total} "
                                    f"páginas · {archivos} {plural}")
        else:
            self.lbl_cuenta.setText("Aún no hay archivos")

    # ------------------------------------------------------------ acciones
    def girar(self, grados):
        for item in self.lista.selectedItems():
            if item.data(ROL_TIPO) == "mas":
                continue
            item.setData(ROL_ROT,
                         (int(item.data(ROL_ROT) or 0) + grados) % 360)
            self._pedir(item, girar_icono=grados)
        self._actualizar_barra()
        self.changed.emit()

    def duplicar_seleccion(self):
        for item in list(self.lista.selectedItems()):
            if item.data(ROL_TIPO) == "mas":
                continue
            fila = self.lista.row(item)
            copia = QListWidgetItem(item.text())
            copia.setFlags(item.flags())
            copia.setData(ROL_RUTA, item.data(ROL_RUTA))
            copia.setData(ROL_PAGINA, item.data(ROL_PAGINA))
            copia.setData(ROL_ROT, item.data(ROL_ROT))
            copia.setCheckState(item.checkState())
            copia.setTextAlignment(Qt.AlignmentFlag.AlignHCenter)
            copia.setIcon(item.icon())
            self._silencioso = True
            self.lista.insertItem(fila + 1, copia)
            self._silencioso = False
            self._pedir(copia)
        self._renumerar()
        self._actualizar_barra()
        self.changed.emit()

    def quitar_seleccion(self):
        for item in self.lista.selectedItems():
            if item.data(ROL_TIPO) == "mas":
                continue
            fila = self.lista.row(item)
            self.lista.takeItem(fila)
            clave = item.data(ROL_CLAVE)
            if clave in self._por_clave and item in self._por_clave[clave]:
                self._por_clave[clave].remove(item)
        if self.paginas_totales() == 0:
            self.clear()
            return
        self._renumerar()
        self._actualizar_barra()
        self.changed.emit()

    def marcar_todo(self, valor=True):
        estado = Qt.CheckState.Checked if valor else Qt.CheckState.Unchecked
        self._silencioso = True
        for i in range(self.lista.count()):
            item = self.lista.item(i)
            if item.data(ROL_TIPO) != "mas":
                item.setCheckState(estado)
        self._silencioso = False
        self._actualizar_barra()
        self.changed.emit()

    # ------------------------------------------------------------ eventos
    def _al_pulsar_item(self, item):
        if item.data(ROL_TIPO) == "mas":
            self._volcar_lote()
            self.changed.emit()

    def _item_cambiado(self, item):
        if getattr(self, "_silencioso", False):
            return
        self._actualizar_barra()
        self.changed.emit()

    def _tras_reordenar(self):
        self._renumerar()
        self.changed.emit()

    def _elegir(self):
        rutas, _ = QFileDialog.getOpenFileNames(
            self, "Seleccionar archivos", "", self.filtro)
        if rutas:
            self.add_files(rutas)

    def cerrar(self):
        """Detiene el hilo de miniaturas (se llama al cerrar la aplicación)."""
        self._cargador.detener()
        cerrar_documentos()

    def dragEnterEvent(self, evento):
        if evento.mimeData().hasUrls():
            evento.acceptProposedAction()
            self.zona.resaltar(True)
        else:
            evento.ignore()

    def dragLeaveEvent(self, evento):
        self.zona.resaltar(False)
        super().dragLeaveEvent(evento)

    def dropEvent(self, evento):
        self.zona.resaltar(False)
        if not evento.mimeData().hasUrls():
            evento.ignore()
            return
        rutas = [u.toLocalFile() for u in evento.mimeData().urls()]
        self.add_files(self.zona._validas(rutas))
        evento.acceptProposedAction()
