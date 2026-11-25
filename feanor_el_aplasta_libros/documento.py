"""Documentos de Word (.docx) a Markdown.

Un .docx guarda el texto ya escrito, igual que un PowerPoint: se copia tal
cual, sin aplanar ni OCR, en el orden del documento. Lo que se conserva:

- títulos (por el estilo «Título N» / «Heading N» o el nivel de esquema),
  como encabezados de Markdown;
- listas, con su sangría: las de viñetas como viñetas y las numeradas con
  su número, contado como lo cuenta Word («3.», «b)», «1.2.»);
- tablas, como tablas de Markdown (una celda combinada se escribe una vez);
- notas al pie y notas al final, con su marca en el texto ([^1]) y su
  contenido al final;
- cuadros de texto, en el lugar donde están anclados y marcados.

Lo que no: encabezados y pies de página (se repiten en cada hoja), texto
eliminado con control de cambios y comentarios. Las imágenes con texto se leen
con OCR igual que en PowerPoint (ver presentacion.py) y van marcadas.

Usa python-docx (licencia MIT, verificada en PyPI el 19/11/2026).
"""
from __future__ import annotations

import re
from pathlib import Path

from .presentacion import (AREA_MINIMA_OCR, DUDOSO, PALABRAS_ESCASAS, PALABRAS_MINIMAS,
                           _texto_de_imagen)

AVISO = """<!-- AVISO: texto copiado tal cual del documento de Word, sin OCR. El texto leído dentro de
     imágenes sí sale de OCR: va entre marcas «texto leído con OCR» y puede tener errores; los renglones
     dudosos van con «[?]». No se incluyen encabezados ni pies de página, ni texto eliminado con control
     de cambios, ni comentarios. -->"""

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
R = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
WP = "{http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing}"
MC_FALLBACK = "{http://schemas.openxmlformats.org/markup-compatibility/2006}Fallback"
_TITULO = re.compile(r"(heading|t[íi]tulo)\s*(\d)", re.IGNORECASE)


def _python_docx():
    try:
        import docx
    except ImportError as e:  # pragma: no cover
        raise SystemExit("Para leer Word falta python-docx: python -m pip install python-docx") from e
    return docx


def _fuera(el, raiz, nombres) -> bool:
    """True si `el` cuelga, dentro de `raiz`, de alguno de los elementos `nombres`.
    Sirve para no leer dos veces lo que Word guarda dos veces (la versión de
    respaldo de un cuadro de texto) ni mezclar un cuadro con su párrafo."""
    for anc in el.iterancestors():
        if anc is raiz:
            return False
        if anc.tag in nombres:
            return True
    return False


def _texto(p, notas_usadas: list) -> str:
    """El texto de un párrafo, con las marcas de las notas al pie."""
    partes = []
    for el in p.iter():
        if _fuera(el, p, (W + "txbxContent", MC_FALLBACK)):
            continue
        if el.tag == W + "t":
            partes.append(el.text or "")
        elif el.tag in (W + "tab",):
            partes.append(" ")
        elif el.tag in (W + "br", W + "cr"):
            partes.append("\n")
        elif el.tag == W + "footnoteReference":
            partes.append(f"[^{el.get(W + 'id')}]")
            notas_usadas.append(("pie", el.get(W + "id")))
        elif el.tag == W + "endnoteReference":
            partes.append(f"[^final{el.get(W + 'id')}]")
            notas_usadas.append(("final", el.get(W + "id")))
    texto = "".join(partes)
    return "\n".join(" ".join(l.split()) for l in texto.split("\n")).strip()


def _nivel_titulo(p, estilos: dict) -> int:
    ppr = p.find(W + "pPr")
    if ppr is not None:
        nivel = ppr.find(W + "outlineLvl")
        if nivel is not None and nivel.get(W + "val", "9").isdigit() and int(nivel.get(W + "val")) < 6:
            return int(nivel.get(W + "val")) + 1
        estilo = ppr.find(W + "pStyle")
        if estilo is not None:
            m = _TITULO.search(estilos.get(estilo.get(W + "val"), estilo.get(W + "val") or ""))
            if m:
                return min(int(m.group(2)), 6)
    return 0


def _romano(n: int) -> str:
    valores = [(1000, "m"), (900, "cm"), (500, "d"), (400, "cd"), (100, "c"), (90, "xc"),
               (50, "l"), (40, "xl"), (10, "x"), (9, "ix"), (5, "v"), (4, "iv"), (1, "i")]
    salida = ""
    for v, letra in valores:
        while n >= v:
            salida, n = salida + letra, n - v
    return salida


