"""Paso 3: pasar el PDF con texto a Markdown, página por página.

Cada página va precedida de una marca con el número del VISOR, que no es el
folio impreso del libro: para citar, el folio se lee en la imagen.
Las páginas marcadas en el paso 1 llevan un aviso para revisarlas a mano.

El texto del cuerpo pasa por una limpieza que no toca el OCR (ver `limpiar`).
Las páginas tipo índice no se limpian: se dejan como las leyó el OCR y se
marcan siempre para revisión, porque ahí los números sueltos son datos.
"""
from __future__ import annotations

import re
from pathlib import Path

import pymupdf as fitz  # PyMuPDF

LETRA = "A-Za-zÁÉÍÓÚÜÑáéíóúüñ"
# Folio mal leído en el encabezado o el pie: 1 a 4 caracteres que parecen
# dígitos (18 → «1S», 19 → «O», 21 → «31»).
_FOLIO = re.compile(r"^[0-9OoSlI|]{1,4}$")
_NUMERO = re.compile(r"^\d{1,4}$")
_CORTE = re.compile(f"([{LETRA}]+)\\s?-$")          # palabra cortada al final de línea
UMBRAL_INDICE = 0.20     # fracción de líneas que son solo un número
LARGA = 40               # una línea «larga» del cuerpo del texto


def es_indice(texto: str) -> bool:
    """¿La página parece un índice? Muchas líneas que son solo un número."""
    lineas = [l.strip() for l in texto.splitlines() if l.strip()]
    if len(lineas) < 5:
        return False
    return sum(bool(_NUMERO.match(l)) for l in lineas) / len(lineas) >= UMBRAL_INDICE


def _sin_ruido(lineas: list[str]) -> list[str]:
    """Quita las líneas que son sombra del lomo leída como texto.

    a) 1 o 2 caracteres sin letras ni dígitos («|», «—», «¡»): siempre.
    b) 1 o 2 caracteres cualesquiera («n», «f», «1») cuando las líneas vecinas
       de más de 2 caracteres son largas: en el cuerpo del texto una línea así
       es ruido. En un índice las vecinas son cortas y no se toca.
    """
    lineas = [l for l in lineas if l.strip()]
    salida = []
    for i, l in enumerate(lineas):
        t = l.strip()
        if len(t) <= 2:
            if not re.search(f"[{LETRA}0-9]", t):
                continue
            arriba = next((x for x in reversed(lineas[:i]) if len(x.strip()) > 2), "")
            abajo = next((x for x in lineas[i + 1:] if len(x.strip()) > 2), "")
            if len(arriba.strip()) > LARGA and len(abajo.strip()) > LARGA:
                continue
        salida.append(l)
    return salida


def _sin_folio(lineas: list[str]) -> list[str]:
    """Quita el folio del encabezado (dos primeras líneas) y del pie (última)."""
    quitar = {i for i in (0, 1, len(lineas) - 1)
              if 0 <= i < len(lineas) and _FOLIO.match(lineas[i].strip())}
    return [l for i, l in enumerate(lineas) if i not in quitar]


def _unir_guiones(lineas: list[str], documento: str) -> list[str]:
    """Une las palabras cortadas con guion al final de la línea.

    La decisión se toma con el propio documento, no con un diccionario:
    - si la forma con guion aparece a mitad de línea en el documento
      («Dor-lómin»), es un nombre compuesto y el guion se conserva;
    - en cualquier otro caso se une («Si-» + «rion» → «Sirion»,
      «anterior-» + «mente» → «anteriormente»).
    """
    salida: list[str] = []
    for l in lineas:
        if salida:
            m = _CORTE.search(salida[-1])
            sig = l.lstrip()
            m2 = re.match(f"[{LETRA}]+", sig)
            if m and m2 and sig[0].islower():
                a, b = m.group(1), m2.group(0)
                compuesto = re.search(f"(?<![{LETRA}]){re.escape(a)}-{re.escape(b)}(?![{LETRA}])",
                                      documento, re.IGNORECASE)
                union = f"{a}-{b}" if compuesto else a + b
                primera = sig.split()[0]
                salida[-1] = salida[-1][:m.start()] + union + primera[len(b):]
                resto = sig[len(primera):].lstrip()
                if resto:
                    salida.append(resto)
                continue
        salida.append(l)
    return salida


def limpiar(texto: str, documento: str | None = None) -> str:
    """Limpieza del texto de una página del cuerpo, sin tocar el OCR.

    1. Quita la sombra del lomo leída como texto (ver `_sin_ruido`).
    2. Quita el folio del encabezado o del pie, que suele salir mal leído.
       El folio verdadero se lee en la imagen.
    3. Une las palabras cortadas con guion al final de la línea.

    `documento` es el texto de todas las páginas; se usa para decidir si un
    guion pertenece a un nombre compuesto. Si no se pasa, se usa la página.
    """
    lineas = [l.rstrip() for l in texto.splitlines()]
    lineas = _sin_ruido(lineas)
    lineas = _sin_folio(lineas)
    lineas = _unir_guiones(lineas, documento if documento is not None else texto)
    return "\n".join(lineas)


def pdf_a_markdown(entrada: Path, salida: Path, resultados: list[dict] | None = None,
                   limpieza: bool = True) -> dict:
    """Escribe el texto de `entrada` en `salida` (.md). Devuelve un resumen."""
    avisos: dict[int, str] = {}
    for r in resultados or []:
        if r.get("revisar"):
            avisos[r["pagina"]] = r.get("motivo_revision") or r["motivo"]
        elif "revisar" not in r and not r["aplanada"] and r["motivo"] not in ("no pedida", "aplanada"):
            avisos[r["pagina"]] = r["motivo"]          # informes de la versión 0.1.0

    doc = fitz.open(entrada)
    textos = [pagina.get_text("text").strip() for pagina in doc]
    documento = "\n".join(textos)
    partes = [
        f"<!-- Texto extraído por OCR de: {Path(entrada).name} -->",
        "<!-- El OCR sirve para leer y buscar. Cifras, nombres y citas se verifican en la imagen. -->",
        "",
    ]
    vacias, indices = 0, []
    for i, texto in enumerate(textos, start=1):
        if es_indice(texto):
            indices.append(i)
            aviso = "página tipo índice: sin limpieza; los números se verifican en la imagen"
            avisos[i] = f"{aviso}; {avisos[i]}" if i in avisos else aviso
        elif limpieza:
            texto = limpiar(texto, documento)
        if not texto:
            vacias += 1
        partes.append(f"<!-- página {i} del visor -->")
        if i in avisos:
            partes.append(f"<!-- REVISAR A MANO: {avisos[i]} -->")
        partes.append("")
        partes.append(texto)
        partes.append("")
    Path(salida).write_text("\n".join(partes), encoding="utf-8")
    return {"paginas": len(doc), "sin_texto": vacias, "indices": indices,
            "a_revisar": sorted(avisos)}
