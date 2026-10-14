# -*- coding: utf-8 -*-
"""Editor visual de PDF: coloca texto, imágenes, formas y enlaces.

El usuario ve la página tal cual y coloca los elementos con el ratón, los
arrastra donde quiera y ajusta color, tamaño u opacidad. Al guardar, los
elementos se escriben en el PDF en sus posiciones exactas.
"""
from __future__ import annotations

import os

import pymupdf
from PyQt6.QtCore import QEvent, QRectF, Qt, pyqtSignal
from PyQt6.QtGui import (QBrush, QColor, QFont, QImage, QMouseEvent, QPainter,
                         QPen, QPixmap)
from PyQt6.QtWidgets import (QComboBox, QFileDialog, QFrame, QGraphicsEllipseItem,
                             QGraphicsItem, QGraphicsLineItem,
                             QGraphicsPixmapItem, QGraphicsRectItem,
                             QGraphicsScene, QGraphicsTextItem, QGraphicsView,
                             QHBoxLayout, QLabel, QLineEdit, QPushButton,
                             QSpinBox, QVBoxLayout, QWidget)

COLORES_EDITOR = {
    "Negro": "#000000", "Rojo": "#d02b34", "Azul": "#2149d1",
    "Verde": "#1c8c3d", "Amarillo": "#ffd633", "Naranja": "#f2880f",
    "Morado": "#8c4ac6", "Rosa": "#ee5c8e", "Gris": "#808080",
    "Blanco": "#ffffff",
}
FUENTES_EDITOR = {
    "Helvetica": "helv", "Times": "tiro", "Courier": "cour",
    "Helvetica negrita": "hebo", "Times negrita": "tibo",
}


def _qimage_desde(pix) -> QImage:
    """Convierte un pixmap de PyMuPDF en una imagen de Qt."""
    return QImage(pix.samples, pix.width, pix.height, pix.stride,
                  QImage.Format.Format_RGB888).copy()


