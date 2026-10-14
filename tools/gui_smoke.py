# -*- coding: utf-8 -*-
"""Prueba de humo de la INTERFAZ de RESG PDF Studio.

Comprueba, sobre la ventana real y sin pantalla (plataforma «offscreen»):

* que el registro de herramientas es coherente y tiene icono cada una;
* que el inicio construye todas las tarjetas y el buscador filtra;
* que todas las páginas de herramienta se construyen, sin huecos de texto
  plano ni avisos dentro del programa;
* que la vista de miniaturas permite reordenar, girar, marcar y quitar
  páginas, y que ese orden llega de verdad al PDF final (unir);
* que el editor visual coloca elementos y los escribe en el PDF;
* que la firma dibujada a mano se estampa en el documento;
* que el diálogo «Estado del sistema» funciona.

Uso:  python tools/gui_smoke.py              (sin ventanas)
      python tools/gui_smoke.py --capturas   (además guarda capturas/ *.png)
"""
import os
import shutil
import sys
import tempfile
import time
import traceback

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

# Permite ejecutarlo sin pantalla (servidor, CI): plataforma «offscreen».
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def _fuentes_offscreen():
    """Copia un par de fuentes a una carpeta temporal para Qt (offscreen).

    Apuntar a todo C:\\Windows\\Fonts hace fallar el motor de fuentes de Qt y
    las capturas saldrían con cuadros en lugar de letras.
    """
    if (os.environ.get("QT_QPA_PLATFORM") != "offscreen"
            or os.environ.get("QT_QPA_FONTDIR")):
        return ""
    origen = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts")
    destino = os.path.join(tempfile.mkdtemp(prefix="resg_fuentes_"), "fonts")
    copiadas = 0
    try:
        os.makedirs(destino, exist_ok=True)
        for nombre in ("arial.ttf", "segoeui.ttf", "tahoma.ttf",
                       "DejaVuSans.ttf"):
            ruta = os.path.join(origen, nombre)
            if os.path.isfile(ruta):
                shutil.copy2(ruta, os.path.join(destino, nombre))
                copiadas += 1
    except OSError:
        return ""
    if copiadas:
        os.environ["QT_QPA_FONTDIR"] = destino
    return destino if copiadas else ""


FUENTES = _fuentes_offscreen()

import pymupdf  # noqa: E402
from PyQt6.QtCore import QEventLoop, QMimeData, QPointF, Qt  # noqa: E402
from PyQt6.QtGui import QDropEvent, QPixmap  # noqa: E402
from PyQt6.QtWidgets import (QApplication, QLabel, QLineEdit,  # noqa: E402
                             QMessageBox)

from resg_pdf import assets_path  # noqa: E402
from resg_pdf.ui.diagnostico import DialogoEstado, informe  # noqa: E402
from resg_pdf.ui.main_window import MainWindow  # noqa: E402
from resg_pdf.ui.preview import ROL_ROT, ROL_TIPO  # noqa: E402
from resg_pdf.ui.registry import TOOLS  # noqa: E402
from resg_pdf.ui.styles import QSS  # noqa: E402
from resg_pdf.ui.widgets import DialogoFirma, ToolCard  # noqa: E402

TMP = tempfile.mkdtemp(prefix="resg_gui_smoke_")
CAPTURAS = os.path.join(RAIZ, "capturas")
OK, FALLOS, AVISOS = [], [], []


def _log(nombre, correcto, extra=""):
    signo = "[ OK ]" if correcto else "[FALLO]"
    print(f"{signo} {nombre:<38} {extra}", flush=True)
    (OK if correcto else FALLOS).append(nombre)


def _pdf(ruta, texto="Hola RESG PDF Studio", paginas=1):
    """Crea un PDF de ejemplo con texto identificable."""
    doc = pymupdf.open()
    for i in range(paginas):
        pagina = doc.new_page()
        pagina.insert_text((72, 96), f"{texto} {i + 1}", fontsize=16)
    doc.save(ruta)
    doc.close()
    return ruta


def _texto_pagina(ruta, indice=0):
    doc = pymupdf.open(ruta)
    texto = doc[indice].get_text().strip()
    doc.close()
    return texto


def _paginas(ruta):
    doc = pymupdf.open(ruta)
    total = doc.page_count
    doc.close()
    return total


