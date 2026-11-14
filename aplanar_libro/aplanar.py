"""Paso 1: aplanar las páginas curvas de un PDF escaneado.

El aplanado lo hace page-dewarp (MIT, https://github.com/lmmx/page-dewarp),
que sigue el método de Matt Zucker (2016). Esta librería no copia su código:
lo usa como dependencia y lo envuelve con tres cosas propias:

1. Un recuadro de salida un poco más grande, para no cortar el final de las
   líneas junto al lomo (page-dewarp calcula ese recuadro algo angosto).
2. Un recorte automático que quita la basura que deja el aplanado en los bordes.
3. Una regla de calidad: si la página tiene pocas líneas de texto, no se aplana
   (con poco texto el ajuste deforma la página en vez de enderezarla).
"""
from __future__ import annotations

import contextlib
import io
import os
import tempfile
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass, asdict
from pathlib import Path

import cv2
import pymupdf as fitz  # PyMuPDF
import msgspec
import numpy as np

import page_dewarp.image as _pdi
from page_dewarp.options import Config

from .calidad import UMBRAL_CURVA, curva_p90
from .pliegos import en_blanco, preparar

# Con menos líneas de texto que esto, la página no se aplana.
MIN_LINEAS = 8
# Cuánto se agranda el recuadro de salida de page-dewarp (8 %).
AMPLIACION = 1.08


@dataclass
class ResultadoPagina:
    pagina: int            # número de página del visor (empieza en 1)
    aplanada: bool
    lineas: int            # líneas de texto que encontró page-dewarp
    motivo: str            # por qué se aplanó o no
    curva_p90: float | None = None   # resto de curva junto al lomo (ver calidad.py)
    revisar: bool = False            # marcar en el Markdown para revisión a mano
    motivo_revision: str = ""
    origen: int = 0                  # página del PDF original de la que sale
    parte: str = "simple"            # simple | izquierda | derecha | girada | blanco


# ---------------------------------------------------------------- page-dewarp
# Se envuelven dos funciones internas de page-dewarp sin modificar su código:
# una para contar las líneas que encuentra y otra para agrandar el recuadro.
_ultima_cuenta = {"lineas": 0}
_assemble_original = _pdi.assemble_spans
_dims_original = _pdi.get_page_dims


def _assemble_contando(*args, **kwargs):
    spans = _assemble_original(*args, **kwargs)
    _ultima_cuenta["lineas"] = len(spans)
    return spans


def _dims_amplias(corners, rough_dims, params):
    return _dims_original(corners, rough_dims, params) * AMPLIACION


_pdi.assemble_spans = _assemble_contando
_pdi.get_page_dims = _dims_amplias


# ------------------------------------------------------------------- recorte
def recortar(gris: np.ndarray, margen: int = 40) -> np.ndarray:
    """Recorta la imagen aplanada al área donde hay texto de tamaño normal.

    El aplanado deja un lienzo grande con manchas y letras gigantes estiradas
    en los bordes. Se buscan las manchas con forma de letra (componentes
    conectados de alto parecido a la mediana) y se recorta a su contorno.
    """
    b = cv2.adaptiveThreshold(gris, 255, cv2.ADAPTIVE_THRESH_MEAN_C,
                              cv2.THRESH_BINARY_INV, 51, 15)
    _, _, st, _ = cv2.connectedComponentsWithStats(b, 8)
    st = st[1:]
    h, w, a = st[:, cv2.CC_STAT_HEIGHT], st[:, cv2.CC_STAT_WIDTH], st[:, cv2.CC_STAT_AREA]
    ok = (h > 8) & (a > 20)
    if ok.sum() < 20:
        return gris
    med = np.median(h[ok])
    ok &= (h < 2.5 * med) & (w < 6 * med)      # fuera letras gigantes y bordes
    s = st[ok]
    izq, arr, der, aba = s[:, 0], s[:, 1], s[:, 0] + s[:, 2], s[:, 1] + s[:, 3]
    # Los percentiles ignoran manchas sueltas lejanas; luego se amplía hasta la
    # última letra cercana, para no cortar el final de las líneas.
    tol = 4 * med
    x0 = izq[izq >= np.percentile(izq, 0.5) - tol].min()
    y0 = arr[arr >= np.percentile(arr, 0.5) - tol].min()
    x1 = der[der <= np.percentile(der, 99.5) + tol].max()
    y1 = aba[aba <= np.percentile(aba, 99.5) + tol].max()
    x0, y0 = max(int(x0) - margen, 0), max(int(y0) - margen, 0)
    x1, y1 = min(int(x1) + margen, gris.shape[1]), min(int(y1) + margen, gris.shape[0])
    return gris[y0:y1, x0:x1]


