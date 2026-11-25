"""Comparación forzada: ¿cuánto se equivoca el OCR sin aplanar?

Se toman al azar (semilla fija) N PDF digitales del lote y, de cada uno, P
páginas del CUERPO: sin portada, índice, referencias ni anexos, porque ahí la
tipografía cambia y el error no es representativo. Como «cuerpo» cuenta una
página que queda en el cuerpo del texto (ver cuerpo.py) con 150 palabras o más;
así quedan fuera la portada, las dedicatorias y la hoja de jurado.

Cada página se convierte en imagen (300 ppp, escala de grises), se lee con el
MISMO método que el lote aplica a los escaneados (OCRmyPDF, segmentación
automática, sin aplanar) y se compara con su texto nativo:

- los dos textos pasan por la MISMA normalización antes de compararse (ver
  `normalizar`): NFKC (ligaduras «ﬁ», «ﬂ» → letras), guion de fin de línea
  unido, minúsculas, solo letras y números. Sin eso, una ligadura del texto
  nativo o un guion unido en un lado y no en el otro contaban como error del
  OCR sin serlo;
- tasa de error por palabra (WER): distancia de edición entre las dos listas de
  palabras, dividida por las palabras del texto nativo;
- similitud de caracteres (0 a 1) del texto normalizado.

Todo queda en comparacion_ocr/: el texto nativo y el del OCR de cada página,
_comparacion.csv (una fila por página) y _comparacion.md (el resumen).
"""
from __future__ import annotations

import csv
import difflib
import json
import random
import re
import statistics
import unicodedata
from pathlib import Path

PALABRAS_MINIMAS_CUERPO = 150
DPI = 300
_TOKEN = re.compile(r"[a-záéíóúüñ0-9]+")


def normalizar(texto: str) -> str:
    """La misma para el texto nativo y para el del OCR."""
    texto = unicodedata.normalize("NFKC", texto).replace("\u00ad", "")          # ligaduras; guion blando
    texto = re.sub(r"(\w)-[ \t]*\n[ \t]*(\w)", r"\1\2", texto)                 # guion de fin de línea
    return texto.lower()


def _tokens(texto: str) -> list[str]:
    return _TOKEN.findall(normalizar(texto))


def distancia(a: list[str], b: list[str]) -> int:
    """Distancia de edición (sustituciones, inserciones y borrados) entre dos listas."""
    ids: dict[str, int] = {}
    x = [ids.setdefault(t, len(ids)) for t in a]
    y = [ids.setdefault(t, len(ids)) for t in b]
    anterior = list(range(len(y) + 1))
    for i, xi in enumerate(x, start=1):
        actual = [i] + [0] * len(y)
        for j, yj in enumerate(y, start=1):
            actual[j] = min(anterior[j] + 1, actual[j - 1] + 1, anterior[j - 1] + (xi != yj))
        anterior = actual
    return anterior[-1]


def metricas(nativo: str, ocr: str) -> dict:
    a, b = _tokens(nativo), _tokens(ocr)
    errores = distancia(a, b)
    return {"palabras_nativo": len(a), "palabras_ocr": len(b), "errores": errores,
            "wer": round(errores / len(a), 4) if a else None,
            "similitud": round(difflib.SequenceMatcher(None, " ".join(a), " ".join(b), autojunk=False).ratio(), 4)}


