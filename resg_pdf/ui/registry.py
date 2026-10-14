# -*- coding: utf-8 -*-
"""Registro de herramientas: metadatos + esquema de opciones.

La interfaz se genera automáticamente a partir de este registro, así que añadir
una herramienta nueva solo requiere una entrada aquí y su función en
``resg_pdf/backend/tools.py``.

Claves de cada herramienta
--------------------------
id, titulo, icono, descripcion, categoria, funcion, multiple, filtro, salida,
opciones
    Igual que siempre (salida = 'pdf', 'dir' o 'file:.ext').

previsualiza
    Muestra las páginas como miniaturas y permite ordenarlas arrastrando.

plan
    ``'paginas'`` envía el orden exacto de páginas elegido en las miniaturas
    (``opts['plan']``); ``'rangos'`` traduce la selección visual a un texto de
    rangos (``opts['rangos']`` o ``opts['paginas']``).

seleccion_inicial
    ``'todas'`` (por defecto) o ``'ninguna'``: cómo empiezan las casillas.

editor
    La herramienta usa el editor visual (texto, imágenes, formas, enlaces).

firma
    El campo de imagen incluye el botón para dibujar la firma a mano.

accion / pista
    Texto del botón principal y su ayuda (se muestra como tooltip).

sin_entrada
    La herramienta funciona sin archivos de entrada (por ejemplo, el escáner).
"""
from ..backend import tools as T

PDF = "Archivos PDF (*.pdf)"
IMG = "Imágenes (*.png *.jpg *.jpeg *.bmp *.tiff *.webp)"
OFFICE = ("Documentos Office (*.docx *.xlsx *.pptx *.odt *.ods *.odp *.doc "
          "*.xls *.ppt *.rtf *.txt)"
          ";;Word (*.docx *.doc *.rtf);;Excel (*.xlsx *.xls *.ods)"
          ";;PowerPoint (*.pptx *.ppt *.odp)")
WEB = "Páginas web (*.html *.htm)"

