# -*- coding: utf-8 -*-
"""Widgets reutilizables de la interfaz.

Contiene las piezas que se usan en varias pantallas: la tarjeta de herramienta,
la distribución que reparte tarjetas según el ancho, la zona de arrastrar y
soltar, el cargador de miniaturas en segundo plano, el campo de imagen y el
cuadro para dibujar la firma a mano.
"""
from __future__ import annotations

import os
import tempfile
import threading
from collections import deque

import pymupdf
from PyQt6.QtCore import QPoint, QRect, QSize, Qt, QThread, pyqtSignal
from PyQt6.QtGui import (QColor, QCursor, QImage, QPainter, QPen, QPixmap,
                         QTransform)
from PyQt6.QtWidgets import (QDialog, QFileDialog, QFrame, QHBoxLayout, QLabel,
                             QLayout, QLineEdit, QPushButton, QSizePolicy,
                             QStyle, QVBoxLayout, QWidget)

from .. import assets_path

IMG_POR_DEFECTO = "Imágenes (*.png *.jpg *.jpeg *.bmp *.tiff *.webp)"


def extensiones_filtro(filtro: str):
    """Extrae las extensiones de un filtro tipo 'Archivos PDF (*.pdf)'."""
    if "(" not in filtro:
        return []
    patrones = filtro.split("(", 1)[1].rstrip(")").split()
    return [p.lstrip("*").lower() for p in patrones if p.startswith("*.")]


def formatear_tamano(bytes_: int) -> str:
    if not bytes_:
        return ""
    if bytes_ < 1024:
        return f"{bytes_} B"
    if bytes_ < 1024 * 1024:
        return f"{bytes_ / 1024:.0f} KB"
    return f"{bytes_ / (1024 * 1024):.1f} MB"


# ===================================================== DISTRIBUCIÓN EN FLUJO
class FlowLayout(QLayout):
    """Coloca los widgets en filas y salta de línea según el ancho libre.

    Así la parrilla de herramientas siempre llena el espacio disponible y no
    quedan huecos vacíos al redimensionar la ventana.
    """

    def __init__(self, parent=None, margen=0, espaciado=14):
        super().__init__(parent)
        self._items = []
        self._margen = margen
        self._espaciado = espaciado
        self.setContentsMargins(margen, margen, margen, margen)

    def addItem(self, item):  # noqa: N802 - API de Qt
        self._items.append(item)

    def count(self):
        return len(self._items)

    def itemAt(self, indice):  # noqa: N802
        if 0 <= indice < len(self._items):
            return self._items[indice]
        return None

    def takeAt(self, indice):  # noqa: N802
        if 0 <= indice < len(self._items):
            return self._items.pop(indice)
        return None

    def expandingDirections(self):  # noqa: N802
        return Qt.Orientation(0)

    def hasHeightForWidth(self):  # noqa: N802
        return True

    def heightForWidth(self, ancho):  # noqa: N802
        return self._repartir(QRect(0, 0, ancho, 0), probar=True)

    def setGeometry(self, rect):  # noqa: N802
        super().setGeometry(rect)
        self._repartir(rect, probar=False)

    def sizeHint(self):  # noqa: N802
        return self.minimumSize()

    def minimumSize(self):  # noqa: N802
        tam = QSize()
        for item in self._items:
            tam = tam.expandedTo(item.minimumSize())
        return tam + QSize(2 * self._margen, 2 * self._margen)

    def _repartir(self, rect, probar):
        izquierda, arriba = rect.x(), rect.y()
        derecha = izquierda + rect.width() - 2 * self._margen
        x, y, alto_fila = izquierda, arriba, 0
        for item in self._items:
            widget = item.widget()
            if widget is not None and widget.isHidden():
                continue
            pista = item.sizeHint()
            siguiente = x + pista.width() + self._espaciado
            if siguiente - self._espaciado > derecha and alto_fila > 0:
                x = izquierda
                y += alto_fila + self._espaciado
                siguiente = x + pista.width() + self._espaciado
                alto_fila = 0
            if not probar:
                item.setGeometry(QRect(QPoint(x, y), pista))
            x = siguiente
            alto_fila = max(alto_fila, pista.height())
        return y + alto_fila + 2 * self._margen