def _bombear(app, pagina, segundos=120):
    """Procesa eventos hasta que el Worker de la página termina."""
    fin = time.time() + segundos
    hilo = pagina.worker
    while hilo is not None and hilo.isRunning() and time.time() < fin:
        app.processEvents(QEventLoop.ProcessEventsFlag.AllEvents, 50)
        time.sleep(0.02)
    fin = time.time() + 5
    while time.time() < fin:
        app.processEvents()
        time.sleep(0.05)
    return hilo is not None and not hilo.isRunning()


def _esperar_miniaturas(app, vista, segundos=30):
    """Espera a que la vista de miniaturas tenga al menos una imagen lista."""
    fin = time.time() + segundos
    while time.time() < fin:
        app.processEvents(QEventLoop.ProcessEventsFlag.AllEvents, 50)
        items = [vista.lista.item(i) for i in range(vista.lista.count())
                 if vista.lista.item(i).data(ROL_TIPO) != "mas"]
        if items and not items[0].icon().isNull():
            return True
        time.sleep(0.05)
    return False


def _captura(widget, nombre):
    """Guarda una captura PNG del widget (solo con --capturas)."""
    if "--capturas" not in sys.argv:
        return ""
    os.makedirs(CAPTURAS, exist_ok=True)
    ruta = os.path.join(CAPTURAS, nombre)
    widget.grab().save(ruta)
    return ruta


