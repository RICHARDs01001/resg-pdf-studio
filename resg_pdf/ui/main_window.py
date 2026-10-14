# -*- coding: utf-8 -*-
"""Ventana principal: cabecera, inicio con buscador y parrilla de herramientas."""
from __future__ import annotations

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QIcon, QKeySequence, QPixmap, QShortcut
from PyQt6.QtWidgets import (QFrame, QHBoxLayout, QLabel, QLineEdit,
                             QMainWindow, QPushButton, QScrollArea,
                             QStackedWidget, QVBoxLayout, QWidget)

from .. import __version__, assets_path
from .diagnostico import mostrar_estado
from .pages import ToolPage
from .registry import CATEGORIAS, TOOLS
from .widgets import FlowLayout, ToolCard


class HomePage(QWidget):
    """Inicio: presentación, buscador y tarjetas agrupadas por categoría."""

    def __init__(self, abrir_tool, parent=None):
        super().__init__(parent)
        self.setObjectName("home")
        self.secciones = []
        self.tarjetas = []

        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(0, 0, 0, 0)
        raiz.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        cuerpo = QWidget()
        lay = QVBoxLayout(cuerpo)
        lay.setContentsMargins(26, 20, 26, 26)
        lay.setSpacing(22)
        scroll.setWidget(cuerpo)
        raiz.addWidget(scroll, 1)

        lay.addWidget(self._heroe())

        # La parrilla de tarjetas se construye DESPUÉS de mostrar la ventana
        # (ver MainWindow.__init__ -> QTimer.singleShot). Montar las ~40
        # tarjetas tardaba ~0,7 s y hacía esperar con la pantalla vacía.
        self._lay = lay
        self._abrir_tool = abrir_tool
        self._grilla_lista = False

        self.lbl_vacio = QLabel("No hay ninguna herramienta con ese nombre.")
        self.lbl_vacio.setObjectName("sinResultados")
        self.lbl_vacio.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_vacio.setVisible(False)

    def construir_grilla(self):
        """Crea las secciones y tarjetas de herramientas.

        Se llama justo después de que la ventana sea visible, para que el
        programa aparezca al instante aunque tenga muchas herramientas.
        """
        if self._grilla_lista:
            return
        self._grilla_lista = True
        lay = self._lay

        for categoria in CATEGORIAS:
            herramientas = [t for t in TOOLS if t["categoria"] == categoria]
            if not herramientas:
                continue
            seccion = QWidget()
            slay = QVBoxLayout(seccion)
            slay.setContentsMargins(0, 0, 0, 0)
            slay.setSpacing(12)
            slay.addLayout(self._titulo_categoria(categoria, len(herramientas)))
            contenedor = QWidget()
            flujo = FlowLayout(contenedor, margen=0, espaciado=14)
            tarjetas = []
            for herramienta in herramientas:
                tarjeta = ToolCard(herramienta)
                tarjeta.clicked.connect(self._abrir_tool)
                flujo.addWidget(tarjeta)
                tarjetas.append(tarjeta)
            slay.addWidget(contenedor)
            lay.addWidget(seccion)
            self.secciones.append((categoria, seccion, tarjetas))
            self.tarjetas.extend(tarjetas)

        lay.addWidget(self.lbl_vacio)
        lay.addStretch(1)

    # ---------------------------------------------------------------- héroe
    def _heroe(self):
        heroe = QFrame()
        heroe.setObjectName("hero")
        lay = QVBoxLayout(heroe)
        lay.setContentsMargins(28, 24, 28, 24)
        lay.setSpacing(10)

        titulo = QLabel("Todas tus herramientas PDF, en tu equipo")
        titulo.setObjectName("heroTitulo")
        lay.addWidget(titulo)

        texto = QLabel("Sin subir archivos, sin cuentas y sin límites: todo se "
                       "procesa dentro de tu ordenador.")
        texto.setObjectName("heroTexto")
        lay.addWidget(texto)
        lay.addSpacing(4)

        self.buscador = QLineEdit()
        self.buscador.setObjectName("buscadorHero")
        self.buscador.setPlaceholderText(
            "Busca una herramienta: unir, comprimir, firmar…")
        self.buscador.setClearButtonEnabled(True)
        self.buscador.textChanged.connect(self.filtrar)
        lay.addWidget(self.buscador)
        lay.addSpacing(6)

        chips = QHBoxLayout()
        chips.setSpacing(8)
        for etiqueta in (f"{len(TOOLS)} herramientas",
                         "Sin límite de archivos", "Sin registro",
                         "Funciona sin internet"):
            chip = QLabel(etiqueta)
            chip.setObjectName("heroChip")
            chips.addWidget(chip)
        chips.addStretch(1)
        lay.addLayout(chips)
        return heroe

    def _titulo_categoria(self, categoria, total):
        fila = QHBoxLayout()
        fila.setSpacing(10)
        barra = QFrame()
        barra.setObjectName("catBarra")
        barra.setFixedSize(5, 20)
        fila.addWidget(barra)
        titulo = QLabel(categoria)
        titulo.setObjectName("catTitulo")
        fila.addWidget(titulo)
        cuenta = QLabel(str(total))
        cuenta.setObjectName("catCuenta")
        fila.addWidget(cuenta)
        fila.addStretch(1)
        return fila

    # ------------------------------------------------------------- buscador
    def filtrar(self, texto):
        """Muestra solo las herramientas que coinciden con la búsqueda."""
        if not self._grilla_lista:
            self.construir_grilla()
        texto = (texto or "").strip().lower()
        mostradas = 0
        for _categoria, seccion, tarjetas in self.secciones:
            visibles = 0
            for tarjeta in tarjetas:
                coincide = (not texto
                            or texto in tarjeta.titulo.lower()
                            or texto in tarjeta.descripcion.lower()
                            or texto in tarjeta.tool_id.lower()
                            or texto in tarjeta.categoria.lower())
                tarjeta.setVisible(coincide)
                visibles += 1 if coincide else 0
            seccion.setVisible(visibles > 0)
            mostradas += visibles
        self.lbl_vacio.setVisible(mostradas == 0)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("RESG PDF Studio")
        self.setWindowIcon(QIcon(assets_path("icono.png")))
        self.resize(1340, 860)
        self.setMinimumSize(1080, 680)

        raiz = QWidget()
        raiz.setObjectName("root")
        self.setCentralWidget(raiz)
        lay = QVBoxLayout(raiz)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        lay.addWidget(self._cabecera())

        self.stack = QStackedWidget()
        lay.addWidget(self.stack, 1)
        self.home = HomePage(self.abrir_tool)
        self.stack.addWidget(self.home)
        self._paginas = {}

        lay.addWidget(self._pie())

        QShortcut(QKeySequence("Ctrl+F"), self,
                  activated=self.home.buscador.setFocus)
        QShortcut(QKeySequence("Escape"), self, activated=self.ir_inicio)

        # La ventana ya está lista: rellenamos la parrilla en cuanto el bucle
        # de eventos tenga un hueco, para que la apertura se sienta inmediata.
        QTimer.singleShot(0, self.home.construir_grilla)

    def _cabecera(self):
        header = QFrame()
        header.setObjectName("header")
        header.setFixedHeight(72)
        h = QHBoxLayout(header)
        h.setContentsMargins(20, 10, 20, 10)
        h.setSpacing(12)

        logo = QLabel()
        logo.setPixmap(QPixmap(assets_path("icono.png")).scaled(
            40, 40, Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation))
        logo.setCursor(Qt.CursorShape.PointingHandCursor)
        logo.mousePressEvent = lambda _e: self.ir_inicio()
        h.addWidget(logo)

        col = QVBoxLayout()
        col.setSpacing(0)
        nombre = QLabel("RESG PDF Studio")
        nombre.setObjectName("marca")
        lema = QLabel("Herramientas PDF locales · RESG-tech")
        lema.setObjectName("marcaTag")
        col.addWidget(nombre)
        col.addWidget(lema)
        h.addLayout(col)

        h.addSpacing(20)
        self.buscador_top = QLineEdit()
        self.buscador_top.setObjectName("buscador")
        self.buscador_top.setPlaceholderText("Buscar herramienta…")
        self.buscador_top.setClearButtonEnabled(True)
        self.buscador_top.textChanged.connect(self._buscar_desde_arriba)
        h.addWidget(self.buscador_top)
        h.addStretch(1)

        self.btn_estado = QPushButton("⚙  Estado del sistema")
        self.btn_estado.setObjectName("btnFantasma")
        self.btn_estado.setToolTip("Qué motores opcionales están disponibles")
        self.btn_estado.clicked.connect(lambda: mostrar_estado(self))
        h.addWidget(self.btn_estado)
        return header

    def _pie(self):
        pie = QFrame()
        pie.setObjectName("statusBar")
        pie.setFixedHeight(28)
        p = QHBoxLayout(pie)
        p.setContentsMargins(18, 0, 18, 0)
        version = QLabel(f"v{__version__} · {len(TOOLS)} herramientas · "
                         "procesado 100 % local")
        version.setObjectName("statusTexto")
        p.addWidget(version)
        p.addStretch(1)
        aviso = QLabel("Sin cuentas · sin límites · sin subir archivos")
        aviso.setObjectName("statusTexto")
        p.addWidget(aviso)
        return pie

    # ---------------------------------------------------------------- páginas
    def _buscar_desde_arriba(self, texto):
        self.home.buscador.setText(texto)
        self.ir_inicio()

    def ir_inicio(self):
        self.stack.setCurrentWidget(self.home)

    def abrir_tool(self, tool_id: str):
        if tool_id not in self._paginas:
            tool = next(t for t in TOOLS if t["id"] == tool_id)
            pagina = ToolPage(tool, self.ir_inicio)
            self._paginas[tool_id] = pagina
            self.stack.addWidget(pagina)
        self.stack.setCurrentWidget(self._paginas[tool_id])

    def closeEvent(self, evento):
        for pagina in self._paginas.values():
            pagina.cerrar()
        super().closeEvent(evento)