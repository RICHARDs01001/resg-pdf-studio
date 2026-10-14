# -*- coding: utf-8 -*-
"""Hoja de estilos de RESG PDF Studio (tema claro, limpio y con tarjetas).

Todos los colores del tema están aquí para que la interfaz sea coherente:
fondo suave, superficies blancas, acento rojo de acción y morado de apoyo.
"""

# Paleta usada también por los widgets (para pintar y para los iconos).
COLOR_FONDO = "#f5f3fa"
COLOR_SUPERFICIE = "#ffffff"
COLOR_BORDE = "#e8e4f1"
COLOR_TINTA = "#241f33"
COLOR_APAGADO = "#7b7590"
COLOR_ACENTO = "#e5323e"
COLOR_ACENTO_OSCURO = "#c52832"
COLOR_APOYO = "#6c5ce7"
COLOR_OK = "#12894b"

QSS = """
* {
    font-family: "Segoe UI", "Noto Sans", "Inter", sans-serif;
    font-size: 13.5px;
    color: __TINTA__;
}
QMainWindow, QWidget#root, QWidget#home { background: __FONDO__; }
QToolTip {
    background: __TINTA__; color: #ffffff; border: none;
    padding: 6px 9px; border-radius: 6px;
}
QScrollArea { border: none; background: transparent; }
QScrollArea > QWidget > QWidget { background: transparent; }

/* ------------------------------------------------------------- cabecera */
QFrame#header {
    background: __SUPERFICIE__;
    border-bottom: 1px solid __BORDE__;
}
QLabel#marca { font-size: 17px; font-weight: 800; letter-spacing: .3px; }
QLabel#marcaTag { color: __APAGADO__; font-size: 11.5px; }
QLineEdit#buscador {
    background: __FONDO__; border: 1px solid __BORDE__; border-radius: 9px;
    padding: 8px 12px; min-width: 210px;
}
QLineEdit#buscador:focus { border: 1px solid __APOYO__; background: __SUPERFICIE__; }
QPushButton#btnFantasma {
    background: __FONDO__; border: 1px solid __BORDE__; border-radius: 9px;
    padding: 8px 13px; font-weight: 600; color: #4d4761;
}
QPushButton#btnFantasma:hover { background: #ece7fa; border-color: #d3cbf0; }

/* ---------------------------------------------------------------- héroe */
QFrame#hero {
    border-radius: 18px;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                stop:0 #3b2a63, stop:.55 #5b45a8, stop:1 #7a5cf0);
}
QLabel#heroTitulo { color: #ffffff; font-size: 26px; font-weight: 800; }
QLabel#heroTexto { color: #ded7ff; font-size: 13.5px; }
QLabel#heroChip {
    background: rgba(255, 255, 255, 0.16); color: #ffffff;
    border: 1px solid rgba(255, 255, 255, 0.25);
    border-radius: 11px; padding: 5px 11px; font-size: 12px; font-weight: 600;
}
QLineEdit#buscadorHero {
    background: rgba(255, 255, 255, 0.94); border: none; border-radius: 10px;
    padding: 11px 14px; font-size: 14px; color: __TINTA__;
}

/* --------------------------------------------------------- categorías */
QLabel#catTitulo { font-size: 17px; font-weight: 800; }
QLabel#catCuenta {
    color: __APAGADO__; font-size: 11.5px; background: #efecf8;
    border-radius: 9px; padding: 2px 8px;
}
QFrame#catBarra { background: __APOYO__; border-radius: 2px; }
QLabel#sinResultados {
    color: __APAGADO__; font-size: 14px; padding: 40px 0;
}

/* -------------------------------------------------------- tarjetas */
QFrame#ToolCard {
    background: __SUPERFICIE__;
    border: 1px solid __BORDE__;
    border-radius: 14px;
}
QFrame#ToolCard:hover { border: 1px solid #c3b8ee; background: #fdfcff; }
QLabel#cardTitulo { font-size: 14.5px; font-weight: 700; }
QLabel#cardDesc { color: __APAGADO__; font-size: 12px; }
QFrame#cardIcono { background: #f2eefc; border-radius: 12px; }

/* ------------------------------------------------------- página herramienta */
QFrame#topBar {
    background: __SUPERFICIE__; border-bottom: 1px solid __BORDE__;
}
QPushButton#btnVolver {
    background: transparent; border: none; padding: 6px 10px;
    border-radius: 8px; font-weight: 700; color: __APOYO__;
}
QPushButton#btnVolver:hover { background: #f0ecfb; }
QLabel#pageTitulo { font-size: 21px; font-weight: 800; }
QLabel#pageSub { color: __APAGADO__; font-size: 12.5px; }

QFrame#panel {
    background: __SUPERFICIE__; border: 1px solid __BORDE__;
    border-radius: 14px;
}
QLabel#panelTitulo {
    font-weight: 800; font-size: 13px; color: #4d4761;
    letter-spacing: .4px;
}
QLabel#campoLabel { color: #5d5675; font-size: 12px; font-weight: 600; }
QFrame#separador { background: __BORDE__; }

/* ------------------------------------------------------------ controles */
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QPlainTextEdit {
    background: __SUPERFICIE__; border: 1px solid #dcd5ee; border-radius: 9px;
    padding: 7px 10px; selection-background-color: __APOYO__;
}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus,
QPlainTextEdit:focus { border: 1px solid __APOYO__; }
QLineEdit:disabled, QComboBox:disabled { background: #f4f2f9; color: #a49fb5; }
QComboBox::drop-down { border: none; width: 24px; }
QComboBox QAbstractItemView {
    background: __SUPERFICIE__; border: 1px solid #dcd5ee;
    selection-background-color: #ece7fb; padding: 4px;
}
QPlainTextEdit { font-family: "Cascadia Mono", Consolas, monospace; font-size: 12px; }
QCheckBox { spacing: 8px; }
QCheckBox::indicator {
    width: 16px; height: 16px; border-radius: 4px;
    border: 1px solid #cfc7e6; background: __SUPERFICIE__;
}
QCheckBox::indicator:checked { background: __APOYO__; border-color: __APOYO__; }
QSlider::groove:horizontal { height: 5px; background: #e5e0f2; border-radius: 3px; }
QSlider::handle:horizontal {
    background: __APOYO__; width: 15px; height: 15px;
    margin: -5px 0; border-radius: 8px;
}

/* -------------------------------------------------------------- botones */
QPushButton#btnPrimario {
    background: __ACENTO__; color: #ffffff; border: none; border-radius: 11px;
    padding: 13px 20px; font-size: 15px; font-weight: 800;
}
QPushButton#btnPrimario:hover { background: __ACENTO_OSCURO__; }
QPushButton#btnPrimario:disabled { background: #dcd7e8; color: #a5a0b6; }
QPushButton#btnSecundario {
    background: __SUPERFICIE__; border: 1px solid #d8d1ea; border-radius: 9px;
    padding: 8px 14px; font-weight: 600;
}
QPushButton#btnSecundario:hover { background: #f3f0fc; border-color: #c3b8ee; }
QPushButton#btnSecundario:disabled { color: #b3aec3; border-color: #ece8f4; }
QPushButton#btnMini {
    background: #f3f0fc; border: 1px solid #e4defa; border-radius: 8px;
    padding: 6px 11px; font-size: 12.5px; font-weight: 600; color: #554d75;
}
QPushButton#btnMini:hover { background: #e9e3fb; }
QPushButton#btnMini:disabled { color: #b6b1c6; background: #f6f4fb; }
QPushButton#btnPeligro {
    background: transparent; border: none; border-radius: 8px;
    padding: 6px 11px; color: __ACENTO__; font-weight: 700; font-size: 12.5px;
}
QPushButton#btnPeligro:hover { background: #fdecee; }
QPushButton#btnEnlace {
    background: transparent; border: none; color: __APOYO__;
    font-weight: 700; padding: 4px 6px; text-align: left;
}
QPushButton#btnEnlace:hover { color: #4a3cc4; }

/* --------------------------------------------------- miniaturas/preview */
QFrame#panelPreview {
    background: #efeaf8; border: 1px solid #e4ddf3; border-radius: 14px;
}
QListWidget#thumbList { background: transparent; border: none; outline: none; }
QListWidget#thumbList::item {
    background: __SUPERFICIE__;
    border: 1px solid #ded7ee;
    border-radius: 9px;
    margin: 6px;
    padding: 5px;
    color: __APAGADO__;
    font-size: 11px;
}
QListWidget#thumbList::item:hover { border: 1px solid #b7a9ea; }
QListWidget#thumbList::item:selected {
    border: 2px solid __APOYO__; background: #f6f3ff; color: __APOYO__;
}

QFrame#zonaSoltar {
    background: __SUPERFICIE__; border: 2px dashed #d3c9ee; border-radius: 14px;
}
QFrame#zonaSoltar[hover="true"] {
    border: 2px dashed __APOYO__; background: #faf8ff;
}
QLabel#soltarTitulo { font-size: 14.5px; font-weight: 700; }
QLabel#soltarTexto { color: __APAGADO__; font-size: 12px; }

QFrame#chipArchivo {
    background: __SUPERFICIE__; border: 1px solid #e3dcf2; border-radius: 9px;
}
QLabel#chipNombre { font-size: 12.5px; font-weight: 600; }
QLabel#chipDatos { color: __APAGADO__; font-size: 11px; }

/* ------------------------------------------------------------ progreso */
QProgressBar {
    background: #e9e4f4; border: none; border-radius: 6px;
    height: 10px; text-align: center; color: #6b6480; font-size: 10.5px;
}
QProgressBar::chunk { background: __APOYO__; border-radius: 6px; }
QLabel#estado { color: __APAGADO__; font-size: 12px; }

/* ------------------------------------------------------------ resultado */
QFrame#resultOk {
    background: #eafaf1; border: 1px solid #bfe9d2; border-radius: 12px;
}
QLabel#resultOkText { color: #14663c; font-weight: 700; font-size: 13.5px; }
QPushButton#btnAbrir {
    background: __OK__; color: #ffffff; border: none; border-radius: 9px;
    padding: 8px 16px; font-weight: 700;
}
QPushButton#btnAbrir:hover { background: #0f6f3d; }

/* -------------------------------------------------------------- editor */
QGraphicsView#lienzoEditor {
    background: #ded8ec; border: 1px solid #d5cde8; border-radius: 12px;
}
QFrame#barraEditor {
    background: __SUPERFICIE__; border: 1px solid __BORDE__; border-radius: 12px;
}
QWidget#papelFirma {
    background: #ffffff; border: 2px dashed #d3c9ee; border-radius: 12px;
}

/* --------------------------------------------------------------- diálogos */
QDialog { background: __FONDO__; }
QFrame#filaEstado {
    background: __SUPERFICIE__; border: 1px solid __BORDE__; border-radius: 10px;
}
QLabel#estadoNombre { font-weight: 700; font-size: 13px; }
QLabel#estadoDetalle { color: __APAGADO__; font-size: 11.5px; }
QLabel#badgeOk {
    background: #e6f7ee; color: __OK__; border-radius: 8px;
    padding: 3px 9px; font-size: 11.5px; font-weight: 700;
}
QLabel#badgeNo {
    background: #fdecee; color: #b02530; border-radius: 8px;
    padding: 3px 9px; font-size: 11.5px; font-weight: 700;
}
QLabel#badgeOpc {
    background: #fdf3d7; color: #8a6d1a; border-radius: 8px;
    padding: 3px 9px; font-size: 11.5px; font-weight: 700;
}

/* ----------------------------------------------------------- barra estado */
QFrame#statusBar {
    background: __SUPERFICIE__; border-top: 1px solid __BORDE__;
}
QLabel#statusTexto { color: __APAGADO__; font-size: 11.5px; }
"""

QSS = (QSS.replace("__TINTA__", COLOR_TINTA)
          .replace("__FONDO__", COLOR_FONDO)
          .replace("__SUPERFICIE__", COLOR_SUPERFICIE)
          .replace("__BORDE__", COLOR_BORDE)
          .replace("__APAGADO__", COLOR_APAGADO)
          .replace("__ACENTO_OSCURO__", COLOR_ACENTO_OSCURO)
          .replace("__ACENTO__", COLOR_ACENTO)
          .replace("__APOYO__", COLOR_APOYO)
          .replace("__OK__", COLOR_OK))
