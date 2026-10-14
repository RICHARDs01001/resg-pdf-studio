# -*- coding: utf-8 -*-
"""Lógica de todas las herramientas PDF de RESG PDF Studio.

Cada función recibe:
    files    lista de rutas de entrada
    out      ruta de salida (archivo o carpeta, según la herramienta)
    opts     dict con las opciones elegidas en la interfaz
    progress callback opcional progress(porcentaje:int, mensaje:str)

Todas devuelven la ruta del resultado (str).
"""
from __future__ import annotations

import glob
import io
import math
import os
import shutil
import subprocess
import tempfile

import pymupdf

# ---------------------------------------------------------------------------
# pypdf se importa de forma DIFERIDA a propósito.
# Importarlo al arrancar costaba ~0,7 s de espera antes de ver la ventana y
# solo lo usan unas pocas herramientas (unir, extraer, proteger, firmar…).
# Se carga la primera vez que se llama a PdfReader/PdfWriter.
# ---------------------------------------------------------------------------
_PYPDF = None


def _pypdf():
    """Devuelve ``(PdfReader, PdfWriter)`` importando pypdf solo al usarlo."""
    global _PYPDF
    if _PYPDF is None:
        from pypdf import PdfReader, PdfWriter
        _PYPDF = (PdfReader, PdfWriter)
    return _PYPDF


def PdfReader(*args, **kwargs):  # noqa: N802 - nombre histórico de la API
    """Igual que ``pypdf.PdfReader`` pero cargando el módulo solo al usarlo."""
    return _pypdf()[0](*args, **kwargs)


def PdfWriter(*args, **kwargs):  # noqa: N802 - nombre histórico de la API
    """Igual que ``pypdf.PdfWriter`` pero cargando el módulo solo al usarlo."""
    return _pypdf()[1](*args, **kwargs)


def _prog(progress, pct, msg=""):
    if progress:
        progress(int(pct), msg)


# ===================================================== PROGRAMAS AUXILIARES
# Rutas típicas donde se instalan en Windows los programas opcionales.
_RUTAS_SOFFICE = (
    r"C:\Program Files\LibreOffice\program\soffice.exe",
    r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
)
_RUTAS_TESSERACT = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    os.path.expandvars(r"%LOCALAPPDATA%\Programs\Tesseract-OCR\tesseract.exe"),
    os.path.expandvars(r"%LOCALAPPDATA%\Tesseract-OCR\tesseract.exe"),
    os.path.expandvars(r"%PROGRAMFILES%\Tesseract-OCR\tesseract.exe"),
)


def _buscar_exe(nombres, rutas=()):
    """Devuelve la ruta de un ejecutable del PATH o de rutas conocidas."""
    for n in nombres:
        ruta = shutil.which(n)
        if ruta:
            return ruta
    for ruta in rutas:
        if ruta and os.path.exists(ruta):
            return ruta
    return None


def buscar_soffice():
    return _buscar_exe(("soffice", "libreoffice"), _RUTAS_SOFFICE)


def buscar_tesseract():
    return _buscar_exe(("tesseract",), _RUTAS_TESSERACT)


def buscar_ghostscript():
    exe = _buscar_exe(("gswin64c", "gswin32c", "gs"))
    if exe:
        return exe
    for patron in (r"C:\Program Files\gs\gs*\bin\gswin64c.exe",
                   r"C:\Program Files (x86)\gs\gs*\bin\gswin32c.exe",
                   r"C:\Program Files\gs\gs*\bin\gswin32c.exe"):
        encontrados = sorted(glob.glob(patron), reverse=True)
        if encontrados:
            return encontrados[0]
    return None


def estado_entorno():
    """Informa de qué motores/formatos están disponibles en este equipo."""
    def _mod(nombre):
        try:
            __import__(nombre)
            return True
        except Exception:
            return False

    return {
        "libreoffice": buscar_soffice(),
        "tesseract": buscar_tesseract(),
        "ghostscript": buscar_ghostscript(),
        "pdf2docx": _mod("pdf2docx"),
        "python-pptx": _mod("pptx"),
        "openpyxl": _mod("openpyxl"),
        "pdfplumber": _mod("pdfplumber"),
        "pywin32": _mod("win32com"),
        "argostranslate": _mod("argostranslate"),
    }


# ================================================================ ORGANIZAR
def unir_pdf(files, out, opts, progress=None):
    if opts.get("plan"):
        return aplicar_plan(files, out, opts, progress)
    writer = PdfWriter()
    for i, f in enumerate(files):
        reader = PdfReader(f)
        if reader.is_encrypted:
            reader.decrypt(opts.get("password", "") or "")
        for page in reader.pages:
            writer.add_page(page)
        _prog(progress, 90 * (i + 1) / len(files), os.path.basename(f))
    with open(out, "wb") as fh:
        writer.write(fh)
    _prog(progress, 100, "Listo")
    return out


def dividir_pdf(files, out, opts, progress=None):
    """opts: modo = 'rangos' | 'cada_pagina' | 'tamano'; rangos = '1-3,5';"""
    src = files[0]
    reader = PdfReader(src)
    if reader.is_encrypted:
        reader.decrypt(opts.get("password", "") or "")
    n = len(reader.pages)
    modo = opts.get("modo", "rangos")
    os.makedirs(out, exist_ok=True)
    base = os.path.splitext(os.path.basename(src))[0]
    hechos = []

    def guardar(paginas, nombre):
        w = PdfWriter()
        for p in paginas:
            w.add_page(reader.pages[p])
        ruta = os.path.join(out, nombre)
        with open(ruta, "wb") as fh:
            w.write(fh)
        hechos.append(ruta)

    if modo == "cada_pagina":
        for i in range(n):
            guardar([i], f"{base}_pagina_{i + 1}.pdf")
            _prog(progress, 100 * (i + 1) / n)
    elif modo == "tamano":
        cada = max(1, int(opts.get("cada", 1)))
        idx, parte = 0, 1
        while idx < n:
            grupo = list(range(idx, min(idx + cada, n)))
            guardar(grupo, f"{base}_parte_{parte}.pdf")
            idx += cada
            parte += 1
            _prog(progress, 100 * idx / n)
    else:  # rangos
        rangos = parse_rangos(opts.get("rangos", ""), n)
        for i, r in enumerate(rangos):
            guardar(r, f"{base}_rango_{i + 1}.pdf")
            _prog(progress, 100 * (i + 1) / len(rangos))
    return out


def parse_rangos(texto, n):
    """'1-3,5,8-' -> lista de listas de índices (base 0)."""
    grupos = []
    for trozo in texto.split(","):
        trozo = trozo.strip()
        if not trozo:
            continue
        if "-" in trozo:
            a, b = trozo.split("-", 1)
            a = int(a) if a else 1
            b = int(b) if b else n
            grupos.append(list(range(a - 1, min(b, n))))
        else:
            grupos.append([int(trozo) - 1])
    if not grupos:
        raise ValueError("Indica al menos un rango, p. ej.: 1-3,5")
    return grupos


def ordenar_pdf(files, out, opts, progress=None):
    """opts: orden = '3,1,2' (nuevo orden, base 1). Páginas omitidas se eliminan.

    Si llega un plan desde la vista de miniaturas (opts['plan']), se usa ese
    plan: las páginas se colocan en el orden visual que eligió el usuario.
    """
    if opts.get("plan"):
        return aplicar_plan(files, out, opts, progress)
    reader = PdfReader(files[0])
    if reader.is_encrypted:
        reader.decrypt(opts.get("password", "") or "")
    n = len(reader.pages)
    orden = [int(x.strip()) for x in opts.get("orden", "").split(",") if x.strip()]
    if not orden:
        raise ValueError("Indica el nuevo orden, p. ej.: 3,1,2")
    if min(orden) < 1 or max(orden) > n:
        raise ValueError(f"Las páginas deben estar entre 1 y {n}")
    w = PdfWriter()
    for i, p in enumerate(orden):
        w.add_page(reader.pages[p - 1])
        _prog(progress, 90 * (i + 1) / len(orden))
    with open(out, "wb") as fh:
        w.write(fh)
    return out


def rotar_pdf(files, out, opts, progress=None):
    if opts.get("plan"):
        return aplicar_plan(files, out, opts, progress)
    grados = int(opts.get("grados", 90))
    paginas = opts.get("paginas", "").strip()
    doc = pymupdf.open(files[0])
    if doc.needs_pass:
        doc.authenticate(opts.get("password", "") or "")
    indices = range(doc.page_count)
    if paginas:
        indices = [i for grupo in parse_rangos(paginas, doc.page_count) for i in grupo]
    indices = list(indices)
    for i, p in enumerate(indices):
        page = doc[p]
        page.set_rotation((page.rotation + grados) % 360)
        _prog(progress, 90 * (i + 1) / len(indices))
    doc.save(out)
    doc.close()
    return out


