# -*- coding: utf-8 -*-
"""Página de herramienta: se construye sola a partir del registro.

La distribución es la de las webs de referencia: a la izquierda los archivos
(con sus miniaturas si la herramienta lo permite) y a la derecha las opciones
con el botón grande de acción. Así no quedan huecos vacíos y todo se ve en una
sola pantalla.
"""
from __future__ import annotations

import os
import subprocess
import sys

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (QCheckBox, QComboBox, QFileDialog, QFrame,
                             QHBoxLayout, QLabel, QLineEdit, QMessageBox,
                             QPlainTextEdit, QProgressBar, QPushButton,
                             QScrollArea, QSpinBox, QVBoxLayout, QWidget)

from .. import assets_path
from .editor import EditorPDF
from .preview import VistaPrevia
from .widgets import CampoImagen, FileListWidget, Worker


class ToolPage(QWidget):
    """Página de una herramienta con archivos, opciones y botón de acción."""

    def __init__(self, tool: dict, volver, parent=None):
        super().__init__(parent)
        self.tool = tool
        self.worker = None
        self._campos = {}
        self._ruta_final = ""
        self.editor = None

        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(0, 0, 0, 0)
        raiz.setSpacing(0)
        raiz.addWidget(self._barra_superior(volver))

        cuerpo = QWidget()
        cuerpo.setObjectName("home")
        lay = QHBoxLayout(cuerpo)
        lay.setContentsMargins(22, 18, 22, 18)
        lay.setSpacing(18)
        lay.addWidget(self._columna_entrada(), 1)
        lay.addWidget(self._panel_con_scroll())
        raiz.addWidget(cuerpo, 1)

    def _panel_con_scroll(self):
        """Columna derecha: el panel de opciones, compacto y con desplazamiento.

        Así, cuando una herramienta tiene pocas opciones, la tarjeta queda
        recogida arriba (sin huecos vacíos en medio) y, si tiene muchas, se
        puede desplazar sin salirse de la ventana.
        """
        panel = self._panel_opciones()
        contenedor = QWidget()
        v = QVBoxLayout(contenedor)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)
        v.addWidget(panel)
        v.addStretch(1)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFixedWidth(372)
        scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setWidget(contenedor)
        return scroll

    # ------------------------------------------------------------ cabecera
    def _barra_superior(self, volver):
        barra = QFrame()
        barra.setObjectName("topBar")
        barra.setFixedHeight(66)
        h = QHBoxLayout(barra)
        h.setContentsMargins(14, 8, 18, 8)
        h.setSpacing(12)

        btn_volver = QPushButton("‹  Todas las herramientas")
        btn_volver.setObjectName("btnVolver")
        btn_volver.clicked.connect(volver)
        h.addWidget(btn_volver)

        icono = QLabel()
        icono.setPixmap(self._pixmap_icono())
        h.addWidget(icono)

        col = QVBoxLayout()
        col.setSpacing(1)
        titulo = QLabel(self.tool["titulo"])
        titulo.setObjectName("pageTitulo")
        descripcion = self.tool["descripcion"]
        if len(descripcion) > 96:
            descripcion = descripcion[:93].rstrip() + "…"
        sub = QLabel(descripcion)
        sub.setObjectName("pageSub")
        col.addWidget(titulo)
        col.addWidget(sub)
        h.addLayout(col)
        h.addStretch(1)
        return barra

    def _pixmap_icono(self):
        from PyQt6.QtGui import QPixmap
        ruta = assets_path("icons", f"{self.tool['icono']}.png")
        return QPixmap(ruta).scaled(34, 34, Qt.AspectRatioMode.KeepAspectRatio,
                                    Qt.TransformationMode.SmoothTransformation)

    # ------------------------------------------------------ columna izquierda
    def _columna_entrada(self):
        columna = QWidget()
        lay = QVBoxLayout(columna)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(12)

        marco = QFrame()
        marco.setObjectName("panelPreview" if (self.tool.get("previsualiza")
                                               or self.tool.get("editor"))
                            else "panel")
        ml = QVBoxLayout(marco)
        ml.setContentsMargins(12, 12, 12, 12)
        ml.setSpacing(10)

        if self.tool.get("editor"):
            self.archivos = FileListWidget(self.tool["filtro"], False)
            self.archivos.changed.connect(self._cargar_editor)
            self.editor = EditorPDF()
            self.editor.cambiado.connect(self._validar)
            ml.addWidget(self.archivos)
            ml.addWidget(self.editor, 1)
        elif self.tool.get("previsualiza"):
            self.archivos = VistaPrevia(self.tool["filtro"],
                                        bool(self.tool["multiple"]))
            self.archivos.marcar_todo(
                self.tool.get("seleccion_inicial", "todas") != "ninguna")
            ml.addWidget(self.archivos, 1)
        else:
            self.archivos = FileListWidget(self.tool["filtro"],
                                           bool(self.tool["multiple"]))
            ml.addWidget(self.archivos, 1)

        self.archivos.changed.connect(self._validar)
        lay.addWidget(marco, 1)
        lay.addWidget(self._zona_estado())
        return columna

    def _zona_estado(self):
        zona = QWidget()
        lay = QVBoxLayout(zona)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)

        self.barra = QProgressBar()
        self.barra.setVisible(False)
        lay.addWidget(self.barra)

        self.lbl_estado = QLabel("")
        self.lbl_estado.setObjectName("estado")
        self.lbl_estado.setVisible(False)
        lay.addWidget(self.lbl_estado)

        self.resultado = QFrame()
        self.resultado.setObjectName("resultOk")
        rl = QHBoxLayout(self.resultado)
        rl.setContentsMargins(14, 10, 12, 10)
        rl.setSpacing(12)
        self.resultado_txt = QLabel()
        self.resultado_txt.setObjectName("resultOkText")
        self.resultado_txt.setWordWrap(True)
        btn_abrir = QPushButton("Abrir resultado")
        btn_abrir.setObjectName("btnAbrir")
        btn_abrir.clicked.connect(self._abrir_resultado)
        rl.addWidget(self.resultado_txt, 1)
        rl.addWidget(btn_abrir)
        self.resultado.setVisible(False)
        lay.addWidget(self.resultado)
        return zona

    # ------------------------------------------------------ panel de opciones
    def _panel_opciones(self):
        panel = QFrame()
        panel.setObjectName("panel")
        panel.setFixedWidth(344)
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.setSpacing(12)

        cabecera = QLabel("OPCIONES")
        cabecera.setObjectName("panelTitulo")
        lay.addWidget(cabecera)

        for spec in self.tool["opciones"]:
            campo = self._crear_campo(spec)
            self._campos[spec["k"]] = (spec, campo)
            fila = QVBoxLayout()
            fila.setSpacing(4)
            etiqueta = QLabel(spec["label"])
            etiqueta.setObjectName("campoLabel")
            etiqueta.setWordWrap(True)
            fila.addWidget(etiqueta)
            fila.addWidget(campo)
            lay.addLayout(fila)

        lay.addWidget(self._bloque_resumen())

        self.chk_auto = QCheckBox("Guardar junto al archivo original")
        self.chk_auto.setToolTip("No vuelve a preguntar dónde guardar: usa la "
                                 "misma carpeta con el sufijo _"
                                 + self.tool["id"])
        self.chk_auto.stateChanged.connect(self._actualizar_resumen)
        lay.addWidget(self.chk_auto)

        self.btn_run = QPushButton(self.tool.get(
            "accion", self.tool["titulo"]))
        self.btn_run.setObjectName("btnPrimario")
        self.btn_run.setMinimumHeight(46)
        if self.tool.get("pista"):
            self.btn_run.setToolTip(self.tool["pista"])
        self.btn_run.clicked.connect(self._ejecutar)
        lay.addWidget(self.btn_run)
        self.btn_run.setEnabled(bool(self.tool.get("sin_entrada")))
        self._actualizar_resumen()
        return panel

    def _bloque_resumen(self):
        """Ficha con lo que se va a procesar y dónde se guardará."""
        marco = QFrame()
        marco.setObjectName("filaEstado")
        lay = QVBoxLayout(marco)
        lay.setContentsMargins(13, 11, 13, 11)
        lay.setSpacing(5)

        titulo = QLabel("RESUMEN")
        titulo.setObjectName("panelTitulo")
        lay.addWidget(titulo)

        self.lbl_res_archivos = QLabel("")
        self.lbl_res_paginas = QLabel("")
        self.lbl_res_salida = QLabel("")
        for etiqueta in (self.lbl_res_archivos, self.lbl_res_paginas,
                         self.lbl_res_salida):
            etiqueta.setObjectName("estadoDetalle")
            etiqueta.setWordWrap(True)
            lay.addWidget(etiqueta)
        return marco

    def _actualizar_resumen(self, *_args):
        archivos = self.archivos.files()
        if archivos:
            nombres = ", ".join(os.path.basename(a) for a in archivos[:2])
            if len(archivos) > 2:
                nombres += f" y {len(archivos) - 2} más"
            self.lbl_res_archivos.setText(f"Archivos: {nombres}")
        else:
            self.lbl_res_archivos.setText("Aún no has añadido archivos")

        detalle = ""
        if hasattr(self.archivos, "paginas_totales"):
            detalle = (f"Páginas: {self.archivos.paginas_marcadas()} "
                       f"de {self.archivos.paginas_totales()}")
        elif self.editor is not None and self.editor.abierto():
            detalle = f"Elementos colocados: {len(self.editor.elementos())}"
        self.lbl_res_paginas.setText(detalle)

        salida = self.tool["salida"]
        if salida == "dir":
            formato = "una carpeta"
        elif salida == "pdf":
            formato = "un PDF"
        else:
            formato = f"un {salida.split('.')[-1].upper()}"
        donde = ("junto al original" if self.chk_auto.isChecked()
                 else "se pregunta al ejecutar")
        self.lbl_res_salida.setText(f"Salida: {formato} · {donde}")

    def _crear_campo(self, spec: dict):
        """Crea el control correspondiente al tipo de opción."""
        tipo = spec["t"]
        if tipo == "combo":
            caja = QComboBox()
            for clave, texto in spec["choices"].items():
                caja.addItem(texto, clave)
            return caja
        if tipo in ("int", "float"):
            caja = QSpinBox()
            caja.setRange(int(spec.get("min", 0)), int(spec.get("max", 9999)))
            caja.setValue(int(spec.get("default", 0)))
            return caja
        if tipo == "multiline":
            caja = QPlainTextEdit()
            caja.setPlaceholderText(spec.get("placeholder", ""))
            caja.setMinimumHeight(96)
            return caja
        if tipo == "image":
            campo = CampoImagen(firma=bool(spec.get("firma")),
                                filtro=spec.get("filtro", ""))
            campo.cambiado.connect(self._validar)
            return campo
        if tipo == "check":
            caja = QCheckBox(spec.get("label_check", "Activar"))
            caja.setChecked(bool(spec.get("default", False)))
            return caja
        caja = QLineEdit(str(spec.get("default", "")))
        if spec.get("placeholder"):
            caja.setPlaceholderText(spec["placeholder"])
        if tipo == "password":
            caja.setEchoMode(QLineEdit.EchoMode.Password)
        if tipo == "pages":
            caja.setPlaceholderText("Ej.: 1-3,5 (vacío = todas)")
        return caja

    # -------------------------------------------------------------- lectura
    def _leer_opciones(self):
        opts = {}
        for k, (spec, campo) in self._campos.items():
            tipo = spec["t"]
            if tipo == "combo":
                opts[k] = campo.currentData()
            elif tipo in ("int", "float"):
                opts[k] = campo.value()
            elif tipo == "multiline":
                opts[k] = campo.toPlainText()
            elif tipo == "image":
                opts[k] = campo.valor()
            elif tipo == "check":
                opts[k] = campo.isChecked()
            else:
                opts[k] = campo.text()
        return opts

    def _rangos_visuales(self):
        """Traduce las páginas marcadas en las miniaturas a '1-3,5'."""
        numeros = sorted({int(p["page"]) + 1 for p in self.archivos.plan()})
        if not numeros:
            return ""
        partes = []
        inicio = anterior = numeros[0]
        for numero in numeros[1:]:
            if numero == anterior + 1:
                anterior = numero
                continue
            partes.append(f"{inicio}-{anterior}" if inicio != anterior
                          else str(inicio))
            inicio = anterior = numero
        partes.append(f"{inicio}-{anterior}" if inicio != anterior
                      else str(inicio))
        return ",".join(partes)

    def _opciones_completas(self):
        """Opciones + la organización visual (plan de páginas o rangos)."""
        opts = self._leer_opciones()
        modo = self.tool.get("plan")
        if modo and hasattr(self.archivos, "plan"):
            pasos = self.archivos.plan()
            if modo == "paginas":
                escrito = str(opts.get("orden")
                              or opts.get("paginas") or "").strip()
                if pasos and not escrito:
                    opts["plan"] = pasos
            elif modo == "rangos":
                clave = "rangos" if "rangos" in opts else "paginas"
                if not str(opts.get(clave, "")).strip():
                    derivado = self._rangos_visuales()
                    if derivado:
                        opts[clave] = derivado
        if self.tool.get("editor") and self.editor is not None:
            opts["elementos"] = self.editor.elementos()
        return opts

    def _cargar_editor(self):
        if self.editor is None:
            return
        archivos = self.archivos.files()
        if not archivos:
            self.editor.cerrar()
            return
        self.editor.cargar(archivos[0])

    # ------------------------------------------------------------ ejecución
    def _validar(self):
        if self.tool.get("sin_entrada"):
            self.btn_run.setEnabled(True)
            self._actualizar_resumen()
            return
        habilitado = bool(self.archivos.files())
        if habilitado and self.editor is not None:
            habilitado = self.editor.abierto()
        self.btn_run.setEnabled(habilitado)
        self._actualizar_resumen()

    def _ruta_salida(self):
        salida = self.tool["salida"]
        archivos = self.archivos.files()
        base = (os.path.splitext(os.path.basename(archivos[0]))[0]
                if archivos else "salida")
        sufijo = "_" + self.tool["id"]
        if salida == "dir":
            if self.chk_auto.isChecked() and archivos:
                destino = os.path.join(os.path.dirname(archivos[0]),
                                       base + sufijo)
                os.makedirs(destino, exist_ok=True)
                return destino
            return QFileDialog.getExistingDirectory(
                self, "Carpeta donde guardar los resultados")
        ext = ".pdf" if salida == "pdf" else salida.split(":", 1)[1]
        if self.tool.get("ext_por_opcion"):
            clave, mapa = self.tool["ext_por_opcion"]
            entrada = self._campos.get(clave)
            if entrada is not None:
                ext = mapa.get(entrada[1].currentData(), ext)
        if self.chk_auto.isChecked() and archivos:
            return os.path.join(os.path.dirname(archivos[0]),
                                base + sufijo + ext)
        etiqueta = ext.lstrip(".").upper()
        ruta, _ = QFileDialog.getSaveFileName(
            self, "Guardar resultado como", base + sufijo + ext,
            f"Archivos {etiqueta} (*{ext})")
        if ruta and not ruta.lower().endswith(ext):
            ruta += ext
        return ruta

    def _ejecutar(self):
        archivos = self.archivos.files()
        if not archivos and not self.tool.get("sin_entrada"):
            return
        opts = self._opciones_completas()
        out = self._ruta_salida()
        if not out:
            return
        self.resultado.setVisible(False)
        self.barra.setVisible(True)
        self.barra.setValue(0)
        self.lbl_estado.setVisible(True)
        self.lbl_estado.setText("Procesando…")
        self.btn_run.setEnabled(False)
        self.worker = Worker(self.tool["funcion"], archivos, out, opts, self)
        self.worker.progreso.connect(self._al_progreso)
        self.worker.terminado.connect(self._ok)
        self.worker.fallo.connect(self._error)
        self.worker.start()

    def _al_progreso(self, pct, mensaje=""):
        self.barra.setValue(int(pct))
        if mensaje:
            self.lbl_estado.setText(mensaje)

    def _ok(self, ruta):
        self._ruta_final = ruta
        self.barra.setValue(100)
        self.lbl_estado.setText("¡Listo!")
        self.btn_run.setEnabled(True)
        self.resultado_txt.setText("Resultado guardado en:\n" + ruta)
        self.resultado.setVisible(True)

    def _error(self, mensaje):
        self.barra.setVisible(False)
        self.lbl_estado.setVisible(False)
        self.btn_run.setEnabled(True)
        QMessageBox.warning(self, self.tool["titulo"],
                            "No se pudo completar la operación:\n\n" + mensaje)

    def _abrir_resultado(self):
        ruta = self._ruta_final
        if not ruta or not os.path.exists(ruta):
            return
        if sys.platform == "win32":
            os.startfile(ruta)  # noqa: S606
        elif sys.platform == "darwin":
            subprocess.Popen(["open", ruta])
        else:
            destino = ruta if os.path.isdir(ruta) else os.path.dirname(ruta)
            subprocess.Popen(["xdg-open", destino])

    def cerrar(self):
        """Libera los hilos de la página (miniaturas y trabajo en curso)."""
        if hasattr(self.archivos, "cerrar"):
            self.archivos.cerrar()
        if self.editor is not None:
            self.editor.cerrar()
        if self.worker is not None and self.worker.isRunning():
            self.worker.wait(3000)
