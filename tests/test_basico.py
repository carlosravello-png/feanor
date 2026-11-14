"""Pruebas rápidas, sin material con derechos de autor: imágenes y PDF sintéticos."""
import cv2
import pymupdf as fitz
import numpy as np

from aplanar_libro.aplanar import recortar
from aplanar_libro.markdown import pdf_a_markdown


def _pagina_sintetica():
    img = np.full((1200, 900), 255, np.uint8)
    for k in range(12):  # doce líneas de "texto" en el centro
        cv2.putText(img, "linea de prueba numero %d" % k, (150, 300 + 50 * k),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, 0, 2)
    cv2.putText(img, "X", (850, 1150), cv2.FONT_HERSHEY_SIMPLEX, 12, 0, 30)  # basura gigante en el borde
    return img


def test_recorte_quita_basura_y_conserva_texto():
    img = _pagina_sintetica()
    texto = img[:, :800] < 128                     # zona del texto, sin la X gigante
    cols = np.where(texto[:900].any(axis=0))[0]
    filas = np.where(texto.any(axis=1))[0]
    rec = recortar(img)
    alto, ancho = rec.shape
    assert alto < 1000                             # quitó la X gigante de abajo
    assert ancho >= cols.max() - cols.min() + 1    # no cortó el final de las líneas
    assert alto >= filas.max() - filas.min() + 1   # ni la primera ni la última línea


def test_markdown_marca_paginas_y_avisos(tmp_path):
    pdf = tmp_path / "x.pdf"
    doc = fitz.open()
    for t in ("uno", "dos"):
        doc.new_page().insert_text((72, 72), t)
    doc.save(pdf)
    md = tmp_path / "x.md"
    res = pdf_a_markdown(pdf, md, [{"pagina": 2, "aplanada": False, "lineas": 3, "motivo": "pocas líneas"}])
    texto = md.read_text(encoding="utf-8")
    assert "<!-- página 1 del visor -->" in texto and "<!-- página 2 del visor -->" in texto
    assert "REVISAR A MANO: pocas líneas" in texto
    assert res["a_revisar"] == [2]