# ================================================================ OPTIMIZAR
def comprimir_pdf(files, out, opts, progress=None):
    """nivel: 'bajo' (máxima compresión) | 'medio' | 'alto' (máxima calidad)."""
    nivel = opts.get("nivel", "medio")
    dpi_img = {"bajo": 72, "medio": 120, "alto": 200}[nivel]
    calidad = {"bajo": 45, "medio": 65, "alto": 85}[nivel]
    src = files[0]
    doc = pymupdf.open(src)
    if doc.needs_pass:
        doc.authenticate(opts.get("password", "") or "")
    _prog(progress, 40, "Limpiando y reescribiendo el documento")

    # método robusto: reescribir con máxima limpieza + recompresión de streams
    doc.save(out, garbage=4, deflate=True, deflate_images=True,
             deflate_fonts=True, clean=True)
    doc.close()

    # si el nivel es bajo/medio, segunda pasada re-renderizando imágenes vía subset
    if nivel in ("bajo", "medio"):
        try:
            _recomprimir_imagenes(out, dpi_img, calidad)
        except Exception:
            pass
    _prog(progress, 100, "Listo")
    return out


def _recomprimir_imagenes(ruta_pdf, dpi, calidad):
    """Segunda pasada: baja la resolución de las imágenes incrustadas.

    Reescala cada imagen para que su lado mayor no supere ``dpi * 4`` píxeles
    y la vuelve a guardar como JPEG con la calidad indicada. Si algo falla en
    una imagen concreta se ignora, para no romper el documento completo.
    """
    from PIL import Image

    doc = pymupdf.open(ruta_pdf)
    objetivo = max(200, dpi * 4)
    modificado = False
    for pno in range(doc.page_count):
        page = doc[pno]
        try:
            infos = page.get_image_info(xrefs=True)
        except Exception:
            continue
        for info in infos:
            xref = info.get("xref", 0)
            if not xref:
                continue
            w, h = info.get("width", 0), info.get("height", 0)
            if max(w, h) <= objetivo:
                continue
            try:
                pix = pymupdf.Pixmap(doc, xref)
                if pix.alpha:
                    pix = pymupdf.Pixmap(pix, 0)
                if pix.n > 3:
                    pix = pymupdf.Pixmap(pymupdf.csRGB, pix)
                img = Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGB")
                escala = objetivo / float(max(w, h))
                nuevo = (max(1, int(w * escala)), max(1, int(h * escala)))
                img = img.resize(nuevo, Image.LANCZOS)
                buf = io.BytesIO()
                img.save(buf, format="JPEG", quality=calidad, optimize=True)
                page.replace_image(xref, stream=buf.getvalue())
                modificado = True
            except Exception:
                continue
    if not modificado:
        doc.close()
        return
    tmp = ruta_pdf + ".tmp"
    doc.save(tmp, garbage=4, deflate=True)
    doc.close()
    shutil.move(tmp, ruta_pdf)


def reparar_pdf(files, out, opts, progress=None):
    """Intenta recuperar un PDF dañado reescribiéndolo por completo."""
    src = files[0]
    try:
        doc = pymupdf.open(src)
    except Exception:
        # último recurso: copia bruta con pymupdf en modo tolerante
        doc = pymupdf.open("pdf", open(src, "rb").read())
    _prog(progress, 40, "Analizando documento")
    doc.save(out, garbage=4, clean=True, deflate=True)
    doc.close()
    _prog(progress, 100, "Reparado")
    return out


# =============================================================== CONVERTIR
def pdf_a_jpg(files, out, opts, progress=None):
    dpi = int(opts.get("dpi", 150))
    formato = opts.get("formato", "jpg").lower()
    os.makedirs(out, exist_ok=True)
    hechos = []
    for fi, f in enumerate(files):
        doc = pymupdf.open(f)
        if doc.needs_pass:
            doc.authenticate(opts.get("password", "") or "")
        base = os.path.splitext(os.path.basename(f))[0]
        for i, page in enumerate(doc):
            pix = page.get_pixmap(dpi=dpi)
            ruta = os.path.join(out, f"{base}_pag_{i + 1}.{formato}")
            pix.save(ruta, jpg_quality=int(opts.get("calidad", 85)))
            hechos.append(ruta)
            _prog(progress, 100 * (fi + (i + 1) / doc.page_count) / len(files))
        doc.close()
    return out


def jpg_a_pdf(files, out, opts, progress=None):
    if opts.get("plan"):
        return aplicar_plan(files, out, opts, progress)
    orientacion = opts.get("orientacion", "auto")
    margen = float(opts.get("margen", 0))  # puntos
    doc = pymupdf.open()
    for i, f in enumerate(files):
        img = pymupdf.open(f)
        w, h = img[0].rect.width, img[0].rect.height
        if orientacion == "horizontal" and h > w:
            w, h = h, w
        elif orientacion == "vertical" and w > h:
            w, h = h, w
        page = doc.new_page(width=w + 2 * margen, height=h + 2 * margen)
        page.insert_image(pymupdf.Rect(margen, margen, margen + w, margen + h),
                          filename=f)
        img.close()
        _prog(progress, 90 * (i + 1) / len(files))
    doc.save(out)
    doc.close()
    return out


def pdf_a_word(files, out, opts, progress=None):
    from pdf2docx import Converter
    doc = None
    try:
        cv = Converter(files[0])
        cv.convert(out)
        cv.close()
    except Exception:
        if doc:
            doc.close()
        raise
    _prog(progress, 100, "Listo")
    return out


def pdf_a_ppt(files, out, opts, progress=None):
    """Cada página del PDF se convierte en una diapositiva a tamaño completo."""
    from pptx import Presentation
    from pptx.util import Emu
    dpi = int(opts.get("dpi", 150))
    doc = pymupdf.open(files[0])
    if doc.needs_pass:
        doc.authenticate(opts.get("password", "") or "")
    prs = Presentation()
    blank = prs.slide_layouts[6]
    tmp = tempfile.mkdtemp()
    for i, page in enumerate(doc):
        pix = page.get_pixmap(dpi=dpi)
        img = os.path.join(tmp, f"p{i}.png")
        pix.save(img)
        w_emu = Emu(int(page.rect.width * 914400 / 72))
        h_emu = Emu(int(page.rect.height * 914400 / 72))
        prs.slide_width, prs.slide_height = w_emu, h_emu
        slide = prs.slides.add_slide(blank)
        slide.shapes.add_picture(img, 0, 0, w_emu, h_emu)
        _prog(progress, 90 * (i + 1) / doc.page_count)
    prs.save(out)
    doc.close()
    shutil.rmtree(tmp, ignore_errors=True)
    return out


def pdf_a_excel(files, out, opts, progress=None):
    """Extrae las tablas del PDF a un libro de Excel (una hoja por tabla)."""
    import pdfplumber
    from openpyxl import Workbook
    wb = Workbook()
    wb.remove(wb.active)
    total = 0
    with pdfplumber.open(files[0], password=opts.get("password", "") or None) as pdf:
        n = len(pdf.pages)
        for i, page in enumerate(pdf.pages):
            tablas = page.extract_tables() or []
            for j, tabla in enumerate(tablas):
                hoja = wb.create_sheet(f"p{i + 1}_tabla{j + 1}")
                for fila in tabla:
                    hoja.append(["" if c is None else str(c) for c in fila])
                total += 1
            _prog(progress, 90 * (i + 1) / n)
    if total == 0:
        # sin tablas: vuelca el texto, una hoja por página
        with pdfplumber.open(files[0], password=opts.get("password", "") or None) as pdf:
            for i, page in enumerate(pdf.pages):
                hoja = wb.create_sheet(f"pagina_{i + 1}")
                for linea in (page.extract_text() or "").splitlines():
                    hoja.append([linea])
    wb.save(out)
    return out


def _soffice_convert(files, out_dir, progress=None, fmt="pdf"):
    """Conversión vía LibreOffice (soffice) en modo headless."""
    soffice = buscar_soffice()
    if not soffice:
        raise RuntimeError(
            "No se encontró LibreOffice. Instálalo (gratis) desde "
            "https://es.libreoffice.org/descarga/ para usar esta conversión.")
    os.makedirs(out_dir, exist_ok=True)
    for i, f in enumerate(files):
        subprocess.run([soffice, "--headless", "--convert-to", fmt,
                        "--outdir", out_dir, f],
                       check=True, capture_output=True, timeout=300)
        _prog(progress, 100 * (i + 1) / len(files), os.path.basename(f))
    return out_dir


def office_a_pdf(files, out, opts, progress=None):
    """Word/PowerPoint/Excel -> PDF.

    Usa LibreOffice si está instalado (máxima fidelidad). Si no lo está,
    convierte con un motor Python interno, así la herramienta funciona
    sin instalar nada extra.
    """
    if buscar_soffice():
        if len(files) == 1 and out.lower().endswith(".pdf"):
            tmpdir = tempfile.mkdtemp()
            _soffice_convert(files, tmpdir, progress)
            generado = os.path.join(
                tmpdir,
                os.path.splitext(os.path.basename(files[0]))[0] + ".pdf")
            shutil.move(generado, out)
            shutil.rmtree(tmpdir, ignore_errors=True)
            return out
        return _soffice_convert(files, out, progress)
    return _office_a_pdf_interno(files, out, progress)


