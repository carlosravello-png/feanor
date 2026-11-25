"""¿Dónde empiezan las referencias de una tesis o un libro?

Se busca por el título de la sección, nada más: una línea sola que diga
«Referencias», «Referencias bibliográficas», «Bibliografía», «Fuentes
consultadas», «Literatura citada», «References» o «Bibliography», con o sin
numeración delante («VII.», «6.», «Capítulo 8»). No se interpreta el contenido.

- Se aceptan erratas del autor en el título: «Referencias» seguido de
  cualquier palabra que empiece por «bibliog» («BIBLIOGÁFICAS», sin la r),
  «Bibliog…» con cualquier terminación, y un punto final. La línea se compara
  en NFC (la «Í» puede venir como «I» más tilde combinante). En singular,
  «Referencia bibliográfica» solo cuenta con numeración de capítulo delante:
  sin ella es la página de UNMSM que dice cómo citar la tesis.
- Una página con un 20 % de líneas que son solo un número es índice, pero los
  años 1900–2099 no cuentan: en muchas bibliografías el año va en su línea.
- Las páginas tipo índice no cuentan (ahí el título aparece como entrada): ni
  las que son mayormente números sueltos, ni las que tienen muchas líneas que
  terminan en un número de página («Referencias ........ 45»), ni las que se
  encabezan «Índice», «Esquema», «Contenido», «Tabla de contenido» o «Sumario»
  aunque no tengan números.
- Un título (y un título de anexos) cuenta solo si su palabra empieza con
  mayúscula: una línea de prosa cortada en «referencias bibliográficas» no.
- Si el título aparece varias veces, se toma el último que esté ANTES del
  primer título de anexos que venga en una página posterior a la del primero
  (en la misma página, «Anexos» es la línea siguiente de un índice): un anexo puede traer
  sus propias referencias (en la UCV se anexa un «artículo científico» con las
  suyas) y no son las de la tesis. Si no hay anexos después, el último.
- No se exige que esté en la segunda mitad (un informe con anexos largos las
  tiene antes), pero si empieza antes de la mitad del documento se marca para
  revisar, con el porcentaje.
- Las referencias terminan en el primer título de anexos o apéndices que venga
  después; si no hay, al final del documento.

Lo que no encuentra, lo dice: el resultado es None y el lote lo lista.
"""
from __future__ import annotations

import re
import unicodedata

_NUMERACION = r"(?:(?:[IVXLC]+|\d+(?:\.\d+)*)\s*[.)\-–]?\s*|cap[ií]tulo\s+\w+\s*[.:\-–]?\s*)?"
TITULO = re.compile(
    r"^\s*" + _NUMERACION +
    r"(referencias(?:\s+bibliog\w*)?|bibliog\w*(?:\s+consultada)?|"
    r"fuentes\s+(?:consultadas|de\s+informaci[oó]n|bibliogr[aá]ficas)|literatura\s+citada|"
    r"references|bibliography|works\s+cited)\s*[:.]?\s*$", re.IGNORECASE)
_ENTRADA_DE_INDICE = re.compile(r"(\.{3,}|…|_{3,})\s*\d{1,4}\s*$|\s\d{1,4}\s*$")


_ENCABEZADO_DE_INDICE = re.compile(
    r"^\s*(índice|indice|esquema|contenidos?|tabla\s+de\s+contenidos?|sumario)\b(?:\s+(general|de\s+contenidos?))?\s*:?\s*$",
    re.IGNORECASE)


_NUMERO_SOLO = re.compile(r"^\s*\d{1,4}\s*$")
_ANIO = re.compile(r"^\s*(19|20)\d\d\s*$")


def _indice_por_numeros(texto: str) -> bool:
    """Como markdown.es_indice (un 20 % o más de líneas que son solo un número),
    pero sin contar los años 1900–2099: en muchas bibliografías el año de cada
    referencia va solo en su línea y la página parecía un índice."""
    lineas = [l for l in texto.splitlines() if l.strip()]
    if len(lineas) < 5:
        return False
    numeros = sum(bool(_NUMERO_SOLO.match(l)) and not _ANIO.match(l) for l in lineas)
    return numeros / len(lineas) >= 0.20


