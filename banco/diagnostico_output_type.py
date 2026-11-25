"""Diagnóstico de --output-type: ¿cuántas páginas que NO se mandan al OCR cambian
de texto al reescribir el PDF, con «auto» (PDF/A, el valor por defecto de
OCRmyPDF) y con «pdf» (el de Feanor desde la 0.5.5)?

    python banco\\diagnostico_output_type.py ruta\\tesis1.pdf ruta\\tesis2.pdf

Para cada PDF manda al OCR, con el mismo comando que el lote, solo las páginas
que Feanor clasifica como escaneadas, una vez con cada modo, y compara el texto
de todas las demás páginas con el del original. No escribe nada junto a los PDF:
trabaja en una carpeta temporal que borra al terminar.
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import pymupdf as fitz

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from feanor_el_aplasta_libros.entorno import entorno_ocr  # noqa: E402
from feanor_el_aplasta_libros.leer import ocr_paginas  # noqa: E402
from feanor_el_aplasta_libros.tipo_pdf import clasificar  # noqa: E402


def medir(pdf: Path, pedidas: list[int], tipo_salida: str, carpeta: Path) -> dict:
    salida = carpeta / f"{pdf.stem}_{tipo_salida}.pdf"
    ocr_paginas(pdf, salida, pedidas, tipo_salida=tipo_salida)
    with fitz.open(pdf) as a, fitz.open(salida) as b:
        otras = [i for i in range(1, len(a) + 1) if i not in pedidas]
        alteradas = [i for i in otras if a[i - 1].get_text("text") != b[i - 1].get_text("text")]
        espacios = [i for i in alteradas if a[i - 1].get_text("text").split() == b[i - 1].get_text("text").split()]
        leidas = sum(len(b[i - 1].get_text("text").split()) for i in pedidas)
    return {"alteradas": alteradas, "solo_espacios": espacios,
            "palabras": [i for i in alteradas if i not in espacios], "palabras_leidas_por_ocr": leidas}


def main(rutas: list[str]) -> None:
    e = entorno_ocr()
    print(f"Feanor {e['feanor']} · OCRmyPDF {e['ocrmypdf']} · {e['tesseract']} · Ghostscript {e['ghostscript']}")
    with tempfile.TemporaryDirectory() as tmp:
        for ruta in rutas:
            pdf = Path(ruta)
            tipos = clasificar(pdf)
            pedidas = [i for i, t in enumerate(tipos, start=1) if t == "escaneada"]
            print(f"\n== {pdf.name}: {len(tipos)} páginas; al OCR: {pedidas or 'ninguna (no hay páginas escaneadas)'}")
            if not pedidas:
                continue
            for modo in ("auto", "pdf"):
                r = medir(pdf, pedidas, modo, Path(tmp))
                print(f"   --output-type {modo:4}: alteradas {len(r['alteradas']):3} "
                      f"(solo espacios {len(r['solo_espacios'])}, cambian palabras {len(r['palabras'])}); "
                      f"palabras leídas por OCR en las pedidas: {r['palabras_leidas_por_ocr']}")
                if r["palabras"]:
                    print(f"      páginas con palabras cambiadas: {r['palabras'][:20]}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    main(sys.argv[1:])