# ------------------------------------------ motor interno (sin LibreOffice)
_CSS_BASE = (
    "<style>body{font-family:sans-serif;font-size:11pt;color:#222222;}"
    "h1{font-size:20pt;}h2{font-size:16pt;}h3{font-size:13pt;}"
    "table{border-collapse:collapse;}"
    "td,th{border:1px solid #999999;padding:4px 6px;font-size:10pt;}"
    "th{background:#eeeeee;}"
    ".slide{border-bottom:2px solid #cccccc;padding-bottom:10px;"
    "margin-bottom:14px;}"
    ".meta{color:#888888;font-size:9pt;}</style>"
)


def _esc(t):
    """Escapa texto para incrustarlo en HTML."""
    return (str(t).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;"))


def _render_html_a_pdf(html, out, mediabox=None, margen=36, dir_recursos=None):
    """Dibuja un HTML en un PDF (multipágina) con el motor Story de PyMuPDF."""
    mediabox = mediabox or pymupdf.paper_rect("a4")
    area = mediabox + (margen, margen, -margen, -margen)
    archivo = pymupdf.Archive(dir_recursos) if dir_recursos else None
    story = pymupdf.Story(html=html, archive=archivo)
    writer = pymupdf.DocumentWriter(out)
    fin = 0
    paginas = 0
    while not fin:
        device = writer.begin_page(mediabox)
        fin, _ = story.place(area)
        story.draw(device)
        writer.end_page()
        paginas += 1
        if paginas >= 1000:          # límite de seguridad: nunca colgarse
            break
    writer.close()
    return out


def _html_desde_docx(ruta):
    """Word (.docx) -> HTML manteniendo orden de párrafos, estilos y tablas."""
    import docx
    from docx.oxml.table import CT_Tbl
    from docx.oxml.text.paragraph import CT_P
    from docx.table import Table
    from docx.text.paragraph import Paragraph

    documento = docx.Document(ruta)
    cuerpo = documento.element.body

    def inline(parrafo):
        trozos = []
        for run in parrafo.runs:
            t = _esc(run.text)
            if not t:
                continue
            if run.bold:
                t = f"<b>{t}</b>"
            if run.italic:
                t = f"<i>{t}</i>"
            trozos.append(t)
        return "".join(trozos) or _esc(parrafo.text)

    partes = ["<html><head>", _CSS_BASE, "</head><body>"]
    for hijo in cuerpo.iterchildren():
        if isinstance(hijo, CT_P):
            parrafo = Paragraph(hijo, documento)
            if not parrafo.text.strip():
                continue
            estilo = (parrafo.style.name or "").lower()
            if estilo.startswith("title"):
                partes.append(f"<h1>{inline(parrafo)}</h1>")
            elif estilo.startswith("heading"):
                try:
                    nivel = int(estilo.split()[-1])
                except (ValueError, IndexError):
                    nivel = 2
                nivel = min(max(nivel + 1, 2), 4)
                partes.append(f"<h{nivel}>{inline(parrafo)}</h{nivel}>")
            else:
                partes.append(f"<p>{inline(parrafo)}</p>")
        elif isinstance(hijo, CT_Tbl):
            tabla = Table(hijo, documento)
            partes.append("<table>")
            for fila in tabla.rows:
                partes.append("<tr>")
                for celda in fila.cells:
                    partes.append(f"<td>{_esc(celda.text)}</td>")
                partes.append("</tr>")
            partes.append("</table>")
    partes.append("</body></html>")
    return "".join(partes), pymupdf.paper_rect("a4")


def _html_desde_xlsx(ruta):
    """Excel (.xlsx) -> HTML con una tabla por hoja (en horizontal)."""
    from openpyxl import load_workbook
    libro = load_workbook(ruta, data_only=True)
    partes = ["<html><head>", _CSS_BASE, "</head><body>"]
    hojas = 0
    for hoja in libro.worksheets:
        filas = [f for f in hoja.iter_rows(values_only=True)
                 if any(c is not None and str(c).strip() != "" for c in f)]
        if not filas:
            continue
        hojas += 1
        partes.append(f"<h2>{_esc(hoja.title)}</h2><table>")
        for i, fila in enumerate(filas):
            etiqueta = "th" if i == 0 else "td"
            celdas = "".join(
                f"<{etiqueta}>{'' if c is None else _esc(c)}</{etiqueta}>"
                for c in fila)
            partes.append(f"<tr>{celdas}</tr>")
        partes.append("</table>")
    if hojas == 0:
        partes.append("<p>(El libro no contiene datos.)</p>")
    partes.append("</body></html>")
    a4 = pymupdf.paper_rect("a4")
    # Las hojas de cálculo se leen mejor en A4 apaisado
    return "".join(partes), pymupdf.Rect(0, 0, a4.height, a4.width)


def _html_desde_pptx(ruta):
    """PowerPoint (.pptx) -> HTML: una sección por diapositiva + imágenes."""
    from pptx import Presentation

    prs = Presentation(ruta)
    ancho = prs.slide_width or 9144000
    alto = prs.slide_height or 6858000
    # tamaño de página en puntos (1 punto = 12700 EMU)
    caja = pymupdf.Rect(0, 0, float(ancho) / 12700.0, float(alto) / 12700.0)
    recursos = tempfile.mkdtemp()
    partes = ["<html><head>", _CSS_BASE, "</head><body>"]
    for idx, slide in enumerate(prs.slides, start=1):
        partes.append("<div class='slide'>")
        partes.append(f"<p class='meta'>Diapositiva {idx}</p>")
        try:
            titulo = slide.shapes.title
        except Exception:
            titulo = None
        for forma in slide.shapes:
            try:
                texto = ""
                if forma.has_text_frame:
                    texto = forma.text_frame.text.strip()
                if texto:
                    etiqueta = "h1" if forma is titulo else "p"
                    partes.append("".join(
                        f"<{etiqueta}>{_esc(linea)}</{etiqueta}>"
                        for linea in texto.split("\n") if linea.strip()))
                    continue
                img = getattr(forma, "image", None)
                if img is not None:
                    archivo = os.path.join(
                        recursos, f"d{idx}_{forma.shape_id}.{img.ext}")
                    with open(archivo, "wb") as manejador:
                        manejador.write(img.blob)
                    partes.append(
                        f"<img src='{os.path.basename(archivo)}' "
                        "style='max-width:100%;margin:6px 0;'/>")
            except Exception:
                continue
        partes.append("</div>")
    partes.append("</body></html>")
    return "".join(partes), caja, recursos


def _office_a_pdf_interno(files, out, progress=None):
    """Convierte Word/Excel/PowerPoint a PDF con librerías Python puras."""
    varios = len(files) > 1 or os.path.isdir(out)
    if varios:
        os.makedirs(out, exist_ok=True)
    resultado = out
    for i, f in enumerate(files):
        ext = os.path.splitext(f)[1].lower()
        recursos = None
        html = None
        caja = None
        try:
            if ext == ".docx":
                html, caja = _html_desde_docx(f)
            elif ext == ".xlsx":
                html, caja = _html_desde_xlsx(f)
            elif ext == ".pptx":
                html, caja, recursos = _html_desde_pptx(f)
            else:
                raise RuntimeError(
                    f"El formato «{ext}» no se puede convertir sin LibreOffice. "
                    "Guarda el archivo como .docx, .xlsx o .pptx, o instala "
                    "LibreOffice (gratis) desde https://es.libreoffice.org.")
            if varios:
                destino = os.path.join(
                    out, os.path.splitext(os.path.basename(f))[0] + ".pdf")
                resultado = out
            else:
                destino = out
                resultado = destino
            _render_html_a_pdf(html, destino, mediabox=caja,
                               dir_recursos=recursos)
        finally:
            if recursos:
                shutil.rmtree(recursos, ignore_errors=True)
        _prog(progress, 100 * (i + 1) / len(files), os.path.basename(f))
    return resultado


def html_a_pdf(files, out, opts, progress=None):
    """Convierte HTML (archivos .html o una URL en opts['url']) a PDF.

    Usa el motor HTML de PyMuPDF: no requiere dependencias extra.
    """
    fuentes = list(files)
    url = (opts.get("url") or "").strip()
    html = None
    if url:
        import urllib.request
        if not url.lower().startswith(("http://", "https://")):
            url = "https://" + url
        try:
            peticion = urllib.request.Request(
                url, headers={"User-Agent": "Mozilla/5.0"})
            html = urllib.request.urlopen(peticion, timeout=30).read().decode(
                "utf-8", "replace")
        except Exception as e:
            raise RuntimeError(f"No se pudo descargar la página «{url}»: {e}")
        fuentes = [None]

    if not fuentes:
        raise ValueError("Añade archivos .html/.htm o escribe una dirección web.")

    if len(fuentes) == 1 and out.lower().endswith(".pdf"):
        destino = out
    else:
        os.makedirs(out, exist_ok=True)
        destino = None

    for i, f in enumerate(fuentes):
        if html is not None:
            contenido = html
            nombre = destino or os.path.join(out, "pagina_web.pdf")
            recursos = None
        else:
            with open(f, encoding="utf-8", errors="replace") as fh:
                contenido = fh.read()
            nombre = destino or os.path.join(
                out, os.path.splitext(os.path.basename(f))[0] + ".pdf")
            recursos = os.path.dirname(os.path.abspath(f))
        try:
            _render_html_a_pdf(contenido, nombre, dir_recursos=recursos)
        except Exception as e:
            raise RuntimeError(f"No se pudo convertir el HTML: {e}")
        _prog(progress, 100 * (i + 1) / len(fuentes))
    return destino or out


def pdf_a_markdown(files, out, opts, progress=None):
    doc = pymupdf.open(files[0])
    if doc.needs_pass:
        doc.authenticate(opts.get("password", "") or "")
    lineas = []
    for i, page in enumerate(doc):
        lineas.append(f"\n\n<!-- Página {i + 1} -->\n")
        bloques = page.get_text("dict")["blocks"]
        for b in bloques:
            if b.get("type") != 0:
                continue
            for linea in b["lines"]:
                texto = "".join(s["text"] for s in linea["spans"]).strip()
                if not texto:
                    continue
                size = max(s["size"] for s in linea["spans"])
                bold = any("Bold" in s["font"] for s in linea["spans"])
                if size >= 20:
                    lineas.append(f"\n# {texto}\n")
                elif size >= 16:
                    lineas.append(f"\n## {texto}\n")
                elif size >= 13 and bold:
                    lineas.append(f"\n### {texto}\n")
                elif bold:
                    lineas.append(f"**{texto}**  ")
                else:
                    lineas.append(texto + "  ")
        _prog(progress, 95 * (i + 1) / doc.page_count)
    doc.close()
    with open(out, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lineas))
    return out