class ToolCard(QFrame):
    """Tarjeta de la parrilla principal (icono + título + descripción)."""

    clicked = pyqtSignal(str)

    def __init__(self, tool: dict, parent=None):
        super().__init__(parent)
        self.tool_id = tool["id"]
        self.titulo = tool["titulo"]
        self.descripcion = tool["descripcion"]
        self.categoria = tool["categoria"]
        self.setObjectName("ToolCard")
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setFixedHeight(104)
        self.setMinimumWidth(252)
        self.setMaximumWidth(420)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.setToolTip(f"{tool['titulo']} · {tool['descripcion']}")

        lay = QHBoxLayout(self)
        lay.setContentsMargins(14, 14, 14, 14)
        lay.setSpacing(13)

        marco = QFrame()
        marco.setObjectName("cardIcono")
        marco.setFixedSize(48, 48)
        mi = QVBoxLayout(marco)
        mi.setContentsMargins(0, 0, 0, 0)
        icono = QLabel()
        icono.setPixmap(QPixmap(assets_path("icons", f"{tool['icono']}.png")).scaled(
            38, 38, Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation))
        icono.setAlignment(Qt.AlignmentFlag.AlignCenter)
        mi.addWidget(icono)
        lay.addWidget(marco, 0, Qt.AlignmentFlag.AlignTop)

        col = QVBoxLayout()
        col.setSpacing(4)
        titulo = QLabel(tool["titulo"])
        titulo.setObjectName("cardTitulo")
        desc = QLabel(tool["descripcion"])
        desc.setObjectName("cardDesc")
        desc.setWordWrap(True)
        desc.setFixedWidth(170)
        desc.setMaximumHeight(32)
        col.addWidget(titulo)
        col.addWidget(desc)
        col.addStretch(1)
        lay.addLayout(col, 1)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.tool_id)
        super().mousePressEvent(event)


# ================================================================ TRABAJADORES
class Worker(QThread):
    """Ejecuta la función de la herramienta en segundo plano."""

    progreso = pyqtSignal(int, str)
    terminado = pyqtSignal(str)
    fallo = pyqtSignal(str)

    def __init__(self, funcion, files, out, opts, parent=None):
        super().__init__(parent)
        self.funcion, self.files, self.out, self.opts = funcion, files, out, opts

    def run(self):
        try:
            def cb(pct, msg=""):
                self.progreso.emit(pct, msg)
            resultado = self.funcion(self.files, self.out, self.opts, cb)
            self.terminado.emit(str(resultado))
        except Exception as e:  # noqa: BLE001 - mostrar cualquier error al usuario
            self.fallo.emit(str(e))


class CargadorMiniaturas(QThread):
    """Renderiza las miniaturas de las páginas en segundo plano.

    Cada miniatura se calcula una sola vez y queda en memoria, así mover o
    reordenar páginas es instantáneo aunque el documento tenga cientos de hojas.
    """

    listo = pyqtSignal(str, QImage)
    fallo = pyqtSignal(str, str)

    def __init__(self, ancho=132, alto=176, parent=None):
        super().__init__(parent)
        self.ancho, self.alto = ancho, alto
        self._pendientes = deque()
        self._hechas = {}
        self._lock = threading.Lock()
        self._parar = False

    def clave(self, ruta, pagina, rot=0):
        return f"{ruta}|{pagina}|{int(rot) % 360}|{self.ancho}x{self.alto}"

    def pedir(self, ruta, pagina, rot=0):
        """Pide una miniatura; si ya estaba hecha la devuelve al instante."""
        clave = self.clave(ruta, pagina, rot)
        with self._lock:
            guardada = self._hechas.get(clave)
            if guardada is None:
                self._pendientes.append((clave, ruta, int(pagina), int(rot) % 360))
        if guardada is not None:
            self.listo.emit(clave, guardada)
        return clave

    def detener(self):
        with self._lock:
            self._parar = True
            self._pendientes.clear()
        self.wait(1500)

    def run(self):
        while True:
            with self._lock:
                if self._parar:
                    return
                tarea = self._pendientes.popleft() if self._pendientes else None
            if tarea is None:
                self.msleep(20)
                continue
            clave, ruta, pagina, rot = tarea
            try:
                imagen = _render_miniatura(ruta, pagina, rot, self.ancho, self.alto)
            except Exception:  # noqa: BLE001 - una miniatura rota no rompe nada
                continue
            with self._lock:
                self._hechas[clave] = imagen
            self.listo.emit(clave, imagen)


