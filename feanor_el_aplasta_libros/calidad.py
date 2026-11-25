"""Señal de calidad geométrica: ¿quedaron rectas las líneas junto al lomo?

Por cada línea de texto se mide la altura del texto en 8 trozos de izquierda a
derecha. Se ajusta una recta a los trozos lejos del lomo y se mide cuánto se
aparta de ella el extremo del lado del lomo, en unidades de altura de letra.
Una página plana da desvíos chicos; una con resto de curva, grandes.

Calibración (14/11/2026, 14 páginas de un libro fotografiado; tabla completa en
CALIBRACION.md): con el percentil 90 de los desvíos de la página, el umbral 0,55
marcó las tres páginas malas (2, 8, 14) y una página cuyo OCR salió bien pese
a tener un resto de curva visible (4). Ninguna página mala quedó sin marcar.
"""
from __future__ import annotations

import cv2
import numpy as np

UMBRAL_CURVA = 0.55
# Fracción de tinta: por debajo, una página sin líneas se toma por figura o
# mitad vacía.
TINTA_MINIMA = 0.02
N_TROZOS = 8


def desvios_lomo(gris: np.ndarray, lomo_derecha: bool) -> np.ndarray:
    """Desvío del extremo del lomo de cada línea, en alturas de letra."""
    _, b = cv2.threshold(gris, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    _, _, st, _ = cv2.connectedComponentsWithStats(b, 8)
    alturas = st[1:, cv2.CC_STAT_HEIGHT]
    alturas = alturas[alturas > 5]
    if len(alturas) < 20:
        return np.array([])
    hmed = float(np.median(alturas))
    # Unir las palabras de una misma línea en una sola mancha
    nucleo = cv2.getStructuringElement(cv2.MORPH_RECT, (max(int(2.5 * hmed), 3), 1))
    manchas = cv2.dilate(b, nucleo)
    contornos, _ = cv2.findContours(manchas, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    ancho = gris.shape[1]
    xs = np.arange(N_TROZOS)
    lado = [N_TROZOS - 2, N_TROZOS - 1] if lomo_derecha else [0, 1]
    desvios = []
    for c in contornos:
        x, y, w, h = cv2.boundingRect(c)
        # Solo líneas largas (no títulos ni finales de párrafo) de alto normal
        if w < 0.48 * ancho or h > 4 * hmed or h < hmed:
            continue
        centros = []
        for t in range(N_TROZOS):
            xa, xb = x + t * w // N_TROZOS, x + (t + 1) * w // N_TROZOS
            filas = np.nonzero(b[y:y + h, xa:xb])[0]
            centros.append(y + np.median(filas) if len(filas) >= 20 else np.nan)
        centros = np.array(centros)
        resto = [i for i in range(N_TROZOS) if i not in lado and not np.isnan(centros[i])]
        if len(resto) < 4 or np.isnan(centros[lado]).all():
            continue
        a, b0 = np.polyfit(xs[resto], centros[resto], 1)
        desvios.append(np.nanmax(np.abs(centros[lado] - (a * xs[lado] + b0))) / hmed)
    return np.array(desvios)


def curva_p90(gris: np.ndarray) -> float | None:
    """Percentil 90 de los desvíos de la página, o None si no hay líneas medibles.

    No se sabe de qué lado está el lomo (depende del libro y de cómo se
    escaneó), así que se miden los dos extremos y se toma el peor.
    """
    valores = []
    for lomo_derecha in (True, False):
        d = desvios_lomo(gris, lomo_derecha)
        if len(d) >= 3:
            valores.append(float(np.percentile(d, 90)))
    return round(max(valores), 2) if valores else None