# ================================================================ SEGURIDAD
def proteger_pdf(files, out, opts, progress=None):
    clave = opts.get("clave", "")
    if not clave:
        raise ValueError("Escribe una contraseña para proteger el PDF.")
    reader = PdfReader(files[0])
    if reader.is_encrypted:
        reader.decrypt(opts.get("password", "") or "")
    w = PdfWriter()
    for p in reader.pages:
        w.add_page(p)
    _prog(progress, 60, "Cifrando")
    w.encrypt(user_password=clave,
              owner_password=opts.get("clave_propietario") or clave,
              algorithm="AES-256")
    with open(out, "wb") as fh:
        w.write(fh)
    _prog(progress, 100, "Protegido")
    return out


def desbloquear_pdf(files, out, opts, progress=None):
    resultados = []
    multiple = len(files) > 1
    if multiple:
        os.makedirs(out, exist_ok=True)
    for i, f in enumerate(files):
        reader = PdfReader(f)
        if reader.is_encrypted:
            if not reader.decrypt(opts.get("password", "") or ""):
                raise ValueError(
                    f"Contraseña incorrecta para {os.path.basename(f)}")
        w = PdfWriter()
        for p in reader.pages:
            w.add_page(p)
        destino = (os.path.join(out, os.path.splitext(os.path.basename(f))[0]
                                + "_desbloqueado.pdf") if multiple else out)
        with open(destino, "wb") as fh:
            w.write(fh)
        resultados.append(destino)
        _prog(progress, 100 * (i + 1) / len(files))
    return out if multiple else resultados[0]


# ================================================================== EDITAR
_POSICIONES_9 = {
    "superior izquierda": (0.05, 0.05), "superior centro": (0.5, 0.05),
    "superior derecha": (0.95, 0.05), "centro izquierda": (0.05, 0.5),
    "centro": (0.5, 0.5), "centro derecha": (0.95, 0.5),
    "inferior izquierda": (0.05, 0.95), "inferior centro": (0.5, 0.95),
    "inferior derecha": (0.95, 0.95),
}


def _paginas_objetivo(doc, opts):
    paginas = (opts.get("paginas") or "").strip()
    if not paginas or paginas.lower() == "todas":
        return list(range(doc.page_count))
    return sorted({i for g in parse_rangos(paginas, doc.page_count) for i in g})


def marca_agua_pdf(files, out, opts, progress=None):
    """opts: tipo='texto'|'imagen', texto, imagen, opacidad(0-100), rotacion,
    posicion, tamano."""
    doc = pymupdf.open(files[0])
    if doc.needs_pass:
        doc.authenticate(opts.get("password", "") or "")
    opacidad = max(5, min(100, int(opts.get("opacidad", 30)))) / 100
    rotacion = float(opts.get("rotacion", 45))
    pos = _POSICIONES_9.get(opts.get("posicion", "centro"), (0.5, 0.5))
    indices = _paginas_objetivo(doc, opts)

    for k, pno in enumerate(indices):
        page = doc[pno]
        r = page.rect
        cx, cy = r.width * pos[0], r.height * pos[1]
        if opts.get("tipo", "texto") == "imagen" and opts.get("imagen"):
            lado = r.width * float(opts.get("tamano", 30)) / 100
            rect = pymupdf.Rect(cx - lado / 2, cy - lado / 2,
                                cx + lado / 2, cy + lado / 2)
            imagen = opts["imagen"]
            tmp_img = None
            if rotacion % 90 != 0:
                # rotación libre: rotamos la imagen con PIL antes de insertarla
                from PIL import Image
                img = Image.open(imagen).convert("RGBA")
                img = img.rotate(-rotacion, expand=True)
                fd, tmp_img = tempfile.mkstemp(suffix=".png")
                os.close(fd)
                img.save(tmp_img)
                imagen = tmp_img
            page.insert_image(rect, filename=imagen,
                              rotate=int(rotacion) % 360 if rotacion % 90 == 0 else 0,
                              overlay=True, keep_proportion=True)
            if tmp_img:
                os.unlink(tmp_img)
        else:
            texto = opts.get("texto", "CONFIDENCIAL")
            tam = float(opts.get("tamano", 48))
            ancho = pymupdf.get_text_length(texto, fontname="helv", fontsize=tam)
            ang = math.radians(rotacion)
            # punto de inicio desplazado para que el texto quede centrado
            sx = cx - (ancho / 2) * math.cos(ang)
            sy = cy + (ancho / 2) * math.sin(ang)
            pivote = pymupdf.Point(sx, sy)
            page.insert_text(
                pivote, texto, fontsize=tam,
                fontname="helv", color=(0.45, 0.45, 0.45),
                rotate=0, overlay=True,
                fill_opacity=opacidad, stroke_opacity=opacidad,
                morph=(pivote, pymupdf.Matrix(rotacion)))
        _prog(progress, 90 * (k + 1) / len(indices))
    doc.save(out, garbage=3, deflate=True)
    doc.close()
    return out


def numeros_pagina_pdf(files, out, opts, progress=None):
    pos = _POSICIONES_9.get(opts.get("posicion", "inferior centro"), (0.5, 0.95))
    tam = float(opts.get("tamano", 11))
    formato = opts.get("formato", "{n}")           # {n} número, {t} total
    inicio = int(opts.get("inicio", 1))
    doc = pymupdf.open(files[0])
    if doc.needs_pass:
        doc.authenticate(opts.get("password", "") or "")
    indices = _paginas_objetivo(doc, opts)
    total = doc.page_count
    for k, pno in enumerate(indices):
        page = doc[pno]
        r = page.rect
        etiqueta = formato.replace("{n}", str(inicio + pno)).replace("{t}", str(total))
        ancho = pymupdf.get_text_length(etiqueta, fontname="helv", fontsize=tam)
        x = r.width * pos[0] - ancho / 2 if pos[0] == 0.5 else (
            r.width * pos[0] - ancho if pos[0] > 0.5 else r.width * pos[0])
        y = r.height * pos[1]
        page.insert_text(pymupdf.Point(x, y), etiqueta, fontsize=tam,
                         fontname="helv", color=(0, 0, 0))
        _prog(progress, 90 * (k + 1) / len(indices))
    doc.save(out)
    doc.close()
    return out


def firmar_pdf(files, out, opts, progress=None):
    """Estampa una imagen de firma. opts: imagen, posicion, pagina (o 'todas'),
    tamano (% del ancho de página)."""
    imagen = opts.get("imagen")
    if not imagen:
        raise ValueError("Elige una imagen con tu firma (PNG con fondo "
                         "transparente queda mejor).")
    doc = pymupdf.open(files[0])
    if doc.needs_pass:
        doc.authenticate(opts.get("password", "") or "")
    pos = _POSICIONES_9.get(opts.get("posicion", "inferior derecha"), (0.95, 0.95))
    pagina_opt = (opts.get("paginas") or "").strip()
    if pagina_opt and pagina_opt.lower() != "todas":
        indices = sorted({i for g in parse_rangos(pagina_opt, doc.page_count)
                          for i in g})
    else:
        indices = [doc.page_count - 1]  # por defecto, la última página
    pct = float(opts.get("tamano", 25)) / 100
    for k, pno in enumerate(indices):
        page = doc[pno]
        r = page.rect
        lado = r.width * pct
        cx, cy = r.width * pos[0], r.height * pos[1]
        rect = pymupdf.Rect(cx - lado / 2, cy - lado / 4, cx + lado / 2, cy + lado / 4)
        page.insert_image(rect, filename=imagen, keep_proportion=True, overlay=True)
        _prog(progress, 90 * (k + 1) / len(indices))
    doc.save(out)
    doc.close()
    return out