def _formato_qt(pix):
    """Formato de QImage que corresponde a los canales que devuelve PyMuPDF."""
    return (QImage.Format.Format_RGBA8888 if pix.n == 4
            else QImage.Format.Format_RGB888)


# ---------------------------------------------------------------------------
# Caché de documentos abiertos.
# Antes cada miniatura hacía su propio pymupdf.open(ruta): en un PDF de 200
# páginas eran 200 aperturas de disco y la vista tardaba muchísimo en
# rellenarse (y el disco no paraba). Ahora se abre una vez por archivo.
# ---------------------------------------------------------------------------
_DOCS = {}                  # ruta -> (firma, documento)
_DOCS_LOCK = threading.Lock()
_DOCS_MAX = 12


def cerrar_documentos():
    """Cierra y vacía la caché de documentos (al cerrar la aplicación)."""
    with _DOCS_LOCK:
        for _firma, doc in _DOCS.values():
            try:
                doc.close()
            except Exception:  # noqa: BLE001
                pass
        _DOCS.clear()


def _doc_de(ruta):
    """Devuelve el documento abierto, reutilizándolo entre miniaturas."""
    try:
        firma = (os.path.getmtime(ruta), os.path.getsize(ruta))
    except OSError:
        firma = None

    with _DOCS_LOCK:
        guardado = _DOCS.get(ruta)
        if guardado is not None:
            if firma is not None and guardado[0] == firma:
                return guardado[1]
            viejo = _DOCS.pop(ruta)[1]
            try:
                viejo.close()
            except Exception:  # noqa: BLE001
                pass

    doc = pymupdf.open(ruta)
    if doc.needs_pass:
        doc.authenticate("")

    with _DOCS_LOCK:
        while len(_DOCS) >= _DOCS_MAX:
            sobrante = _DOCS.pop(next(iter(_DOCS)))[1]
            try:
                sobrante.close()
            except Exception:  # noqa: BLE001
                pass
        _DOCS[ruta] = (firma, doc)
    return doc


def _render_miniatura(ruta, pagina, rot, ancho, alto) -> QImage:
    """Dibuja una página (o imagen) como miniatura, entera y sin recortes."""
    doc = _doc_de(ruta)
    pagina = max(0, min(doc.page_count - 1, int(pagina)))
    rect = doc[pagina].rect
    # Se ajusta la página completa dentro de la caja de la miniatura, así no
    # se corta ningún borde y siempre se ve el PDF entero.
    zoom = min(ancho / max(1.0, rect.width), alto / max(1.0, rect.height))
    zoom = max(0.05, min(4.0, zoom))
    pix = doc[pagina].get_pixmap(matrix=pymupdf.Matrix(zoom, zoom),
                                 alpha=False)
    imagen = QImage(pix.samples, pix.width, pix.height, pix.stride,
                    _formato_qt(pix)).copy()
    if rot:
        imagen = imagen.transformed(QTransform().rotate(rot),
                                    Qt.TransformationMode.SmoothTransformation)
    return imagen