def _letra(n: int) -> str:
    salida = ""
    while n > 0:
        n, resto = divmod(n - 1, 26)
        salida = chr(ord("a") + resto) + salida
    return salida


def _formato(n: int, fmt: str) -> str:
    """El número n escrito como lo escribe Word en ese formato de numeración."""
    if fmt in ("lowerRoman", "upperRoman"):
        r = _romano(n)
        return r.upper() if fmt == "upperRoman" else r
    if fmt in ("lowerLetter", "upperLetter"):
        r = _letra(n)
        return r.upper() if fmt == "upperLetter" else r
    if fmt == "decimalZero":
        return f"{n:02d}"
    return str(n)                                    # decimal y los formatos que no se reconocen


def _numeracion(documento) -> tuple[dict, dict]:
    """Lee la parte de numeración: para cada numId, su lista abstracta, y para
    cada (lista abstracta, nivel), el formato, el inicio y el rótulo («%1.»)."""
    try:
        raiz = documento.part.numbering_part.element
    except Exception:
        return {}, {}
    niveles = {}
    for abst in raiz.findall(W + "abstractNum"):
        aid = abst.get(W + "abstractNumId")
        for lvl in abst.findall(W + "lvl"):
            fmt, ini, rot = lvl.find(W + "numFmt"), lvl.find(W + "start"), lvl.find(W + "lvlText")
            niveles[(aid, int(lvl.get(W + "ilvl", "0")))] = (
                fmt.get(W + "val") if fmt is not None else "decimal",
                int(ini.get(W + "val", "1")) if ini is not None else 1,
                rot.get(W + "val") if rot is not None else "")
    listas = {}
    for num in raiz.findall(W + "num"):
        aid = num.find(W + "abstractNumId")
        inicios = {}
        for o in num.findall(W + "lvlOverride"):
            ini = o.find(W + "startOverride")
            if ini is not None:
                inicios[int(o.get(W + "ilvl", "0"))] = int(ini.get(W + "val", "1"))
        listas[num.get(W + "numId")] = (aid.get(W + "val") if aid is not None else None, inicios)
    return listas, niveles


def _tabla(tbl, notas_usadas: list) -> list[str]:
    filas = []
    for tr in tbl.findall(W + "tr"):
        celdas = []
        for tc in tr.findall(W + "tc"):
            texto = " ".join(_texto(p, notas_usadas) for p in tc.iter(W + "p"))
            celdas.append(" ".join(texto.split()).replace("|", "/"))
            span = tc.find(f"{W}tcPr/{W}gridSpan")
            if span is not None and span.get(W + "val", "1").isdigit():
                celdas += [""] * (int(span.get(W + "val")) - 1)   # celda combinada: se escribe una vez
        filas.append(celdas)
    filas = [f for f in filas if any(f)]
    if not filas:
        return []
    ancho = max(len(f) for f in filas)
    filas = [f + [""] * (ancho - len(f)) for f in filas]
    salida = ["| " + " | ".join(filas[0]) + " |", "|" + " --- |" * ancho]
    return salida + ["| " + " | ".join(f) + " |" for f in filas[1:]]