def editar_pdf(files, out, opts, progress=None):
    """Añade contenido al PDF.

    Con ``opts['elementos']`` (lista de dicts que envía el editor visual) dibuja
    textos, imágenes, formas, resaltados y enlaces. Sin esa clave mantiene el
    modo simple de siempre: un texto en una posición.
    """
    if opts.get("elementos"):
        return _aplicar_elementos(files, out, opts, progress)
    doc = pymupdf.open(files[0])
    if doc.needs_pass:
        doc.authenticate(opts.get("password", "") or "")
    pno = max(0, min(doc.page_count - 1, int(opts.get("pagina", 1)) - 1))
    page = doc[pno]
    r = page.rect
    colores = {"negro": (0, 0, 0), "rojo": (0.8, 0.1, 0.1),
               "azul": (0.1, 0.2, 0.8), "verde": (0.1, 0.55, 0.2),
               "blanco": (1, 1, 1)}
    color = colores.get(opts.get("color", "negro"), (0, 0, 0))
    x = r.width * float(opts.get("x", 10)) / 100
    y = r.height * float(opts.get("y", 10)) / 100
    _prog(progress, 40, "Escribiendo")
    page.insert_text(pymupdf.Point(x, y), opts.get("texto", ""),
                     fontsize=float(opts.get("tamano", 14)),
                     fontname="helv", color=color)
    doc.save(out)
    doc.close()
    _prog(progress, 100, "Listo")
    return out


def recortar_pdf(files, out, opts, progress=None):
    """Recorta márgenes. opts: izquierda, derecha, superior, inferior (en %)."""
    doc = pymupdf.open(files[0])
    if doc.needs_pass:
        doc.authenticate(opts.get("password", "") or "")
    iz = float(opts.get("izquierda", 5)) / 100
    de = float(opts.get("derecha", 5)) / 100
    su = float(opts.get("superior", 5)) / 100
    inf = float(opts.get("inferior", 5)) / 100
    indices = _paginas_objetivo(doc, opts)
    for k, pno in enumerate(indices):
        page = doc[pno]
        r = page.rect
        nuevo = pymupdf.Rect(r.x0 + r.width * iz, r.y0 + r.height * su,
                             r.x1 - r.width * de, r.y1 - r.height * inf)
        if nuevo.width > 36 and nuevo.height > 36:
            page.set_cropbox(nuevo)
        _prog(progress, 90 * (k + 1) / len(indices))
    doc.save(out)
    doc.close()
    return out


def censurar_pdf(files, out, opts, progress=None):
    """Redacción REAL: elimina el texto buscado o las áreas marcadas.

    opts: modo='texto'|'area'; buscar (texto, separado por comas);
    area = 'x0,y0,x1,y1' en % de la página; pagina (para modo área).
    """
    doc = pymupdf.open(files[0])
    if doc.needs_pass:
        doc.authenticate(opts.get("password", "") or "")
    modo = opts.get("modo", "texto")
    if modo == "texto":
        terminos = [t.strip() for t in opts.get("buscar", "").split(",") if t.strip()]
        if not terminos:
            raise ValueError("Escribe el texto que quieres censurar.")
        total_hits = 0
        for pno in range(doc.page_count):
            page = doc[pno]
            for t in terminos:
                for rect in page.search_for(t):
                    page.add_redact_annot(rect, fill=(0, 0, 0))
                    total_hits += 1
            _prog(progress, 80 * (pno + 1) / doc.page_count)
        if total_hits == 0:
            doc.close()
            raise ValueError("No se encontró ese texto en el documento.")
    else:
        pno = max(0, min(doc.page_count - 1, int(opts.get("pagina", 1)) - 1))
        page = doc[pno]
        r = page.rect
        try:
            x0, y0, x1, y1 = [float(v) / 100 for v in opts["area"].split(",")]
        except Exception:
            raise ValueError("Área inválida. Usa porcentajes: x0,y0,x1,y1")
        rect = pymupdf.Rect(r.width * x0, r.height * y0,
                            r.width * x1, r.height * y1)
        page.add_redact_annot(rect, fill=(0, 0, 0))
    for page in doc:
        page.apply_redactions()
    _prog(progress, 95, "Aplicando censura permanente")
    doc.save(out, garbage=4, clean=True)
    doc.close()
    return out


def formularios_pdf(files, out, opts, progress=None):
    """Rellena campos de formulario. opts: valores = 'campo=valor' por línea,
    o modo='listar' para generar una plantilla con los campos detectados."""
    doc = pymupdf.open(files[0])
    if doc.needs_pass:
        doc.authenticate(opts.get("password", "") or "")
    modo = opts.get("modo", "rellenar")
    campos = {}
    for page in doc:
        for w in page.widgets() or []:
            campos[w.field_name] = w
    _prog(progress, 40, f"{len(campos)} campos detectados")

    if modo == "crear":
        doc.close()
        return crear_formulario_pdf(files, out, opts, progress)

    if modo == "listar":
        plantilla = out if out.endswith(".txt") else out + ".txt"
        with open(plantilla, "w", encoding="utf-8") as fh:
            fh.write("# Rellena cada línea con campo=valor y úsala en "
                     "'Rellenar formulario'\n")
            for nombre, w in campos.items():
                fh.write(f"{nombre}=\n")
        doc.close()
        return plantilla

    valores = {}
    for linea in opts.get("valores", "").splitlines():
        if "=" in linea and not linea.strip().startswith("#"):
            k, v = linea.split("=", 1)
            valores[k.strip()] = v.strip()
    if not valores:
        raise ValueError("Escribe los valores como campo=valor (uno por línea). "
                         "Usa 'Listar campos' para ver los nombres.")
    for page in doc:
        for w in page.widgets() or []:
            if w.field_name in valores:
                w.field_value = valores[w.field_name]
                w.update()
    _prog(progress, 90, "Guardando")
    doc.save(out)
    doc.close()
    return out


# ==================================================================== OCR
def ocr_pdf(files, out, opts, progress=None):
    """Convierte un PDF escaneado en PDF con texto seleccionable.

    Requiere Tesseract instalado (https://github.com/UB-Mannheim/tesseract/wiki).
    Se busca automáticamente en el PATH y en las rutas típicas de Windows.
    opts: idioma ('spa', 'eng', 'spa+eng'...).
    """
    exe = buscar_tesseract()
    if not exe:
        raise RuntimeError(
            "OCR necesita Tesseract. Descárgalo gratis desde "
            "https://github.com/UB-Mannheim/tesseract/wiki e instálalo; "
            "la app lo detectará automáticamente.")
    # Aseguramos que PyMuPDF encuentre el motor y sus idiomas
    carpeta = os.path.dirname(exe)
    if carpeta.lower() not in os.environ.get("PATH", "").lower():
        os.environ["PATH"] = carpeta + os.pathsep + os.environ.get("PATH", "")
    datos = os.path.join(carpeta, "tessdata")
    if os.path.isdir(datos):
        os.environ.setdefault("TESSDATA_PREFIX", datos)
    idioma = opts.get("idioma", "spa") or "spa"
    dpi = int(opts.get("dpi", 200))
    src = pymupdf.open(files[0])
    if src.needs_pass:
        src.authenticate(opts.get("password", "") or "")
    doc = pymupdf.open()
    for i, page in enumerate(src):
        pix = page.get_pixmap(dpi=dpi)
        try:
            pdfbytes = pix.pdfocr_tobytes(language=idioma)
        except Exception:
            # ese idioma no está instalado: reintentamos con inglés
            pdfbytes = pix.pdfocr_tobytes(language="eng")
        ocr = pymupdf.open("pdf", pdfbytes)
        doc.insert_pdf(ocr)
        ocr.close()
        _prog(progress, 95 * (i + 1) / src.page_count, f"Página {i + 1}")
    doc.save(out, garbage=3, deflate=True)
    doc.close()
    src.close()
    return out


# ================================================================ COMPARAR
def comparar_pdf(files, out, opts, progress=None):
    """Compara dos PDF página a página y resalta las diferencias en rojo."""
    if len(files) < 2:
        raise ValueError("Selecciona los dos PDF que quieres comparar.")
    dpi = int(opts.get("dpi", 100))
    a = pymupdf.open(files[0])
    b = pymupdf.open(files[1])
    resultado = pymupdf.open()
    n = max(a.page_count, b.page_count)
    for i in range(n):
        pix_a = a[i].get_pixmap(dpi=dpi) if i < a.page_count else None
        pix_b = b[i].get_pixmap(dpi=dpi) if i < b.page_count else None
        base = pix_a or pix_b
        w, h = base.width, base.height
        page = resultado.new_page(width=w, height=h)
        if pix_a is None or pix_b is None:
            page.insert_image(page.rect, pixmap=base)
            faltante = "B" if pix_a is None else "A"
            page.insert_text((40, 60), f"Página ausente en documento {faltante}",
                             fontsize=24, color=(1, 0, 0))
        else:
            import numpy as np
            from PIL import Image

            # Normalizamos ambas páginas a RGB para comparar sin sorpresas
            img_a = Image.open(io.BytesIO(pix_a.tobytes("png"))).convert("RGB")
            img_b = Image.open(io.BytesIO(pix_b.tobytes("png"))).convert("RGB")
            if img_b.size != img_a.size:
                img_b = img_b.resize(img_a.size)
            arr_a = np.asarray(img_a, dtype=np.int16)
            arr_b = np.asarray(img_b, dtype=np.int16)
            diff = np.abs(arr_a - arr_b).sum(axis=2)
            mascara = diff > 60
            img = arr_a.astype(np.uint8)
            img[mascara] = (255, 0, 0)
            pix = pymupdf.Pixmap(pymupdf.csRGB, img_a.width, img_a.height,
                                 img.tobytes(), False)
            page.insert_image(page.rect, pixmap=pix)
            porc = 100 * float(mascara.mean())
            page.insert_text((30, 30),
                             f"Página {i + 1}: {porc:.1f}% de diferencia",
                             fontsize=14, color=(1, 0, 0),
                             fill=(1, 1, 1), fill_opacity=0.8)
        _prog(progress, 95 * (i + 1) / n)
    resultado.save(out)
    for d in (a, b, resultado):
        d.close()
    return out


