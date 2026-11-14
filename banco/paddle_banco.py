"""Versión B del banco: las mismas muestras, leídas con PaddleOCR en lugar de Tesseract.

Solo cambia el lector. Partir pliegos y aplanar ya lo hizo aplanar-libro en
el entorno `base` (banco.py); este script, en el entorno `paddle`, toma las
páginas de esos x_plano.pdf, las lee con PaddleOCR y escribe un .md por
muestra con el mismo formato y la misma limpieza que la librería.

Uso (Anaconda Prompt, entorno paddle):
    conda activate paddle
    python D:\\PDF_A_MD\\banco\\paddle_banco.py

    python D:\\PDF_A_MD\\banco\\paddle_banco.py paddle_aplanado tolkien --umbral 0.3

Variantes (dos columnas):
    paddle_sin_aplanar    páginas partidas, sin aplanar
    paddle_aplanado       páginas aplanadas por aplanar-libro 0.4.4

El aplanador propio de PaddleOCR (UVDoc) se probó en la corrida
20261114-021926_paddle y se descartó: dejó páginas casi vacías. Sin él hay
un solo lector cargado, y la memoria de la tarjeta queda bien medida.

--umbral X  baja el umbral con que el detector acepta un renglón (por defecto
            0.6). Sirve para probar si recupera renglones inclinados que hoy
            no ve (Tolkien, página 8). Los resultados van a <variante>_umbralX.

Cada corrida va a una carpeta nueva en banco\\corridas; no sobrescribe nada.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI / "versiones" / "v0.4.4"))      # para usar la misma limpieza

import pymupdf as fitz
from aplanar_libro.markdown import AVISO, compuestos_del_documento, es_indice, limpiar

VARIANTES = {"paddle_sin_aplanar": "sin-aplanar", "paddle_aplanado": "aplanado"}


def ultima_corrida(sufijo: str) -> Path:
    """La corrida más reciente de banco.py cuyo nombre termina en `sufijo`."""
    candidatas = sorted(p for p in (AQUI / "corridas").iterdir() if p.is_dir() and p.name.endswith(sufijo))
    if not candidatas:
        sys.exit(f"No hay ninguna corrida que termine en {sufijo!r} en {AQUI / 'corridas'}")
    return candidatas[-1]


class MedidorVRAM:
    """Pregunta a nvidia-smi cada medio segundo cuánta memoria de la tarjeta está en uso."""

    def __init__(self) -> None:
        self.pico, self.base, self._seguir = 0, self._leer(), True
        self._hilo = threading.Thread(target=self._bucle, daemon=True)
        self._hilo.start()

    @staticmethod
    def _leer() -> int:
        try:
            r = subprocess.run(["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
                               capture_output=True, text=True, timeout=10)
            return int(r.stdout.strip().splitlines()[0])
        except Exception:
            return 0

    def _bucle(self) -> None:
        while self._seguir:
            self.pico = max(self.pico, self._leer())
            time.sleep(0.5)

    def parar(self) -> dict:
        self._seguir = False
        self._hilo.join(timeout=5)
        return {"vram_antes_mb": self.base, "vram_pico_mb": self.pico, **memoria_paddle()}


def memoria_paddle() -> dict:
    """Lo que Paddle usa de verdad frente a lo que tiene apartado en la tarjeta.

    nvidia-smi solo ve lo apartado. Si «usada» queda muy por debajo de
    «apartada», la tarjeta no está al límite: Paddle reserva y no suelta.
    """
    try:
        from paddle.device import cuda
        mb = 1024 * 1024
        return {"paddle_usada_pico_mb": round(cuda.max_memory_allocated() / mb),
                "paddle_apartada_pico_mb": round(cuda.max_memory_reserved() / mb)}
    except Exception:
        return {}


def exportar_paginas(pdf: Path, carpeta: Path) -> list[Path]:
    """Saca de x_plano.pdf la imagen de cada página, tal cual, a un PNG."""
    carpeta.mkdir(parents=True, exist_ok=True)
    doc, rutas = fitz.open(pdf), []
    for i, pagina in enumerate(doc, start=1):
        png = carpeta / f"p{i:04d}.png"
        imagenes = pagina.get_images()
        if imagenes:
            fitz.Pixmap(doc, imagenes[0][0]).save(png)
        else:
            pagina.get_pixmap(dpi=200).save(png)
        rutas.append(png)
    return rutas


def ordenar(textos: list[str], cajas: list[list[float]], ancho: float) -> list[str]:
    """Orden de lectura de los renglones que devuelve PaddleOCR.

    Una columna: de arriba abajo. Dos columnas (el Tizard): si hay bastantes
    renglones angostos a cada lado del centro, se lee la columna izquierda y
    después la derecha; los renglones que cruzan el centro van con la izquierda.
    """
    filas = [(c[0], c[1], c[2], c[3], t) for t, c in zip(textos, cajas) if t.strip()]
    if not filas:
        return []
    angostas = [f for f in filas if (f[2] - f[0]) < 0.6 * ancho]
    izq = [f for f in angostas if f[2] < 0.52 * ancho]
    der = [f for f in angostas if f[0] > 0.48 * ancho]
    dos_columnas = len(izq) >= 0.3 * len(filas) and len(der) >= 0.3 * len(filas)
    if dos_columnas:
        derecha = sorted(der, key=lambda f: (f[1], f[0]))
        resto = sorted([f for f in filas if f not in der], key=lambda f: (f[1], f[0]))
        filas = resto + derecha
    else:
        filas = sorted(filas, key=lambda f: (f[1], f[0]))
    return [f[4] for f in filas]


def crear_lector(umbral: float | None = None):
    if os.environ.get("PRUEBA_SIN_PADDLE"):           # solo para probar el script sin PaddleOCR
        return None
    from paddleocr import PaddleOCR
    extra = {"text_det_box_thresh": umbral} if umbral is not None else {}
    return PaddleOCR(lang="es", device="gpu:0", use_doc_orientation_classify=False,
                     use_doc_unwarping=False, use_textline_orientation=False, **extra)


def leer_pagina(lector, png: Path, carpeta_json: Path) -> dict:
    """Lee una página y devuelve el resultado que PaddleOCR guarda en JSON."""
    carpeta_json.mkdir(parents=True, exist_ok=True)
    destino = carpeta_json / f"{png.stem}_res.json"
    if lector is None:                                 # modo de prueba: Tesseract hace de lector
        r = subprocess.run(["tesseract", str(png), "-", "-l", "spa", "--psm", "6", "tsv"],
                           capture_output=True, text=True)
        lineas: dict[tuple, list] = {}
        for fila in r.stdout.splitlines()[1:]:
            c = fila.split("\t")
            if len(c) == 12 and c[11].strip():
                lineas.setdefault((c[2], c[3], c[4]), []).append(c)
        datos = {"rec_texts": [" ".join(c[11] for c in v) for v in lineas.values()],
                 "rec_boxes": [[int(v[0][6]), int(v[0][7]), int(v[-1][6]) + int(v[-1][8]), int(v[0][7]) + int(v[0][9])]
                               for v in lineas.values()],
                 "rec_scores": [0.9] * len(lineas)}
        destino.write_text(json.dumps(datos), encoding="utf-8")
        return datos
    for res in lector.predict(str(png)):
        res.save_to_json(str(carpeta_json))
    return json.loads(destino.read_text(encoding="utf-8"))


def main() -> None:
    args, umbral = sys.argv[1:], None
    if "--umbral" in args:
        i = args.index("--umbral")
        umbral = float(args[i + 1])
        del args[i:i + 2]
    pedido = [a for a in args if not a.startswith("--")]
    variantes = pedido[0].split(",") if pedido else list(VARIANTES)
    solo = pedido[1].split(",") if len(pedido) > 1 else None
    fuentes = {"sin-aplanar": ultima_corrida("_v0.4.4-sin-aplanar"), "aplanado": ultima_corrida("_v0.4.4")}
    muestras = json.loads((AQUI / "muestras.json").read_text(encoding="utf-8"))["muestras"]
    corrida = AQUI / "corridas" / f"{datetime.now():%Y%m%d-%H%M%S}_paddle"
    corrida.mkdir(parents=True)
    print(f"Banco con PaddleOCR. Resultados en {corrida}")
    for clave, ruta in fuentes.items():
        print(f"  páginas {clave}: {ruta.name}")
    resumen: dict = {"fuentes": {k: v.name for k, v in fuentes.items()}, "umbral_detector": umbral}
    try:
        import paddle, paddleocr
        resumen["entorno"] = {"paddle": paddle.__version__, "paddleocr": paddleocr.__version__,
                              "python": sys.version.split()[0]}
    except Exception:
        resumen["entorno"] = {"python": sys.version.split()[0]}
    print("  cargando PaddleOCR (un solo lector)…", flush=True)
    lector = crear_lector(umbral)
    for base in variantes:
        fuente = VARIANTES[base]
        variante = base if umbral is None else f"{base}_umbral{umbral:g}"
        resumen[variante] = {}
        for m in muestras:
            if solo and m["nombre"] not in solo:
                continue
            origen = fuentes[fuente] / m["nombre"]
            if not (origen / "x_plano.pdf").exists():
                print(f"  {variante} / {m['nombre']}: falta {origen / 'x_plano.pdf'}")
                continue
            salida = corrida / variante / m["nombre"]
            paginas = exportar_paginas(origen / "x_plano.pdf", salida / "paginas")
            informe = json.loads((origen / "x_informe.json").read_text(encoding="utf-8"))
            (salida / "x_informe.json").write_text(json.dumps(informe, ensure_ascii=False, indent=1), encoding="utf-8")
            medidor, textos, por_pagina = MedidorVRAM(), [], []
            for png in paginas:
                t = time.perf_counter()
                try:
                    datos = leer_pagina(lector, png, salida / "json")
                    ancho = fitz.Pixmap(str(png)).width
                    renglones = ordenar(datos.get("rec_texts", []), datos.get("rec_boxes", []), ancho)
                    notas = datos.get("rec_scores", [])
                    error = None
                except Exception as e:                 # una página que falla no tumba la corrida
                    renglones, notas, error = [], [], f"{type(e).__name__}: {str(e)[:120]}"
                textos.append("\n".join(renglones))
                por_pagina.append({"pagina": len(textos), "segundos": round(time.perf_counter() - t, 2),
                                   "renglones": len(renglones),
                                   "confianza_media": round(sum(notas) / len(notas), 3) if notas else None,
                                   "renglones_bajo_0.8": sum(n < 0.8 for n in notas), "error": error})
            vram = medidor.parar()
            documento = compuestos_del_documento("\n".join(textos))
            partes = [f"<!-- Texto leído con PaddleOCR ({variante}) de: {m['nombre']} -->", AVISO, ""]
            for i, texto in enumerate(textos, start=1):
                partes += [f"<!-- página {i} del visor -->", "",
                           texto.strip() if es_indice(texto) else limpiar(texto, documento), ""]
            (salida / "x_ocr.md").write_text("\n".join(partes), encoding="utf-8")
            palabras = len(re.findall(r"[a-záéíóúñü]{2,}", "\n".join(textos)))
            segundos = sum(p["segundos"] for p in por_pagina)
            resumen[variante][m["nombre"]] = {
                "paginas": len(paginas), "palabras": palabras, "segundos": round(segundos, 1),
                "segundos_por_pagina": round(segundos / max(len(paginas), 1), 2),
                "errores": [p for p in por_pagina if p["error"]], **vram, "por_pagina": por_pagina}
            print(f"  {variante} / {m['nombre']}: {len(paginas)} páginas, {palabras} palabras, "
                  f"{segundos:.0f} s ({segundos / max(len(paginas), 1):.1f} s por página), "
                  f"VRAM pico {vram['vram_pico_mb']} MB (Paddle usa {vram.get('paddle_usada_pico_mb', '?')} MB), {len(resumen[variante][m['nombre']]['errores'])} errores", flush=True)
            (corrida / "resumen.json").write_text(json.dumps(resumen, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Listo. Resumen: {corrida / 'resumen.json'}")


if __name__ == "__main__":
    main()