# ----------------------------------------------------------------- una página
def aplanar_imagen(ruta_png: Path, carpeta_tmp: Path) -> tuple[np.ndarray, ResultadoPagina]:
    """Aplana una imagen de página. Devuelve la imagen final y el resultado."""
    original = cv2.imread(str(ruta_png), cv2.IMREAD_GRAYSCALE)
    _ultima_cuenta["lineas"] = 0
    cfg = msgspec.structs.replace(Config(), NO_BINARY=1, PAGE_MARGIN_X=10,
                                  PAGE_MARGIN_Y=10, OUTPUT_DIR=str(carpeta_tmp))
    try:
        _pdi.WarpedImage(str(ruta_png), config=cfg)
    except Exception as e:  # page-dewarp puede fallar en páginas sin texto
        return original, ResultadoPagina(0, False, _ultima_cuenta["lineas"],
                                         f"page-dewarp falló: {type(e).__name__}")
    lineas = _ultima_cuenta["lineas"]
    if lineas < MIN_LINEAS:
        return original, ResultadoPagina(0, False, lineas,
                                         f"pocas líneas de texto ({lineas} < {MIN_LINEAS})")
    salida = carpeta_tmp / f"{ruta_png.stem}_thresh.png"
    if not salida.exists():
        return original, ResultadoPagina(0, False, lineas, "page-dewarp no escribió salida")
    aplanada = cv2.imread(str(salida), cv2.IMREAD_GRAYSCALE)
    return recortar(aplanada), ResultadoPagina(0, True, lineas, "aplanada")