class LienzoEditor(QGraphicsView):
    """Área donde se ven y se mueven los elementos sobre la página.

    El ratón funciona así:
      * arrastrar sobre un elemento -> lo mueve libremente por la página.
      * arrastrar sobre el fondo -> selecciona con un rectángulo elástico.
      * botón central y arrastrar -> desplaza la página.
      * Ctrl + rueda -> acerca y aleja.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("lienzoEditor")
        self.setRenderHints(QPainter.RenderHint.Antialiasing
                            | QPainter.RenderHint.SmoothPixmapTransform)
        self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
        self.setScene(QGraphicsScene(self))
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setTransformationAnchor(
            QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self._zoom = 1.0

    def resetear_zoom(self):
        """Vuelve al zoom normal (se llama al abrir otro archivo)."""
        if self._zoom != 1.0:
            self.resetTransform()
            self._zoom = 1.0

    def wheelEvent(self, evento):
        """Ctrl + rueda acerca y aleja; sin Ctrl, desplaza la vista."""
        if evento.modifiers() & Qt.KeyboardModifier.ControlModifier:
            factor = 1.15 if evento.angleDelta().y() > 0 else 1 / 1.15
            nuevo = max(0.25, min(6.0, self._zoom * factor))
            if nuevo != self._zoom:
                self.scale(nuevo / self._zoom, nuevo / self._zoom)
                self._zoom = nuevo
            evento.accept()
            return
        super().wheelEvent(evento)

    def mousePressEvent(self, evento):
        # Con el botón central se arrastra la vista, como en cualquier visor de
        # PDF. QGraphicsView solo sabe hacerlo con el botón izquierdo, así que
        # se le entrega una pulsación izquierda equivalente.
        if evento.button() == Qt.MouseButton.MiddleButton:
            self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
            super().mousePressEvent(self._como_izquierdo(
                evento, QEvent.Type.MouseButtonPress))
            return
        super().mousePressEvent(evento)

    def mouseReleaseEvent(self, evento):
        if (evento.button() == Qt.MouseButton.MiddleButton
                and self.dragMode() == QGraphicsView.DragMode.ScrollHandDrag):
            super().mouseReleaseEvent(self._como_izquierdo(
                evento, QEvent.Type.MouseButtonRelease))
            self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
            return
        super().mouseReleaseEvent(evento)

    @staticmethod
    def _como_izquierdo(evento, tipo):
        """Copia un evento del ratón como si se hubiera pulsado el izquierdo."""
        return QMouseEvent(tipo, evento.position(),
                           Qt.MouseButton.LeftButton,
                           Qt.MouseButton.LeftButton
                           if tipo == QEvent.Type.MouseButtonPress
                           else Qt.MouseButton.NoButton,
                           Qt.KeyboardModifier.NoModifier)


class EditorPDF(QWidget):
    """Editor de las páginas de un PDF con sus elementos."""

    cambiado = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._doc = None
        self._ruta = ""
        self._pagina = 0
        self._escala = 1.0
        self._tamanos = []          # (ancho, alto) en puntos de cada página
        self._elementos = []        # dicts con su QGraphicsItem
        self._fondo = None
        self._escalas = {}          # escala usada en cada página

        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(0, 0, 0, 0)
        raiz.setSpacing(10)
        raiz.addWidget(self._construir_barra())

        self.lienzo = LienzoEditor()
        self.lienzo.setMinimumHeight(380)
        raiz.addWidget(self.lienzo, 1)

        self.lbl_vacio = QLabel("Añade un PDF para editarlo aquí")
        self.lbl_vacio.setObjectName("estado")
        raiz.addWidget(self.lbl_vacio)

    # -------------------------------------------------------------- barra
    def _construir_barra(self):
        barra = QFrame()
        barra.setObjectName("barraEditor")
        lay = QVBoxLayout(barra)
        lay.setContentsMargins(12, 10, 12, 10)
        lay.setSpacing(8)
        lay.addLayout(self._fila_paginas())
        lay.addLayout(self._fila_herramientas())
        lay.addLayout(self._fila_propiedades())
        return barra

    def _fila_paginas(self):
        fila = QHBoxLayout()
        fila.setSpacing(6)
        self.btn_prev = QPushButton("◀")
        self.btn_prev.setObjectName("btnMini")
        self.btn_prev.clicked.connect(lambda: self.ir_a(self._pagina - 1))
        fila.addWidget(self.btn_prev)

        self.spin_pagina = QSpinBox()
        self.spin_pagina.setMinimum(1)
        self.spin_pagina.setMaximum(1)
        self.spin_pagina.setFixedWidth(76)
        self.spin_pagina.valueChanged.connect(lambda v: self.ir_a(v - 1))
        fila.addWidget(self.spin_pagina)

        self.lbl_paginas = QLabel("/ 0")
        self.lbl_paginas.setObjectName("estado")
        fila.addWidget(self.lbl_paginas)

        self.btn_next = QPushButton("▶")
        self.btn_next.setObjectName("btnMini")
        self.btn_next.clicked.connect(lambda: self.ir_a(self._pagina + 1))
        fila.addWidget(self.btn_next)
        fila.addSpacing(10)
        return fila

    def _fila_herramientas(self):
        fila = QHBoxLayout()
        fila.setSpacing(6)
        botones = (
            ("T  Texto", self.anadir_texto, "Coloca un texto en la página"),
            ("Imagen", self.anadir_imagen, "Inserta una imagen"),
            ("Rectángulo", lambda: self.anadir_forma("rectangulo"),
             "Dibuja un rectángulo relleno"),
            ("Elipse", lambda: self.anadir_forma("elipse"),
             "Dibuja una elipse rellena"),
            ("Línea", self.anadir_linea, "Dibuja una línea"),
            ("Resaltar", lambda: self.anadir_forma("resaltado"),
             "Resalta una zona con color translúcido"),
            ("Enlace", self.anadir_enlace,
             "Crea un enlace con la dirección del campo «Enlace»"),
        )
        for texto, accion, ayuda in botones:
            btn = QPushButton(texto)
            btn.setObjectName("btnMini")
            btn.setToolTip(ayuda)
            btn.clicked.connect(lambda _=False, a=accion: a())
            fila.addWidget(btn)

        fila.addStretch(1)
        btn_ultimo = QPushButton("Deshacer")
        btn_ultimo.setObjectName("btnMini")
        btn_ultimo.setToolTip("Quita el último elemento añadido")
        btn_ultimo.clicked.connect(self.quitar_ultimo)
        fila.addWidget(btn_ultimo)
        btn_borrar = QPushButton("Borrar")
        btn_borrar.setObjectName("btnMini")
        btn_borrar.setToolTip("Borra los elementos seleccionados")
        btn_borrar.clicked.connect(self.borrar_seleccion)
        fila.addWidget(btn_borrar)
        return fila

    def _fila_propiedades(self):
        fila = QHBoxLayout()
        fila.setSpacing(8)
        fila.addWidget(QLabel("Texto:"))
        self.campo_texto = QLineEdit("Escribe aquí")
        self.campo_texto.setMinimumWidth(170)
        self.campo_texto.setToolTip("Lo que escribas aquí es lo que se coloca "
                                    "con el botón «Texto»")
        self.campo_texto.textChanged.connect(self._actualizar_texto_elegido)
        fila.addWidget(self.campo_texto)

        fila.addWidget(QLabel("Color:"))
        self.combo_color = QComboBox()
        for nombre, valor in COLORES_EDITOR.items():
            self.combo_color.addItem(nombre, valor)
        self.combo_color.currentIndexChanged.connect(self._actualizar_propiedades)
        fila.addWidget(self.combo_color)

        fila.addWidget(QLabel("Tamaño:"))
        self.spin_tamano = QSpinBox()
        self.spin_tamano.setRange(6, 200)
        self.spin_tamano.setValue(18)
        self.spin_tamano.valueChanged.connect(self._actualizar_propiedades)
        fila.addWidget(self.spin_tamano)

        fila.addWidget(QLabel("Fuente:"))
        self.combo_fuente = QComboBox()
        for nombre, valor in FUENTES_EDITOR.items():
            self.combo_fuente.addItem(nombre, valor)
        self.combo_fuente.currentIndexChanged.connect(self._actualizar_propiedades)
        fila.addWidget(self.combo_fuente)

        fila.addWidget(QLabel("Opacidad:"))
        self.spin_opacidad = QSpinBox()
        self.spin_opacidad.setRange(5, 100)
        self.spin_opacidad.setValue(100)
        self.spin_opacidad.setSuffix(" %")
        self.spin_opacidad.valueChanged.connect(self._actualizar_propiedades)
        fila.addWidget(self.spin_opacidad)

        fila.addWidget(QLabel("Enlace:"))
        self.campo_url = QLineEdit()
        self.campo_url.setPlaceholderText("https://…")
        self.campo_url.setMinimumWidth(140)
        fila.addWidget(self.campo_url)
        fila.addStretch(1)
        return fila

    # -------------------------------------------------------- documento
    def cargar(self, ruta):
        """Abre el PDF que se va a editar."""
        self._cerrar_documento()
        if not ruta:
            return False
        try:
            self._doc = pymupdf.open(ruta)
            if self._doc.needs_pass:
                self._doc.authenticate("")
            self._tamanos = [(p.rect.width, p.rect.height) for p in self._doc]
        except Exception:  # noqa: BLE001
            self._doc = None
            return False
        self._ruta = ruta
        self._elementos = []
        self.spin_pagina.setMaximum(max(1, len(self._tamanos)))
        self.lbl_paginas.setText(f"/ {len(self._tamanos)}")
        self.lbl_vacio.setVisible(False)
        self.ir_a(0)
        return True

    def _cerrar_documento(self):
        if self._doc is not None:
            self._doc.close()
            self._doc = None
        self.lienzo.resetear_zoom()
        self.lienzo.scene().clear()
        self._fondo = None
        self._elementos = []
        self._tamanos = []
        self._ruta = ""

    def ir_a(self, indice):
        if self._doc is None or not self._tamanos:
            return
        indice = max(0, min(len(self._tamanos) - 1, int(indice)))
        if indice == self._pagina and self._fondo is not None:
            return
        self._pagina = indice
        self.spin_pagina.blockSignals(True)
        self.spin_pagina.setValue(indice + 1)
        self.spin_pagina.blockSignals(False)
        self._pintar_pagina()

    def _pintar_pagina(self):
        if self._doc is None:
            return
        pagina = self._doc[self._pagina]
        ancho_pt, alto_pt = self._tamanos[self._pagina]
        zoom = min(1.6, max(0.6, 760.0 / max(1.0, ancho_pt * 1.1)))
        pix = pagina.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), alpha=False)
        imagen = QPixmap.fromImage(_qimage_desde(pix))
        escena = self.lienzo.scene()
        for elemento in self._elementos:
            elemento["item"].setVisible(elemento["pagina"] == self._pagina)
        if self._fondo is None:
            self._fondo = QGraphicsPixmapItem(imagen)
            self._fondo.setZValue(-10)
            escena.addItem(self._fondo)
        else:
            self._fondo.setPixmap(imagen)
        self._escala = imagen.width() / max(1.0, ancho_pt)
        self._escalas[self._pagina] = self._escala
        escena.setSceneRect(0, 0, imagen.width(), imagen.height())

    def _centro(self):
        """Punto central de la página, donde se colocan los elementos."""
        ancho, alto = self._tamanos[self._pagina] if self._tamanos else (600, 800)
        return ancho * self._escala, alto * self._escala

    # ----------------------------------------------------------- elementos
    def _color(self):
        return QColor(self.combo_color.currentData())

    def _nuevo_elemento(self, tipo, item, **extra):
        item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        # Necesario para que el elemento se repinte al moverlo.
        item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges,
                     True)
        item.setCursor(Qt.CursorShape.SizeAllCursor)
        item.setCacheMode(QGraphicsItem.CacheMode.DeviceCoordinateCache)
        item.setZValue(10 + len(self._elementos))
        self.lienzo.scene().addItem(item)
        elemento = {"pagina": self._pagina, "tipo": tipo, "item": item,
                    "color": self.combo_color.currentData(),
                    "tamano": int(self.spin_tamano.value()),
                    "fuente": self.combo_fuente.currentData(),
                    "opacidad": int(self.spin_opacidad.value())}
        elemento.update(extra)
        self._elementos.append(elemento)
        item.setSelected(True)
        self.cambiado.emit()
        return elemento

    def anadir_texto(self):
        if self._doc is None:
            return
        texto = self.campo_texto.text().strip() or "Texto"
        item = QGraphicsTextItem(texto)
        # Sin esto, al hacer clic el texto entra en modo edición y el ratón no
        # lo arrastra (era el motivo de que «no se dejara mover»).
        item.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        fuente = QFont("Segoe UI")
        fuente.setPixelSize(max(6, int(self.spin_tamano.value() * self._escala)))
        item.setFont(fuente)
        item.setDefaultTextColor(self._color())
        ancho_px, alto_px = self._centro()
        caja = item.boundingRect()
        item.setPos((ancho_px - caja.width()) / 2, (alto_px - caja.height()) / 2)
        self._nuevo_elemento("texto", item)

    def anadir_imagen(self):
        if self._doc is None:
            return
        ruta, _ = QFileDialog.getOpenFileName(
            self, "Imagen para el PDF", "",
            "Imágenes (*.png *.jpg *.jpeg *.bmp *.webp *.tiff)")
        if not ruta:
            return
        pix = QPixmap(ruta)
        if pix.isNull():
            return
        ancho_px, alto_px = self._centro()
        destino = max(40, int(ancho_px * 0.35))
        pix = pix.scaledToWidth(destino, Qt.TransformationMode.SmoothTransformation)
        item = QGraphicsPixmapItem(pix)
        item.setOpacity(self.spin_opacidad.value() / 100)
        item.setPos((ancho_px - pix.width()) / 2, (alto_px - pix.height()) / 2)
        self._nuevo_elemento("imagen", item, imagen=ruta)

    def anadir_forma(self, tipo):
        if self._doc is None:
            return
        ancho_px, alto_px = self._centro()
        w = ancho_px * 0.34
        h = alto_px * 0.05
        rect = QRectF((ancho_px - w) / 2, (alto_px - h) / 2, w, h)
        color = self._color()
        if tipo == "elipse":
            item = QGraphicsEllipseItem(rect)
            item.setBrush(QBrush(color))
            item.setPen(QPen(color.darker(120), 1.5))
        elif tipo == "resaltado":
            item = QGraphicsRectItem(rect)
            item.setBrush(QBrush(QColor(color.red(), color.green(),
                                        color.blue(), 90)))
            item.setPen(QPen(Qt.PenStyle.NoPen))
        else:
            item = QGraphicsRectItem(rect)
            item.setBrush(QBrush(color))
            item.setPen(QPen(color.darker(120), 1.5))
        item.setOpacity(self.spin_opacidad.value() / 100)
        self._nuevo_elemento(tipo, item)

    def anadir_linea(self):
        if self._doc is None:
            return
        ancho_px, alto_px = self._centro()
        item = QGraphicsLineItem(ancho_px * 0.28, alto_px * 0.5,
                                 ancho_px * 0.72, alto_px * 0.5)
        item.setPen(QPen(self._color(), 2.5))
        self._nuevo_elemento("linea", item)

    def anadir_enlace(self):
        if self._doc is None:
            return
        url = self.campo_url.text().strip()
        if not url:
            self.campo_url.setFocus()
            return
        ancho_px, alto_px = self._centro()
        w, h = ancho_px * 0.3, alto_px * 0.04
        item = QGraphicsRectItem(QRectF((ancho_px - w) / 2, (alto_px - h) / 2,
                                        w, h))
        item.setPen(QPen(QColor("#2149d1"), 1.5, Qt.PenStyle.DashLine))
        item.setBrush(QBrush(QColor(33, 73, 209, 30)))
        self._nuevo_elemento("enlace", item, url=url)

    # ---------------------------------------------------------- propiedades
    def _seleccionados(self):
        return [el for el in self._elementos if el["item"].isSelected()]

    def _actualizar_propiedades(self):
        color = self.combo_color.currentData()
        tamano = int(self.spin_tamano.value())
        fuente = self.combo_fuente.currentData()
        opacidad = int(self.spin_opacidad.value())
        for el in self._seleccionados():
            el.update(color=color, tamano=tamano, fuente=fuente,
                      opacidad=opacidad)
            item = el["item"]
            if el["tipo"] == "texto":
                letra = item.font()
                letra.setPixelSize(max(6, int(tamano * self._escala)))
                item.setFont(letra)
                item.setDefaultTextColor(self._color())
            elif el["tipo"] == "imagen":
                item.setOpacity(opacidad / 100)
            elif el["tipo"] == "linea":
                lapiz = item.pen()
                lapiz.setColor(self._color())
                lapiz.setWidth(2.5)
                item.setPen(lapiz)
            else:
                item.setBrush(QBrush(self._color()))
                item.setPen(QPen(self._color().darker(120), 1.5))
                item.setOpacity(opacidad / 100)
        self.cambiado.emit()

    def _actualizar_texto_elegido(self, texto):
        for el in self._seleccionados():
            if el["tipo"] == "texto":
                el["item"].setPlainText(texto)
        self.cambiado.emit()

    def quitar_ultimo(self):
        if not self._elementos:
            return
        elemento = self._elementos.pop()
        self.lienzo.scene().removeItem(elemento["item"])
        self.cambiado.emit()

    def borrar_seleccion(self):
        for elemento in self._seleccionados():
            self.lienzo.scene().removeItem(elemento["item"])
            self._elementos.remove(elemento)
        self.cambiado.emit()

    # ------------------------------------------------------------------ API
    def _escala_de(self, pagina):
        return self._escalas.get(pagina, self._escala)

    def elementos(self):
        """Elementos listos para el backend (posiciones en % de la página)."""
        salida = []
        for el in self._elementos:
            item = el["item"]
            pagina = el["pagina"]
            ancho_pt, alto_pt = self._tamanos[pagina]
            escala = self._escala_de(pagina) or 1.0
            ancho_px = max(1.0, ancho_pt * escala)
            alto_px = max(1.0, alto_pt * escala)
            caja = item.sceneBoundingRect()
            datos = {
                "tipo": el["tipo"],
                "pagina": pagina + 1,
                "x": max(0.0, caja.x() / ancho_px * 100),
                "y": max(0.0, caja.y() / alto_px * 100),
                "w": max(0.5, caja.width() / ancho_px * 100),
                "h": max(0.5, caja.height() / alto_px * 100),
                "color": el.get("color"),
                "opacidad": el.get("opacidad", 100),
                "grosor": 1.5,
            }
            if el["tipo"] == "texto":
                datos.update(texto=item.toPlainText(),
                             tamano=int(el.get("tamano", 18)),
                             fuente=el.get("fuente", "helv"))
            elif el["tipo"] == "imagen":
                datos.update(imagen=el.get("imagen"), proporcion=True)
            elif el["tipo"] == "enlace":
                datos.update(url=el.get("url", ""))
            elif el["tipo"] == "resaltado":
                datos["relleno"] = el.get("color") or "#ffd633"
                datos["opacidad"] = min(60, el.get("opacidad", 100))
            salida.append(datos)
        return salida

    def listo(self):
        return bool(self._elementos) and self._doc is not None

    def abierto(self):
        return self._doc is not None

    def cerrar(self):
        self._cerrar_documento()