TOOLS = [
    # ---------------------------------------------------------------- ORGANIZAR
    dict(id="unir", titulo="Unir PDF", icono="unir", categoria="Organizar",
         descripcion="Une varios PDF en el orden que prefieras.",
         funcion=T.unir_pdf, multiple=True, filtro=PDF, salida="pdf",
         previsualiza=True, plan="paginas",
         opciones=[dict(k="password", t="password",
                        label="Contraseña (si alguno está protegido)")]),

    dict(id="dividir", titulo="Dividir PDF", icono="dividir",
         categoria="Organizar",
         descripcion="Extrae páginas o separa el documento en varios PDF.",
         funcion=T.dividir_pdf, multiple=False, filtro=PDF, salida="dir",
         previsualiza=True, plan="rangos",
         opciones=[
             dict(k="modo", t="combo", label="Cómo dividir",
                  choices={"rangos": "Por rangos (usa la selección)",
                           "cada_pagina": "Una página por archivo",
                           "tamano": "Bloques de N páginas"}),
             dict(k="rangos", t="text", label="Rangos (ej. 1-3,5,8-)",
                  default=""),
             dict(k="cada", t="int", label="N (bloques de N páginas)",
                  default=2),
             dict(k="password", t="password",
                  label="Contraseña (si está protegido)")],
         pista="Marca en las miniaturas las páginas que quieres extraer."),

    dict(id="ordenar", titulo="Ordenar PDF", icono="ordenar",
         categoria="Organizar",
         descripcion="Organiza las páginas como quieras: muévelas con el ratón.",
         funcion=T.ordenar_pdf, multiple=True, filtro=PDF, salida="pdf",
         previsualiza=True, plan="paginas",
         opciones=[dict(k="orden", t="text",
                        label="Orden manual (ej. 3,1,2,4)", default="",
                        placeholder="Vacío = el orden de las miniaturas"),
                   dict(k="password", t="password",
                        label="Contraseña (si está protegido)")]),

    dict(id="rotar", titulo="Rotar PDF", icono="rotar", categoria="Organizar",
         descripcion="Gira las páginas una a una, las veces que necesites.",
         funcion=T.rotar_pdf, multiple=True, filtro=PDF, salida="pdf",
         previsualiza=True, plan="paginas",
         opciones=[
             dict(k="grados", t="combo", label="Giro rápido para todo",
                  choices={"90": "90° a la derecha", "180": "180°",
                           "270": "90° a la izquierda"}),
             dict(k="paginas", t="pages",
                  label="Páginas (vacío = según las miniaturas)"),
             dict(k="password", t="password",
                  label="Contraseña (si está protegido)")],
         pista="Selecciona páginas en las miniaturas y pulsa «Girar»."),

    dict(id="eliminar", titulo="Eliminar páginas", icono="eliminar",
         categoria="Organizar",
         descripcion="Quita las páginas que no necesites del documento.",
         funcion=T.eliminar_paginas, multiple=True, filtro=PDF, salida="pdf",
         previsualiza=True, plan="paginas", seleccion_inicial="todas",
         opciones=[dict(k="paginas", t="text",
                        label="Páginas a eliminar (ej. 2,5-7)", default="",
                        placeholder="Vacío = las desmarcadas"),
                   dict(k="password", t="password",
                        label="Contraseña (si está protegido)")],
         pista="Desmarca en las miniaturas las páginas que sobran."),

    dict(id="extraer", titulo="Extraer páginas", icono="extraer",
         categoria="Organizar",
         descripcion="Queda solo con las páginas que elijas, en su orden.",
         funcion=T.extraer_paginas, multiple=False, filtro=PDF, salida="pdf",
         previsualiza=True, plan="rangos", seleccion_inicial="ninguna",
         opciones=[
             dict(k="modo", t="combo", label="Resultado",
                  choices={"unico": "Un único PDF con lo extraído",
                           "separados": "Un PDF por rango (en una carpeta)"}),
             dict(k="rangos", t="text", label="Rangos (ej. 1-3,5)", default="",
                  placeholder="Vacío = las páginas marcadas"),
             dict(k="password", t="password",
                  label="Contraseña (si está protegido)")]),

    # ---------------------------------------------------------------- OPTIMIZAR
    dict(id="comprimir", titulo="Comprimir PDF", icono="comprimir",
         categoria="Optimizar",
         descripcion="Reduce el tamaño manteniendo la mejor calidad posible.",
         funcion=T.comprimir_pdf, multiple=False, filtro=PDF, salida="pdf",
         opciones=[
             dict(k="nivel", t="combo", label="Nivel de compresión",
                  choices={"alto": "Alta calidad (comprime menos)",
                           "medio": "Equilibrado (recomendado)",
                           "bajo": "Máxima compresión"}),
             dict(k="password", t="password",
                  label="Contraseña (si está protegido)")]),

    dict(id="reparar", titulo="Reparar PDF", icono="reparar",
         categoria="Optimizar",
         descripcion="Recupera datos de un PDF dañado o corrupto.",
         funcion=T.reparar_pdf, multiple=True, filtro=PDF, salida="pdf",
         opciones=[]),

    dict(id="ocr", titulo="OCR PDF", icono="ocr", categoria="Optimizar",
         descripcion="Convierte escaneos en documentos con texto seleccionable.",
         funcion=T.ocr_pdf, multiple=False, filtro=PDF, salida="pdf",
         opciones=[
             dict(k="idioma", t="combo", label="Idioma del documento",
                  choices={"spa": "Español", "eng": "Inglés",
                           "spa+eng": "Español + Inglés", "fra": "Francés",
                           "deu": "Alemán", "ita": "Italiano",
                           "por": "Portugués"}),
             dict(k="dpi", t="combo", label="Calidad de análisis",
                  choices={"150": "Rápida",
                           "200": "Normal (recomendada)",
                           "300": "Alta (más lenta)"}),
             dict(k="password", t="password",
                  label="Contraseña (si está protegido)")]),

    # ----------------------------------------------------- CONVERTIR DESDE PDF
    dict(id="pdf_word", titulo="PDF a Word", icono="pdf_word",
         categoria="Convertir desde PDF",
         descripcion="Convierte tu PDF en un documento DOCX editable.",
         funcion=T.pdf_a_word, multiple=False, filtro=PDF,
         salida="file:.docx", opciones=[]),

    dict(id="pdf_ppt", titulo="PDF a PowerPoint", icono="pdf_ppt",
         categoria="Convertir desde PDF",
         descripcion="Convierte cada página en una diapositiva PPTX.",
         funcion=T.pdf_a_ppt, multiple=False, filtro=PDF, salida="file:.pptx",
         opciones=[dict(k="dpi", t="combo", label="Calidad de la imagen",
                        choices={"110": "Ligera", "150": "Buena",
                                 "220": "Máxima"}),
                   dict(k="password", t="password",
                        label="Contraseña (si está protegido)")]),

    dict(id="pdf_excel", titulo="PDF a Excel", icono="pdf_excel",
         categoria="Convertir desde PDF",
         descripcion="Extrae las tablas del PDF a un libro de Excel.",
         funcion=T.pdf_a_excel, multiple=False, filtro=PDF,
         salida="file:.xlsx",
         opciones=[dict(k="password", t="password",
                        label="Contraseña (si está protegido)")]),

    dict(id="pdf_jpg", titulo="PDF a JPG", icono="pdf_jpg",
         categoria="Convertir desde PDF",
         descripcion="Convierte cada página del PDF en una imagen.",
         funcion=T.pdf_a_jpg, multiple=True, filtro=PDF, salida="dir",
         opciones=[
             dict(k="formato", t="combo", label="Formato de imagen",
                  choices={"jpg": "JPG (más ligero)",
                           "png": "PNG (sin pérdida)", "webp": "WEBP"}),
             dict(k="dpi", t="combo", label="Resolución",
                  choices={"96": "Pantalla (96 ppp)",
                           "150": "Normal (150 ppp)",
                           "300": "Alta (300 ppp, impresión)"}),
             dict(k="calidad", t="int", label="Calidad JPG (1-100)",
                  default=85),
             dict(k="password", t="password",
                  label="Contraseña (si está protegido)")]),

    dict(id="pdf_markdown", titulo="PDF a Markdown", icono="pdf_markdown",
         categoria="Convertir desde PDF",
         descripcion="Convierte el PDF a Markdown conservando la estructura.",
         funcion=T.pdf_a_markdown, multiple=False, filtro=PDF,
         salida="file:.md",
         opciones=[dict(k="password", t="password",
                        label="Contraseña (si está protegido)")]),

    dict(id="pdf_pdfa", titulo="PDF a PDF/A", icono="pdf_pdfa",
         categoria="Convertir desde PDF",
         descripcion="Transforma tu PDF al formato ISO para archivar a largo "
                     "plazo.",
         funcion=T.pdf_a_pdfa, multiple=False, filtro=PDF, salida="pdf",
         opciones=[
             dict(k="nivel", t="combo", label="Nivel PDF/A",
                  choices={"2": "PDF/A-2b (recomendado)", "3": "PDF/A-3b",
                           "1": "PDF/A-1b (estricto)"})]),

    # ------------------------------------------------------- CONVERTIR A PDF
    dict(id="jpg_pdf", titulo="JPG a PDF", icono="jpg_pdf",
         categoria="Convertir a PDF",
         descripcion="Convierte tus imágenes a PDF, en el orden que elijas.",
         funcion=T.jpg_a_pdf, multiple=True, filtro=IMG, salida="pdf",
         previsualiza=True, plan="paginas",
         opciones=[
             dict(k="orientacion", t="combo", label="Orientación de página",
                  choices={"auto": "Automática (según la imagen)",
                           "vertical": "Vertical",
                           "horizontal": "Horizontal"}),
             dict(k="margen", t="int", label="Margen en puntos (0-72)",
                  default=0)]),

    dict(id="word_pdf", titulo="Word a PDF", icono="word_pdf",
         categoria="Convertir a PDF",
         descripcion="Convierte documentos Word a PDF.",
         funcion=T.office_a_pdf, multiple=True, filtro=OFFICE, salida="pdf",
         opciones=[]),

    dict(id="ppt_pdf", titulo="PowerPoint a PDF", icono="ppt_pdf",
         categoria="Convertir a PDF",
         descripcion="Convierte presentaciones PowerPoint a PDF.",
         funcion=T.office_a_pdf, multiple=True, filtro=OFFICE, salida="pdf",
         opciones=[]),

    dict(id="excel_pdf", titulo="Excel a PDF", icono="excel_pdf",
         categoria="Convertir a PDF",
         descripcion="Convierte hojas de cálculo con las columnas ajustadas.",
         funcion=T.office_a_pdf, multiple=True, filtro=OFFICE, salida="pdf",
         opciones=[]),

    dict(id="html_pdf", titulo="HTML a PDF", icono="html_pdf",
         categoria="Convertir a PDF",
         descripcion="Convierte una página web o un archivo HTML a PDF.",
         funcion=T.html_a_pdf, multiple=True, filtro=WEB, salida="pdf",
         opciones=[dict(k="url", t="text", label="Dirección web (opcional)",
                        placeholder="https://ejemplo.com")],
         sin_entrada=True),

    dict(id="escanear", titulo="Escanear a PDF", icono="escanear",
         categoria="Convertir a PDF",
         descripcion="Trae el documento del escáner directamente a PDF.",
         funcion=T.escanear_a_pdf, multiple=True, filtro=IMG, salida="pdf",
         opciones=[], sin_entrada=True,
         pista="Si no hay escáner, añade fotos JPG y se unirán en un PDF."),

    # ------------------------------------------------------------------ EDITAR
    dict(id="editar", titulo="Editar PDF", icono="editar", categoria="Editar",
         descripcion="Añade texto, imágenes, formas, resaltados y enlaces.",
         funcion=T.editar_pdf, multiple=False, filtro=PDF, salida="pdf",
         editor=True,
         opciones=[dict(k="password", t="password",
                        label="Contraseña (si está protegido)")]),

    dict(id="marca_agua", titulo="Marca de agua", icono="marca_agua",
         categoria="Editar",
         descripcion="Estampa un texto o una imagen sobre el documento.",
         funcion=T.marca_agua_pdf, multiple=True, filtro=PDF, salida="pdf",
         opciones=[
             dict(k="tipo", t="combo", label="Tipo de marca",
                  choices={"texto": "Texto", "imagen": "Imagen"}),
             dict(k="texto", t="text", label="Texto de la marca",
                  default="CONFIDENCIAL"),
             dict(k="imagen", t="image", label="Imagen de la marca"),
             dict(k="posicion", t="combo", label="Posición",
                  choices={p: p.capitalize() for p in (
                      "centro", "superior izquierda", "superior centro",
                      "superior derecha", "centro izquierda", "centro derecha",
                      "inferior izquierda", "inferior centro",
                      "inferior derecha")}),
             dict(k="rotacion", t="combo", label="Inclinación",
                  choices={"45": "45°", "0": "Sin inclinación", "90": "90°",
                           "315": "-45°"}),
             dict(k="opacidad", t="int", label="Opacidad (%)", default=30),
             dict(k="tamano", t="int", label="Tamaño", default=48),
             dict(k="paginas", t="pages", label="Páginas (vacío = todas)"),
             dict(k="password", t="password",
                  label="Contraseña (si está protegido)")]),

    dict(id="firmar", titulo="Firmar PDF", icono="firmar", categoria="Editar",
         descripcion="Dibuja tu firma con el ratón y estampala en el PDF.",
         funcion=T.firmar_pdf, multiple=True, filtro=PDF, salida="pdf",
         opciones=[
             dict(k="imagen", t="image", label="Firma", firma=True),
             dict(k="posicion", t="combo", label="Posición",
                  choices={p: p.capitalize() for p in (
                      "inferior derecha", "inferior centro",
                      "inferior izquierda", "centro", "superior derecha",
                      "superior izquierda")}),
             dict(k="tamano", t="int", label="Tamaño (% del ancho)",
                  default=25),
             dict(k="paginas", t="pages", label="Páginas (vacío = la última)"),
             dict(k="password", t="password",
                  label="Contraseña (si está protegido)")]),

    dict(id="numeros", titulo="Números de página", icono="numeros",
         categoria="Editar",
         descripcion="Numera las páginas donde y como quieras.",
         funcion=T.numeros_pagina_pdf, multiple=False, filtro=PDF, salida="pdf",
         opciones=[
             dict(k="formato", t="text", label="Formato ({n} y {t})",
                  default="Página {n} de {t}"),
             dict(k="posicion", t="combo", label="Posición",
                  choices={p: p.capitalize() for p in (
                      "inferior centro", "inferior derecha",
                      "inferior izquierda", "superior centro",
                      "superior derecha", "superior izquierda")}),
             dict(k="tamano", t="int", label="Tamaño de letra", default=11),
             dict(k="inicio", t="int", label="Primer número", default=1),
             dict(k="paginas", t="pages", label="Páginas (vacío = todas)"),
             dict(k="password", t="password",
                  label="Contraseña (si está protegido)")]),

    dict(id="recortar", titulo="Recortar PDF", icono="recortar",
         categoria="Editar",
         descripcion="Elimina los márgenes que no necesitas.",
         funcion=T.recortar_pdf, multiple=False, filtro=PDF, salida="pdf",
         opciones=[
             dict(k="izquierda", t="int", label="Margen izquierdo (%)",
                  default=5),
             dict(k="derecha", t="int", label="Margen derecho (%)", default=5),
             dict(k="superior", t="int", label="Margen superior (%)", default=5),
             dict(k="inferior", t="int", label="Margen inferior (%)", default=5),
             dict(k="paginas", t="pages", label="Páginas (vacío = todas)"),
             dict(k="password", t="password",
                  label="Contraseña (si está protegido)")]),

    dict(id="censurar", titulo="Censurar PDF", icono="censurar",
         categoria="Editar",
         descripcion="Oculta para siempre el texto o las zonas sensibles.",
         funcion=T.censurar_pdf, multiple=False, filtro=PDF, salida="pdf",
         opciones=[
             dict(k="modo", t="combo", label="Modo",
                  choices={"texto": "Buscar y censurar texto",
                           "area": "Censurar un área rectangular"}),
             dict(k="buscar", t="text",
                  label="Texto a ocultar (separa con comas)"),
             dict(k="pagina", t="int", label="Página (modo área)", default=1),
             dict(k="area", t="text", label="Área %: x0,y0,x1,y1 (modo área)",
                  default="10,10,50,20"),
             dict(k="password", t="password",
                  label="Contraseña (si está protegido)")]),

    dict(id="formularios", titulo="Formularios PDF", icono="formularios",
         categoria="Editar",
         descripcion="Crea, rellena o lista los campos de un formulario.",
         funcion=T.formularios_pdf, multiple=False, filtro=PDF, salida="pdf",
         opciones=[
             dict(k="modo", t="combo", label="Acción",
                  choices={"crear": "Crear campos rellenables",
                           "rellenar": "Rellenar el formulario",
                           "listar": "Ver los campos (plantilla .txt)"}),
             dict(k="campos", t="multiline",
                  label="Campos a crear: tipo;página;x;y;ancho;alto;nombre;valor",
                  placeholder="texto;1;10;12;40;6;nombre;Ana\n"
                              "casilla;1;10;22;5;5;acepto;si\n"
                              "desplegable;1;10;32;40;6;ciudad;"
                              "Madrid|Bilbao|Sevilla\n"
                              "firma;1;10;45;40;12;firma_cliente;"),
             dict(k="valores", t="multiline",
                  label="Valores para rellenar: campo=valor",
                  placeholder="nombre=Ana\napellido=Pérez"),
             dict(k="password", t="password",
                  label="Contraseña (si está protegido)")]),

    # --------------------------------------------------------------- SEGURIDAD
    dict(id="proteger", titulo="Proteger PDF", icono="proteger",
         categoria="Seguridad",
         descripcion="Cifra el PDF con contraseña (AES-256).",
         funcion=T.proteger_pdf, multiple=False, filtro=PDF, salida="pdf",
         opciones=[
             dict(k="clave", t="password", label="Contraseña nueva"),
             dict(k="clave_propietario", t="password",
                  label="Contraseña de propietario (opcional)"),
             dict(k="password", t="password",
                  label="Contraseña actual (si ya está protegido)")]),

    dict(id="desbloquear", titulo="Desbloquear PDF", icono="desbloquear",
         categoria="Seguridad",
         descripcion="Quita la contraseña y usa el PDF como quieras.",
         funcion=T.desbloquear_pdf, multiple=True, filtro=PDF, salida="pdf",
         opciones=[dict(k="password", t="password", label="Contraseña actual")]),

    dict(id="comparar", titulo="Comparar PDF", icono="comparar",
         categoria="Seguridad",
         descripcion="Marca en rojo las diferencias entre dos documentos.",
         funcion=T.comparar_pdf, multiple=True, filtro=PDF, salida="pdf",
         opciones=[dict(k="dpi", t="combo", label="Precisión",
                        choices={"72": "Rápida", "100": "Normal",
                                 "150": "Alta"})],
         pista="Selecciona exactamente 2 documentos PDF."),

    # ----------------------------------------------------------- INTELIGENCIA
    dict(id="resumir", titulo="Resumir PDF", icono="resumir",
         categoria="Inteligencia",
         descripcion="Saca las ideas clave del documento en segundos.",
         funcion=T.resumir_pdf, multiple=False, filtro=PDF, salida="file:.md",
         opciones=[
             dict(k="frases", t="int", label="Ideas clave", default=12),
             dict(k="formato", t="combo", label="Formato del resumen",
                  choices={"md": "Markdown (.md)", "txt": "Texto (.txt)",
                           "pdf": "PDF (.pdf)"}),
             dict(k="password", t="password",
                  label="Contraseña (si está protegido)")],
         ext_por_opcion=("formato", {"md": ".md", "txt": ".txt",
                                     "pdf": ".pdf"})),

    dict(id="traducir", titulo="Traducir PDF", icono="traducir",
         categoria="Inteligencia",
         descripcion="Traduce el documento con un traductor local opcional.",
         funcion=T.traducir_pdf, multiple=False, filtro=PDF, salida="file:.pdf",
         opciones=[
             dict(k="origen", t="combo", label="Idioma original",
                  choices={"es": "Español", "en": "Inglés", "fr": "Francés",
                           "de": "Alemán", "it": "Italiano",
                           "pt": "Portugués"}),
             dict(k="destino", t="combo", label="Traducir a",
                  choices={"en": "Inglés", "es": "Español", "fr": "Francés",
                           "de": "Alemán", "it": "Italiano",
                           "pt": "Portugués"}),
             dict(k="formato", t="combo", label="Formato de salida",
                  choices={"pdf": "PDF (.pdf)", "md": "Markdown (.md)",
                           "txt": "Texto (.txt)"}),
             dict(k="password", t="password",
                  label="Contraseña (si está protegido)")],
         ext_por_opcion=("formato", {"pdf": ".pdf", "md": ".md",
                                     "txt": ".txt"}),
         pista="Necesita el motor local argostranslate (gratis)."),
]

BY_ID = {t["id"]: t for t in TOOLS}

CATEGORIAS = ["Organizar", "Optimizar", "Convertir desde PDF",
              "Convertir a PDF", "Editar", "Seguridad", "Inteligencia"]