# ======================================================= ARCHIVOS DE ENTRADA
class ZonaSoltar(QFrame):
    """Zona donde se sueltan los archivos (o se eligen con el botón)."""

    archivos = pyqtSignal(list)

    def __init__(self, filtro: str, multiple: bool, parent=None):
        super().__init__(parent)
        self.filtro = filtro
        self.multiple = multiple
        self.setObjectName("zonaSoltar")
        self.setProperty("hover", "false")
        self.setAcceptDrops(True)
        self.setMinimumHeight(112)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 14, 18, 14)
        lay.setSpacing(4)
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.titulo = QLabel("Arrastra aquí tus archivos")
        self.titulo.setObjectName("soltarTitulo")
        self.titulo.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.detalle = QLabel("o pulsa «Elegir archivos» · sin límite de cantidad")
        self.detalle.setObjectName("soltarTexto")
        self.detalle.setAlignment(Qt.AlignmentFlag.AlignCenter)

        btn = QPushButton("Elegir archivos")
        btn.setObjectName("btnSecundario")
        btn.clicked.connect(self._elegir)

        fila = QHBoxLayout()
        fila.addStretch(1)
        fila.addWidget(btn)
        fila.addStretch(1)

        lay.addWidget(self.titulo)
        lay.addWidget(self.detalle)
        lay.addSpacing(4)
        lay.addLayout(fila)

    def _elegir(self):
        if self.multiple:
            rutas, _ = QFileDialog.getOpenFileNames(
                self, "Seleccionar archivos", "", self.filtro)
        else:
            ruta, _ = QFileDialog.getOpenFileName(
                self, "Seleccionar archivo", "", self.filtro)
            rutas = [ruta] if ruta else []
        if rutas:
            self.archivos.emit(rutas)

    def resaltar(self, activo: bool):
        self.setProperty("hover", "true" if activo else "false")
        self.style().unpolish(self)
        self.style().polish(self)

    def dragEnterEvent(self, evento):
        if evento.mimeData().hasUrls():
            evento.acceptProposedAction()
            self.resaltar(True)
        else:
            evento.ignore()

    def dragLeaveEvent(self, evento):
        self.resaltar(False)
        super().dragLeaveEvent(evento)

    def dropEvent(self, evento):
        self.resaltar(False)
        if not evento.mimeData().hasUrls():
            evento.ignore()
            return
        rutas = [u.toLocalFile() for u in evento.mimeData().urls()]
        self.archivos.emit(self._validas(rutas))
        evento.acceptProposedAction()

    def _validas(self, rutas):
        extensiones = extensiones_filtro(self.filtro)
        salida = []
        for ruta in rutas:
            if not (ruta and os.path.isfile(ruta)):
                continue
            if extensiones and os.path.splitext(ruta)[1].lower() not in extensiones:
                continue
            salida.append(ruta)
        return salida


class ChipArchivo(QFrame):
    """Ficha compacta con el nombre, el tamaño y el botón de quitar."""

    quitar = pyqtSignal(str)

    def __init__(self, ruta: str, parent=None):
        super().__init__(parent)
        self.ruta = ruta
        self.setObjectName("chipArchivo")
        try:
            tam = formatear_tamano(os.path.getsize(ruta))
        except OSError:
            tam = ""
        lay = QHBoxLayout(self)
        lay.setContentsMargins(10, 7, 8, 7)
        lay.setSpacing(9)

        icono = QLabel()
        icono.setPixmap(self.style().standardIcon(
            QStyle.StandardPixmap.SP_FileIcon).pixmap(22, 22))
        lay.addWidget(icono)

        col = QVBoxLayout()
        col.setSpacing(1)
        nombre = QLabel(os.path.basename(ruta))
        nombre.setObjectName("chipNombre")
        detalle = QLabel(f"{tam} · {os.path.dirname(ruta) or ruta}")
        detalle.setObjectName("chipDatos")
        detalle.setMaximumWidth(320)
        col.addWidget(nombre)
        col.addWidget(detalle)
        lay.addLayout(col, 1)
        self.setToolTip(ruta)

        btn = QPushButton("×")
        btn.setObjectName("btnPeligro")
        btn.setFixedWidth(30)
        btn.setToolTip("Quitar de la lista")
        btn.clicked.connect(lambda: self.quitar.emit(self.ruta))
        lay.addWidget(btn)


