"""Modo lote: una carpeta de PDF de una vez, con una salida por archivo.

    aplanar-libro carpeta_de_tesis                    # todas las de texto
    aplanar-libro carpeta_de_tesis --solo-digitales   # solo las de texto digital

Cada PDF va por la ruta digital y deja su carpeta, como un archivo suelto: su
.md, su .json y, si se encontró, su _referencias.md. El nombre sale del nombre
del archivo: si los PDF se guardan con su handle («20.500.12692_12345.pdf»),
los resultados quedan nombrados por handle.

En el lote nunca se hace OCR: un PDF escaneado tarda minutos u horas y se lista
aparte, sin procesarlo. Con --solo-digitales también se apartan los que traen
OCR previo de otro programa (su texto sale de un OCR, no del documento).

Con --metadatos (un CSV con una fila por PDF, unida por el nombre del archivo)
cada resultado lleva su handle, universidad, carrera, año y título, y además:
- si el CSV trae el SHA-256 del PDF bajado y no coincide, el PDF no se procesa;
- si el CSV dice que la descarga falló, el PDF no se procesa;
- un PDF que no está en el CSV no se procesa;
- con --anios, uno cuyo año quede fuera del rango no se procesa (candado).

Lo que se hace al final: un resumen del lote (_lote.json, _lote.csv y
_lote.md) con cada archivo, su clase, su estado y por qué. Si el lote se corta,
se vuelve a correr igual: los PDF ya convertidos con esta versión (mismo
SHA-256) se saltan.
"""
from __future__ import annotations

import csv
import json
import re
import time
import traceback
from datetime import datetime
from pathlib import Path

from . import __version__

# Clase de un documento según el tipo de sus páginas (ver tipo_pdf.py). La regla
# es estricta a propósito y va escrita en el resumen del lote.
REGLA_CLASE = ("digital: ninguna página con OCR previo ni dudosa, y más páginas con texto que "
               "escaneadas (una hoja escaneada suelta, como la de aprobación, no la saca: sin --auto "
               "esa página no se lee y queda anotada; con --auto se lee con OCR sin aplanar); ocr_previo: alguna página con OCR previo o "
               "dudosa, y más páginas con texto que escaneadas; escaneada: más páginas escaneadas "
               "que con texto; vacia: sin texto ni imágenes")

COLUMNAS_METADATOS = ["handle", "universidad", "carrera", "anio", "titulo", "estado_descarga", "paginas_descarga"]
OBLIGATORIAS = ("archivo", "handle", "universidad", "carrera", "anio")

COLUMNAS = ["archivo", "tipo", "metodo", "palabras", "handle", "universidad", "carrera", "anio", "titulo", "estado_descarga",
            "estado", "clase", "motivo", "revisar", "palabras_cuerpo", "paginas_cuerpo", "palabras_por_pagina",
            "lineas_de_margen_quitadas", "paginas_texto_sobre_foto", "referencias_inicio_pct", "paginas", "digital", "ocr_previo", "dudosa",
            "escaneada", "vacia", "referencias_pagina", "referencias_titulo", "segundos", "carpeta",
            "sha256"]


def leer_metadatos(ruta: Path) -> dict[str, dict]:
    """{nombre de archivo: fila} del CSV de metadatos. Se niega si faltan columnas."""
    with open(ruta, newline="", encoding="utf-8-sig") as f:
        lector = csv.DictReader(f)
        faltan = [c for c in OBLIGATORIAS if c not in (lector.fieldnames or [])]
        if faltan:
            raise SystemExit(f"El CSV de metadatos {ruta.name} no tiene las columnas: {', '.join(faltan)}. "
                             f"Obligatorias: {', '.join(OBLIGATORIAS)}.")
        filas = {}
        for fila in lector:
            nombre = (fila.get("archivo") or "").strip()
            if nombre:
                filas[nombre] = {k: (v or "").strip() for k, v in fila.items() if k}
    return filas


