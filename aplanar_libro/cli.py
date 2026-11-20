"""Línea de comandos.

    aplanar-libro libro.pdf                  # los tres pasos
    aplanar-libro libro.pdf --solo aplanar   # solo el paso 1
    aplanar-libro libro.pdf --paginas 2,4,6  # aplanar solo esas páginas
    aplanar-libro clase.pptx                 # PowerPoint: copia su texto a Markdown
    aplanar-libro trabajo.docx               # Word: copia su texto a Markdown

Sin --solo ni --paginas, Feanor mira antes de qué tipo es cada página: si el
PDF ya trae su texto (digital, o con un OCR previo), lo copia directo a
Markdown sin aplanar ni leer (ruta digital). --releer obliga a leerlo con el
OCR de Feanor aunque ya traiga texto.

Cada archivo deja su resultado en una carpeta propia dentro de la carpeta de
salida (por defecto D:\\FEANOR_salida; otra con --salida): el .md y un .json con
el registro de lo que se hizo. Si la carpeta ya existe y es del mismo archivo
(mismo SHA-256), se reemplaza; si es de otro archivo con el mismo nombre, se usa
una carpeta nueva con sufijo (_2, _3…) y se avisa.
"""
from __future__ import annotations

import argparse
import json
import time
from datetime import datetime
from pathlib import Path

from . import __version__
from .aplanar import ULTIMA_CORRIDA, aplanar_pdf, resultados_a_dict
from .entorno import _sha256, entorno, entorno_ocr
from .leer import leer_pdf
from .markdown import pdf_a_markdown


def _paginas(texto: str | None) -> list[int] | None:
    if not texto:
        return None
    if texto in ("pares", "impares"):
        return texto  # se resuelve cuando se conoce el número de páginas
    return [int(x) for x in texto.split(",") if x.strip()]


SALIDA_POR_DEFECTO = Path(r"D:\FEANOR_salida")
FORMATO_JSON = 1          # sube si cambia la forma del .json


def _carpeta_salida(entrada: Path, salida: Path | None, sha: str) -> Path:
    """La carpeta de este archivo dentro de la carpeta de salida."""
    if salida is None:
        salida = SALIDA_POR_DEFECTO
        if not Path(salida.anchor).exists():
            salida = entrada.parent / "FEANOR_salida"
            print(f"  OJO: no existe {SALIDA_POR_DEFECTO.anchor}; el resultado va a {salida}")
    k = 1
    while True:
        carpeta = salida / (entrada.stem if k == 1 else f"{entrada.stem}_{k}")
        previo = carpeta / f"{entrada.stem}.json"
        if not carpeta.exists() or not previo.exists():
            break
        try:
            if json.loads(previo.read_text(encoding="utf-8"))["archivo"]["sha256"] == sha:
                break
        except Exception:
            pass
        k += 1
    if k > 1:
        print(f"  OJO: ya había otro archivo llamado {entrada.name} en la salida; este va a {carpeta.name}")
    carpeta.mkdir(parents=True, exist_ok=True)
    return carpeta


def _registro(entrada: Path, sha: str, tipo: str, idioma: str) -> dict:
    return {"formato_json": FORMATO_JSON, "fecha": datetime.now().isoformat(timespec="seconds"),
            "archivo": {"nombre": entrada.name, "ruta": str(entrada.resolve()),
                        "bytes": entrada.stat().st_size, "sha256": sha},
            "tipo_entrada": tipo, "entorno": entorno_ocr(idioma)}


def _escribir_json(ruta: Path, registro: dict) -> None:
    ruta.write_text(json.dumps(registro, ensure_ascii=False, indent=2), encoding="utf-8")


def _duracion(segundos: float) -> str:
    m, s = divmod(int(round(segundos)), 60)
    return f"{m} min {s:02d} s" if m else f"{s} s"


def _presentacion(entrada: Path, idioma: str, carpeta: Path, registro: dict) -> None:
    """PowerPoint: se copia el texto que trae; las imágenes con texto se leen con OCR."""
    from .presentacion import pptx_a_markdown
    md = carpeta / f"{entrada.stem}.md"
    print(f"aplanar-libro {__version__} · PowerPoint: texto copiado; OCR solo en las imágenes con texto")
    inicio = time.perf_counter()
    r = pptx_a_markdown(entrada, md, idioma=idioma)
    if not r["ocr"]:
        print("  OJO: no se encontró Tesseract; las imágenes no se leyeron, solo se anotan")
    print(f"  {r['diapositivas']} diapositivas, sin texto: {r['sin_texto'] or 'ninguna'}; "
          f"imágenes: {r['imagenes']} (con texto leído por OCR: {r['imagenes_leidas']}, "
          f"con texto escaso marcado [?]: {r['imagenes_escasas']}), "
          f"tablas: {r['tablas']}, gráficos: {r['graficos']}, con notas del orador: {r['con_notas']}")
    registro.update({"resumen": r, "segundos": {"total": round(time.perf_counter() - inicio, 1)}})
    _escribir_json(carpeta / f"{entrada.stem}.json", registro)
    print(f"  resultado: {carpeta}")
    print(f"Listo. Tiempo total: {_duracion(time.perf_counter() - inicio)}")


