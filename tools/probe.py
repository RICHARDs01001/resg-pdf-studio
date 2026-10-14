# -*- coding: utf-8 -*-
"""Sonda rápida de la API de PyMuPDF para validar supuestos del código."""
import pymupdf

print("version:", pymupdf.__version__)
print("Matrix(45) =", pymupdf.Matrix(45))
print("Matrix()   =", pymupdf.Matrix())
print("Matrix(1,1).prerotate(45) =", pymupdf.Matrix(1, 1).prerotate(45))
print("has replace_image:", hasattr(pymupdf.Page, "replace_image"))
print("has Story:", hasattr(pymupdf, "Story"))
print("has get_text_length:", hasattr(pymupdf, "get_text_length"))
print("has pdfocr_tobytes:", hasattr(pymupdf.Pixmap, "pdfocr_tobytes"))

# probar insert_text con morph rotado y verificar caja
doc = pymupdf.open()
page = doc.new_page(width=300, height=300)
piv = pymupdf.Point(150, 150)
page.insert_text(piv, "PRUEBA", fontsize=20,
                 morph=(piv, pymupdf.Matrix(45)))
texto = page.get_text()
print("texto extraido len:", len(texto.strip()))
print("---- fin sonda ----")
