"""El cuerpo de una tesis, para contar palabras (análisis léxico).

Se arma solo en el modo lote con --cuerpo, en un archivo aparte
(<nombre>_cuerpo.md); el .md de siempre no cambia. Lo que se deja fuera:

- las referencias y todo lo que viene después (anexos), desde el título de la
  sección (ver referencias.py);
- las páginas tipo índice;
- los encabezados y pies de página repetidos: una línea de las 3 primeras o
  las 3 últimas de la página que, normalizada (minúsculas, sin números ni
  signos), aparece en el margen de más de la mitad de las páginas con texto. Así
  «Universidad …» o el título de la tesis arriba de cada página no se cuentan
  150 veces. Solo se quita en el margen: la misma frase dentro del texto queda.

Al texto que queda se le aplica la limpieza de siempre (ver markdown.limpiar).
Lo que se quitó se cuenta y va al resumen.
"""
from __future__ import annotations

import re

from .markdown import compuestos_del_documento, es_indice, limpiar
from .referencias import parece_indice

MARGEN = 3              # líneas de arriba y de abajo que se miran
REPETIDA = 0.5          # fracción de páginas con texto en la que debe repetirse
PALABRAS_POR_PAGINA_MINIMAS = 100   # por debajo, la tesis se marca para revisar


def _normal(linea: str) -> str:
    t = re.sub(r"[^a-záéíóúüñ ]", " ", linea.lower())
    return " ".join(t.split())


def margenes_repetidos(textos: list[str]) -> set[str]:
    con_texto = [t for t in textos if t.strip()]
    cuenta: dict[str, int] = {}
    for t in con_texto:
        lineas = [l for l in t.splitlines() if l.strip()]
        vistas = {_normal(l) for l in lineas[:MARGEN] + lineas[-MARGEN:]}
        for n in vistas:
            if len(n) >= 3:
                cuenta[n] = cuenta.get(n, 0) + 1
    return {n for n, c in cuenta.items() if c > REPETIDA * len(con_texto)}


def cuerpo(textos: list[str], ref: dict | None) -> tuple[str, dict]:
    """`textos`: el texto crudo de cada página. Devuelve el cuerpo y su resumen."""
    hasta = ref["pagina"] if ref else len(textos)
    repetidas = margenes_repetidos(textos)
    paginas, quitadas, indices = [], 0, 0
    for i in range(1, hasta + 1):
        texto = textos[i - 1]
        if ref and i == ref["pagina"]:
            texto = "\n".join(texto.splitlines()[:ref["linea"]])
        if es_indice(texto) or parece_indice(texto):
            indices += 1
            continue
        lineas = [l for l in texto.splitlines() if l.strip()]
        n = len(lineas)
        quedan = []
        for k, l in enumerate(lineas):
            if (k < MARGEN or k >= n - MARGEN) and _normal(l) in repetidas:
                quitadas += 1
                continue
            quedan.append(l)
        if quedan:
            paginas.append((i, "\n".join(quedan)))
    compuestos = compuestos_del_documento("\n".join(t for _, t in paginas))
    limpias = [(i, limpiar(t, compuestos)) for i, t in paginas]
    palabras = sum(len(t.split()) for _, t in limpias)
    resumen = {"paginas": len(limpias), "palabras": palabras,
               "palabras_por_pagina": round(palabras / len(limpias), 1) if limpias else 0.0,
               "paginas_indice_fuera": indices, "lineas_de_margen_quitadas": quitadas,
               "margenes_repetidos": sorted(repetidas), "hasta_pagina": hasta,
               "corta_en_referencias": bool(ref)}
    texto = "\n\n".join(f"<!-- página {i} del visor -->\n\n{t}" for i, t in limpias)
    return texto, resumen