def _anios(texto: str | None) -> tuple[int, int] | None:
    if not texto:
        return None
    a, _, b = texto.partition("-")
    return int(a), int(b or a)


def _veto_por_metadatos(pdf: Path, meta: dict | None, sha: str, anios: tuple[int, int] | None) -> str:
    """Motivo para no procesar el PDF según el CSV, o "" si pasa."""
    if meta is None:
        return "no está en el CSV de metadatos"
    if anios:
        try:
            anio = int(meta.get("anio", "")[:4])
        except ValueError:
            return f"año ilegible en el CSV ({meta.get('anio')!r}) (candado {anios[0]}–{anios[1]})"
        if not anios[0] <= anio <= anios[1]:
            return f"año {anio} fuera de {anios[0]}–{anios[1]} (candado)"
    if meta.get("estado", "").lower() in ("falló", "fallo", "fallida"):
        return "la descarga figura como fallida en el CSV"
    if meta.get("sha256") and meta["sha256"].lower() != sha:
        return "el SHA-256 no coincide con el del CSV: no es el PDF que se bajó"
    return ""


def clase_de_documento(tipos: list[str]) -> str:
    n = {t: tipos.count(t) for t in ("digital", "ocr_previo", "dudosa", "escaneada", "vacia")}
    con_texto = n["digital"] + n["ocr_previo"] + n["dudosa"]
    if con_texto == 0 and n["escaneada"] == 0:
        return "vacia"
    if n["escaneada"] > con_texto:
        return "escaneada"
    return "digital" if n["ocr_previo"] + n["dudosa"] == 0 else "ocr_previo"


def _ya_hecho(base: Path, pdf: Path, sha: str) -> Path | None:
    """La carpeta de este PDF si ya se convirtió con esta versión de Feanor."""
    for carpeta in sorted(base.glob(f"{pdf.stem}*")):
        previo = carpeta / f"{pdf.stem}.json"
        if not previo.exists():
            continue
        try:
            r = json.loads(previo.read_text(encoding="utf-8"))
        except Exception:
            continue
        if r.get("archivo", {}).get("sha256") == sha and r.get("entorno", {}).get("feanor") == __version__:
            return carpeta
    return None


def revisar(registro: dict) -> list[str]:
    """Motivos para revisar a mano una tesis convertida (no la sacan del lote)."""
    from .cuerpo import PALABRAS_POR_PAGINA_MINIMAS
    from .tipo_pdf import COBERTURA_TAPA
    motivos = []
    sobre_foto = sum(p["tipo"] == "digital" and p["cobertura_imagen"] >= COBERTURA_TAPA
                     for p in registro.get("paginas_pdf", []))
    if sobre_foto:
        motivos.append(f"{sobre_foto} páginas con texto visible sobre una foto de página completa (¿sello sobre un escaneo?)")
    ocr = registro.get("ocr") or {}
    alteradas = ocr.get("paginas_alteradas") or []
    if alteradas:
        espacios = ocr.get("paginas_alteradas_solo_espacios")
        palabras = ocr.get("paginas_alteradas_palabras")
        if espacios is None:                       # registro de la 0.5.4, sin el desglose
            motivos.append(f"{len(alteradas)} páginas de texto nativo cambiaron al reescribir el PDF para el OCR; "
                           f"se usó su texto del original: {alteradas}")
        else:
            if palabras:
                motivos.append(f"{len(palabras)} páginas de texto nativo cambiaron al reescribir el PDF para el OCR "
                               f"(cambian palabras); se usó su texto del original: {palabras}")
            if espacios:
                motivos.append(f"{len(espacios)} páginas de texto nativo cambiaron al reescribir el PDF para el OCR "
                               f"(solo espacios); se usó su texto del original: {espacios}")
    no_leidas = (registro.get("ocr") or {}).get("paginas_no_leidas") or []
    if no_leidas:
        motivos.append(f"{len(no_leidas)} páginas de imagen que el OCR no pudo leer: {no_leidas}")
    ref = registro.get("referencias")
    if not ref:
        motivos.append("sin título de referencias: el cuerpo llega hasta el final (anexos incluidos)")
    elif ref.get("revisar"):
        motivos.append(f"referencias: {ref['revisar']}")
    c = registro.get("cuerpo")
    if c and c["palabras_por_pagina"] < PALABRAS_POR_PAGINA_MINIMAS:
        motivos.append(f"pocas palabras por página en el cuerpo ({c['palabras_por_pagina']}): ¿escaneo con sello?")
    return motivos


