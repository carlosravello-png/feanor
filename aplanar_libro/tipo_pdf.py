"""¿De dónde sale el texto de cada página de un PDF?

Un PDF puede traer el texto de tres maneras, y cada una deja su huella:

- digital: el texto viene de origen (Word, LaTeX, la editorial) y se ve. Se
  copia tal cual, sin aplanar ni OCR.
- ocr_previo: la página es una foto y alguien ya le pasó OCR antes de Feanor.
  El texto está, pero puesto por otro programa: invisible encima de la foto
  (lo habitual) o escondido debajo de ella. Se puede copiar, pero puede traer
  los errores de ese OCR.
- escaneada: una foto sin texto. Va por el camino largo: aplanar y leer.

Y dos casos de borde: «vacia» (ni texto ni imagen: una hoja en blanco o solo
dibujos) y «dudosa» (texto visible y texto de OCR mezclados en la misma
página). Se decide página por página, porque un mismo PDF puede mezclar tipos.

Solo se lee la estructura del PDF (qué se dibuja, en qué orden y si es
visible); no se renderiza ni se lee ninguna imagen.
"""
from __future__ import annotations

from pathlib import Path

import pymupdf as fitz

PALABRAS_MINIMAS = 3      # menos que esto en una página no cuenta como «tiene texto»
COBERTURA_FOTO = 0.30     # una imagen que cubre al menos esto de la página la hace «foto»
COBERTURA_TAPA = 0.90     # una imagen así de grande tapa el texto que se dibujó antes
OCR_SI = 0.90             # fracción de texto invisible o tapado para decir «OCR previo»
OCR_NO = 0.10             # por debajo de esto, el texto es digital; entre ambos, «dudosa»

TIPOS = ("digital", "ocr_previo", "dudosa", "escaneada", "vacia")


def _fraccion_ocr(pagina) -> float:
    """Fracción del texto de la página que es invisible o que queda tapado por una
    imagen de página completa dibujada después. Eso es lo que deja un OCR."""
    area = abs(pagina.rect) or 1
    vistos: list[fitz.Rect] = []
    total = invisibles = tapados = 0
    for tipo, caja in pagina.get_bboxlog():
        if tipo in ("fill-text", "stroke-text", "ignore-text"):
            total += 1
            if tipo == "ignore-text":
                invisibles += 1
            else:
                vistos.append(fitz.Rect(caja))
        elif tipo == "fill-image" and vistos:
            img = fitz.Rect(caja) & pagina.rect
            if abs(img) / area >= COBERTURA_TAPA:
                quedan = [c for c in vistos if not img.contains(c)]
                tapados += len(vistos) - len(quedan)
                vistos = quedan
    return (invisibles + tapados) / total if total else 0.0


def _cobertura_imagen(pagina) -> float:
    area = abs(pagina.rect) or 1
    mayor = 0.0
    for info in pagina.get_image_info():
        mayor = max(mayor, abs(fitz.Rect(info["bbox"]) & pagina.rect) / area)
    return mayor


def tipo_de_pagina(pagina) -> str:
    palabras = len(pagina.get_text("text").split())
    if palabras >= PALABRAS_MINIMAS:
        ocr = _fraccion_ocr(pagina)
        if ocr >= OCR_SI:
            return "ocr_previo"
        if ocr > OCR_NO:
            return "dudosa"
        return "digital"
    return "escaneada" if _cobertura_imagen(pagina) >= COBERTURA_FOTO else "vacia"


def clasificar(pdf: Path) -> list[str]:
    """El tipo de cada página, en orden (la página 1 es el elemento 0)."""
    with fitz.open(pdf) as doc:
        return [tipo_de_pagina(p) for p in doc]


def rangos(numeros: list[int]) -> str:
    """[1, 2, 3, 7, 9, 10] → «1–3, 7, 9–10»."""
    tramos: list[list[int]] = []
    for n in sorted(numeros):
        if tramos and n == tramos[-1][1] + 1:
            tramos[-1][1] = n
        else:
            tramos.append([n, n])
    return ", ".join(f"{a}" if a == b else f"{a}–{b}" for a, b in tramos)


def por_tipo(tipos: list[str]) -> dict[str, list[int]]:
    """{tipo: [números de página]}, solo con los tipos presentes."""
    salida: dict[str, list[int]] = {}
    for i, t in enumerate(tipos, start=1):
        salida.setdefault(t, []).append(i)
    return salida