def _ejecutar_pagina(app, pagina, salida, segundos=180):
    """Ejecuta la herramienta de la página sin diálogo de guardado."""
    pagina._ruta_salida = lambda: salida
    pagina._ejecutar()
    return _bombear(app, pagina, segundos)


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("RESG PDF Studio")
    app.setStyleSheet(QSS)

    # Los avisos se capturan en vez de abrirse: la prueba no debe quedarse
    # esperando a que alguien pulse un botón.
    QMessageBox.warning = staticmethod(
        lambda *args, **_k: AVISOS.append(
            str(args[2] if len(args) > 2 else args[-1])))
    QMessageBox.information = staticmethod(lambda *args, **_k: None)

    # ------------------------------------------------ 1 · registro correcto
    problemas = []
    ids = set()
    claves_min = {"id", "titulo", "descripcion", "categoria", "icono",
                  "filtro", "multiple", "salida", "opciones", "funcion"}
    for t in TOOLS:
        salida = t.get("salida", "")
        if t["id"] in ids:
            problemas.append(f"{t['id']}: id repetido")
        ids.add(t["id"])
        faltan = claves_min - set(t)
        if faltan:
            problemas.append(f"{t['id']}: faltan {sorted(faltan)}")
        if not (salida in ("pdf", "dir")
                or (salida.startswith("file:.") and len(salida) > 6)):
            problemas.append(f"{t['id']}: salida inesperada ({salida!r})")
        if not callable(t.get("funcion")):
            problemas.append(f"{t['id']}: funcion no invocable")
        for spec in t["opciones"]:
            if not {"k", "t", "label"} <= set(spec):
                problemas.append(f"{t['id']}: opción incompleta")
        if t.get("plan") not in (None, False, "paginas", "rangos"):
            problemas.append(f"{t['id']}: plan inválido ({t.get('plan')!r})")
        if t.get("ext_por_opcion"):
            clave, mapa = t["ext_por_opcion"]
            campos = {s["k"] for s in t["opciones"]}
            if clave not in campos or not isinstance(mapa, dict):
                problemas.append(f"{t['id']}: ext_por_opcion incoherente")
        if t.get("plan") and not (t.get("previsualiza") or t.get("editor")):
            problemas.append(f"{t['id']}: usa plan sin vista de páginas")
        if not os.path.isfile(assets_path("icons", f"{t['icono']}.png")):
            problemas.append(f"{t['id']}: falta el icono {t['icono']}.png")
    _log(f"Registro de las {len(TOOLS)} herramientas", not problemas,
         "; ".join(problemas))

    win = MainWindow()
    win.show()
    app.processEvents()

    # ------------------------------------------------ 2 · inicio y buscador
    tarjetas = win.home.findChildren(ToolCard)
    _log("Parrilla de inicio (tarjetas)", len(tarjetas) == len(TOOLS),
         f"{len(tarjetas)} tarjetas / {len(TOOLS)} herramientas")

    win.home.filtrar("firmar")
    app.processEvents()
    visibles = [t for t in tarjetas if t.isVisible()]
    _log("El buscador filtra herramientas", len(visibles) == 1
         and visibles[0].tool_id == "firmar",
         f"{len(visibles)} resultado(s) para «firmar»")

    win.home.filtrar("zzztalcosaquenoexiste")
    app.processEvents()
    _log("Buscador sin resultados avisa",
         win.home.lbl_vacio.isVisible()
         and not any(t.isVisible() for t in tarjetas))
    win.buscador_top.setText("")
    win.home.filtrar("")
    app.processEvents()

    # ------------------------------------------------ 3 · todas las páginas
    problemas = []
    textos_largos = []
    for t in TOOLS:
        try:
            win.abrir_tool(t["id"])
            pagina = win.stack.currentWidget()
            if pagina is not win._paginas[t["id"]] or pagina.tool["id"] != t["id"]:
                problemas.append(f"{t['id']}: no se abrió su página")
                continue
            if pagina.btn_run.isEnabled() != bool(t.get("sin_entrada")):
                problemas.append(f"{t['id']}: botón «Ejecutar» mal activado")
            if set(pagina._leer_opciones()) != {s["k"] for s in t["opciones"]}:
                problemas.append(f"{t['id']}: opciones mal leídas")
            for spec in t["opciones"]:
                if spec["t"] != "image":
                    continue
                caja = pagina._campos[spec["k"]][1]
                if not callable(getattr(caja, "valor", None)):
                    problemas.append(f"{t['id']}: campo de imagen sin valor()")
                    continue
                if not caja.findChild(QLineEdit):
                    problemas.append(f"{t['id']}: campo de imagen sin caja")
            for etiqueta in pagina.findChildren(QLabel):
                if etiqueta.objectName() == "nota":
                    problemas.append(f"{t['id']}: conserva un aviso «nota»")
                if len(etiqueta.text()) > 200:
                    textos_largos.append(f"{t['id']}: {etiqueta.text()[:40]}…")
        except Exception as e:  # noqa: BLE001
            problemas.append(f"{t['id']}: {type(e).__name__}: {e}")
    _log(f"Páginas de las {len(TOOLS)} herramientas", not problemas,
         "; ".join(problemas))
    _log("Sin bloques de texto largo dentro de las páginas", not textos_largos,
         "; ".join(textos_largos))

    sin_entrada = [t["titulo"] for t in TOOLS if t.get("sin_entrada")]
    _log("Herramientas que funcionan sin archivos", bool(sin_entrada),
         ", ".join(sin_entrada))

    # ------------------------------------------------ 4 · vista de miniaturas
    muestra_a = _pdf(os.path.join(TMP, "a.pdf"), "Documento A", 2)
    muestra_b = _pdf(os.path.join(TMP, "b.pdf"), "Documento B", 1)
    win.abrir_tool("unir")
    pagina = win._paginas["unir"]
    vista = pagina.archivos
    vista.add_files([muestra_a, muestra_b])
    hay_miniaturas = _esperar_miniaturas(app, vista)
    _log("Miniaturas al añadir archivos",
         vista.paginas_totales() == 3 and hay_miniaturas
         and vista.files() == [muestra_a, muestra_b],
         f"{vista.paginas_totales()} páginas de {len(vista.files())} archivos")

    plan_inicial = vista.plan()
    _log("El plan de páginas conserva el orden",
         [p["page"] for p in plan_inicial] == [0, 1, 0]
         and [os.path.basename(p["file"]) for p in plan_inicial]
         == ["a.pdf", "a.pdf", "b.pdf"])

    # arrastrar la última miniatura a la primera posición (arrastre real)
    # La prueba corre sin pantalla real: hay que forzar la maquetación para
    # que el punto donde se suelta caiga sobre una miniatura concreta.
    vista.lista.resize(1000, 620)
    app.processEvents()
    vista.lista.clearSelection()
    vista.lista.item(2).setSelected(True)
    objetivo = vista.lista.visualItemRect(vista.lista.item(0)).center()
    evento = QDropEvent(QPointF(objetivo), Qt.DropAction.MoveAction,
                        QMimeData(), Qt.MouseButton.LeftButton,
                        Qt.KeyboardModifier.NoModifier)
    vista.lista.dropEvent(evento)
    app.processEvents()
    plan = vista.plan()
    _log("Arrastrar una miniatura cambia el orden",
         len(plan) == 3 and plan[0]["file"] == muestra_b,
         f"primera página: {os.path.basename(plan[0]['file'])}")

    vista.lista.clearSelection()
    vista.lista.item(0).setSelected(True)
    vista.girar(90)
    _log("Girar una página desde las miniaturas",
         vista.plan()[0]["rot"] == 90)

    vista.marcar_todo(False)
    sin_marcar = vista.paginas_marcadas()
    vista.lista.item(0).setCheckState(Qt.CheckState.Checked)
    _log("Marcar y desmarcar páginas",
         sin_marcar == 0 and vista.paginas_marcadas() == 1,
         f"{vista.paginas_marcadas()} marcada(s)")

    vista.lista.clearSelection()
    vista.lista.clearSelection()
    vista.lista.item(0).setSelected(True)
    vista.duplicar_seleccion()
    _log("Duplicar una página", vista.paginas_totales() == 4,
         f"{vista.paginas_totales()} páginas en total")
    vista.lista.clearSelection()
    vista.lista.item(1).setSelected(True)
    vista.quitar_seleccion()
    _log("Quitar una página de la lista", vista.paginas_totales() == 3,
         f"{vista.paginas_totales()} páginas en total")

    _captura(win, "02_miniaturas.png")

    # ------------------------------------------------ 5 · unir con el orden visual
    vista.marcar_todo(True)
    for i in range(vista.lista.count()):
        vista.lista.item(i).setData(ROL_ROT, 0)
    salida = os.path.join(TMP, "gui_unido.pdf")
    termino = _ejecutar_pagina(app, pagina, salida)
    primero = _texto_pagina(salida) if os.path.isfile(salida) else ""
    _log("Unir PDF respetando el orden visual",
         termino and _paginas(salida) == 3 and "Documento B" in primero,
         f"{_paginas(salida) if os.path.isfile(salida) else 0} páginas, "
         f"1ª: {primero[:18]!r}")
    _captura(win, "03_unir_resultado.png")

    # ------------------------------------------------ 6 · rotar desde la interfaz
    win.abrir_tool("rotar")
    rotar = win._paginas["rotar"]
    rotar.archivos.add_files([muestra_a])
    _esperar_miniaturas(app, rotar.archivos)
    rotar.archivos.marcar_todo(True)
    for i in range(rotar.archivos.lista.count()):
        rotar.archivos.lista.item(i).setSelected(True)
    rotar.archivos.girar(90)
    salida_rotada = os.path.join(TMP, "gui_rotado.pdf")
    termino = _ejecutar_pagina(app, rotar, salida_rotada)
    doc = pymupdf.open(salida_rotada) if os.path.isfile(salida_rotada) else None
    grados = [p.rotation for p in doc] if doc else []
    if doc:
        doc.close()
    _log("Rotar páginas desde las miniaturas",
         termino and grados == [90, 90], f"rotaciones {grados}")

    # ------------------------------------------------ 7 · eliminar desmarcando
    win.abrir_tool("eliminar")
    eliminar = win._paginas["eliminar"]
    eliminar.archivos.add_files([muestra_a])
    _esperar_miniaturas(app, eliminar.archivos)
    eliminar.archivos.lista.item(1).setCheckState(Qt.CheckState.Unchecked)
    salida_edit = os.path.join(TMP, "gui_sin_pagina2.pdf")
    termino = _ejecutar_pagina(app, eliminar, salida_edit)
    _log("Eliminar páginas desmarcadas",
         termino and _paginas(salida_edit) == 1,
         f"{_paginas(salida_edit) if os.path.isfile(salida_edit) else 0} "
         "páginas conservadas")

    # ------------------------------------------------ 8 · editor visual
    win.abrir_tool("editar")
    pagina_editor = win._paginas["editar"]
    pagina_editor.archivos.add_files([muestra_a])
    app.processEvents()
    editor = pagina_editor.editor
    editor.anadir_texto()
    editor.anadir_forma("rectangulo")
    editor.anadir_linea()
    editor.campo_url.setText("https://resg-tech.example")
    editor.anadir_enlace()
    elementos = editor.elementos()
    _log("Editor: colocar elementos en la página",
         len(elementos) == 4
         and {e["tipo"] for e in elementos} == {"texto", "rectangulo",
                                                "linea", "enlace"}
         and all(0 <= e["x"] <= 100 and 0 <= e["y"] <= 100
                 for e in elementos),
         f"{len(elementos)} elementos colocados")
    editor.lienzo.scene().items()          # la escena tiene contenido
    editor.quitar_ultimo()
    _log("Editor: deshacer el último elemento", len(editor.elementos()) == 3)
    editor.anadir_enlace()                 # se vuelve a poner el enlace
    _log("Editor: el enlace vuelve a añadirse", len(editor.elementos()) == 4)
    salida_editor = os.path.join(TMP, "gui_editor.pdf")
    termino = _ejecutar_pagina(app, pagina_editor, salida_editor)
    enlaces = 0
    if os.path.isfile(salida_editor):
        doc = pymupdf.open(salida_editor)
        enlaces = sum(len(p.get_links()) for p in doc)
        total_paginas = doc.page_count
        doc.close()
    else:
        total_paginas = 0
    _log("Editor: escribir los elementos en el PDF",
         termino and total_paginas == 2 and enlaces >= 1,
         f"{total_paginas} páginas, {enlaces} enlace(s)")
    _captura(win, "04_editor.png")

    # ------------------------------------------------ 9 · firma dibujada
    dialogo = DialogoFirma(win)
    dialogo.papel._trazos = [[QPointF(14, 130), QPointF(120, 40),
                              QPointF(240, 150), QPointF(360, 60)]]
    dialogo._validar()
    valido = dialogo.btn_usar.isEnabled()
    dialogo._usar()
    firma_ok = (bool(dialogo.ruta) and os.path.isfile(dialogo.ruta)
                and os.path.getsize(dialogo.ruta) > 0)
    _log("Firma dibujada a mano (PNG transparente)", valido and firma_ok,
         os.path.basename(dialogo.ruta) if firma_ok else "sin archivo")

    win.abrir_tool("firmar")
    firmar = win._paginas["firmar"]
    firmar.archivos.add_files([muestra_a])
    firmar._campos["imagen"][1].set_valor(dialogo.ruta)
    salida_firma = os.path.join(TMP, "gui_firmado.pdf")
    termino = _ejecutar_pagina(app, firmar, salida_firma)
    _log("Estampar la firma en el PDF",
         termino and _paginas(salida_firma) == 2,
         f"{_paginas(salida_firma) if os.path.isfile(salida_firma) else 0} "
         "páginas")

    # ------------------------------------------------ 10 · resumen local
    largo = os.path.join(TMP, "largo.pdf")
    doc = pymupdf.open()
    for i in range(2):
        pagina = doc.new_page()
        parrafos = " ".join(
            f"La gestión documental local permite trabajar sin internet y sin "
            f"cuentas de usuario. Párrafo {n} de la página {i + 1} con datos "
            "suficientes para que el resumen automático tenga de dónde elegir."
            for n in range(10))
        pagina.insert_textbox(pymupdf.Rect(60, 60, 540, 770), parrafos,
                              fontsize=11)
    doc.save(largo)
    doc.close()
    win.abrir_tool("resumir")
    resumir = win._paginas["resumir"]
    resumir.archivos.add_files([largo])
    salida_resumen = os.path.join(TMP, "gui_resumen.md")
    termino = _ejecutar_pagina(app, resumir, salida_resumen)
    contenido = ""
    if os.path.isfile(salida_resumen):
        with open(salida_resumen, encoding="utf-8") as fh:
            contenido = fh.read()
    _log("Resumir PDF desde la interfaz",
         termino and "Ideas clave" in contenido
         and "Palabras clave" in contenido, f"{len(contenido)} caracteres")

    # ------------------------------------------------ 11 · estado del sistema
    filas, texto = informe()
    dlg = DialogoEstado(win)
    dlg.show()
    app.processEvents()
    dlg._copiar()
    _log("Diálogo Estado del sistema",
         len(filas) >= 10 and "Estado" in dlg.windowTitle()
         and "RESG PDF Studio" in texto
         and QApplication.clipboard().text() in texto,
         f"{len(filas)} componentes comprobados")
    _captura(dlg, "05_estado.png")
    dlg.close()

    _log("Sin avisos de error en los flujos probados", not AVISOS,
         "; ".join(AVISOS[:3]))

    # ------------------------------------------------ 12 · capturas
    win.ir_inicio()
    app.processEvents()
    _captura(win, "01_inicio_ventana.png")
    _captura(win.home, "00_inicio.png")
    _captura(win._paginas["unir"], "06_herramienta_unir.png")

    print("\n" + "=" * 62)
    print(f"OK: {len(OK)}   FALLOS: {len(FALLOS)}")
    if FALLOS:
        print("FALLARON: " + ", ".join(FALLOS))
    if "--capturas" in sys.argv:
        print(f"Capturas en: {CAPTURAS}")
    win.close()
    shutil.rmtree(TMP, ignore_errors=True)
    return 1 if FALLOS else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:  # noqa: BLE001
        traceback.print_exc()
        sys.exit(2)