def _fila(pdf: Path, sha: str, estado: str, motivo: str = "", registro: dict | None = None,
          paginas_pdf: list[dict] | None = None, carpeta: Path | None = None, segundos: float = 0.0,
          meta: dict | None = None) -> dict:
    tipos = [p["tipo"] for p in (paginas_pdf or (registro or {}).get("paginas_pdf") or [])]
    ref = (registro or {}).get("referencias") or {}
    fila = {"archivo": pdf.name, "tipo": pdf.suffix.lower().lstrip(".") or "?",
            "metodo": ((registro or {}).get("lote") or {}).get("metodo", ""),
            "palabras": (registro or {}).get("palabras", ""), "estado": estado, "clase": clase_de_documento(tipos) if tipos else "",
            "motivo": motivo, "paginas": len(tipos),
            **{t: tipos.count(t) for t in ("digital", "ocr_previo", "dudosa", "escaneada", "vacia")},
            "referencias_pagina": ref.get("pagina", ""), "referencias_titulo": ref.get("titulo", ""),
            "segundos": round(segundos, 1), "carpeta": carpeta.name if carpeta else "", "sha256": sha}
    r = registro or {}
    c = r.get("cuerpo") or {}
    from .tipo_pdf import COBERTURA_TAPA
    fila.update({"revisar": " | ".join(revisar(r)) if r.get("paginas_md") else "",
                 "palabras_cuerpo": c.get("palabras", ""), "paginas_cuerpo": c.get("paginas", ""),
                 "palabras_por_pagina": c.get("palabras_por_pagina", ""),
                 "lineas_de_margen_quitadas": c.get("lineas_de_margen_quitadas", ""),
                 "paginas_texto_sobre_foto": sum(p["tipo"] == "digital" and p["cobertura_imagen"] >= COBERTURA_TAPA
                                                 for p in r.get("paginas_pdf", [])) if r.get("paginas_pdf") else "",
                 "referencias_inicio_pct": round(100 * ref["inicio_fraccion"]) if ref.get("inicio_fraccion") is not None else ""})
    meta = meta or {}
    fila.update({c: meta.get(c, "") for c in ("handle", "universidad", "carrera", "anio", "titulo")})
    fila["estado_descarga"] = meta.get("estado", "")
    return fila


IGNORAR = ("desktop.ini", "thumbs.db", ".ds_store")
METODOS = {
    "texto_nativo": "texto nativo del PDF, copiado tal cual",
    "capa_ocr_previa": "capa de texto que ya traía el PDF, de un OCR anterior (marcada)",
    "texto_nativo+ocr_feanor": "PDF mixto: texto nativo donde lo hay, OCR de Feanor sin aplanar en las páginas que son solo imagen",
    "capa_ocr_previa+ocr_feanor": "capa de OCR previa donde la hay, OCR de Feanor sin aplanar en las páginas que son solo imagen",
    "ocr_feanor": "PDF escaneado: OCR de Feanor sin aplanar",
    "docx": "Word: texto copiado; OCR solo en las imágenes con texto",
    "pptx": "PowerPoint: texto copiado; OCR solo en las imágenes con texto",
}


def _palabras_md(md: Path) -> int:
    texto = re.sub(r"<!--.*?-->", " ", md.read_text(encoding="utf-8"), flags=re.S)
    return len(texto.split())


