"""Paso 0: preparar cada página del PDF antes de aplanar.

Un PDF escaneado puede traer, en una misma página:
- un pliego (el libro abierto: dos páginas lado a lado), que hay que partir;
- una página girada 90° (una tabla impresa de costado), que no se debe
  partir ni aplanar: la endereza OCRmyPDF con `--rotate-pages`;
- una página en blanco, que no hace falta procesar.

Todo se decide con medidas simples sobre la imagen, sin modelos.
"""
from __future__ import annotations

import cv2
import numpy as np

TINTA_BLANCA = 0.004     # menos de 0,4 % de píxeles oscuros: página en blanco
PROPORCION_PLIEGO = 1.2  # ancho / alto a partir del cual puede ser un pliego


def _binaria(gris: np.ndarray) -> np.ndarray:
    _, b = cv2.threshold(gris, 0, 1, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    return b


def en_blanco(gris: np.ndarray) -> bool:
    """Página sin contenido (o solo con el borde oscuro del escaneo)."""
    alto, ancho = gris.shape
    centro = gris[alto // 10: alto - alto // 10, ancho // 10: ancho - ancho // 10]
    return float((centro < 128).mean()) < TINTA_BLANCA


def orientacion(gris: np.ndarray) -> str:
    """'horizontal' si las líneas de texto van de lado a lado, 'vertical' si la
    página está girada 90°.

    Se unen las letras con una mancha alargada en cada dirección y se mira en
    cuál de las dos salen más manchas largas y delgadas: esas son las líneas.
    """
    b = _binaria(gris)
    # reducir para que sea rápido
    escala = 1200 / max(b.shape)
    b = cv2.resize(b, None, fx=escala, fy=escala, interpolation=cv2.INTER_AREA)
    b = (b > 0).astype(np.uint8)
    _, _, st, _ = cv2.connectedComponentsWithStats(b, 8)
    h = st[1:, cv2.CC_STAT_HEIGHT]
    w = st[1:, cv2.CC_STAT_WIDTH]
    letras = (h > 2) & (h < 40) & (w < 40)
    if letras.sum() < 50:
        return "horizontal"
    t = int(max(np.median(np.maximum(h[letras], w[letras])), 3))
    puntos = {}
    for nombre, k in (("horizontal", (3 * t, 1)), ("vertical", (1, 3 * t))):
        manchas = cv2.dilate(b, cv2.getStructuringElement(cv2.MORPH_RECT, k))
        _, _, s2, _ = cv2.connectedComponentsWithStats(manchas, 8)
        hh, ww = s2[1:, cv2.CC_STAT_HEIGHT], s2[1:, cv2.CC_STAT_WIDTH]
        if nombre == "horizontal":
            largas = (ww > 8 * t) & (hh < 3 * t)
            puntos[nombre] = int(ww[largas].sum())
        else:
            largas = (hh > 8 * t) & (ww < 3 * t)
            puntos[nombre] = int(hh[largas].sum())
    # En 25 hojas de prueba, las páginas normales dieron vertical/horizontal
    # ≤ 0,25 y la página girada 48: el umbral 5 deja margen de sobra.
    return "vertical" if puntos["vertical"] > 5 * puntos["horizontal"] else "horizontal"


def corte_de_pliego(gris: np.ndarray) -> int | None:
    """Columna donde partir un pliego, o None si la imagen es una sola página.

    Solo se buscan pliegos en imágenes apaisadas. El lomo está cerca del centro
    (entre el 38 % y el 62 % del ancho) y es, o una franja vacía entre dos
    bloques de texto, o la línea oscura de la sombra del lomo. Además, a cada
    lado del corte tiene que haber texto.
    """
    alto, ancho = gris.shape
    if ancho < PROPORCION_PLIEGO * alto:
        return None
    b = _binaria(gris)
    banda = b[alto // 10: alto - alto // 10]            # sin encabezado ni pie
    perfil = banda.mean(axis=0)                          # tinta por columna
    perfil = np.convolve(perfil, np.ones(15) / 15, mode="same")
    a, z = int(0.38 * ancho), int(0.62 * ancho)
    centro = perfil[a:z]
    # 1) sombra del lomo: una columna casi toda oscura
    oscura = int(np.argmax(centro))
    if centro[oscura] > 0.6:
        x = a + oscura
    else:
        # 2) franja vacía entre las dos páginas: se corta en el medio del tramo
        #    más largo de columnas casi sin tinta
        if centro.min() > 0.02:
            return None
        vacias = centro <= centro.min() + 0.002
        mejor, inicio, largo = (0, 0), None, 0
        for k, v in enumerate(list(vacias) + [False]):
            if v and inicio is None:
                inicio = k
            elif not v and inicio is not None:
                if k - inicio > mejor[1]:
                    mejor = (inicio, k - inicio)
                inicio = None
        x = a + mejor[0] + mejor[1] // 2
    izquierda, derecha = perfil[:x].mean(), perfil[x:].mean()
    if izquierda < 0.01 or derecha < 0.01:              # un lado vacío: tapa, hoja suelta
        return None
    return x


def preparar(gris: np.ndarray) -> list[tuple[np.ndarray, str]]:
    """Devuelve las páginas que salen de una imagen del PDF, con su tipo:
    'blanco', 'girada', 'izquierda', 'derecha' o 'simple'."""
    if en_blanco(gris):
        return [(gris, "blanco")]
    if orientacion(gris) == "vertical":
        return [(gris, "girada")]
    x = corte_de_pliego(gris)
    if x is None:
        return [(gris, "simple")]
    # Se corta justo en el lomo, sin margen: con texto pegado al lomo, cualquier
    # margen se comería las últimas letras de las líneas.
    return [(gris[:, :x], "izquierda"), (gris[:, x:], "derecha")]
