"""Presentaciones de PowerPoint (.pptx) a Markdown.

Un .pptx no es una imagen: por dentro guarda el texto de cada diapositiva ya
escrito, con sus títulos, viñetas, tablas y notas del orador. Aquí no hay
aplanado ni OCR; se copia ese texto en el orden en que se lee la diapositiva.

Las imágenes: si una imagen trae texto (una lámina armada como foto, un
esquema), se lee con OCR (Tesseract) y ese texto va entre marcas propias,
aparte del texto copiado, porque puede tener errores. Las fotos y logos sin
texto legible quedan solo anotados. El contenido de los gráficos no se lee.

Usa python-pptx (licencia MIT, verificada en PyPI el 19/11/2026).
"""
from __future__ import annotations

import io
import subprocess
import tempfile
from pathlib import Path

AVISO = """<!-- AVISO: el texto de las diapositivas está copiado tal cual de la presentación, sin OCR. El texto
leído dentro de imágenes sí sale de OCR: va entre marcas «texto leído con OCR» y puede tener errores;
se verifica en el original. Las imágenes sin texto legible y los gráficos solo quedan anotados. -->"""

# Una imagen que ocupa menos que esto de la diapositiva es un logo o un ícono: no se lee.
AREA_MINIMA_OCR = 0.03
# Un renglón leído por OCR con confianza media menor que esto se descarta, igual
# que uno sin letras ni cifras. Los demás se conservan: si no tienen ninguna
# palabra con forma de palabra
# (ver _parece_palabra), van marcados con «[?]» en vez de borrarse, para no
# perder en silencio un número o un rótulo corto.
CONFIANZA_MINIMA = 50
DUDOSO = "[?] "
# Una imagen cuenta como «con texto» si de ella salen al menos estas palabras con forma de palabra.
PALABRAS_MINIMAS = 6


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


def _imagenes(formas, tipos) -> list:
    """Todas las imágenes de la diapositiva, también las que están dentro de grupos."""
    salida = []
    for forma in formas:
        if forma.shape_type == tipos.GROUP:
            salida += _imagenes(forma.shapes, tipos)
        elif forma.shape_type == tipos.PICTURE:
            salida.append(forma)
    return salida


class _Renglon:
    """Un renglón leído por OCR, con su caja, para ordenarlo como una forma más."""

    def __init__(self, izq: int, arriba: int, ancho: int, alto: int, texto: str, confianza: float):
        self.left, self.top, self.width, self.height = izq, arriba, ancho, alto
        self.texto, self.suma, self.n = texto, confianza, 1

    def sumar(self, otro: "_Renglon") -> None:
        derecha = max(self.left + self.width, otro.left + otro.width)
        abajo = max(self.top + self.height, otro.top + otro.height)
        self.top = min(self.top, otro.top)
        self.width, self.height = derecha - self.left, abajo - self.top
        self.texto += " " + otro.texto
        self.suma += otro.suma
        self.n += 1

    @property
    def confianza(self) -> float:
        return self.suma / self.n


_VOCALES = set("aeiouáéíóúüAEIOUÁÉÍÓÚÜ")


def _parece_palabra(w: str) -> bool:
    """Forma de palabra, sin diccionario (sirve igual en español o en inglés):
    solo letras (con signos solo en los bordes), al menos tres, alguna vocal, y
    mayúsculas coherentes: todo en minúscula, todo en mayúscula o solo la
    inicial. Así no pasan «Cpg?» (sin vocal), «%00s» (cifras dentro) ni
    «SUPoOSICION» (mayúsculas mezcladas)."""
    w = w.strip(".,;:!?¡¿()[]{}\"'«»“”‘’-–—/")
    if len(w) < 3 or not w.isalpha() or not (_VOCALES & set(w)):
        return False
    return w.islower() or w.isupper() or (w[0].isupper() and w[1:].islower())