def procesar_carpeta(carpeta: Path, salida: Path | None, idioma: str = "spa",
                     solo_digitales: bool = False, metadatos: Path | None = None,
                     anios: str | None = None, destino: Path | None = None,
                     con_cuerpo: bool = False, auto: bool = False, comparar: int = 0,
                     paginas_comparacion: int = 10, semilla: int = 20261119,
                     linea_de_comandos: list[str] | None = None) -> list[dict]:
    """`destino`: carpeta exacta del lote (sin crear una subcarpeta con el nombre
    de la carpeta de entrada); si se da, `salida` no se usa.

    Con --auto el lote es automático: toma todos los archivos de la carpeta y
    usa con cada uno el método que le corresponde (ver METODOS), con OCR sin
    aplanar para las páginas que son solo imagen; los de otro tipo van a fallos
    con el motivo. Sin --auto, como en la 0.5.3: solo PDF, sin OCR (los
    escaneados se apartan). --solo-digitales y --metadatos no se combinan con
    --auto: son para un corpus muestreado."""
    from .cli import (SALIDA_POR_DEFECTO, _carpeta_salida, _documento, _escribir_json, _presentacion,
                      _registro, _ruta_digital, _ruta_ocr_directo)
    from .entorno import _sha256
    from .tipo_pdf import clasificar_con_medidas

    if salida is None:
        salida = SALIDA_POR_DEFECTO
        if not Path(salida.anchor).exists():
            salida = carpeta.parent / "FEANOR_salida"
            print(f"OJO: no existe {SALIDA_POR_DEFECTO.anchor}; el resultado va a {salida}")
    base = destino or salida / carpeta.name
    base.mkdir(parents=True, exist_ok=True)
    rango = _anios(anios)
    tabla = leer_metadatos(metadatos) if metadatos else None
    if rango and tabla is None:
        raise SystemExit("--anios necesita --metadatos: el año se lee del CSV.")
    if auto and (solo_digitales or tabla is not None):
        raise SystemExit("--auto no se combina con --solo-digitales ni con --metadatos.")
    automatico = auto
    con_ocr = auto
    todos = sorted(p for p in carpeta.iterdir() if p.is_file() and p.name.lower() not in IGNORAR
                   and not p.name.startswith(("~$", "."))
                   and not (metadatos and p.resolve() == metadatos.resolve()))
    archivos = todos if automatico else [p for p in todos if p.suffix.lower() == ".pdf"]
    otros = [p.name for p in todos if p not in archivos]
    print(f"aplanar-libro {__version__} · modo lote: {len(archivos)} archivos en {carpeta}"
          + (f" ({len(otros)} que no son PDF, no se tocan)" if otros else ""))
    print(f"  salida: {base}" + ("  ·  solo texto digital" if solo_digitales else "")
          + ("  ·  automático: cada archivo con su método, OCR sin aplanar" if auto else ""))
    if tabla is not None:
        sin_pdf = sorted(set(tabla) - {p.name for p in archivos})
        print(f"  metadatos: {metadatos.name}, {len(tabla)} filas" + (f"; candado de años {rango[0]}–{rango[1]}" if rango else "")
              + (f"; {len(sin_pdf)} filas del CSV sin su PDF en la carpeta" if sin_pdf else ""))
    inicio_lote = time.perf_counter()
    filas: list[dict] = []
    for k, arch in enumerate(archivos, start=1):
        inicio = time.perf_counter()
        etiqueta = f"[{k}/{len(archivos)}] {arch.name}"
        ext = arch.suffix.lower()
        sha = ""
        meta = tabla.get(arch.name) if tabla is not None else None
        try:
            if ext not in (".pdf", ".docx", ".pptx"):
                motivo = {".doc": "Word antiguo (.doc): guárdalo como .docx",
                          ".ppt": "PowerPoint antiguo (.ppt): guárdalo como .pptx"}.get(
                              ext, f"tipo de archivo no soportado ({ext or 'sin extensión'})")
                filas.append(_fila(arch, "", "fallo", motivo))
                print(f"{etiqueta}: FALLÓ ({motivo})")
                continue
            sha = _sha256(arch)
            if tabla is not None:
                veto = _veto_por_metadatos(arch, meta, sha, rango)
                if veto:
                    filas.append(_fila(arch, sha, "apartada", veto, meta=meta, segundos=time.perf_counter() - inicio))
                    print(f"{etiqueta}: apartada ({veto})")
                    continue
            hecho = _ya_hecho(base, arch, sha)
            r = json.loads((hecho / f"{arch.stem}.json").read_text(encoding="utf-8")) if hecho else None
            if r and solo_digitales and clase_de_documento([p["tipo"] for p in r.get("paginas_pdf", [])]) != "digital":
                hecho = None                           # convertida antes, pero ahora va aparte
            if r and con_cuerpo and ext == ".pdf" and not r.get("cuerpo"):
                hecho = None                           # convertida antes sin el cuerpo: se rehace
            if r and ext == ".pdf" and r.get("lote", {}).get("metodo") is None:
                hecho = None                           # de una versión del lote sin método: se rehace
            if hecho:
                filas.append(_fila(arch, sha, "ya_hecha", "convertida antes con esta versión", r, carpeta=hecho, meta=meta))
                print(f"{etiqueta}: ya convertida, se salta")
                continue

            if ext in (".docx", ".pptx"):
                destino_arch = _carpeta_salida(arch, base, sha)
                registro = _registro(arch, sha, ext[1:], idioma)
                registro["lote"] = {"carpeta": str(carpeta.resolve()), "metodo": ext[1:]}
                (_documento if ext == ".docx" else _presentacion)(arch, idioma, destino_arch, registro)
                registro["palabras"] = _palabras_md(destino_arch / f"{arch.stem}.md")
                _escribir_json(destino_arch / f"{arch.stem}.json", registro)
                filas.append(_fila(arch, sha, "convertida", "", registro, carpeta=destino_arch,
                                   segundos=time.perf_counter() - inicio, meta=meta))
                print(f"{etiqueta}: {ext[1:]}, {time.perf_counter() - inicio:.1f} s")
                continue

            paginas_pdf = clasificar_con_medidas(arch)
            tipos = [p["tipo"] for p in paginas_pdf]
            clase = clase_de_documento(tipos)
            hay_fotos = "escaneada" in tipos
            if clase == "vacia" or (solo_digitales and clase == "ocr_previo") or (clase == "escaneada" and not con_ocr):
                motivo = {"escaneada": "escaneada: en el lote no se hace OCR (con --auto, sí)" if not solo_digitales
                                       else "escaneada (--solo-digitales)",
                          "vacia": "sin texto ni imágenes",
                          "ocr_previo": "texto de un OCR previo (--solo-digitales)"}[clase]
                filas.append(_fila(arch, sha, "apartada", motivo, paginas_pdf=paginas_pdf,
                                   segundos=time.perf_counter() - inicio, meta=meta))
                print(f"{etiqueta}: apartada ({motivo})")
                continue
            if clase == "escaneada":
                metodo = "ocr_feanor"
            elif con_ocr and hay_fotos:
                metodo = ("texto_nativo" if clase == "digital" else "capa_ocr_previa") + "+ocr_feanor"
            else:
                metodo = "texto_nativo" if clase == "digital" else "capa_ocr_previa"
            destino_arch = _carpeta_salida(arch, base, sha)
            registro = _registro(arch, sha, "pdf", idioma)
            registro["lote"] = {"carpeta": str(carpeta.resolve()), "clase": clase, "regla_clase": REGLA_CLASE,
                                "metodo": metodo, "metodo_texto": METODOS[metodo]}
            if meta is not None:
                registro["metadatos"] = meta
            md = destino_arch / f"{arch.stem}.md"
            if metodo.endswith("ocr_feanor"):
                print(f"{etiqueta}: {METODOS[metodo]} …")
                _ruta_ocr_directo(arch, md, registro, inicio, paginas_pdf, destino_arch, idioma)
            elif not _ruta_digital(arch, md, registro, inicio, paginas_pdf=paginas_pdf):
                filas.append(_fila(arch, sha, "apartada", "la ruta digital no la aceptó",
                                   paginas_pdf=paginas_pdf, segundos=time.perf_counter() - inicio, meta=meta))
                continue
            registro["palabras"] = sum(len(p["texto_crudo"].split()) for p in registro["paginas_md"])
            if con_cuerpo:
                from .cuerpo import cuerpo
                texto, resumen_cuerpo = cuerpo([p["texto_crudo"] for p in registro["paginas_md"]],
                                               registro.get("referencias"))
                (destino_arch / f"{arch.stem}_cuerpo.md").write_text(
                    f"<!-- Cuerpo de {arch.name} para el análisis léxico: sin referencias ni anexos, sin páginas de "
                    f"índice, sin encabezados ni pies repetidos ({resumen_cuerpo['lineas_de_margen_quitadas']} líneas "
                    f"quitadas). Ver «cuerpo» en el .json. -->\n\n" + texto + "\n", encoding="utf-8")
                registro["cuerpo"] = {**resumen_cuerpo, "archivo": f"{arch.stem}_cuerpo.md"}
            registro["revisar"] = revisar(registro)
            _escribir_json(destino_arch / f"{arch.stem}.json", registro)
            aviso = ("la descarga la marcó sospechosa" if meta and meta.get("estado", "").lower().startswith("sospech")
                     else "")
            filas.append(_fila(arch, sha, "convertida", aviso, registro, carpeta=destino_arch,
                               segundos=time.perf_counter() - inicio, meta=meta))
            print(f"{etiqueta}: {clase}, {metodo}, {len(paginas_pdf)} páginas, {time.perf_counter() - inicio:.1f} s"
                  + (f"  · REVISAR: {' | '.join(registro['revisar'])}" if registro["revisar"] else ""))
        except Exception as e:                      # un archivo roto no tumba el lote
            filas.append(_fila(arch, sha, "fallo", f"{type(e).__name__}: {e}",
                               segundos=time.perf_counter() - inicio, meta=meta))
            with open(base / "_errores.txt", "a", encoding="utf-8") as errores:
                errores.write(f"== {arch.name}\n{traceback.format_exc()}\n")
            print(f"{etiqueta}: FALLÓ ({type(e).__name__}: {e})")
    extra = {"metadatos": str(metadatos.resolve()) if metadatos else None,
             "candado_anios": list(rango) if rango else None,
             "filas_csv_sin_pdf": sorted(set(tabla) - {p.name for p in archivos}) if tabla is not None else [],
             "automatico": automatico, "ocr": con_ocr, "linea_de_comandos": linea_de_comandos}
    if comparar:
        from .comparacion import comparar_ocr
        extra["comparacion_ocr"] = comparar_ocr(base, filas, comparar, paginas_comparacion, semilla, idioma)
    _resumen_lote(base, carpeta, filas, otros, solo_digitales, time.perf_counter() - inicio_lote, extra)
    return filas


