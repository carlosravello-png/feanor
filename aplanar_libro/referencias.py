"""¿Dónde empiezan las referencias de una tesis o un libro?

Se busca por el título de la sección, nada más: una línea sola que diga
«Referencias», «Referencias bibliográficas», «Bibliografía», «Fuentes
consultadas», «Literatura citada», «References» o «Bibliography», con o sin
numeración delante («VII.», «6.», «Capítulo 8»). No se interpreta el contenido.

- Las páginas tipo índice no cuentan (ahí el título aparece como entrada): ni
  las que son mayormente números sueltos ni las que tienen muchas líneas que
  terminan en un número de página («Referencias ........ 45»).
- Si el título aparece varias veces, se toma la última: el índice va al
  principio y la sección, al final.
- No se exige que esté en la segunda mitad (un informe con anexos largos las
  tiene antes), pero si empieza antes de la mitad del documento se marca para
  revisar, con el porcentaje.
- Las referencias terminan en el primer título de anexos o apéndices que venga
  después; si no hay, al final del documento.

Lo que no encuentra, lo dice: el resultado es None y el lote lo lista.
"""
from __future__ import annotations

import re

_NUMERACION = r"(?:(?:[IVXLC]+|\d+(?:\.\d+)*)\s*[.)\-–]?\s*|cap[ií]tulo\s+\w+\s*[.:\-–]?\s*)?"
TITULO = re.compile(
    r"^\s*" + _NUMERACION +
    r"(referencias(?:\s+bibliogr[aá]ficas)?|bibliograf[ií]a(?:\s+consultada)?|"
    r"fuentes\s+(?:consultadas|de\s+informaci[oó]n|bibliogr[aá]ficas)|literatura\s+citada|"
    r"references|bibliography|works\s+cited)\s*:?\s*$", re.IGNORECASE)
_ENTRADA_DE_INDICE = re.compile(r"(\.{3,}|…|_{3,})\s*\d{1,4}\s*$|\s\d{1,4}\s*$")


def parece_indice(texto: str) -> bool:
    """Página de índice: al menos 5 líneas y un 40 % o más que terminan en número de página."""
    lineas = [l for l in texto.splitlines() if l.strip()]
    if len(lineas) < 5:
        return False
    return sum(bool(_ENTRADA_DE_INDICE.search(l)) for l in lineas) / len(lineas) >= 0.4


FIN = re.compile(r"^\s*" + _NUMERACION + r"(anexos?|ap[eé]ndices?|annex(?:es)?|appendix|appendices)\b.{0,40}$",
                 re.IGNORECASE)


def buscar_referencias(textos: list[str], indices: list[int] | None = None) -> dict | None:
    """`textos`: el texto de cada página (la 1 es el elemento 0). `indices`: los
    números de página tipo índice. Devuelve dónde empieza y termina la sección,
    o None si no hay título."""
    saltar = set(indices or [])
    candidatos = []
    for i, texto in enumerate(textos, start=1):
        if i in saltar or parece_indice(texto):
            continue
        for j, linea in enumerate(texto.splitlines()):
            if TITULO.match(linea):
                candidatos.append((i, j, linea.strip()))
    if not candidatos:
        return None
    pagina, linea, titulo = candidatos[-1]
    fin_pagina, fin_linea, fin_titulo = None, None, None
    for i in range(pagina, len(textos) + 1):
        lineas = textos[i - 1].splitlines()
        for j, l in enumerate(lineas):
            if (i, j) <= (pagina, linea):
                continue
            if FIN.match(l):
                fin_pagina, fin_linea, fin_titulo = i, j, l.strip()
                break
        if fin_pagina:
            break
    inicio = round((pagina - 1) / len(textos), 3)
    return {"metodo": "título de sección", "titulo": titulo, "pagina": pagina, "linea": linea,
            "candidatos": len(candidatos), "inicio_fraccion": inicio,
            "revisar": (f"empieza antes de la mitad del documento ({inicio:.0%})" if inicio < 0.5 else None),
            "termina_antes_de": ({"pagina": fin_pagina, "linea": fin_linea, "titulo": fin_titulo}
                                 if fin_pagina else None)}


def texto_de_referencias(textos: list[str], ref: dict) -> list[tuple[int, str]]:
    """El texto de la sección, página por página: [(página, texto), …]."""
    fin = ref["termina_antes_de"]
    ultima = fin["pagina"] if fin else len(textos)
    salida = []
    for i in range(ref["pagina"], ultima + 1):
        lineas = textos[i - 1].splitlines()
        desde = ref["linea"] if i == ref["pagina"] else 0
        hasta = fin["linea"] if fin and i == fin["pagina"] else len(lineas)
        trozo = "\n".join(lineas[desde:hasta]).strip()
        if trozo:
            salida.append((i, trozo))
    return salida
