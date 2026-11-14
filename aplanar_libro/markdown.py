"""Paso 3: pasar el PDF con texto a Markdown, página por página.

Cada página va precedida de una marca con el número del VISOR, que no es el
folio impreso del libro: para citar, el folio se lee en la imagen.
Las páginas que no se pudieron aplanar llevan un aviso para revisarlas a mano.
"""
from __future__ import annotations

from pathlib import Path

import pymupdf as fitz  # PyMuPDF


def pdf_a_markdown(entrada: Path, salida: Path, resultados: list[dict] | None = None) -> dict:
    """Escribe el texto de `entrada` en `salida` (.md). Devuelve un resumen."""
    avisos = {}
    for r in resultados or []:
        if not r["aplanada"] and r["motivo"] not in ("no pedida", "aplanada"):
            avisos[r["pagina"]] = r["motivo"]

    doc = fitz.open(entrada)
    partes = [
        f"<!-- Texto extraído por OCR de: {Path(entrada).name} -->",
        "<!-- El OCR sirve para leer y buscar. Cifras, nombres y citas se verifican en la imagen. -->",
        "",
    ]
    vacias = 0
    for i, pagina in enumerate(doc, start=1):
        texto = pagina.get_text("text").strip()
        if not texto:
            vacias += 1
        partes.append(f"<!-- página {i} del visor -->")
        if i in avisos:
            partes.append(f"<!-- REVISAR A MANO: {avisos[i]} -->")
        partes.append("")
        partes.append(texto)
        partes.append("")
    Path(salida).write_text("\n".join(partes), encoding="utf-8")
    return {"paginas": len(doc), "sin_texto": vacias, "a_revisar": sorted(avisos)}
