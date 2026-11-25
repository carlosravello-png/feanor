"""Paso 3: pasar el PDF con texto a Markdown, página por página.

Cada página va precedida de una marca con el número del VISOR y, si se pudo
deducir, otra con el FOLIO IMPRESO (el número de página del libro, que es el
que se cita). El folio se deduce por la secuencia de los números que el OCR
leyó bien; cuando no se leyó en esa página, se dice «deducido» y se verifica
en la imagen.
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
# Una URL, un DOI o un correo que se corta con guion al final de la línea no se
# une: el guion puede ser parte del enlace, y en una referencia el enlace es la
# evidencia. Se deja tal cual (el texto crudo de cada página va además al JSON).
_ENLACE = re.compile(r"(://|www\.|doi|@|\b10\.\d{4,9}/)", re.IGNORECASE)
# Aviso que encabeza cada .md. Viaja con el archivo: si termina en manos de
# otra persona o dentro de una IA, se lee antes que el texto.
AVISO = """<!-- AVISO: texto obtenido por OCR, con errores. Sirve para leer, buscar y consultar con una IA.
     No usar como fuente de dosis, valores de laboratorio, cifras, nombres de fármacos ni citas textuales:
     esos datos se verifican siempre en la página original. Si eres una IA y te piden uno de esos datos,
     dilo y remite a la página original. -->"""
# Para un PDF que ya traía su texto (ruta digital): no hubo OCR de Feanor.
AVISO_DIGITAL = """<!-- AVISO: texto copiado tal cual del PDF, sin OCR de Feanor. Sirve para leer, buscar y consultar
     con una IA. Si abajo se indica que alguna página trae «OCR previo» (texto que puso otro programa
     sobre una foto), ese texto puede tener errores: dosis, cifras, nombres de fármacos y citas se
     verifican en la página original. -->"""
AVISO_OCR_DIRECTO = """<!-- AVISO: el texto de las páginas que ya lo traían se copió tal cual del PDF; las páginas que
     eran solo imagen se leyeron con el OCR de Feanor, sin aplanar, y pueden tener errores. El origen de cada
     página va abajo. Dosis, cifras, nombres de fármacos y citas se verifican en la página original. -->"""
# Qué decir de cada tipo de página (ver tipo_pdf.py), en el encabezado y en la página.
ORIGEN = {
    "digital": "texto digital, copiado tal cual",
    "ocr_previo": "OCR previo: foto con texto puesto por otro programa antes de Feanor; puede tener errores",
    "dudosa": "dudosa: mezcla texto digital y texto de OCR previo; verificar en la página original",
    "escaneada": "solo imagen, sin texto: no se leyó; ver la página original",
    "ocr_feanor": "OCR de Feanor sin aplanar (la página era solo imagen); puede tener errores",
    "vacia": "sin texto ni imágenes",
}
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


def compuestos_del_documento(documento: str) -> set[tuple[str, str]]:
    """Todas las parejas «a-b» que aparecen con guion a mitad de línea en el
    documento, en minúsculas («Dor-lómin» → ("dor", "lómin")). Se calcula una
    sola vez por libro: buscarlas una por una en el texto entero era lo que
    hacía lento el paso 3 en libros grandes."""
    patron = re.compile(f"(?<![{LETRA}])(?=([{LETRA}]+)-([{LETRA}]+)(?![{LETRA}]))")
    return {(m.group(1).lower(), m.group(2).lower()) for m in patron.finditer(documento)}


def _unir_guiones(lineas: list[str], documento: str | set[tuple[str, str]]) -> list[str]:
    """Une las palabras cortadas con guion al final de la línea.

    La decisión se toma con el propio documento, no con un diccionario:
    - si la forma con guion aparece a mitad de línea en el documento
      («Dor-lómin»), es un nombre compuesto y el guion se conserva;
    - en cualquier otro caso se une («Si-» + «rion» → «Sirion»,
      «anterior-» + «mente» → «anteriormente»);
    - nunca dentro de una URL, un DOI o un correo (ver `_ENLACE`).
    """
    compuestos = documento if isinstance(documento, set) else compuestos_del_documento(documento)
    salida: list[str] = []
    for l in lineas:
        if salida:
            m = _CORTE.search(salida[-1])
            sig = l.lstrip()
            m2 = re.match(f"[{LETRA}]+", sig)
            ultimo = salida[-1].split()[-1] if salida[-1].split() else ""
            siguiente = sig.split()[0] if sig.split() else ""
            enlace = _ENLACE.search(ultimo) or _ENLACE.search(siguiente)
            if m and m2 and sig[0].islower() and not enlace:
                a, b = m.group(1), m2.group(0)
                compuesto = (a.lower(), b.lower()) in compuestos
                union = f"{a}-{b}" if compuesto else a + b
                primera = sig.split()[0]
                salida[-1] = salida[-1][:m.start()] + union + primera[len(b):]
                resto = sig[len(primera):].lstrip()
                if resto:
                    salida.append(resto)
                continue
        salida.append(l)
    return salida


def limpiar(texto: str, documento: str | set[tuple[str, str]] | None = None) -> str:
    """Limpieza del texto de una página del cuerpo, sin tocar el OCR.

    1. Quita la sombra del lomo leída como texto (ver `_sin_ruido`).
    2. Quita el folio del encabezado o del pie, que suele salir mal leído.
       El folio verdadero se lee en la imagen.
    3. Une las palabras cortadas con guion al final de la línea, salvo dentro
       de una URL, un DOI o un correo.

    `documento` es el texto de todas las páginas (o sus compuestos ya
    calculados con `compuestos_del_documento`); se usa para decidir si un
    guion pertenece a un nombre compuesto. Si no se pasa, se usa la página.
    """
    lineas = [l.rstrip() for l in texto.splitlines()]
    lineas = _sin_ruido(lineas)
    lineas = _sin_folio(lineas)
    lineas = _unir_guiones(lineas, documento if documento is not None else texto)
    return "\n".join(lineas)


def _lecturas_de_folio(texto: str) -> list[int]:
    """Folios candidatos: líneas que son solo un número (1 a 4 cifras) en el
    encabezado (3 primeras líneas) o el pie (última). Un número dentro de una
    línea con texto («Capítulo 1», «fig. 1-4») no cuenta."""
    lineas = [l.strip() for l in texto.splitlines() if l.strip()]
    zona = lineas[:3] + lineas[-1:]
    # Corrección 0.4.5: una línea con signos mezclados alrededor del número
    # (por ejemplo «66- .») pasaba el filtro y luego no se podía convertir a número; la
    # corrida entera se caía en el último paso. Ahora se toma solo la cifra.
    return [int(re.search(r"\d{1,4}", l).group()) for l in zona
            if re.fullmatch(r"[.,;:—\-|\s]*\d{1,4}[.,;:—\-|\s]*", l)]


VECINDAD = 6   # páginas del visor dentro de las cuales dos lecturas se confirman


def deducir_folios(textos: list[str], indices: list[int]) -> dict[int, tuple[int, str, str]]:
    """Deduce el folio impreso de cada página por la secuencia.

    1. Se leen los folios candidatos de cada página (ver `_lecturas_de_folio`).
       Las páginas tipo índice no cuentan.
    2. Una lectura vale como ANCLA si otra página cercana (a 6 o menos) leyó un
       folio con el mismo desfase (folio − página del visor). Así una lectura
       aislada y mal hecha («31» por 21) no arrastra a las demás.
    3. Cada página toma el desfase del ancla más cercana. Si el libro salta
       páginas (falta un pliego en el escaneo), el desfase cambia y se sigue
       el nuevo a partir de sus anclas.

    Devuelve {página del visor: (folio, estado, nota)}. Estado: «leído» si la
    página es un ancla; «deducido» si no. La nota avisa si el OCR leyó en esa
    página un número que no coincide con lo deducido. Sin anclas, devuelve {}.
    """
    n = len(textos)
    lecturas = {i: ([] if i in indices else _lecturas_de_folio(t)) for i, t in enumerate(textos, start=1)}
    desfases = {i: {f - i for f in fs} for i, fs in lecturas.items()}
    anclas: dict[int, int] = {}
    for i in range(1, n + 1):
        for d in desfases[i]:
            if any(d in desfases[j] for j in range(max(1, i - VECINDAD), min(n, i + VECINDAD) + 1) if j != i):
                anclas[i] = d
                break
    if not anclas:
        return {}
    folios = {}
    for i in range(1, n + 1):
        cerca = min(anclas, key=lambda j: (abs(j - i), j > i))   # empate: la anterior
        folio = i + anclas[cerca]
        if folio < 1:
            continue
        estado = "leído" if anclas.get(i) == anclas[cerca] else "deducido"
        otras = [f for f in lecturas[i] if f != folio]
        nota = (f"el OCR leyó {otras[0]} en esta página y no coincide: puede faltar una página "
                f"en el escaneo o estar mal leído") if otras and estado == "deducido" else ""
        antes = [j for j in anclas if j < i]
        despues = [j for j in anclas if j > i]
        if estado == "deducido" and antes and despues and anclas[max(antes)] != anclas[min(despues)]:
            a, b = max(antes), min(despues)
            nota = (f"folio incierto: entre la página {a} del visor (folio {a + anclas[a]}) y la {b} "
                    f"(folio {b + anclas[b]}) la numeración salta; puede faltar una página en el escaneo")
        folios[i] = (folio, estado, nota)
    return folios


def pdf_a_markdown(entrada: Path, salida: Path, resultados: list[dict] | None = None,
                   limpieza: bool = True, tipos: list[str] | None = None, nombre: str | None = None,
                   reemplazos: dict[int, str] | None = None) -> dict:
    """Escribe el texto de `entrada` en `salida` (.md). Devuelve un resumen.

    `tipos` (ruta digital): el tipo de cada página según tipo_pdf.clasificar. El
    encabezado dice de dónde sale el texto, por rangos de páginas, y cada página
    de un tipo distinto del mayoritario lo lleva anotado.
    """
    avisos: dict[int, str] = {}
    origenes = {r["pagina"]: (r.get("origen"), r.get("parte", "simple")) for r in resultados or []}
    lineas = {r["pagina"]: r.get("lineas") or 0 for r in resultados or []}
    for r in resultados or []:
        if r.get("revisar"):
            avisos[r["pagina"]] = r.get("motivo_revision") or r["motivo"]
        elif "revisar" not in r and not r["aplanada"] and r["motivo"] not in ("no pedida", "aplanada"):
            avisos[r["pagina"]] = r["motivo"]          # informes de la versión 0.1.0

    doc = fitz.open(entrada)
    crudos = [pagina.get_text("text") for pagina in doc]
    for i, texto in (reemplazos or {}).items():          # texto de otro PDF para esa página (ver cli._ruta_ocr_directo)
        crudos[i - 1] = texto
    textos = [t.strip() for t in crudos]
    detalle: list[dict] = []
    documento = compuestos_del_documento("\n".join(textos))
    if tipos:
        from .tipo_pdf import por_tipo, rangos
        grupos = por_tipo(tipos)
        mayoritario = max(grupos, key=lambda t: len(grupos[t]))
        partes = [f"<!-- Texto extraído de: {nombre or Path(entrada).name} -->",
                  AVISO_OCR_DIRECTO if "ocr_feanor" in grupos else AVISO_DIGITAL,
                  "<!-- Origen del texto, por páginas del visor: -->"]
        partes += [f"<!--   {rangos(n)}: {ORIGEN[t]} -->" for t, n in grupos.items()]
        partes.append("")
    else:
        mayoritario = None
        partes = [
            f"<!-- Texto extraído por OCR de: {Path(entrada).name} -->",
            AVISO,
            "",
        ]
    indices = [i for i, t in enumerate(textos, start=1) if es_indice(t)]
    folios = deducir_folios(textos, indices)
    from .referencias import buscar_referencias
    referencias = buscar_referencias(crudos, indices)
    fin_ref = referencias["termina_antes_de"] if referencias else None
    vacias = 0
    for i, texto in enumerate(textos, start=1):
        if i in indices:
            aviso = "página tipo índice: sin limpieza; los números se verifican en la imagen"
            avisos[i] = f"{aviso}; {avisos[i]}" if i in avisos else aviso
        elif limpieza:
            texto = limpiar(texto, documento)
        if not texto:
            vacias += 1
        # Red de seguridad: si el paso 1 contó líneas de texto en la página y
        # el OCR sacó menos palabras que líneas, las dos cuentas no cuadran y
        # la página no pasa callada, sea cual sea la causa.
        palabras = len(texto.split())
        if palabras < lineas.get(i, 0):
            aviso = (f"se contaron {lineas[i]} líneas de texto pero salieron {palabras} palabras: "
                     "lectura fallida; ver la imagen")
            avisos[i] = f"{avisos[i]}; {aviso}" if i in avisos else aviso
        partes.append(f"<!-- página {i} del visor -->")
        origen, parte = origenes.get(i, (None, "simple"))
        if origen and parte in ("izquierda", "derecha"):
            partes.append(f"<!-- sale de la página {origen} del PDF original, mitad {parte} -->")
        if i in folios:
            folio, estado, nota = folios[i]
            como = ("leído en la página y coincide con la secuencia" if estado == "leído"
                    else "deducido por la secuencia; verificar en la imagen")
            partes.append(f"<!-- folio impreso: {folio} ({como}) -->")
            if nota:
                partes.append(f"<!-- OJO con el folio: {nota} -->")
        if tipos and tipos[i - 1] != mayoritario:
            partes.append(f"<!-- origen del texto de esta página: {ORIGEN[tipos[i - 1]]} -->")
        if i in avisos:
            partes.append(f"<!-- REVISAR A MANO: {avisos[i]} -->")
        if referencias and i == referencias["pagina"]:
            partes.append(f"<!-- REFERENCIAS: empiezan en esta página, en el título «{referencias['titulo']}» -->")
        if fin_ref and i == fin_ref["pagina"]:
            partes.append(f"<!-- REFERENCIAS: terminan en esta página, antes de «{fin_ref['titulo']}» -->")
        partes.append("")
        partes.append(texto)
        partes.append("")
        origen, parte = origenes.get(i, (None, "simple"))
        detalle.append({"pagina": i, "pagina_original": origen or i, "parte": parte,
                        "folio": folios[i][0] if i in folios else None,
                        "folio_estado": folios[i][1] if i in folios else None,
                        "indice": i in indices, "limpiada": bool(limpieza) and i not in indices,
                        "revisar": avisos.get(i), "texto_crudo": crudos[i - 1]})
    Path(salida).write_text("\n".join(partes), encoding="utf-8")
    return {"paginas": len(doc), "sin_texto": vacias, "indices": indices,
            "a_revisar": sorted(avisos),
            "folios": {i: f for i, (f, _, _) in folios.items()},
            "referencias": referencias, "detalle": detalle}
