# -*- coding: utf-8 -*-
"""Genera los iconos PNG de las herramientas (96x96, tile pastel + glifo blanco).

Los iconos se hornean como PNG, así la app no depende de fuentes en runtime.
Uso:  python tools/generate_icons.py
"""
import math
import os
import sys

from PIL import Image, ImageDraw, ImageFont

SIZE = 96
RADIUS = 22
GLYPH = (255, 255, 255, 255)


def _resolver_fuente(candidatas, por_defecto=None):
    """Primera fuente que exista en el sistema (Linux, Windows o macOS)."""
    for ruta in candidatas:
        if ruta and os.path.exists(ruta):
            return ruta
    return por_defecto


FONT_BOLD = _resolver_fuente([
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    r"C:\Windows\Fonts\arialbd.ttf",
    r"C:\Windows\Fonts\segoeuib.ttf",
    r"C:\Windows\Fonts\tahomabd.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
])
FONT_REG = _resolver_fuente([
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    r"C:\Windows\Fonts\arial.ttf",
    r"C:\Windows\Fonts\segoeui.ttf",
    r"C:\Windows\Fonts\tahoma.ttf",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
])

OUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "assets", "icons")


# ---------------------------------------------------------------- utilidades
def rr(draw, box, r, fill):
    draw.rounded_rectangle(box, radius=r, fill=fill)


def _cargar_fuente(font, size):
    if font:
        try:
            return ImageFont.truetype(font, size)
        except OSError:
            pass
    try:
        return ImageFont.load_default(size)
    except TypeError:                    # Pillow antiguo
        return ImageFont.load_default()


def text_center(draw, cx, cy, s, size, font=None):
    f = _cargar_fuente(font or FONT_BOLD, size)
    box = draw.textbbox((0, 0), s, font=f)
    w, h = box[2] - box[0], box[3] - box[1]
    draw.text((cx - w / 2 - box[0], cy - h / 2 - box[1]), s, font=f, fill=GLYPH)


def doc_shape(draw, cx, cy, w, h, fold=8, fill=GLYPH):
    """Documento con esquina doblada."""
    x0, y0, x1, y1 = cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2
    pts = [(x0, y0), (x1 - fold, y0), (x1, y0 + fold), (x1, y1), (x0, y1)]
    draw.polygon(pts, fill=fill)


def arrow(draw, x0, y0, x1, y1, width=5, head=9, fill=GLYPH):
    draw.line([(x0, y0), (x1, y1)], fill=fill, width=width)
    ang = math.atan2(y1 - y0, x1 - x0)
    for da in (math.radians(150), math.radians(-150)):
        draw.line([(x1, y1),
                   (x1 + head * math.cos(ang + da), y1 + head * math.sin(ang + da))],
                  fill=fill, width=width)


def padlock(draw, cx, cy, s, open_=False):
    bw, bh = s, s * 0.72
    rr(draw, [cx - bw / 2, cy - bh / 2 + s * 0.18, cx + bw / 2, cy + bh / 2 + s * 0.18],
       r=int(s * 0.14), fill=GLYPH)
    sw = int(s * 0.16)
    top = cy - s * 0.30
    if open_:
        draw.arc([cx - bw * 0.30 - s * 0.14, top - s * 0.30, cx + bw * 0.34, top + s * 0.34],
                 start=200, end=70, fill=GLYPH, width=sw)
    else:
        draw.arc([cx - bw * 0.30, top - s * 0.30, cx + bw * 0.30, top + s * 0.34],
                 start=180, end=360, fill=GLYPH, width=sw)


def eye(draw, cx, cy, s):
    w, h = s * 1.15, s * 0.62
    draw.ellipse([cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2], outline=GLYPH, width=5)
    r = s * 0.22
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=GLYPH)


def image_glyph(draw, cx, cy, s):
    draw.rounded_rectangle([cx - s / 2, cy - s * 0.42, cx + s / 2, cy + s * 0.42],
                        radius=6, outline=GLYPH, width=5)
    r = s * 0.11
    draw.ellipse([cx - s * 0.28, cy - s * 0.24, cx - s * 0.28 + 2 * r, cy - s * 0.24 + 2 * r],
                 fill=GLYPH)
    draw.polygon([(cx - s * 0.42, cy + s * 0.30), (cx - s * 0.08, cy - s * 0.06),
                  (cx + s * 0.10, cy + s * 0.12), (cx + s * 0.24, cy - s * 0.02),
                  (cx + s * 0.42, cy + s * 0.30)], fill=GLYPH)


def crop_glyph(draw, cx, cy, s):
    w = 6
    L = s * 0.34
    off = s * 0.32
    for sx, sy in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
        x, y = cx + sx * off, cy + sy * off
        draw.line([(x, y), (x - sx * L, y)], fill=GLYPH, width=w)
        draw.line([(x, y), (x, y - sy * L)], fill=GLYPH, width=w)