# --------------------------------------------------------------------- un PDF
def _tinta(gris: np.ndarray) -> float:
    """Fracción de píxeles oscuros en el centro de la página (sin bordes)."""
    alto, ancho = gris.shape
    centro = igualar_luz(gris)[alto // 10: alto - alto // 10, ancho // 10: ancho - ancho // 10]
    return float((centro < 128).mean())


def igualar_luz(gris: np.ndarray) -> np.ndarray:
    """Quita las sombras y la luz despareja de una foto: divide cada píxel por
    el brillo del fondo a su alrededor. En un escaneo blanco casi no cambia
    nada; en una foto de celular con fondo gris, deja el papel blanco y la
    letra negra, que es lo que Tesseract lee mejor."""
    chico = cv2.resize(gris, None, fx=0.1, fy=0.1, interpolation=cv2.INTER_AREA)
    fondo = cv2.medianBlur(chico, 31)
    fondo = cv2.resize(fondo, (gris.shape[1], gris.shape[0]), interpolation=cv2.INTER_LINEAR)
    return np.clip(gris.astype(np.float32) / np.maximum(fondo.astype(np.float32), 1) * 235, 0, 255).astype(np.uint8)


def _evaluar(img: np.ndarray, res: ResultadoPagina) -> tuple[bytes, dict]:
    """Mide la curva, decide si se marca para revisión y codifica la imagen."""
    res.curva_p90 = curva_p90(img) if res.parte not in ("blanco", "girada") else None
    avisos = []
    if res.parte == "girada":
        avisos.append("página girada 90°: la endereza el OCR, pero no se aplanó; revisar el orden del texto")
    if res.motivo.startswith(("pocas líneas", "page-dewarp")):
        avisos.append(res.motivo)
    if res.curva_p90 is not None and res.curva_p90 >= UMBRAL_CURVA:
        avisos.append(f"líneas todavía curvas junto al lomo (curva {res.curva_p90} ≥ {UMBRAL_CURVA})")
    res.revisar = bool(avisos)
    res.motivo_revision = "; ".join(avisos)
    ok, buf = cv2.imencode(".png", img)
    return buf.tobytes(), asdict(res)


def _procesar_pagina(args: tuple[int, str, str, bool]) -> tuple[int, list[tuple[bytes, dict]]]:
    """Trabajo de una página del PDF original, pensado para correr en un proceso aparte.

    Recibe el número de página, la ruta de su PNG, una carpeta temporal propia
    y si hay que intentar aplanarla. Primero la prepara (paso 0: blanco, girada,
    pliego o simple); un pliego da dos páginas. Devuelve, por cada página que
    sale, la imagen final codificada en PNG y su resultado como diccionario.
    """
    i, ruta_png, carpeta, intentar = args
    png, tmp = Path(ruta_png), Path(carpeta)
    gris = cv2.imread(str(png), cv2.IMREAD_GRAYSCALE)
    salidas = []
    for k, (img, parte) in enumerate(preparar(gris)):
        if parte in ("izquierda", "derecha") and en_blanco(img):
            parte = "blanco"                      # la otra mitad de una portada, por ejemplo
        res = ResultadoPagina(0, False, 0, "", origen=i, parte=parte)
        if parte == "blanco":
            res.motivo = "página en blanco"
        elif parte == "girada":
            res.motivo = "página girada 90°: no se aplana"
        elif not intentar:
            res.motivo = "no pedida"
        else:
            media = tmp / f"{png.stem}_{k}.png"
            # Borde blanco alrededor: al partir un pliego, el texto queda pegado
            # al corte, y page-dewarp, al estirar la imagen, repite el último
            # píxel del borde y emborrona las últimas letras de cada línea.
            # El borde es del color del fondo de la página, no blanco: en una foto
            # con fondo gris, un marco blanco confunde a page-dewarp y no
            # encuentra ninguna línea (probado con fotos de celular, 14/11/2026).
            m = max(img.shape) // 30
            fondo = int(np.median(img))
            cv2.imwrite(str(media), cv2.copyMakeBorder(img, m, m, m, m, cv2.BORDER_CONSTANT, value=fondo))
            # page-dewarp escribe mucho en pantalla; con varias páginas a la vez se
            # mezcla y no se entiende. Se silencia y se informa al final de cada página.
            with contextlib.redirect_stdout(io.StringIO()):
                img, r = aplanar_imagen(media, tmp)
            res.aplanada, res.lineas, res.motivo = r.aplanada, r.lineas, r.motivo
            if r.lineas == 0 and r.motivo.startswith("pocas líneas") and _tinta(img) < 0.02:
                res.motivo = "sin líneas de texto (figura o mitad vacía)"
        if parte != "blanco":
            img = igualar_luz(img)
        salidas.append(_evaluar(img, res))
    return i, salidas


def dpi_de_pagina(doc: "fitz.Document", pagina: "fitz.Page", dpi: int) -> int:
    """Resolución a la que se rasteriza una página.

    Si la página es una sola foto de menor resolución que `dpi` (por debajo
    del 75 %), se usa la de la foto: agrandarla no agrega información y solo
    gasta memoria y tiempo. En una prueba con fotos de celular a 180 ppp, una
    página rasterizada a 300 ppp agotó la memoria al aplanar.
    """
    imagenes = pagina.get_images()
    if len(imagenes) != 1:
        return dpi
    try:
        info = doc.extract_image(imagenes[0][0])
    except Exception:
        return dpi
    nativo = max(info["width"], info["height"]) / (max(pagina.rect.width, pagina.rect.height) / 72)
    return int(nativo) if nativo < 0.75 * dpi else dpi


def nucleos_por_defecto() -> int:
    """Todos los núcleos menos uno, para no congelar la computadora.

    Tope de 8: cada página aplanada ocupa varios cientos de MB de memoria
    mientras se procesa.
    """
    return max(1, min((os.cpu_count() or 2) - 1, 8))


def aplanar_pdf(entrada: Path, salida: Path, dpi: int = 300,
                paginas: list[int] | None = None, nucleos: int | None = None) -> list[ResultadoPagina]:
    """Aplana las páginas de `entrada` y escribe un PDF de imágenes en `salida`.

    `paginas`: números de página del PDF original (desde 1) que se intentan
    aplanar; las demás pasan tal cual. Si es None, se intenta con todas.
    Antes de aplanar, cada página se prepara (ver pliegos.py): los pliegos se
    parten en dos y las páginas en blanco o giradas no se aplanan. Por eso el
    PDF de salida puede tener más páginas que el original.
    `nucleos`: cuántas páginas se procesan a la vez (por defecto, todos los
    núcleos menos uno, con tope de 8).
    """
    entrada, salida = Path(entrada), Path(salida)
    nucleos = nucleos or nucleos_por_defecto()
    doc = fitz.open(entrada)
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        # 1. Rasterizar todas las páginas (rápido, en serie)
        tareas = []
        dpis: dict[int, int] = {}
        for i, pagina in enumerate(doc, start=1):
            png = tmp / f"p{i:04d}.png"
            dpis[i] = dpi_de_pagina(doc, pagina, dpi)
            pagina.get_pixmap(dpi=dpis[i], colorspace=fitz.csGRAY).save(png)
            propia = tmp / f"t{i:04d}"
            propia.mkdir()
            tareas.append((i, str(png), str(propia), paginas is None or i in paginas))
        # 2. Aplanar y medir, varias páginas a la vez
        print(f"  {len(tareas)} páginas, {nucleos} a la vez")
        hechas: dict[int, list[tuple[bytes, dict]]] = {}
        if nucleos == 1:
            for i, salidas in map(_procesar_pagina, tareas):
                hechas[i] = salidas
                _avisar(i, salidas)
        else:
            with ProcessPoolExecutor(max_workers=nucleos) as pool:
                futuros = [pool.submit(_procesar_pagina, t) for t in tareas]
                for f in as_completed(futuros):
                    i, salidas = f.result()
                    hechas[i] = salidas
                    _avisar(i, salidas)
    # 3. Armar el PDF en el orden original
    nuevo = fitz.open()
    resultados = []
    for i in sorted(hechas):
        for img_png, res in hechas[i]:
            alto, ancho = cv2.imdecode(np.frombuffer(img_png, np.uint8), cv2.IMREAD_GRAYSCALE).shape
            hoja = nuevo.new_page(width=ancho * 72 / dpis[i], height=alto * 72 / dpis[i])
            hoja.insert_image(hoja.rect, stream=img_png)
            res["pagina"] = len(resultados) + 1   # número en el PDF de salida
            resultados.append(ResultadoPagina(**res))
    nuevo.save(salida, deflate=True)
    return resultados


def _avisar(i: int, salidas: list[tuple[bytes, dict]]) -> None:
    for _, res in salidas:
        parte = "" if res["parte"] in ("simple", "blanco", "girada") else f" ({res['parte']})"
        print(f"  página {i}{parte}: {res['motivo']}"
              + (f"  [REVISAR: {res['motivo_revision']}]" if res["revisar"] else ""), flush=True)


def resultados_a_dict(resultados: list[ResultadoPagina]) -> list[dict]:
    return [asdict(r) for r in resultados]