def comparar_ocr(base: Path, filas: list[dict], n: int, paginas: int, semilla: int, idioma: str = "spa") -> dict:
    import pymupdf as fitz

    from .cuerpo import cuerpo
    from .entorno import entorno_ocr
    from .leer import ocr_paginas

    salida = base / "comparacion_ocr"
    salida.mkdir(exist_ok=True)
    candidatos = sorted((f for f in filas if f["estado"] in ("convertida", "ya_hecha")
                         and f["tipo"] == "pdf" and f["clase"] == "digital" and f["metodo"] == "texto_nativo"),
                        key=lambda f: f["archivo"])
    azar = random.Random(semilla)
    orden = azar.sample(candidatos, len(candidatos))      # todo el orden al azar: los reemplazos salen de aquí
    print(f"Comparación de OCR: se piden {n} PDF digitales de {len(candidatos)}, "
          f"{paginas} páginas del cuerpo cada uno, semilla {semilla}")
    resultado, medidos, saltados, comandos = [], [], [], {}
    for f in orden:
        if len(medidos) == n:
            break
        stem = Path(f["archivo"]).stem
        registro = json.loads((base / f["carpeta"] / f"{stem}.json").read_text(encoding="utf-8"))
        crudos = [p["texto_crudo"] for p in registro["paginas_md"]]
        _, c = cuerpo(crudos, registro.get("referencias"))
        pool = [i for i, w in zip(c["paginas_lista"], c["palabras_por_pagina_lista"]) if w >= PALABRAS_MINIMAS_CUERPO]
        tomadas = sorted(azar.sample(pool, min(paginas, len(pool))))
        if not tomadas:
            saltados.append(f["archivo"])
            print(f"  {f['archivo']}: sin páginas de cuerpo con {PALABRAS_MINIMAS_CUERPO}+ palabras; se reemplaza por el siguiente")
            continue
        carpeta = salida / stem
        carpeta.mkdir(exist_ok=True)
        imagen, leido = carpeta / "_paginas_como_imagen.pdf", carpeta / "_paginas_ocr.pdf"
        with fitz.open(registro["archivo"]["ruta"]) as original, fitz.open() as nuevo:
            for i in tomadas:
                p = original[i - 1]
                pix = p.get_pixmap(dpi=DPI, colorspace=fitz.csGRAY)
                q = nuevo.new_page(width=p.rect.width, height=p.rect.height)
                q.insert_image(q.rect, pixmap=pix)
            nuevo.save(imagen)
        usado = ocr_paginas(imagen, leido, list(range(1, len(tomadas) + 1)), idioma)
        comandos[f["archivo"]] = [Path(usado[0]).name] + usado[1:-2] + ["<entrada>", "<salida>"]
        with fitz.open(leido) as doc:
            textos_ocr = [p.get_text("text") for p in doc]
        for i, ocr in zip(tomadas, textos_ocr):
            nativo = crudos[i - 1]
            (carpeta / f"p{i:04d}_nativo.txt").write_text(nativo, encoding="utf-8")
            (carpeta / f"p{i:04d}_ocr.txt").write_text(ocr, encoding="utf-8")
            resultado.append({"archivo": f["archivo"], "pagina": i, **metricas(nativo, ocr)})
        medidos.append(f["archivo"])
        print(f"  {f['archivo']}: páginas {', '.join(map(str, tomadas))}")

    with open(salida / "_comparacion.csv", "w", newline="", encoding="utf-8-sig") as g:
        w = csv.DictWriter(g, fieldnames=["archivo", "pagina", "palabras_nativo", "palabras_ocr", "errores", "wer", "similitud"])
        w.writeheader()
        w.writerows(resultado)
    wers = sorted(r["wer"] for r in resultado if r["wer"] is not None)
    total = sum(r["palabras_nativo"] for r in resultado)
    resumen = {"semilla": semilla, "pdf_pedidos": n, "pdf_candidatos": len(candidatos), "pdf": len(medidos),
               "pdf_saltados_sin_cuerpo": saltados, "paginas_pedidas_por_pdf": paginas, "paginas": len(resultado),
               "metodo": f"página convertida en imagen a {DPI} ppp en grises y leída con el mismo OCR que el lote",
               "comandos_ocr": comandos, "normalizacion": "NFKC, guion de fin de línea unido, minúsculas, letras y números",
               "wer_global": round(sum(r["errores"] for r in resultado) / total, 4) if total else None,
               "wer_mediana": round(statistics.median(wers), 4) if wers else None,
               "wer_p90": round(wers[int(0.9 * (len(wers) - 1))], 4) if wers else None,
               "wer_maximo": wers[-1] if wers else None, "entorno": entorno_ocr(idioma)}
    md = ["# Comparación forzada de OCR", "",
          f"Se pidieron {n} PDF digitales ({len(candidatos)} candidatos) y {paginas} páginas del cuerpo de cada uno; "
          f"se midieron {resumen['pdf']} PDF y {resumen['paginas']} páginas. Semilla {semilla}.",
          *([f"Reemplazados por no tener páginas de cuerpo con {PALABRAS_MINIMAS_CUERPO}+ palabras: {', '.join(saltados)}."]
            if saltados else []),
          *(["**Se midieron menos PDF de los pedidos: no hubo más candidatos.**"] if len(medidos) < n else []),
          f"Método: {resumen['metodo']}.",
          *[f"Comando ({', '.join(a for a, c in comandos.items() if ' '.join(c) == cmd)}): `{cmd}`"
            for cmd in sorted({' '.join(c) for c in comandos.values()})],
          f"Normalización de los dos textos antes de comparar: {resumen['normalizacion']}.", "",
          "| Medida | Valor |", "|---|---|",
          f"| Tasa de error por palabra, global (errores / palabras nativas) | {resumen['wer_global']} |",
          f"| Mediana por página | {resumen['wer_mediana']} |",
          f"| Percentil 90 por página | {resumen['wer_p90']} |",
          f"| Peor página | {resumen['wer_maximo']} |", "",
          "Una página con tasa alta no es necesariamente un mal OCR: si la página tiene una tabla o una "
          "fórmula, el orden de lectura cambia. Los textos de cada página están al lado para verlo.", "",
          "El detalle por página está en `_comparacion.csv`.", ""]
    (salida / "_comparacion.md").write_text("\n".join(md), encoding="utf-8")
    (salida / "_comparacion.json").write_text(json.dumps({**resumen, "paginas_detalle": resultado},
                                                         ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  tasa de error por palabra: global {resumen['wer_global']}, mediana {resumen['wer_mediana']}")
    return {k: v for k, v in resumen.items() if k != "entorno"}
