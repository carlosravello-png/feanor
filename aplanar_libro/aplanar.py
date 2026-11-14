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

import tempfile
from dataclasses import dataclass, asdict
from pathlib import Path

import cv2
import pymupdf as fitz  # PyMuPDF
import msgspec
import numpy as np

import page_dewarp.image as _pdi
from page_dewarp.options import Config

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
def aplanar_pdf(entrada: Path, salida: Path, dpi: int = 300,
                paginas: list[int] | None = None) -> list[ResultadoPagina]:
    """Aplana las páginas de `entrada` y escribe un PDF de imágenes en `salida`.

    `paginas`: números del visor (desde 1) que se intentan aplanar; las demás
    pasan tal cual. Si es None, se intenta con todas.
    """
    entrada, salida = Path(entrada), Path(salida)
    doc = fitz.open(entrada)
    nuevo = fitz.open()
    resultados: list[ResultadoPagina] = []
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        for i, pagina in enumerate(doc, start=1):
            png = tmp / f"p{i:04d}.png"
            pagina.get_pixmap(dpi=dpi, colorspace=fitz.csGRAY).save(png)
            if paginas is not None and i not in paginas:
                img = cv2.imread(str(png), cv2.IMREAD_GRAYSCALE)
                res = ResultadoPagina(i, False, 0, "no pedida")
            else:
                img, res = aplanar_imagen(png, tmp)
                res.pagina = i
            resultados.append(res)
            print(f"  página {i}: {res.motivo}")
            ok, buf = cv2.imencode(".png", img)
            alto, ancho = img.shape
            hoja = nuevo.new_page(width=ancho * 72 / dpi, height=alto * 72 / dpi)
            hoja.insert_image(hoja.rect, stream=buf.tobytes())
    nuevo.save(salida, deflate=True)
    return resultados


def resultados_a_dict(resultados: list[ResultadoPagina]) -> list[dict]:
    return [asdict(r) for r in resultados]