class FileListWidget(QWidget):
    """Lista de archivos de entrada: zona de arrastre + ficha de cada archivo.

    Mantiene la misma interfaz que usan las pruebas y las páginas
    (``add_files``, ``files``, ``changed``, ``clear``).
    """

    changed = pyqtSignal()

    def __init__(self, filtro: str, multiple: bool, parent=None):
        super().__init__(parent)
        self.filtro = filtro
        self.multiple = multiple
        self._rutas = []
        self.setAcceptDrops(True)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)

        self.zona = ZonaSoltar(filtro, multiple)
        self.zona.archivos.connect(self.add_files)
        lay.addWidget(self.zona)

        fila = QHBoxLayout()
        fila.setSpacing(8)
        self.btn_add = QPushButton("Elegir archivos")
        self.btn_add.setObjectName("btnSecundario")
        self.btn_add.setToolTip("Añade o cambia los archivos de entrada")
        self.btn_add.clicked.connect(self.zona._elegir)
        self.btn_add.setVisible(False)
        fila.addWidget(self.btn_add)
        fila.addStretch(1)
        lay.addLayout(fila)

        self._contenedor = QWidget()
        self.flujo = FlowLayout(self._contenedor, margen=0, espaciado=8)
        self._contenedor.setVisible(False)
        lay.addWidget(self._contenedor)

    # ---------------------------------------------------------------- API
    def add_files(self, rutas):
        rutas = [r for r in rutas if r]
        if not rutas:
            return
        if not self.multiple:
            self._rutas = []
            rutas = rutas[:1]
        for ruta in rutas:
            if ruta not in self._rutas:
                self._rutas.append(ruta)
        self._refrescar()
        self.changed.emit()

    def files(self):
        return list(self._rutas)

    def clear(self):
        self._rutas = []
        self._refrescar()
        self.changed.emit()

    def quitar(self, ruta):
        if ruta in self._rutas:
            self._rutas.remove(ruta)
            self._refrescar()
            self.changed.emit()

    def _refrescar(self):
        while self.flujo.count():
            item = self.flujo.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()
        for ruta in self._rutas:
            chip = ChipArchivo(ruta)
            chip.quitar.connect(self.quitar)
            self.flujo.addWidget(chip)
        hay = bool(self._rutas)
        self._contenedor.setVisible(hay)
        # La zona de arrastre solo se muestra cuando no hay archivos: así las
        # herramientas con contenido (como el editor) aprovechan todo el alto.
        self.zona.setVisible(not hay)
        self.btn_add.setVisible(hay)
        self._contenedor.updateGeometry()

    def contar(self):
        return len(self._rutas)

    # ----------------------------------------------------------- arrastrar
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


# ================================================ CAMPOS ESPECIALES E IMAGEN
class CampoImagen(QWidget):
    """Campo de imagen: elegir el archivo, ver la miniatura y dibujar la firma."""

    cambiado = pyqtSignal()

    def __init__(self, firma=False, filtro=IMG_POR_DEFECTO, parent=None):
        super().__init__(parent)
        self.es_firma = firma
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)

        fila = QHBoxLayout()
        fila.setSpacing(8)
        self.ruta = QLineEdit()
        self.ruta.setPlaceholderText("Ninguna imagen seleccionada")
        self.ruta.textChanged.connect(self._previsualizar)
        self.ruta.textChanged.connect(lambda *_: self.cambiado.emit())
        fila.addWidget(self.ruta, 1)

        btn = QPushButton("Examinar…")
        btn.setObjectName("btnSecundario")
        btn.clicked.connect(self._elegir)
        fila.addWidget(btn)

        if firma:
            btn_firma = QPushButton("Dibujar firma")
            btn_firma.setObjectName("btnSecundario")
            btn_firma.setToolTip("Dibuja tu firma con el ratón y se usará como imagen")
            btn_firma.clicked.connect(self._dibujar)
            fila.addWidget(btn_firma)
        lay.addLayout(fila)

        self.miniatura = QLabel()
        self.miniatura.setFixedSize(104, 58)
        self.miniatura.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.miniatura.setVisible(False)
        lay.addWidget(self.miniatura)

    # ---------------------------------------------------------------- API
    def valor(self):
        return self.ruta.text().strip()

    def set_valor(self, ruta):
        self.ruta.setText(ruta or "")

    # ------------------------------------------------------------ acciones
    def _elegir(self):
        ruta, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar imagen", "", self.filtro if hasattr(self, "filtro")
            else IMG_POR_DEFECTO)
        if ruta:
            self.set_valor(ruta)

    def _dibujar(self):
        dialogo = DialogoFirma(self)
        if dialogo.exec() and dialogo.ruta:
            self.set_valor(dialogo.ruta)

    def _previsualizar(self):
        ruta = self.valor()
        if not (ruta and os.path.isfile(ruta)):
            self.miniatura.setVisible(False)
            return
        pix = QPixmap(ruta)
        if pix.isNull():
            self.miniatura.setVisible(False)
            return
        self.miniatura.setPixmap(pix.scaled(
            104, 58, Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation))
        self.miniatura.setVisible(True)