def _texto_de_imagen(blob: bytes, idioma: str, exe: str) -> list[str] | None:
    """Lee con OCR el texto de una imagen y lo devuelve en orden de lectura.

    None si la imagen no se puede abrir (por ejemplo, un dibujo vectorial).
    Tesseract en modo «texto disperso» (psm 11), porque en una lámina el texto
    va en recuadros sueltos; los renglones se ordenan después con la misma
    regla de columnas que las diapositivas.
    """
    try:
        from PIL import Image
        imagen = Image.open(io.BytesIO(blob)).convert("L")
    except Exception:
        return None
    if max(imagen.size) < 2000:                      # letra chica: se lee mejor al doble
        imagen = imagen.resize((imagen.width * 2, imagen.height * 2), Image.LANCZOS)
    with tempfile.TemporaryDirectory() as tmp:
        png = Path(tmp) / "imagen.png"
        imagen.save(png)
        r = subprocess.run([exe, str(png), "-", "-l", idioma, "--psm", "11", "tsv"],
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
    palabras = []
    for fila in r.stdout.splitlines()[1:]:
        c = fila.split("\t")
        if len(c) == 12 and c[11].strip():
            try:
                palabras.append(_Renglon(int(c[6]), int(c[7]), int(c[8]), int(c[9]),
                                         c[11].strip(), float(c[10])))
            except ValueError:
                continue
    renglones: list[_Renglon] = []
    for p in sorted(palabras, key=lambda w: w.left):
        for r_ in renglones:
            comun = min(r_.top + r_.height, p.top + p.height) - max(r_.top, p.top)
            hueco = p.left - (r_.left + r_.width)
            if comun > 0.5 * min(r_.height, p.height) and 0 <= hueco < 0.7 * max(r_.height, p.height):
                r_.sumar(p)
                break
        else:
            renglones.append(p)
    # Se borran solo los renglones que no tienen ni letras ni cifras (signos sueltos,
    # restos de flechas): los que tienen algo de eso se conservan, marcados si dudan.
    buenos = [r_ for r_ in renglones if r_.confianza >= CONFIANZA_MINIMA
              and any(ch.isalnum() for ch in r_.texto)]
    claras = sum(_parece_palabra(w) for r_ in buenos for w in r_.texto.split())
    if claras < PALABRAS_MINIMAS:                    # foto o logo: no hay texto que leer
        return []
    return [r_.texto if any(_parece_palabra(w) for w in r_.texto.split()) else DUDOSO + r_.texto
            for r_ in _orden_de_lectura(buenos, imagen.width)]


def _bloques_de_imagenes(imagenes: list, area_diapositiva: int, idioma: str,
                         exe: str | None, cuenta: dict) -> list[str]:
    partes: list[str] = []
    sin_texto = 0
    for k, forma in enumerate(sorted(imagenes, key=lambda f: _caja(f)[:2][::-1]), start=1):
        area = (forma.width or 0) * (forma.height or 0) / max(1, area_diapositiva)
        lineas = None
        if exe and area >= AREA_MINIMA_OCR:
            try:
                lineas = _texto_de_imagen(forma.image.blob, idioma, exe)
            except Exception:
                lineas = None
        if lineas:
            cuenta["imagenes_leidas"] += 1
            partes += [f"<!-- imagen {k}: texto leído con OCR, puede tener errores; verificar en el original -->",
                       "", *lineas, "", f"<!-- fin del texto leído en la imagen {k} -->", ""]
        else:
            sin_texto += 1
    if sin_texto:
        que = ("1 imagen sin texto legible" if sin_texto == 1 else f"{sin_texto} imágenes sin texto legible")
        if not exe:
            que += " (no se encontró Tesseract: no se intentó leerlas)"
        partes += [f"<!-- {que} en esta diapositiva; ver el original -->", ""]
    return partes


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


def pptx_a_markdown(entrada: Path, salida: Path, idioma: str = "spa", ocr_imagenes: bool = True) -> dict:
    """Escribe el .md de la presentación y devuelve un resumen."""
    from .entorno import ruta_tesseract
    Presentation, tipos = _python_pptx()
    presentacion = Presentation(str(entrada))
    exe = ruta_tesseract() if ocr_imagenes else None
    area = (presentacion.slide_width or 9144000) * (presentacion.slide_height or 6858000)
    cuenta = {"diapositivas": 0, "sin_texto": [], "imagenes": 0, "imagenes_leidas": 0,
              "tablas": 0, "graficos": 0, "con_notas": 0, "ocr": bool(exe)}
    partes = [f"<!-- Texto extraído de la presentación: {Path(entrada).name} -->", AVISO, ""]
    for n, diapositiva in enumerate(presentacion.slides, start=1):
        cuenta["diapositivas"] += 1
        titulo_forma = diapositiva.shapes.title
        titulo = " ".join(titulo_forma.text.split()) if titulo_forma is not None and titulo_forma.has_text_frame else ""
        resto = [f for f in diapositiva.shapes if titulo_forma is None or f.shape_id != titulo_forma.shape_id]
        bloques = _formas(resto, tipos, cuenta, presentacion.slide_width or 9144000)
        partes.append(f"## Diapositiva {n}" + (f": {titulo}" if titulo else ""))
        partes.append("")
        for bloque in bloques:
            partes += bloque + [""]
        imagenes = _imagenes(diapositiva.shapes, tipos)
        cuenta["imagenes"] += len(imagenes)
        leidas_antes = cuenta["imagenes_leidas"]
        if imagenes:
            partes += _bloques_de_imagenes(imagenes, area, idioma, exe, cuenta)
        tiene_texto = (bool(titulo) or any(not l.startswith("<!--") for b in bloques for l in b)
                       or cuenta["imagenes_leidas"] > leidas_antes)
        if not tiene_texto:
            cuenta["sin_texto"].append(n)
            partes += ["<!-- diapositiva sin texto -->", ""]
        if diapositiva.has_notes_slide:
            notas = diapositiva.notes_slide.notes_text_frame.text.strip()
            if notas:
                cuenta["con_notas"] += 1
                partes += ["**Notas del orador:**", "", notas, ""]
    salida.write_text("\n".join(partes), encoding="utf-8")
    return cuenta