def _documento(entrada: Path, idioma: str, carpeta: Path, registro: dict) -> None:
    """Word: se copia el texto que trae; las imágenes con texto se leen con OCR."""
    from .documento import docx_a_markdown
    md = carpeta / f"{entrada.stem}.md"
    print(f"aplanar-libro {__version__} · Word: texto copiado; OCR solo en las imágenes con texto")
    inicio = time.perf_counter()
    r = docx_a_markdown(entrada, md, idioma=idioma)
    if not r["ocr"]:
        print("  OJO: no se encontró Tesseract; las imágenes no se leyeron, solo se anotan")
    print(f"  {r['parrafos']} párrafos, {r['titulos']} títulos, {r['tablas']} tablas, "
          f"{r['notas']} notas, {r['cuadros']} cuadros de texto; imágenes: {r['imagenes']} "
          f"(con texto leído por OCR: {r['imagenes_leidas']}, con texto escaso marcado [?]: {r['imagenes_escasas']})")
    registro.update({"resumen": r, "segundos": {"total": round(time.perf_counter() - inicio, 1)}})
    _escribir_json(carpeta / f"{entrada.stem}.json", registro)
    print(f"  resultado: {carpeta}")
    print(f"Listo. Tiempo total: {_duracion(time.perf_counter() - inicio)}")


