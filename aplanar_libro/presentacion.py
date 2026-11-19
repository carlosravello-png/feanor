"""Presentaciones de PowerPoint (.pptx) a Markdown.

Un .pptx no es una imagen: por dentro guarda el texto de cada diapositiva ya
escrito, con sus títulos, viñetas, tablas y notas del orador. Aquí no hay
aplanado ni OCR; se copia ese texto en el orden en que se lee la diapositiva.

Lo que no se lee: el texto que esté dentro de una imagen (una captura, un
esquema pegado como foto) y el contenido de los gráficos. Se anotan para que
quien lea el .md sepa que ahí hay algo que no está en el texto.

Usa python-pptx (licencia MIT, verificada en PyPI el 19/11/2026).
"""
from __future__ import annotations

from pathlib import Path

AVISO = """<!-- AVISO: texto copiado tal cual de la presentación, sin OCR. El texto que esté dentro de
imágenes o gráficos no se lee: cada uno queda anotado en su diapositiva para revisarlo en el original. -->"""


def _python_pptx():
    try:
        from pptx import Presentation
        from pptx.enum.shapes import MSO_SHAPE_TYPE
    except ImportError as e:  # pragma: no cover
        raise SystemExit("Para leer PowerPoint falta python-pptx: python -m pip install python-pptx") from e
    return Presentation, MSO_SHAPE_TYPE


def _caja(forma) -> tuple[int, int, int, int]:
    izq, arriba = forma.left or 0, forma.top or 0
    return izq, arriba, izq + (forma.width or 0), arriba + (forma.height or 0)


def _misma_fila(f, g) -> bool:
    """Dos formas van en la misma fila si comparten buena parte de su altura."""
    _, fa, _, fb = _caja(f)
    _, ga, _, gb = _caja(g)
    comun = min(fb, gb) - max(fa, ga)
    return comun > 0.6 * max(1, min(fb - fa, gb - ga))


def _en_fila(formas: list) -> list:
    """Arriba hacia abajo y, dentro de una misma fila, de izquierda a derecha."""
    filas: list[list] = []
    for f in sorted(formas, key=lambda g: _caja(g)[1]):
        if filas and _misma_fila(filas[-1][0], f):
            filas[-1].append(f)
        else:
            filas.append([f])
    return [f for fila in filas for f in sorted(fila, key=lambda g: _caja(g)[0])]


def _columnas(formas: list, ancho_min: int) -> list[list] | None:
    """Parte en columnas si hay huecos verticales limpios y cada columna es ancha.

    El ancho mínimo evita leer como columna aparte los números o viñetas
    dibujados a la izquierda de cada renglón; pedir anchos parecidos evita
    leer como columnas una lista de «rótulo: valor».
    """
    grupos: list[list] = []
    derecha = None
    for f in sorted(formas, key=lambda g: _caja(g)[0]):
        izq, _, der, _ = _caja(f)
        if derecha is None or izq >= derecha:
            grupos.append([f])
            derecha = der
        else:
            grupos[-1].append(f)
            derecha = max(derecha, der)
    if len(grupos) < 2:
        return None
    anchos = [max(_caja(f)[2] for f in g) - min(_caja(f)[0] for f in g) for g in grupos]
    if min(anchos) < ancho_min or max(anchos) > 2 * min(anchos):
        return None
    return grupos


def _orden_de_lectura(formas: list, ancho: int) -> list:
    """Orden en que se lee una diapositiva.

    Las formas anchas que no tienen nada al lado (título, pie, una franja de
    texto) cortan la diapositiva
    en tramos. Dentro de cada tramo, si las formas forman columnas anchas se
    lee columna por columna; si no, fila por fila.
    """
    formas = sorted(formas, key=lambda f: _caja(f)[1])
    if len(formas) <= 1:
        return formas
    izq = min(_caja(f)[0] for f in formas)
    der = max(_caja(f)[2] for f in formas)
    salida, tramo = [], []

    def bandas(formas_tramo: list) -> list[list]:
        """Franjas horizontales separadas por un hueco que ninguna forma cruza."""
        salida_b: list[list] = []
        fondo = None
        for f in sorted(formas_tramo, key=lambda g: _caja(g)[1]):
            _, arriba, _, abajo = _caja(f)
            if fondo is None or arriba >= fondo:
                salida_b.append([f])
                fondo = abajo
            else:
                salida_b[-1].append(f)
                fondo = max(fondo, abajo)
        return salida_b

    def cerrar() -> None:
        """Dentro del tramo, junta las franjas seguidas que forman columnas
        anchas y las lee columna por columna; el resto, fila por fila."""
        if not tramo:
            return
        fr = bandas(tramo)
        i = 0
        while i < len(fr):
            ultima, cols_ok = None, None
            for j in range(i, len(fr)):
                union = [f for b in fr[i:j + 1] for f in b]
                cols = _columnas(union, int(0.15 * ancho)) if len(union) > 1 else None
                if cols:
                    ultima, cols_ok = j, cols
                elif ultima is not None:
                    break
            if ultima is None:
                salida.extend(_en_fila(fr[i]))
                i += 1
            else:
                for c in cols_ok:
                    salida.extend(_orden_de_lectura(c, ancho))
                i = ultima + 1
        tramo.clear()

    def sola_en_su_altura(f) -> bool:
        return not any(g is not f and _misma_fila(f, g) for g in formas)

    for f in formas:
        a, _, b, _ = _caja(f)
        if (b - a) > 0.5 * (der - izq) and sola_en_su_altura(f):
            cerrar()
            salida.append(f)
        else:
            tramo.append(f)
    cerrar()
    return salida