class _Lector:
    def __init__(self, documento, idioma: str, exe: str | None):
        self.doc = documento
        self.idioma, self.exe = idioma, exe
        self.notas_usadas: list = []
        self.cuenta = {"parrafos": 0, "titulos": 0, "tablas": 0, "cuadros": 0, "imagenes": 0,
                       "imagenes_leidas": 0, "imagenes_escasas": 0, "notas": 0, "ocr": bool(exe)}
        estilos = {}
        for s in documento.styles:
            try:
                estilos[s.style_id] = s.name or ""
            except Exception:
                continue
        self.estilos = estilos
        # Numeración que traen los estilos (directa o heredada de su estilo base).
        propia, base = {}, {}
        for el in documento.styles.element.findall(W + "style"):
            sid = el.get(W + "styleId")
            num = el.find(f"{W}pPr/{W}numPr")
            if num is not None:
                nid, niv = num.find(W + "numId"), num.find(W + "ilvl")
                propia[sid] = (nid.get(W + "val") if nid is not None else None,
                               int(niv.get(W + "val", "0")) if niv is not None else 0)
            b = el.find(W + "basedOn")
            if b is not None:
                base[sid] = b.get(W + "val")
        def hereda(sid, vistos=()):
            if sid in propia:
                return propia[sid]
            if sid in base and sid not in vistos:
                return hereda(base[sid], vistos + (sid,))
            return None
        self.num_estilo = {sid: hereda(sid) for sid in estilos if hereda(sid)}
        self.listas, self.niveles = _numeracion(documento)
        self.contadores: dict[str, list] = {}
        seccion = documento.sections[0] if documento.sections else None
        ancho = (seccion.page_width or 7772400) if seccion else 7772400
        alto = (seccion.page_height or 10058400) if seccion else 10058400
        self.area_pagina = ancho * alto
        self.n_imagen = 0

    def _lista(self, p) -> tuple[int, str] | None:
        """Nivel y viñeta del párrafo si es de una lista; None si no lo es. La
        numeración puede venir en el propio párrafo o en su estilo. Las listas
        numeradas llevan su número («3.», «b)», «1.2.»), contado como Word."""
        num = p.find(f"{W}pPr/{W}numPr")
        estilo = p.find(f"{W}pPr/{W}pStyle")
        del_estilo = self.num_estilo.get(estilo.get(W + "val")) if estilo is not None else None
        if num is None and del_estilo is None:
            return None
        nid = num.find(W + "numId") if num is not None else None
        niv = num.find(W + "ilvl") if num is not None else None
        numid = nid.get(W + "val") if nid is not None else (del_estilo[0] if del_estilo else None)
        nivel = int(niv.get(W + "val", "0")) if niv is not None else (del_estilo[1] if del_estilo else 0)
        if numid == "0":                              # numId 0: el párrafo quita la numeración
            return None
        aid, inicios = self.listas.get(numid, (None, {}))
        fmt, inicio, rotulo = self.niveles.get((aid, nivel), ("bullet", 1, ""))
        if fmt in ("bullet", "none") or not rotulo:
            return nivel, "-"
        cuenta = self.contadores.setdefault(numid, [None] * 9)
        nivel = min(nivel, 8)
        cuenta[nivel] = inicios.get(nivel, inicio) if cuenta[nivel] is None else cuenta[nivel] + 1
        for k in range(nivel + 1, 9):                 # un punto de un nivel reinicia los de abajo
            cuenta[k] = None
        def cifra(m):
            k = int(m.group(1)) - 1
            n = cuenta[k] if cuenta[k] is not None else self.niveles.get((aid, k), ("", 1, ""))[1]
            return _formato(n, self.niveles.get((aid, k), ("decimal", 1, ""))[0])
        marca = re.sub(r"%(\d)", cifra, rotulo).strip()
        if re.fullmatch(r"\d+\.", marca):              # «3.»: lista numerada de Markdown
            return nivel, marca
        return nivel, "- " + marca                   # «b)», «1.2.», «IV.»: se conserva el rótulo

    def _imagenes(self, p) -> list[str]:
        """Las imágenes ancladas en el párrafo, leídas con OCR si traen texto."""
        partes = []
        for dibujo in p.iter(W + "drawing"):
            if _fuera(dibujo, p, (MC_FALLBACK,)):
                continue
            blip = next(dibujo.iter(A + "blip"), None)
            if blip is None or not blip.get(R + "embed"):
                continue
            self.cuenta["imagenes"] += 1
            self.n_imagen += 1
            k = self.n_imagen
            ext = next(dibujo.iter(WP + "extent"), None)
            area = (int(ext.get("cx", 0)) * int(ext.get("cy", 0)) / self.area_pagina) if ext is not None else 1
            if not self.exe:
                partes.append(f"<!-- imagen {k}: no leída, no se encontró Tesseract; ver el original -->")
                continue
            if area < AREA_MINIMA_OCR:
                partes.append(f"<!-- imagen {k}: no leída, imagen muy pequeña (logo o ícono); ver el original -->")
                continue
            try:
                blob = self.doc.part.related_parts[blip.get(R + "embed")].blob
                leido = _texto_de_imagen(blob, self.idioma, self.exe)
            except Exception:
                leido = None
            if leido is None:
                partes.append(f"<!-- imagen {k}: no leída, formato que no se puede abrir; ver el original -->")
                continue
            descartes = (f"; {leido['baja_confianza']} renglones descartados por baja confianza"
                         if leido["baja_confianza"] else "")
            if leido["palabras"] >= PALABRAS_MINIMAS:
                self.cuenta["imagenes_leidas"] += 1
                partes += [f"<!-- imagen {k}: texto leído con OCR, puede tener errores{descartes}; "
                           "verificar en el original -->", "", *leido["lineas"], "",
                           f"<!-- fin del texto leído en la imagen {k} -->"]
            elif leido["palabras"] >= PALABRAS_ESCASAS:
                self.cuenta["imagenes_escasas"] += 1
                lineas = [l if l.startswith(DUDOSO) else DUDOSO + l for l in leido["lineas"]]
                partes += [f"<!-- imagen {k}: texto escaso leído con OCR ({leido['palabras']} palabras), "
                           f"todo dudoso{descartes}; verificar en el original -->", "", *lineas, "",
                           f"<!-- fin del texto leído en la imagen {k} -->"]
            else:
                suelta = (f"; texto escaso descartado ({leido['palabras']} palabra)" if leido["palabras"] else "")
                partes.append(f"<!-- imagen {k}: sin texto legible{suelta}{descartes}; ver el original -->")
        return partes

    def _cuadros(self, p) -> list[str]:
        partes = []
        for caja in p.iter(W + "txbxContent"):
            if _fuera(caja, p, (MC_FALLBACK,)) or _fuera(caja, p, (W + "txbxContent",)):
                continue
            lineas = [t for t in (_texto(q, self.notas_usadas) for q in caja.iter(W + "p")) if t]
            if lineas:
                self.cuenta["cuadros"] += 1
                partes += ["<!-- cuadro de texto -->", *lineas, "<!-- fin del cuadro de texto -->"]
        return partes

    def bloques(self, contenedor) -> list[list[str]]:
        salida: list[list[str]] = []
        for el in contenedor:
            if el.tag == W + "p":
                texto = _texto(el, self.notas_usadas)
                if texto:
                    self.cuenta["parrafos"] += 1
                    nivel = _nivel_titulo(el, self.estilos)
                    lista = self._lista(el)
                    if nivel:
                        self.cuenta["titulos"] += 1
                        salida.append(["#" * nivel + " " + texto.replace("\n", " ")])
                    elif lista is not None:
                        nivel_lista, marca = lista
                        salida.append(["   " * nivel_lista + marca + " " + texto.replace("\n", " ")])
                    else:
                        salida.append([texto])
                extra = self._cuadros(el) + self._imagenes(el)
                if extra:
                    salida.append(extra)
            elif el.tag == W + "tbl":
                self.cuenta["tablas"] += 1
                tabla = _tabla(el, self.notas_usadas)
                if tabla:
                    salida.append(tabla)
            elif el.tag == W + "sdt":                    # control de contenido (por ejemplo, un índice)
                contenido = el.find(W + "sdtContent")
                if contenido is not None:
                    salida += self.bloques(contenido)
        return salida

    def notas(self) -> list[str]:
        """El texto de las notas al pie y al final que se citan en el documento."""
        from lxml import etree
        textos: dict[tuple[str, str], str] = {}
        for rel in self.doc.part.rels.values():
            tipo = rel.reltype.rsplit("/", 1)[-1]
            if tipo not in ("footnotes", "endnotes") or rel.is_external:
                continue
            raiz = etree.fromstring(rel.target_part.blob)
            clase = "pie" if tipo == "footnotes" else "final"
            for nota in raiz:
                if nota.tag in (W + "footnote", W + "endnote"):
                    texto = " ".join(_texto(p, []) for p in nota.iter(W + "p")).strip()
                    textos[(clase, nota.get(W + "id"))] = " ".join(texto.split())
        salida, vistas = [], set()
        for clase, n in self.notas_usadas:
            if (clase, n) in vistas:
                continue
            vistas.add((clase, n))
            marca = f"[^{n}]" if clase == "pie" else f"[^final{n}]"
            salida.append(f"{marca}: {textos.get((clase, n), '(nota sin texto)')}")
        self.cuenta["notas"] = len(salida)
        return salida


def docx_a_markdown(entrada: Path, salida: Path, idioma: str = "spa", ocr_imagenes: bool = True) -> dict:
    """Escribe el .md del documento de Word y devuelve un resumen."""
    from .entorno import ruta_tesseract
    docx = _python_docx()
    documento = docx.Document(str(entrada))
    lector = _Lector(documento, idioma, ruta_tesseract() if ocr_imagenes else None)
    bloques = lector.bloques(documento.element.body)
    notas = lector.notas()
    partes = [f"<!-- Texto extraído del documento de Word: {Path(entrada).name} -->", AVISO, ""]
    for b in bloques:
        partes += b + [""]
    if notas:
        partes += ["## Notas", ""] + notas + [""]
    salida.write_text("\n".join(partes), encoding="utf-8")
    return lector.cuenta