class PapelFirma(QWidget):
    """Superficie donde se firma con el ratón (o el lápiz de la tableta)."""

    cambiado = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("papelFirma")
        self.setFixedSize(620, 240)
        self.setCursor(QCursor(Qt.CursorShape.CrossCursor))
        self._trazos = []
        self._actual = None

    def limpiar(self):
        self._trazos = []
        self._actual = None
        self.update()
        self.cambiado.emit()

    def vacio(self):
        return not self._trazos

    def imagen(self) -> QImage:
        """Devuelve la firma como PNG con fondo transparente."""
        imagen = QImage(self.size(), QImage.Format.Format_ARGB32_Premultiplied)
        imagen.fill(Qt.GlobalColor.transparent)
        pintor = QPainter(imagen)
        pintor.setRenderHint(QPainter.RenderHint.Antialiasing)
        self._pintar_trazos(pintor)
        pintor.end()
        return imagen

    def guardar(self, destino):
        return self.imagen().save(destino, "PNG")

    def _pintar_trazos(self, pintor):
        lapiz = QPen(QColor("#12122b"))
        lapiz.setWidth(3)
        lapiz.setCapStyle(Qt.PenCapStyle.RoundCap)
        lapiz.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        pintor.setPen(lapiz)
        for trazo in self._trazos:
            if len(trazo) == 1:
                pintor.drawPoint(trazo[0])
                continue
            for i in range(1, len(trazo)):
                pintor.drawLine(trazo[i - 1], trazo[i])

    def paintEvent(self, evento):
        pintor = QPainter(self)
        pintor.setRenderHint(QPainter.RenderHint.Antialiasing)
        self._pintar_trazos(pintor)
        pintor.end()

    def mousePressEvent(self, evento):
        if evento.button() == Qt.MouseButton.LeftButton:
            self._actual = [evento.position()]
            self._trazos.append(self._actual)
            self.update()

    def mouseMoveEvent(self, evento):
        if self._actual is not None:
            self._actual.append(evento.position())
            self.update()

    def mouseReleaseEvent(self, evento):
        if self._actual is not None:
            self._actual = None
            self.cambiado.emit()


class DialogoFirma(QDialog):
    """Ventana para dibujar la firma a mano y guardarla como PNG transparente."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Dibujar firma · RESG PDF Studio")
        self.ruta = ""
        self._carpeta = tempfile.mkdtemp(prefix="resg_firma_")

        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(18, 16, 18, 16)
        raiz.setSpacing(12)

        titulo = QLabel("Firma aquí")
        titulo.setObjectName("pageTitulo")
        raiz.addWidget(titulo)

        self.papel = PapelFirma()
        self.papel.cambiado.connect(self._validar)
        raiz.addWidget(self.papel)

        fila = QHBoxLayout()
        self.btn_limpiar = QPushButton("Limpiar")
        self.btn_limpiar.setObjectName("btnSecundario")
        self.btn_limpiar.clicked.connect(self.papel.limpiar)
        fila.addWidget(self.btn_limpiar)
        fila.addStretch(1)

        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.setObjectName("btnSecundario")
        btn_cancelar.clicked.connect(self.reject)
        fila.addWidget(btn_cancelar)

        self.btn_usar = QPushButton("Usar esta firma")
        self.btn_usar.setObjectName("btnPrimario")
        self.btn_usar.setEnabled(False)
        self.btn_usar.clicked.connect(self._usar)
        fila.addWidget(self.btn_usar)
        raiz.addLayout(fila)

    def _validar(self):
        self.btn_usar.setEnabled(not self.papel.vacio())

    def _usar(self):
        destino = os.path.join(self._carpeta, "firma.png")
        if self.papel.guardar(destino):
            self.ruta = destino
            self.accept()