def _tabla(tabla) -> list[str]:
    filas = [[" ".join(c.text.split()).replace("|", "/") for c in fila.cells] for fila in tabla.rows]
    if not filas:
        return []
    ancho = max(len(f) for f in filas)
    filas = [f + [""] * (ancho - len(f)) for f in filas]
    salida = ["| " + " | ".join(filas[0]) + " |", "|" + " --- |" * ancho]
    salida += ["| " + " | ".join(f) + " |" for f in filas[1:]]
    return salida


def _tiene_texto(forma) -> bool:
    return bool(getattr(forma, "has_text_frame", False) and forma.has_text_frame and forma.text_frame.text.strip())


def _util(forma, tipos) -> bool:
    """Formas que aportan contenido. Los fondos, marcos, líneas y flechas vacíos
    no cuentan para el orden: solo estorbarían al buscar filas y columnas."""
    if forma.shape_type == tipos.GROUP:
        return any(_util(g, tipos) for g in forma.shapes)
    return (_tiene_texto(forma) or (getattr(forma, "has_table", False) and forma.has_table)
            or (getattr(forma, "has_chart", False) and forma.has_chart))


def _imagenes(formas, tipos) -> int:
    n = 0
    for forma in formas:
        if forma.shape_type == tipos.GROUP:
            n += _imagenes(forma.shapes, tipos)
        elif forma.shape_type == tipos.PICTURE:
            n += 1
    return n


def _formas(formas, tipos, cuenta: dict, ancho: int) -> list[list[str]]:
    """Bloques de texto de un grupo de formas, en orden de lectura."""
    bloques: list[list[str]] = []
    for forma in _orden_de_lectura([f for f in formas if _util(f, tipos)], ancho):
        if forma.shape_type == tipos.GROUP:
            bloques += _formas(forma.shapes, tipos, cuenta, ancho)
            continue
        if getattr(forma, "has_table", False) and forma.has_table:
            cuenta["tablas"] += 1
            bloques.append(_tabla(forma.table))
            continue
        if getattr(forma, "has_chart", False) and forma.has_chart:
            cuenta["graficos"] += 1
            bloques.append(["<!-- gráfico: su contenido no se lee; ver la diapositiva original -->"])
            continue
        lineas = []
        for parrafo in forma.text_frame.paragraphs:
            texto = " ".join(parrafo.text.split())
            if texto:
                lineas.append("  " * (parrafo.level or 0) + texto)
        if lineas:
            bloques.append(lineas)
    return _numeros_pegados(bloques)


def _numeros_pegados(bloques: list[list[str]]) -> list[list[str]]:
    """Un número suelto dibujado junto a un renglón («1», «2») se pega a ese renglón."""
    salida: list[list[str]] = []
    i = 0
    while i < len(bloques):
        b = bloques[i]
        if (len(b) == 1 and b[0].strip().isdigit() and len(b[0].strip()) <= 2
                and i + 1 < len(bloques) and not bloques[i + 1][0].startswith(("<!--", "|"))):
            siguiente = list(bloques[i + 1])
            siguiente[0] = f"{b[0].strip()}. {siguiente[0].strip()}"
            salida.append(siguiente)
            i += 2
            continue
        salida.append(b)
        i += 1
    return salida


def pptx_a_markdown(entrada: Path, salida: Path) -> dict:
    """Escribe el .md de la presentación y devuelve un resumen."""
    Presentation, tipos = _python_pptx()
    presentacion = Presentation(str(entrada))
    cuenta = {"diapositivas": 0, "sin_texto": [], "imagenes": 0, "tablas": 0, "graficos": 0, "con_notas": 0}
    partes = [f"<!-- Texto extraído de la presentación: {Path(entrada).name} -->", AVISO, ""]
    for n, diapositiva in enumerate(presentacion.slides, start=1):
        cuenta["diapositivas"] += 1
        titulo_forma = diapositiva.shapes.title
        titulo = " ".join(titulo_forma.text.split()) if titulo_forma is not None and titulo_forma.has_text_frame else ""
        resto = [f for f in diapositiva.shapes if titulo_forma is None or f.shape_id != titulo_forma.shape_id]
        bloques = _formas(resto, tipos, cuenta, presentacion.slide_width or 9144000)
        partes.append(f"## Diapositiva {n}" + (f": {titulo}" if titulo else ""))
        partes.append("")
        tiene_texto = bool(titulo) or any(not l.startswith("<!--") for b in bloques for l in b)
        if not tiene_texto:
            cuenta["sin_texto"].append(n)
            partes += ["<!-- diapositiva sin texto -->", ""]
        for bloque in bloques:
            partes += bloque + [""]
        imagenes = _imagenes(diapositiva.shapes, tipos)
        if imagenes:
            cuenta["imagenes"] += imagenes
            que = ("1 imagen en esta diapositiva: si tiene texto, no se lee" if imagenes == 1 else
                   f"{imagenes} imágenes en esta diapositiva: si tienen texto, no se lee")
            partes += [f"<!-- {que}; ver el original -->", ""]
        if diapositiva.has_notes_slide:
            notas = diapositiva.notes_slide.notes_text_frame.text.strip()
            if notas:
                cuenta["con_notas"] += 1
                partes += ["**Notas del orador:**", "", notas, ""]
    salida.write_text("\n".join(partes), encoding="utf-8")
    return cuenta