# ================================================================ ESCANEAR
def escanear_a_pdf(files, out, opts, progress=None):
    """Escanea desde un escáner WIA (Windows) o crea el PDF desde imágenes.

    En Windows usa el diálogo de escaneo del sistema (WIA). En otros sistemas,
    o si no hay escáner, selecciona imágenes y se unen en un PDF.
    """
    if files:  # modo imágenes (multiplataforma)
        return jpg_a_pdf(files, out, {"orientacion": "auto", "margen": 0}, progress)
    if os.name != "nt":
        raise RuntimeError(
            "No se encontró escáner. Añade imágenes (JPG/PNG) a la lista y "
            "pulsa «Ejecutar» para unirlas en un PDF.")
    try:
        import win32com.client  # type: ignore
        _prog(progress, 10, "Abriendo el escáner…")
        dlg = win32com.client.Dispatch("WIA.CommonDialog")
        item = dlg.ShowAcquireImage()
        if item is None:
            raise RuntimeError("el diálogo se canceló")
        tmp = os.path.join(tempfile.mkdtemp(), "escaneo")
        os.makedirs(tmp, exist_ok=True)
        ruta_img = os.path.join(tmp, "escaneo.png")
        item.SaveFile(ruta_img)
        _prog(progress, 70, "Creando PDF")
        return jpg_a_pdf([ruta_img], out, {"orientacion": "auto", "margen": 0})
    except Exception as e:
        raise RuntimeError(
            f"No se pudo usar el escáner ({e}). Añade imágenes (JPG/PNG) a la "
            "lista y pulsa «Ejecutar» para unirlas en un PDF.")


# =================================================================== PDF/A
def pdf_a_pdfa(files, out, opts, progress=None):
    """Convierte a PDF/A usando Ghostscript (debe estar instalado)."""
    gs = buscar_ghostscript()
    if not gs:
        raise RuntimeError(
            "PDF/A necesita Ghostscript. Descárgalo gratis desde "
            "https://www.ghostscript.com/releases/gsdnld.html e instálalo; "
            "la app lo detectará automáticamente.")
    nivel = opts.get("nivel", "2")
    _prog(progress, 30, "Convirtiendo con Ghostscript")
    cmd = [gs, "-dBATCH", "-dNOPAUSE", "-dQUIET", "-sDEVICE=pdfwrite",
           f"-dPDFA={nivel}", "-dPDFACompatibilityPolicy=1",
           "-sColorConversionStrategy=RGB",
           f"-sOutputFile={out}", files[0]]
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if res.returncode != 0 or not os.path.exists(out):
        raise RuntimeError("Ghostscript no pudo crear el PDF/A:\n" + res.stderr[-500:])
    _prog(progress, 100, "Listo")
    return out