def _ruta_digital(pdf: Path, md: Path, registro: dict, inicio: float) -> bool:
    """Si el PDF ya trae su texto, lo pasa a Markdown sin aplanar ni leer, y
    completa el registro.

    Devuelve False (y no escribe nada) si la mayoría de las páginas con algo son
    fotos sin texto: ese PDF va por la ruta completa.
    """
    from .tipo_pdf import UMBRALES, clasificar_con_medidas, por_tipo, rangos
    from .markdown import ORIGEN
    paginas_pdf = clasificar_con_medidas(pdf)
    tipos = [p["tipo"] for p in paginas_pdf]
    grupos = por_tipo(tipos)
    registro["umbrales_tipo"] = UMBRALES
    registro["paginas_pdf"] = paginas_pdf
    registro["tipos_de_pagina"] = {t: rangos(n) for t, n in grupos.items()}
    con_texto = sum(len(grupos.get(t, [])) for t in ("digital", "ocr_previo", "dudosa"))
    escaneadas = len(grupos.get("escaneada", []))
    print(f"aplanar-libro {__version__} · tipo de cada página:")
    for t, n in grupos.items():
        print(f"  {rangos(n)}: {ORIGEN[t]}")
    if escaneadas > con_texto:
        print("  → la mayoría son fotos sin texto: ruta completa (aplanar, leer y Markdown)")
        return False
    print("  → el PDF ya trae su texto: ruta digital, sin aplanar ni OCR")
    if "ocr_previo" in grupos or "dudosa" in grupos:
        print("  OJO: hay páginas con OCR previo de otro programa; su texto puede tener errores. "
              "Para leerlas con el OCR de Feanor: --releer")
    print("Markdown")
    resumen = pdf_a_markdown(pdf, md, None, tipos=tipos)
    total = round(time.perf_counter() - inicio, 1)
    print(f"  {resumen['paginas']} páginas, {resumen['sin_texto']} sin texto, "
          f"revisar a mano: {resumen['a_revisar'] or 'ninguna'}")
    registro.update({"ruta": "digital", "segundos": {"total": total},
                     "resumen": {k: resumen[k] for k in ("paginas", "sin_texto", "indices", "a_revisar")},
                     "paginas_md": resumen["detalle"]})
    return True


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(prog="aplanar-libro",
                                description="Aplana páginas curvas, pasa OCR en español y genera Markdown.")
    p.add_argument("pdf", type=Path, help="PDF, presentación de PowerPoint (.pptx) o documento de Word (.docx)")
    p.add_argument("--solo", choices=["aplanar", "leer", "markdown"],
                   help="correr un solo paso (por defecto, los tres)")
    p.add_argument("--paginas", help="páginas a aplanar: 2,4,6 | pares | impares (por defecto, todas)")
    p.add_argument("--idioma", default="spa", help="idioma de Tesseract (por defecto spa; no mezclar)")
    p.add_argument("--modo", default="libro", choices=["libro", "auto"],
                   help="libro = un solo bloque de texto; auto = deja que Tesseract busque columnas")
    p.add_argument("--dpi", type=int, default=300)
    p.add_argument("--releer", action="store_true",
                   help="leer con el OCR de Feanor aunque el PDF ya traiga texto (por ejemplo, un OCR previo malo)")
    p.add_argument("--salida", type=Path, default=None,
                   help=f"carpeta donde se escriben los resultados (por defecto {SALIDA_POR_DEFECTO})")
    p.add_argument("--nucleos", type=int, default=None,
                   help="páginas que se aplanan a la vez (por defecto, según los núcleos físicos y la memoria libre, máx. 8)")
    a = p.parse_args(argv)

    extension = a.pdf.suffix.lower()
    if extension == ".ppt":
        raise SystemExit("Es un PowerPoint antiguo (.ppt). Ábrelo en PowerPoint, guárdalo como .pptx y vuelve a intentarlo.")
    if extension == ".doc":
        raise SystemExit("Es un Word antiguo (.doc). Ábrelo en Word, guárdalo como .docx y vuelve a intentarlo.")
    if not a.pdf.is_file():
        raise SystemExit(f"No encuentro el archivo: {a.pdf}")
    sha = _sha256(a.pdf)
    carpeta = _carpeta_salida(a.pdf, a.salida, sha)
    tipo = {".pptx": "pptx", ".docx": "docx"}.get(extension, "pdf")
    registro = _registro(a.pdf, sha, tipo, a.idioma)
    if tipo == "pptx":
        _presentacion(a.pdf, a.idioma, carpeta, registro)
        return
    if tipo == "docx":
        _documento(a.pdf, a.idioma, carpeta, registro)
        return

    nombre = a.pdf.stem
    plano = carpeta / f"{nombre}_plano.pdf"
    ocr = carpeta / f"{nombre}_ocr.pdf"
    md = carpeta / f"{nombre}.md"
    informe = carpeta / f"{nombre}_informe.json"
    registro_json = carpeta / f"{nombre}.json"
    tiempos: dict[str, float] = {}
    inicio_total = time.perf_counter()

    def medir(paso: str, desde: float) -> None:
        tiempos[paso] = round(time.perf_counter() - desde, 1)
        print(f"  {paso}: {_duracion(tiempos[paso])}")

    paginas = _paginas(a.paginas)
    if paginas in ("pares", "impares"):
        import pymupdf as fitz
        n = len(fitz.open(a.pdf))
        paginas = [i for i in range(1, n + 1) if (i % 2 == 0) == (paginas == "pares")]

    if not a.solo and not a.paginas and not a.releer:
        if _ruta_digital(a.pdf, md, registro, inicio_total):
            _escribir_json(registro_json, registro)
            print(f"  resultado: {carpeta}")
            print(f"Listo. Tiempo total: {_duracion(registro['segundos']['total'])}")
            return
    else:
        from .tipo_pdf import UMBRALES, clasificar_con_medidas
        registro["umbrales_tipo"] = UMBRALES
        registro["paginas_pdf"] = clasificar_con_medidas(a.pdf)

    donde = entorno()
    print(f"aplanar-libro {__version__} · optimizador: {donde['optimizador']} · "
          f"JAX {donde['jax'] or 'no instalado'} · numpy {donde['numpy']} · scipy {donde['scipy']}")
    resultados = None
    if a.solo in (None, "aplanar"):
        print("Paso 1: aplanar")
        t = time.perf_counter()
        resultados = resultados_a_dict(aplanar_pdf(a.pdf, plano, dpi=a.dpi, paginas=paginas, nucleos=a.nucleos, idioma=a.idioma))
        informe.write_text(json.dumps({"entorno": donde, "paginas": resultados},
                                      ensure_ascii=False, indent=2), encoding="utf-8")
        medir("aplanar", t)
    if a.solo in (None, "leer"):
        print("Paso 2: leer (OCR)")
        # Corrección 14/11/2026: con --solo leer se leía el PDF original aunque
        # existiera el aplanado. Ahora se usa el aplanado si existe.
        entrada = plano if plano.exists() else a.pdf
        print(f"  entrada: {entrada.name}")
        t = time.perf_counter()
        leer_pdf(entrada, ocr, idioma=a.idioma, modo=a.modo, forzar=a.releer)
        medir("leer", t)
    if a.solo in (None, "markdown"):
        print("Paso 3: Markdown")
        if resultados is None and informe.exists():
            resultados = json.loads(informe.read_text(encoding="utf-8"))
            if isinstance(resultados, dict):          # desde la 0.4.4: {"entorno", "paginas"}
                resultados = resultados["paginas"]
        # Misma corrección: con --solo markdown se usa el PDF con OCR si existe.
        entrada = ocr if ocr.exists() else a.pdf
        print(f"  entrada: {entrada.name}")
        t = time.perf_counter()
        resumen = pdf_a_markdown(entrada, md, resultados)
        medir("markdown", t)
        print(f"  {resumen['paginas']} páginas, {resumen['sin_texto']} sin texto, "
              f"revisar a mano: {resumen['a_revisar'] or 'ninguna'}")
        registro["resumen"] = {k: resumen[k] for k in ("paginas", "sin_texto", "indices", "a_revisar")}
        registro["paginas_md"] = resumen["detalle"]

    tiempos["total"] = round(time.perf_counter() - inicio_total, 1)
    registro.update({"ruta": "completa", "pasos": a.solo or "todos", "segundos": tiempos})
    registro["entorno"].update({k: v for k, v in donde.items() if k not in registro["entorno"]})
    if ULTIMA_CORRIDA:
        registro["procesos"] = dict(ULTIMA_CORRIDA)
    _escribir_json(registro_json, registro)
    print(f"  resultado: {carpeta}")
    print(f"Listo. Tiempo total: {_duracion(tiempos['total'])}")


if __name__ == "__main__":
    main()