def droplet(draw, cx, cy, s):
    r = s * 0.42
    top = (cx, cy - s * 0.52)
    draw.pieslice([cx - r, cy - r * 0.4, cx + r, cy + r * 1.6], 0, 360, fill=GLYPH)
    draw.polygon([top, (cx - r * 0.86, cy + r * 0.35), (cx + r * 0.86, cy + r * 0.35)],
                 fill=GLYPH)


# ------------------------------------------------------------------ glifos
def g_unir(d, c):
    doc_shape(d, 34, 48, 22, 30)
    doc_shape(d, 62, 48, 22, 30)
    text_center(d, 48, 48, "+", 30)


def g_dividir(d, c):
    doc_shape(d, 40, 48, 24, 32)
    text_center(d, 62, 48, "✂", 30, FONT_REG)


def g_comprimir(d, c):
    doc_shape(d, 48, 48, 26, 34)
    arrow(d, 20, 48, 33, 48)
    arrow(d, 76, 48, 63, 48)


def g_letra(letter):
    def f(d, c):
        text_center(d, 48, 46, letter, 44)
    return f


def g_letra_flecha(letter):
    def f(d, c):
        text_center(d, 42, 46, letter, 40)
        arrow(d, 66, 60, 78, 60, width=4, head=7)
    return f


def g_editar(d, c):
    doc_shape(d, 44, 48, 24, 32)
    text_center(d, 62, 40, "✎", 30, FONT_REG)


def g_pdf_jpg(d, c):
    image_glyph(d, 48, 48, 44)


def g_jpg_pdf(d, c):
    image_glyph(d, 40, 48, 36)
    arrow(d, 66, 60, 78, 60, width=4, head=7)


def g_firmar(d, c):
    d.line([(34, 56), (58, 32)], fill=GLYPH, width=7)
    d.polygon([(54, 30), (66, 24), (72, 34), (60, 42)], fill=GLYPH)
    d.line([(28, 70), (68, 70)], fill=GLYPH, width=4)


def g_marca_agua(d, c):
    doc_shape(d, 42, 48, 26, 34)
    droplet(d, 62, 56, 22)


def g_rotar(d, c):
    d.arc([28, 26, 68, 66], start=40, end=320, fill=GLYPH, width=6)
    arrow(d, 62, 30, 66, 42, width=6, head=8)


def g_html(d, c):
    text_center(d, 48, 48, "</>", 34)


def g_desbloquear(d, c):
    padlock(d, 48, 46, 34, open_=True)


def g_proteger(d, c):
    padlock(d, 48, 46, 34, open_=False)


def g_ordenar(d, c):
    for i, w in enumerate((30, 22, 14)):
        rr(d, [26, 30 + i * 14, 26 + w, 38 + i * 14], r=3, fill=GLYPH)
    d.line([(62, 30), (62, 66)], fill=GLYPH, width=4)
    arrow(d, 62, 30, 62, 40, width=4, head=7)
    arrow(d, 62, 66, 62, 56, width=4, head=7)


def g_pdfa(d, c):
    text_center(d, 48, 46, "A", 44)
    rr(d, [30, 66, 66, 72], r=3, fill=GLYPH)


def g_reparar(d, c):
    text_center(d, 48, 48, "⚒", 40, FONT_REG)


def g_numeros(d, c):
    text_center(d, 48, 42, "123", 30)
    d.line([(30, 64), (66, 64)], fill=GLYPH, width=4)


def g_escanear(d, c):
    rr(d, [28, 40, 68, 60], r=6, fill=GLYPH)
    d.rectangle([30, 46, 66, 52], fill=(0, 0, 0, 90))
    arrow(d, 48, 66, 48, 78, width=4, head=7)


def g_ocr(d, c):
    eye(d, 48, 42, 30)
    text_center(d, 48, 68, "A", 22)


def g_comparar(d, c):
    doc_shape(d, 34, 48, 20, 28)
    doc_shape(d, 62, 48, 20, 28)
    text_center(d, 48, 70, "⇄", 22, FONT_REG)


def g_censurar(d, c):
    doc_shape(d, 46, 48, 28, 36)
    d.rectangle([34, 38, 58, 44], fill=(40, 40, 40, 255))
    d.rectangle([34, 50, 54, 56], fill=(40, 40, 40, 255))


def g_recortar(d, c):
    crop_glyph(d, 48, 48, 40)


def g_formularios(d, c):
    for i in range(3):
        y = 32 + i * 16
        d.rounded_rectangle([28, y, 38, y + 10], radius=2, outline=GLYPH, width=3)
        d.line([(44, y + 5), (68, y + 5)], fill=GLYPH, width=4)
    text_center(d, 33, 37, "✓", 12)


def g_markdown(d, c):
    text_center(d, 48, 48, "M↓", 36)


