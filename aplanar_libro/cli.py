"""Línea de comandos.

    aplanar-libro libro.pdf                  # los tres pasos
    aplanar-libro libro.pdf --solo aplanar   # solo el paso 1
    aplanar-libro libro.pdf --paginas 2,4,6  # aplanar solo esas páginas
"""
from __future__ import annotations

import argparse
import json
import time
from datetime import datetime
from pathlib import Path

from .aplanar import aplanar_pdf, resultados_a_dict
from .leer import leer_pdf
from .markdown import pdf_a_markdown


def _paginas(texto: str | None) -> list[int] | None:
    if not texto:
        return None
    if texto in ("pares", "impares"):
        return texto  # se resuelve cuando se conoce el número de páginas
    return [int(x) for x in texto.split(",") if x.strip()]


def _duracion(segundos: float) -> str:
    m, s = divmod(int(round(segundos)), 60)
    return f"{m} min {s:02d} s" if m else f"{s} s"


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(prog="aplanar-libro",
                                description="Aplana páginas curvas, pasa OCR en español y genera Markdown.")
    p.add_argument("pdf", type=Path, help="PDF escaneado de entrada")
    p.add_argument("--solo", choices=["aplanar", "leer", "markdown"],
                   help="correr un solo paso (por defecto, los tres)")
    p.add_argument("--paginas", help="páginas a aplanar: 2,4,6 | pares | impares (por defecto, todas)")
    p.add_argument("--idioma", default="spa", help="idioma de Tesseract (por defecto spa; no mezclar)")
    p.add_argument("--modo", default="libro", choices=["libro", "auto"],
                   help="libro = un solo bloque de texto; auto = deja que Tesseract busque columnas")
    p.add_argument("--dpi", type=int, default=300)
    p.add_argument("--nucleos", type=int, default=None,
                   help="páginas que se aplanan a la vez (por defecto, todos los núcleos menos uno, máx. 8)")
    a = p.parse_args(argv)

    base = a.pdf.with_suffix("")
    plano = base.with_name(base.name + "_plano.pdf")
    ocr = base.with_name(base.name + "_ocr.pdf")
    md = base.with_name(base.name + "_ocr.md")
    informe = base.with_name(base.name + "_informe.json")
    tiempos_json = base.with_name(base.name + "_tiempos.json")
    tiempos: dict[str, float] = {}
    inicio_total = time.perf_counter()

    def medir(paso: str, desde: float) -> None:
        tiempos[paso] = round(time.perf_counter() - desde, 1)
        print(f"  {paso}: {_duracion(tiempos[paso])}")

    paginas = _paginas(a.paginas)
    if paginas in ("pares", "impares"):
        import pymupdf as fitz
        n = len(fitz.open(a.pdf))
        paginas = [i for i in range(1, n + 1) if (i % 2 == 0) == (paginas == "pares")]

    resultados = None
    if a.solo in (None, "aplanar"):
        print("Paso 1: aplanar")
        t = time.perf_counter()
        resultados = resultados_a_dict(aplanar_pdf(a.pdf, plano, dpi=a.dpi, paginas=paginas, nucleos=a.nucleos))
        informe.write_text(json.dumps(resultados, ensure_ascii=False, indent=2), encoding="utf-8")
        medir("aplanar", t)
    if a.solo in (None, "leer"):
        print("Paso 2: leer (OCR)")
        # Corrección 14/11/2026: con --solo leer se leía el PDF original aunque
        # existiera el aplanado. Ahora se usa el aplanado si existe.
        entrada = plano if plano.exists() else a.pdf
        print(f"  entrada: {entrada.name}")
        t = time.perf_counter()
        leer_pdf(entrada, ocr, idioma=a.idioma, modo=a.modo)
        medir("leer", t)
    if a.solo in (None, "markdown"):
        print("Paso 3: Markdown")
        if resultados is None and informe.exists():
            resultados = json.loads(informe.read_text(encoding="utf-8"))
        # Misma corrección: con --solo markdown se usa el PDF con OCR si existe.
        entrada = ocr if ocr.exists() else a.pdf
        print(f"  entrada: {entrada.name}")
        t = time.perf_counter()
        resumen = pdf_a_markdown(entrada, md, resultados)
        medir("markdown", t)
        print(f"  {resumen['paginas']} páginas, {resumen['sin_texto']} sin texto, "
              f"revisar a mano: {resumen['a_revisar'] or 'ninguna'}")

    tiempos["total"] = round(time.perf_counter() - inicio_total, 1)
    registro = {"fecha": datetime.now().isoformat(timespec="seconds"), "archivo": a.pdf.name,
                "pasos": a.solo or "todos", "segundos": tiempos}
    tiempos_json.write_text(json.dumps(registro, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Listo. Tiempo total: {_duracion(tiempos['total'])}")


if __name__ == "__main__":
    main()