# ==================================================== PLAN DE PÁGINAS (vista)
# La vista de miniaturas de la interfaz envía un "plan": la lista ordenada de
# páginas que tendrá el documento final (con su rotación y sin las omitidas).
# Así se organizan las páginas arrastrándolas y sin límite de archivos.
_EXT_IMAGEN = (".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".webp", ".gif")


def es_imagen(ruta) -> bool:
    """True si la ruta es una imagen que se puede convertir en página."""
    return os.path.splitext(str(ruta))[1].lower() in _EXT_IMAGEN


def _abrir_pdf(ruta, password=""):
    doc = pymupdf.open(ruta)
    if doc.needs_pass and not doc.authenticate(password or ""):
        raise ValueError(f"Contraseña incorrecta para {os.path.basename(ruta)}")
    return doc


def aplicar_plan(files, out, opts, progress=None):
    """Crea el PDF final siguiendo el plan de páginas de la interfaz.

    ``opts['plan']`` es una lista de pasos::

        {"file": ruta, "page": 0, "rot": 90}

    Cada paso aporta una página (de un PDF o de una imagen) en ese orden exacto.
    """
    plan = opts.get("plan") or []
    if not plan:
        raise ValueError("No hay páginas que procesar.")
    password = opts.get("password", "") or ""
    salida = pymupdf.open()
    cache = {}
    total = len(plan)
    try:
        for i, paso in enumerate(plan):
            ruta = paso.get("file") or (files[0] if files else "")
            if not ruta:
                raise ValueError("El plan contiene una página sin archivo de origen.")
            rot = int(paso.get("rot", 0) or 0) % 360
            pno = int(paso.get("page", 0) or 0)
            if es_imagen(ruta):
                img = pymupdf.open(ruta)
                r = img[0].rect
                ancho, alto = ((r.height, r.width) if rot in (90, 270)
                               else (r.width, r.height))
                pagina = salida.new_page(width=ancho, height=alto)
                pagina.insert_image(pagina.rect, filename=ruta, rotate=rot,
                                    keep_proportion=True)
                img.close()
            else:
                doc = cache.get(ruta)
                if doc is None:
                    doc = _abrir_pdf(ruta, password)
                    cache[ruta] = doc
                pno = max(0, min(doc.page_count - 1, pno))
                salida.insert_pdf(doc, from_page=pno, to_page=pno)
                if rot:
                    ultima = salida[-1]
                    ultima.set_rotation((ultima.rotation + rot) % 360)
            _prog(progress, 95 * (i + 1) / total,
                  f"{i + 1}/{total} · " + os.path.basename(str(ruta)))
        salida.save(out, garbage=3, deflate=True)
    finally:
        salida.close()
        for doc in cache.values():
            doc.close()
    _prog(progress, 100, "Listo")
    return out


def eliminar_paginas(files, out, opts, progress=None):
    """Elimina las páginas indicadas ('1-3,7'). El resto se conserva.

    Si llega un plan desde la vista de miniaturas (``opts['plan']``), se
    conservan exactamente las páginas incluidas en él y el resto se borra.
    """
    doc = pymupdf.open(files[0])
    if doc.needs_pass:
        doc.authenticate(opts.get("password", "") or "")
    if opts.get("plan") is not None:
        conservar = {int(p.get("page", 0)) for p in opts.get("plan") or []}
        borrar = [i for i in range(doc.page_count) if i not in conservar]
    else:
        borrar = sorted({i for g in parse_rangos(opts.get("paginas", ""),
                                                 doc.page_count) for i in g})
    if not borrar:
        doc.close()
        raise ValueError("Indica qué páginas quieres eliminar (ej.: 1-3,7).")
    if len(borrar) >= doc.page_count:
        doc.close()
        raise ValueError("No puedes eliminar todas las páginas del documento.")
    _prog(progress, 40, f"Quitando {len(borrar)} página(s)")
    doc.delete_pages(borrar)
    doc.save(out, garbage=3, deflate=True)
    doc.close()
    _prog(progress, 100, "Listo")
    return out


def extraer_paginas(files, out, opts, progress=None):
    """Extrae las páginas indicadas.

    ``modo``: ``unico`` (todas juntas en un PDF) o ``separados`` (un PDF por
    rango). En modo ``separados`` la salida es una carpeta.
    """
    doc = pymupdf.open(files[0])
    if doc.needs_pass:
        doc.authenticate(opts.get("password", "") or "")
    rangos = parse_rangos(opts.get("rangos", ""), doc.page_count)
    base = os.path.splitext(os.path.basename(files[0]))[0]
    hechos = []
    if opts.get("modo", "unico") == "separados":
        os.makedirs(out, exist_ok=True)
        for i, grupo in enumerate(rangos):
            nuevo = pymupdf.open()
            for p in grupo:
                nuevo.insert_pdf(doc, from_page=p, to_page=p)
            destino = os.path.join(out, f"{base}_extraido_{i + 1}.pdf")
            nuevo.save(destino, garbage=3, deflate=True)
            nuevo.close()
            hechos.append(destino)
            _prog(progress, 95 * (i + 1) / len(rangos))
        doc.close()
        return out
    nuevo = pymupdf.open()
    for i, grupo in enumerate(rangos):
        for p in grupo:
            nuevo.insert_pdf(doc, from_page=p, to_page=p)
        _prog(progress, 90 * (i + 1) / len(rangos))
    nuevo.save(out, garbage=3, deflate=True)
    nuevo.close()
    doc.close()
    _prog(progress, 100, "Listo")
    return out


# ============================================ EDITOR: ELEMENTOS DE LA PÁGINA
_COLORES_NOMBRE = {
    "negro": (0, 0, 0), "blanco": (1, 1, 1), "gris": (0.5, 0.5, 0.5),
    "rojo": (0.83, 0.13, 0.18), "verde": (0.11, 0.55, 0.24),
    "azul": (0.13, 0.29, 0.82), "amarillo": (1, 0.85, 0.16),
    "naranja": (0.95, 0.53, 0.12), "morado": (0.55, 0.29, 0.78),
    "rosa": (0.93, 0.36, 0.56), "cian": (0.10, 0.70, 0.78),
}
_FUENTES_PDF = {"helvetica": "helv", "helv": "helv", "arial": "helv",
                "sans": "helv", "times": "tiro", "serif": "tiro",
                "courier": "cour", "mono": "cour",
                "times-bold": "tibo", "helvetica-bold": "hebo"}
_ALINEACION_PDF = {"izquierda": 0, "centro": 1, "derecha": 2, "justificado": 3}


def _parse_color(valor, defecto=(0, 0, 0)):
    """'#RRGGBB' | 'rojo' | (r,g,b) -> tupla RGB con valores 0-1."""
    if isinstance(valor, (list, tuple)) and len(valor) == 3:
        return tuple(max(0.0, min(1.0, float(c))) for c in valor)
    texto = str(valor or "").strip().lower()
    if texto.startswith("#") and len(texto) == 7:
        try:
            return tuple(int(texto[i:i + 2], 16) / 255 for i in (1, 3, 5))
        except ValueError:
            return defecto
    if texto.startswith("rgb(") and texto.endswith(")"):
        try:
            canales = [float(x) for x in texto[4:-1].split(",")]
            return tuple(max(0.0, min(1.0, c / 255)) for c in canales)
        except ValueError:
            return defecto
    return _COLORES_NOMBRE.get(texto, defecto)


def _rect_desde_pct(page, el, caja=(6, 6, 40, 12)):
    """Rectángulo en puntos a partir de porcentajes de la página."""
    r = page.rect
    x = float(el.get("x", caja[0])) / 100
    y = float(el.get("y", caja[1])) / 100
    w = float(el.get("w", caja[2])) / 100
    h = float(el.get("h", caja[3])) / 100
    x0 = r.x0 + r.width * x
    y0 = r.y0 + r.height * y
    return pymupdf.Rect(x0, y0, x0 + max(1.0, r.width * w),
                        y0 + max(1.0, r.height * h))


def _aplicar_elementos(files, out, opts, progress=None):
    """Dibuja en el PDF los elementos creados en el editor visual."""
    elementos = opts.get("elementos") or []
    if not elementos:
        raise ValueError("Añade al menos un elemento antes de guardar.")
    doc = pymupdf.open(files[0])
    if doc.needs_pass:
        doc.authenticate(opts.get("password", "") or "")
    total = len(elementos)
    for i, el in enumerate(elementos):
        tipo = str(el.get("tipo", "texto")).lower()
        pno = max(0, min(doc.page_count - 1, int(el.get("pagina", 1)) - 1))
        page = doc[pno]
        rect = _rect_desde_pct(page, el)
        color = _parse_color(el.get("color"), (0, 0, 0))
        grosor = float(el.get("grosor", 1.5))
        opac = max(0, min(100, int(el.get("opacidad", 100)))) / 100
        if tipo == "texto":
            fuente = _FUENTES_PDF.get(str(el.get("fuente", "helv")).lower(), "helv")
            page.insert_textbox(
                rect, str(el.get("texto", "")),
                fontsize=float(el.get("tamano", 12)), fontname=fuente,
                color=color, fill_opacity=opac,
                align=_ALINEACION_PDF.get(str(el.get("alineacion", "izquierda")).lower(), 0))
        elif tipo == "imagen":
            ruta = el.get("imagen")
            if not ruta or not os.path.isfile(str(ruta)):
                raise ValueError("Falta la imagen de uno de los elementos.")
            page.insert_image(rect, filename=str(ruta), overlay=True,
                              keep_proportion=bool(el.get("proporcion", True)),
                              rotate=int(el.get("rot", 0) or 0) % 360)
        elif tipo == "linea":
            page.draw_line(pymupdf.Point(rect.x0, rect.y0),
                           pymupdf.Point(rect.x1, rect.y1),
                           color=color, width=grosor, stroke_opacity=opac)
        elif tipo == "enlace":
            url = str(el.get("url", "")).strip()
            if not url:
                raise ValueError("Uno de los elementos es un enlace sin dirección.")
            page.insert_link({"kind": pymupdf.LINK_URI, "from": rect, "uri": url})
        else:  # rectangulo | elipse | resaltado | borrar
            relleno = _parse_color(
                el.get("relleno") or ("#ffffff" if tipo == "borrar" else el.get("color")),
                (1, 1, 1))
            borde = el.get("borde")
            dibujar = page.draw_oval if tipo == "elipse" else page.draw_rect
            dibujar(rect, color=_parse_color(borde, None) if borde else None,
                    fill=relleno, width=grosor, fill_opacity=opac,
                    stroke_opacity=opac)
        _prog(progress, 95 * (i + 1) / total, f"Elemento {i + 1}/{total}")
    doc.save(out, garbage=3, deflate=True)
    doc.close()
    _prog(progress, 100, "Listo")
    return out


# ================================================ INTELIGENCIA DE DOCUMENTO
_PALABRAS_VACIAS = {
    "que", "los", "las", "una", "uno", "unos", "unas", "del", "con", "por",
    "para", "como", "mas", "más", "pero", "sus", "sin", "sobre", "entre",
    "cuando", "donde", "esta", "este", "estos", "estas", "esos", "esas",
    "muy", "todo", "toda", "todos", "todas", "hay", "han", "fue", "son",
    "ser", "está", "estan", "están", "también", "tambien", "cada", "desde",
    "hasta", "porque", "puede", "pueden", "debe", "deben", "esto", "eso",
    "aquello", "otro", "otra", "otros", "otras", "mismo", "misma", "the",
    "and", "for", "with", "that", "this", "these", "those", "from", "are",
    "was", "were", "has", "have", "had", "not", "but", "you", "your", "its",
    "which", "will", "would", "can", "could", "should", "there", "their",
}


def _separar_frases(texto):
    """Divide el texto en frases razonables (sin dependencias externas)."""
    import re
    limpio = re.sub(r"(?<=\w)-\n(?=\w)", "", texto)
    limpio = re.sub(r"\s+", " ", limpio)
    partes = re.split(r"(?<=[.!?…])\s+", limpio)
    return [p.strip() for p in partes if len(p.strip()) > 30]


def _palabras(texto):
    import re
    return re.findall(r"[0-9A-Za-zÁÉÍÓÚÜÑáéíóúüñ]{3,}", texto.lower())


def _texto_plano(markdown):
    """Quita el formato Markdown (para exportar en .txt)."""
    lineas = []
    for linea in markdown.splitlines():
        t = linea.rstrip()
        for marca in ("### ", "## ", "# ", "- "):
            if t.strip().startswith(marca):
                t = t.replace(marca, "", 1)
        lineas.append(t.replace("**", "").replace("`", ""))
    return "\n".join(lineas)


def _markdown_a_html(markdown):
    """Conversión mínima Markdown -> HTML para generar PDF con PyMuPDF."""
    import re
    piezas, en_lista = [], False
    for linea in markdown.splitlines():
        t = linea.strip()
        if not t:
            continue
        texto = _esc(t)
        texto = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", texto)
        texto = re.sub(r"`(.+?)`", r"<i>\1</i>", texto)
        if texto.startswith("- "):
            if not en_lista:
                piezas.append("<ul>")
                en_lista = True
            piezas.append(f"<li>{texto[2:]}</li>")
            continue
        if en_lista:
            piezas.append("</ul>")
            en_lista = False
        if texto.startswith("### "):
            piezas.append(f"<h3>{texto[4:]}</h3>")
        elif texto.startswith("## "):
            piezas.append(f"<h2>{texto[3:]}</h2>")
        elif texto.startswith("# "):
            piezas.append(f"<h1>{texto[2:]}</h1>")
        else:
            piezas.append(f"<p>{texto}</p>")
    if en_lista:
        piezas.append("</ul>")
    return ("<html><head>" + _CSS_BASE + "</head><body>"
            + "".join(piezas) + "</body></html>")


def _resumen_markdown(nombre, n_paginas, texto, limite):
    """Resumen extractivo calculado en local (sin enviar nada a internet)."""
    from collections import Counter
    frases = _separar_frases(texto)
    terminos = [p for p in _palabras(texto) if p not in _PALABRAS_VACIAS]
    if not frases or not terminos:
        raise ValueError("El PDF no tiene texto seleccionable. Pásalo antes "
                         "por «OCR PDF» y vuelve a intentarlo.")
    frecuencia = Counter(terminos)
    puntuadas = []
    for i, frase in enumerate(frases):
        suyas = [p for p in _palabras(frase) if p not in _PALABRAS_VACIAS]
        if not suyas:
            continue
        peso = sum(frecuencia[p] for p in suyas) / (len(suyas) ** 0.55)
        if i < 3:                       # la introducción suele marcar el tema
            peso *= 1.25
        puntuadas.append((peso, i, frase))
    puntuadas.sort(reverse=True)
    elegidas = sorted(puntuadas[:max(3, limite)], key=lambda x: x[1])
    claves = [p for p, _ in frecuencia.most_common(12)]
    minutos = max(1, round(len(terminos) / 200))
    lineas = [f"# Resumen de {nombre}", "",
              f"**{n_paginas} páginas** · {len(terminos)} palabras · "
              f"~{minutos} min de lectura", "", "## Ideas clave", ""]
    lineas += [f"- {frase}" for _, _, frase in elegidas]
    lineas += ["", "## Palabras clave", "",
               " · ".join(f"`{c}`" for c in claves)]
    return "\n".join(lineas)


def resumir_pdf(files, out, opts, progress=None):
    """Resume el PDF con un algoritmo extractivo, todo en el equipo.

    ``opts``: ``frases`` (nº de ideas clave) y ``formato``: md | txt | pdf.
    """
    doc = pymupdf.open(files[0])
    if doc.needs_pass:
        doc.authenticate(opts.get("password", "") or "")
    partes = []
    for i, page in enumerate(doc):
        partes.append(page.get_text("text"))
        _prog(progress, 50 * (i + 1) / doc.page_count, f"Leyendo página {i + 1}")
    n_paginas = doc.page_count
    doc.close()
    texto = "\n".join(partes).strip()
    if len(_palabras(texto)) < 40:
        raise ValueError("El PDF no tiene texto seleccionable. Pásalo antes "
                         "por «OCR PDF» y vuelve a intentarlo.")
    resumen = _resumen_markdown(
        os.path.splitext(os.path.basename(files[0]))[0], n_paginas, texto,
        int(opts.get("frases", 12) or 12))
    _prog(progress, 75, "Componiendo el resumen")
    formato = (opts.get("formato", "md") or "md").lower()
    if formato == "pdf":
        _render_html_a_pdf(_markdown_a_html(resumen), out)
    else:
        with open(out, "w", encoding="utf-8") as fh:
            fh.write(resumen if formato == "md" else _texto_plano(resumen))
    _prog(progress, 100, "Listo")
    return out


_IDIOMAS_TRADUCCION = {
    "es": "Español", "en": "Inglés", "fr": "Francés", "de": "Alemán",
    "it": "Italiano", "pt": "Portugués", "nl": "Neerlandés", "ru": "Ruso",
    "pl": "Polaco", "tr": "Turco", "ar": "Árabe", "zh": "Chino",
    "ja": "Japonés", "ca": "Catalán", "gl": "Gallego", "eu": "Euskera",
    "ro": "Rumano", "sv": "Sueco", "da": "Danés", "fi": "Finés",
    "cs": "Checo", "el": "Griego", "hi": "Hindi", "id": "Indonesio",
    "uk": "Ucraniano", "vi": "Vietnamita", "he": "Hebreo", "th": "Tailandés",
    "ko": "Coreano", "fa": "Persa", "no": "Noruego", "hu": "Húngaro",
}


def idiomas_traduccion():
    """Códigos de idioma disponibles en el motor opcional (argostranslate)."""
    try:
        from argostranslate import translate as _argos
        return sorted({i.code for i in _argos.get_installed_languages()})
    except Exception:
        return []


def _traductor_argos(origen, destino):
    """Traductor local origen->destino o error explicando cómo instalarlo."""
    try:
        from argostranslate import translate as _argos
    except Exception as e:  # noqa: BLE001
        raise RuntimeError(
            "Traducir PDF usa el motor opcional argostranslate (gratis y "
            "100 % local: nada sale de tu equipo). Instálalo así:\n\n"
            "    pip install argostranslate\n\n"
            f"Detalle: {e}")
    idiomas = {lang.code: lang for lang in _argos.get_installed_languages()}
    faltan = [c for c in (origen, destino) if c not in idiomas]
    if faltan:
        raise RuntimeError(
            "El traductor local no tiene instalados estos idiomas: "
            + ", ".join(_IDIOMAS_TRADUCCION.get(c, c) for c in faltan)
            + "\n\nDescárgalos con:\n\n    argospm update\n"
            f"    argospm install translate-{origen}_{destino}")
    traductor = idiomas[origen].get_translation(idiomas[destino])
    if traductor is None:
        raise RuntimeError(
            f"Falta el par de idiomas {origen}->{destino}. Descárgalo con:\n\n"
            "    argospm update\n"
            f"    argospm install translate-{origen}_{destino}")
    return traductor


def traducir_pdf(files, out, opts, progress=None):
    """Traduce el documento con el motor local opcional.

    ``opts``: ``origen`` y ``destino`` (códigos ISO) y ``formato`` pdf | md | txt.
    """
    origen = (opts.get("origen") or "es").lower()[:2]
    destino = (opts.get("destino") or "en").lower()[:2]
    if origen == destino:
        raise ValueError("El idioma de origen y el de destino deben ser distintos.")
    traductor = _traductor_argos(origen, destino)
    doc = pymupdf.open(files[0])
    if doc.needs_pass:
        doc.authenticate(opts.get("password", "") or "")
    bloques = []
    for i, page in enumerate(doc):
        bloques.append(page.get_text("text"))
        _prog(progress, 25 * (i + 1) / doc.page_count, f"Leyendo página {i + 1}")
    doc.close()
    if not any(b.strip() for b in bloques):
        raise ValueError("El PDF no tiene texto seleccionable. Pásalo antes "
                         "por «OCR PDF» y vuelve a intentarlo.")
    parrafos = [(i, p.strip())
                for i, bloque in enumerate(bloques)
                for p in bloque.split("\n") if p.strip()]
    traducidos = []
    for j, (pagina, parrafo) in enumerate(parrafos):
        traducidos.append((pagina, traductor.translate(parrafo)))
        _prog(progress, 25 + 60 * (j + 1) / len(parrafos),
              f"Traduciendo {j + 1}/{len(parrafos)}")
    lineas, pagina_actual = [], -1
    for pagina, texto in traducidos:
        if pagina != pagina_actual:
            if pagina_actual >= 0:
                lineas.append("")
            lineas += [f"## Página {pagina + 1}", ""]
            pagina_actual = pagina
        lineas += [texto, ""]
    markdown = "\n".join(lineas)
    formato = (opts.get("formato", "pdf") or "pdf").lower()
    if formato == "pdf":
        _render_html_a_pdf(_markdown_a_html(markdown), out)
    else:
        with open(out, "w", encoding="utf-8") as fh:
            fh.write(markdown if formato == "md" else _texto_plano(markdown))
    _prog(progress, 100, "Listo")
    return out


# ===================================================== CREAR FORMULARIOS
def crear_formulario_pdf(files, out, opts, progress=None):
    """Crea campos de formulario rellenables sobre el PDF.

    ``opts['campos']``: una definición por línea, separada por «;»::

        tipo ; página ; x% ; y% ; ancho% ; alto% ; nombre ; valor

    tipo = texto | casilla | lista | desplegable | firma. En lista/desplegable
    el valor son las opciones separadas por «|».
    """
    especificacion = (opts.get("campos") or "").strip()
    if not especificacion:
        raise ValueError("Describe los campos a crear, uno por línea.")
    doc = pymupdf.open(files[0])
    if doc.needs_pass:
        doc.authenticate(opts.get("password", "") or "")
    lineas = [l for l in especificacion.splitlines()
              if l.strip() and not l.strip().startswith("#")]
    creados = 0
    for i, linea in enumerate(lineas):
        partes = [p.strip() for p in linea.split(";")]
        if len(partes) < 7:
            raise ValueError(
                f"Línea {i + 1}: faltan datos. Formato: "
                "tipo;página;x;y;ancho;alto;nombre;valor")
        tipo = partes[0].lower()
        pno = max(0, min(doc.page_count - 1, int(partes[1]) - 1))
        x, y, ancho, alto = (float(v) / 100 for v in partes[2:6])
        nombre = partes[6]
        valor = partes[7] if len(partes) > 7 else ""
        page = doc[pno]
        r = page.rect
        campo = pymupdf.Widget()
        campo.field_name = nombre
        campo.rect = pymupdf.Rect(r.x0 + r.width * x, r.y0 + r.height * y,
                                  r.x0 + r.width * (x + ancho),
                                  r.y0 + r.height * (y + alto))
        if tipo == "casilla":
            campo.field_type = pymupdf.PDF_WIDGET_TYPE_CHECKBOX
            campo.field_value = str(valor).strip().lower() in (
                "1", "si", "sí", "x", "yes", "true", "on")
        elif tipo in ("lista", "desplegable"):
            campo.field_type = (pymupdf.PDF_WIDGET_TYPE_LISTBOX
                                if tipo == "lista"
                                else pymupdf.PDF_WIDGET_TYPE_COMBOBOX)
            campo.choice_values = [o.strip() for o in valor.split("|") if o.strip()]
            if campo.choice_values:
                campo.field_value = campo.choice_values[0]
        elif tipo == "firma":
            campo.field_type = pymupdf.PDF_WIDGET_TYPE_SIGNATURE
        else:
            campo.field_type = pymupdf.PDF_WIDGET_TYPE_TEXT
            campo.field_value = valor
            campo.text_fontsize = 11
            campo.text_color = (0, 0, 0)
        page.add_widget(campo)
        creados += 1
        _prog(progress, 90 * (i + 1) / len(lineas), f"Campo «{nombre}»")
    doc.need_appearances = True
    doc.save(out, garbage=3, deflate=True)
    doc.close()
    _prog(progress, 100, f"{creados} campo(s) creados")
    return out