def g_eliminar(d, c):
    """Papelera: tapa, cuerpo y ranuras."""
    d.rounded_rectangle([34, 24, 62, 32], radius=3, fill=GLYPH)
    d.rectangle([44, 19, 52, 24], fill=GLYPH)
    d.polygon([(32, 36), (64, 36), (60, 74), (36, 74)], fill=GLYPH)
    for x in (41, 48, 55):
        d.line([(x, 44), (x - 1, 66)], fill=(0, 0, 0, 70), width=3)


def g_extraer(d, c):
    """Documento con una flecha que sale de él."""
    doc_shape(d, 42, 48, 26, 34)
    arrow(d, 54, 48, 78, 48, width=5, head=9)


def g_resumir(d, c):
    """Documento con las líneas destacadas del resumen."""
    doc_shape(d, 48, 48, 30, 38, fill=GLYPH)
    d.rectangle([36, 36, 60, 42], fill=(0, 0, 0, 90))
    d.rectangle([36, 47, 56, 52], fill=(0, 0, 0, 60))
    d.rectangle([36, 57, 52, 62], fill=(0, 0, 0, 60))
    text_center(d, 62, 30, "*", 30)


def g_traducir(d, c):
    """Letra A + líneas de texto + flecha (traducción)."""
    text_center(d, 36, 40, "A", 34)
    d.line([(52, 32), (70, 32)], fill=GLYPH, width=5)
    d.line([(46, 46), (70, 46)], fill=GLYPH, width=5)
    arrow(d, 46, 62, 72, 62, width=5, head=8)


# ------------------------------------------------------------------ registro
ICONS = {
    "unir":          (g_unir,          "#E86A6A"),
    "dividir":       (g_dividir,       "#F08C4A"),
    "comprimir":     (g_comprimir,     "#57B894"),
    "pdf_word":      (g_letra_flecha("W"), "#4A7FD4"),
    "pdf_ppt":       (g_letra_flecha("P"), "#9B59B6"),
    "pdf_excel":     (g_letra_flecha("X"), "#3FA05A"),
    "word_pdf":      (g_letra("W"),    "#2E5FA3"),
    "ppt_pdf":       (g_letra("P"),    "#7D3C98"),
    "excel_pdf":     (g_letra("X"),    "#2E7D46"),
    "editar":        (g_editar,        "#B5577B"),
    "pdf_jpg":       (g_pdf_jpg,       "#D4A03C"),
    "jpg_pdf":       (g_jpg_pdf,       "#C9A227"),
    "firmar":        (g_firmar,        "#3C6E9E"),
    "marca_agua":    (g_marca_agua,    "#8E5EA2"),
    "rotar":         (g_rotar,         "#7E57C2"),
    "html_pdf":      (g_html,          "#E0A93E"),
    "desbloquear":   (g_desbloquear,   "#3E7CB1"),
    "proteger":      (g_proteger,      "#2C6E9B"),
    "ordenar":       (g_ordenar,       "#D96C4F"),
    "pdf_pdfa":      (g_pdfa,          "#5B7DB1"),
    "reparar":       (g_reparar,       "#5FA052"),
    "numeros":       (g_numeros,       "#8D6E63"),
    "escanear":      (g_escanear,      "#C05555"),
    "ocr":           (g_ocr,           "#4E9B47"),
    "comparar":      (g_comparar,      "#4A6FA5"),
    "censurar":      (g_censurar,      "#37474F"),
    "recortar":      (g_recortar,      "#7B5EA7"),
    "formularios":   (g_formularios,   "#6D4C8E"),
    "pdf_markdown":  (g_markdown,      "#546E7A"),
    "eliminar":      (g_eliminar,      "#C2544A"),
    "extraer":       (g_extraer,       "#4E8D7C"),
    "resumir":       (g_resumir,       "#3F7FA6"),
    "traducir":      (g_traducir,      "#7A55C4"),
}


def generate(solo_faltantes=False):
    os.makedirs(OUT_DIR, exist_ok=True)
    creados = 0
    for name, (glyph_fn, color) in ICONS.items():
        destino = os.path.join(OUT_DIR, f"{name}.png")
        if solo_faltantes and os.path.exists(destino):
            continue
        img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        # sombra suave
        sh = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
        ImageDraw.Draw(sh).rounded_rectangle([4, 8, SIZE - 4, SIZE - 2],
                                             radius=RADIUS, fill=(0, 0, 0, 40))
        img.alpha_composite(sh)
        rr(d, [4, 4, SIZE - 4, SIZE - 8], RADIUS, color)
        glyph_fn(d, color)
        img.save(destino)
        creados += 1
    print(f"{creados} iconos generados en {OUT_DIR} "
          f"(total del catálogo: {len(ICONS)})")


if __name__ == "__main__":
    generate(solo_faltantes="--nuevos" in sys.argv or "--solo-faltantes" in sys.argv)