def _resumen_lote(base: Path, carpeta: Path, filas: list[dict], otros: list[str],
                  solo_digitales: bool, segundos: float, extra: dict | None = None) -> None:
    from .entorno import entorno_ocr
    from .tipo_pdf import UMBRALES
    a_revisar = sum(bool(f.get("revisar")) for f in filas)
    por_tipo = {t: sum(f["tipo"] == t for f in filas) for t in sorted({f["tipo"] for f in filas})}
    por_metodo = {m: sum(f["metodo"] == m for f in filas) for m in METODOS if any(f["metodo"] == m for f in filas)}
    estados = {e: sum(f["estado"] == e for f in filas) for e in ("convertida", "ya_hecha", "apartada", "fallo")}
    clases = {c: sum(f["clase"] == c for f in filas) for c in ("digital", "ocr_previo", "escaneada", "vacia")}
    sin_ref = [f["archivo"] for f in filas if f["estado"] in ("convertida", "ya_hecha") and not f["referencias_pagina"]]
    registro = {"fecha": datetime.now().isoformat(timespec="seconds"), "carpeta": str(carpeta.resolve()),
                "solo_digitales": solo_digitales, "regla_clase": REGLA_CLASE, "umbrales_tipo": UMBRALES,
                "entorno": entorno_ocr(), "segundos": round(segundos, 1), "estados": estados, "clases": clases,
                "sin_referencias": sin_ref, "a_revisar": a_revisar, "por_tipo": por_tipo, "por_metodo": por_metodo, "no_pdf": otros, **(extra or {}), "archivos": filas}
    (base / "_lote.json").write_text(json.dumps(registro, ensure_ascii=False, indent=2), encoding="utf-8")
    with open(base / "_lote.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNAS)
        w.writeheader()
        w.writerows(filas)
    def lista(estado):
        return [f"- {f['archivo']} — {f['motivo']}" for f in filas if f["estado"] == estado] or ["- ninguna"]
    md = [f"# Lote: {carpeta.name}", "",
          f"Feanor {__version__} · {registro['fecha']} · {len(filas)} archivos · {segundos / 60:.1f} min"
          + (" · solo texto digital" if solo_digitales else ""), "",
          "| Estado | N |", "|---|---|", *[f"| {e} | {n} |" for e, n in estados.items()], "",
          "| Clase (PDF) | N |", "|---|---|", *[f"| {c} | {n} |" for c, n in clases.items()], "",
          "| Tipo de archivo | N |", "|---|---|", *[f"| {t} | {n} |" for t, n in por_tipo.items()], "",
          *(["| Método | N |", "|---|---|", *[f"| {METODOS[m]} | {n} |" for m, n in por_metodo.items()], ""]
            if por_metodo else []),
          *([f"**Comparación forzada de OCR:** {extra['comparacion_ocr']['paginas']} páginas del cuerpo de "
             f"{extra['comparacion_ocr']['pdf']} PDF digitales; tasa de error por palabra global "
             f"{extra['comparacion_ocr']['wer_global']}, mediana {extra['comparacion_ocr']['wer_mediana']}. "
             "Detalle en `comparacion_ocr/_comparacion.md`.", ""] if extra and extra.get("comparacion_ocr") else []),
          f"Regla de clase: {REGLA_CLASE}.", "",
          *([f"Metadatos: `{Path(extra['metadatos']).name}`"
             + (f" · candado de años {extra['candado_anios'][0]}–{extra['candado_anios'][1]}" if extra.get("candado_anios") else ""),
             ""] if extra and extra.get("metadatos") else []),
          *(["## Filas del CSV sin su PDF en la carpeta", "", *[f"- {a}" for a in extra["filas_csv_sin_pdf"]], ""]
            if extra and extra.get("filas_csv_sin_pdf") else []),
          "## Fallaron", "", *lista("fallo"), "",
          "## Apartadas, sin procesar", "", *lista("apartada"), "",
          "## Para revisar a mano (convertidas, pero con una señal rara)", "",
          *([f"- {f['archivo']} — {f['revisar']}" for f in filas if f.get("revisar")] or ["- ninguna"]), "",
          "## Convertidas sin título de referencias encontrado", "", *([f"- {a}" for a in sin_ref] or ["- ninguna"]), "",
          "El detalle de cada archivo está en `_lote.csv` y `_lote.json`; el de cada página, en el `.json` de cada carpeta.", ""]
    (base / "_lote.md").write_text("\n".join(md), encoding="utf-8")
    print(f"Lote listo en {segundos / 60:.1f} min: " + ", ".join(f"{n} {e}" for e, n in estados.items() if n))
    print(f"  resumen: {base / '_lote.md'}")