def parece_indice(texto: str) -> bool:
    """Página de índice: se encabeza «Índice», «Esquema», «Contenido»… (en sus 4
    primeras líneas), o tiene al menos 5 líneas y un 40 % o más que terminan en
    número de página."""
    lineas = [l for l in texto.splitlines() if l.strip()]
    if any(_ENCABEZADO_DE_INDICE.match(l) for l in lineas[:4]):
        return True
    if len(lineas) < 5:
        return False
    return sum(bool(_ENTRADA_DE_INDICE.search(l)) for l in lineas) / len(lineas) >= 0.4


# «Referencia bibliográfica» en singular solo con numeración de capítulo delante
# («VII. REFERENCIA BIBLIOGRAFICA»): sin ella es la página que UNMSM agrega a cada
# tesis para indicar cómo citarla, con la cita de la propia tesis debajo.
TITULO_SINGULAR = re.compile(r"^\s*(?:[IVXLC]+|\d+(?:\.\d+)*)\s*[.)\-–]?\s*(referencia\s+bibliog\w*)\s*[:.]?\s*$",
                             re.IGNORECASE)
FIN = re.compile(r"^\s*" + _NUMERACION + r"(anexos?|ap[eé]ndices?|annex(?:es)?|appendix|appendices)\b.{0,40}$",
                 re.IGNORECASE)


def _es_titulo(linea: str, patron: re.Pattern) -> bool:
    """Coincide con el patrón y la palabra empieza con mayúscula: una línea de
    prosa que se corta justo en «referencias bibliográficas» va en minúscula."""
    m = patron.match(linea)
    return bool(m) and m.group(1)[:1].isupper()


def buscar_referencias(textos: list[str], indices: list[int] | None = None) -> dict | None:
    """`textos`: el texto de cada página (la 1 es el elemento 0). `indices`: los
    números de página tipo índice. Devuelve dónde empieza y termina la sección,
    o None si no hay título."""
    saltar = set(indices or [])
    candidatos = []
    for i, texto in enumerate(textos, start=1):
        if (i in saltar and _indice_por_numeros(texto)) or parece_indice(texto):
            continue
        for j, linea in enumerate(texto.splitlines()):
            normal = unicodedata.normalize("NFC", linea)
            if _es_titulo(normal, TITULO) or _es_titulo(normal, TITULO_SINGULAR):
                candidatos.append((i, j, linea.strip()))
    if not candidatos:
        return None
    # Primer título de anexos (fuera de los índices) después del primer candidato.
    primero = candidatos[0][:2]
    anexo = None
    for i, texto in enumerate(textos, start=1):
        if i < primero[0] or (i in saltar and _indice_por_numeros(texto)) or parece_indice(texto):
            continue
        if i == primero[0]:
            continue        # en la misma página que el primer título: es un índice, no la sección
        for j, l in enumerate(texto.splitlines()):
            if _es_titulo(unicodedata.normalize("NFC", l), FIN):
                anexo = (i, j)
                break
        if anexo:
            break
    antes = [c for c in candidatos if anexo is None or c[:2] < anexo]
    pagina, linea, titulo = antes[-1]
    fin_pagina, fin_linea, fin_titulo = None, None, None
    for i in range(pagina, len(textos) + 1):
        lineas = textos[i - 1].splitlines()
        for j, l in enumerate(lineas):
            if (i, j) <= (pagina, linea):
                continue
            if _es_titulo(unicodedata.normalize("NFC", l), FIN):
                fin_pagina, fin_linea, fin_titulo = i, j, l.strip()
                break
        if fin_pagina:
            break
    inicio = round((pagina - 1) / len(textos), 3)
    return {"metodo": "título de sección", "titulo": titulo, "pagina": pagina, "linea": linea,
            "candidatos": len(candidatos), "inicio_fraccion": inicio,
            "regla": ("último título antes del primer anexo" if anexo and len(antes) < len(candidatos)
                      else "último título"),
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
