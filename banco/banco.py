"""Banco de pruebas fijo de Feanor (hasta la 0.5.5, aplanar-libro).

Uso (Anaconda Prompt):
    python D:\\PDF_A_MD\\banco\\banco.py v0.4.4
    python D:\\PDF_A_MD\\banco\\banco.py v0.4.4 --sin-aplanar

Con --sin-aplanar solo se parten los pliegos y se iguala la luz, sin aplanar
ni leer: deja en cada muestra un x_plano.pdf con las páginas tal como
vienen, para dárselas a otro lector (ver paddle_banco.py).

Corre las mismas muestras (muestras.json) con la versión de la librería que
está en banco\\versiones\\<versión>, sin tocar la que está instalada. Cada
corrida va a una carpeta nueva dentro de banco\\corridas y no sobrescribe
nada. Al final escribe resumen.json y una tabla en pantalla.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

AQUI = Path(__file__).resolve().parent
LIBROS = AQUI.parent


def armar_muestra(m: dict) -> Path:
    """PDF con las páginas de la muestra, sacadas del libro completo."""
    import pymupdf as fitz
    destino = AQUI / "muestras" / f"{m['nombre']}.pdf"
    if destino.exists():
        return destino
    destino.parent.mkdir(exist_ok=True)
    libro = fitz.open(LIBROS / m["pdf"])
    paginas = range(1, len(libro) + 1) if m["paginas"] == "todas" else m["paginas"]
    nuevo = fitz.open()
    for p in paginas:
        nuevo.insert_pdf(libro, from_page=p - 1, to_page=p - 1)
    nuevo.save(destino)
    return destino


def paginas_del_md(md: str) -> dict[int, str]:
    trozos = re.split(r"<!-- página (\d+) del visor -->", md)[1:]
    return {int(trozos[k]): trozos[k + 1] for k in range(0, len(trozos), 2)}


def sin_comentarios(bloque: str) -> str:
    return re.sub(r"<!--.*?-->", "", bloque, flags=re.S).strip()


def medir(carpeta: Path, m: dict) -> dict:
    informe = json.loads((carpeta / "x_informe.json").read_text(encoding="utf-8"))
    paginas = informe["paginas"] if isinstance(informe, dict) else informe
    md = paginas_del_md((carpeta / "x_ocr.md").read_text(encoding="utf-8"))
    tiempos = json.loads((carpeta / "x_tiempos.json").read_text(encoding="utf-8"))
    texto = " ".join(sin_comentarios(b) for b in md.values())
    palabras = re.findall(r"[a-záéíóúñü]{2,}", texto)
    try:
        from wordfreq import zipf_frequency
        validas = sum(zipf_frequency(w, "es") > 0 for w in palabras)
    except ImportError:
        validas = None                      # sin wordfreq: lo calcula quien lea el .md
    no_cuadran = [n for n, b in md.items()
                  if len(sin_comentarios(b).split()) < paginas[n - 1]["lineas"] and "REVISAR A MANO" not in b]
    return {
        "descripcion": m["descripcion"],
        "paginas": len(paginas),
        "aplanadas": sum(p["aplanada"] for p in paginas),
        "devueltas_por_lectura": [(p["origen"], p["parte"]) for p in paginas if "se lee peor" in p["motivo"]],
        "descartadas_por_tamano": [(p["origen"], p["parte"]) for p in paginas if "tamaño absurdo" in p["motivo"]],
        "errores_de_memoria": [(p["origen"], p["parte"]) for p in paginas if "MemoryError" in p["motivo"]],
        "marcadas_revisar": sum("REVISAR A MANO" in b for b in md.values()),
        "palabras": len(palabras),
        "validas": validas,
        "no_cuadran_sin_aviso": no_cuadran,
        "escalas": [(p["origen"], p["parte"], p.get("escala_alto"), p.get("escala_ancho"),
                     p["aplanada"], p.get("lectura_original"), p.get("lectura_aplanada")) for p in paginas],
        "segundos": tiempos["segundos"],
        "procesos": tiempos.get("procesos"),
        "entorno": tiempos.get("entorno") or (informe.get("entorno") if isinstance(informe, dict) else None),
    }


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit("Falta la versión. Ejemplo: python banco.py v0.4.4")
    version = sys.argv[1]
    codigo = AQUI / "versiones" / version
    # Desde la 0.6.0 el paquete se llama feanor_el_aplasta_libros; las copias de
    # versiones anteriores guardadas en versiones\ conservan aplanar_libro.
    paquete = next((n for n in ("feanor_el_aplasta_libros", "aplanar_libro")
                    if (codigo / n).is_dir()), None)
    if paquete is None:
        sys.exit(f"No existe {codigo}\\feanor_el_aplasta_libros ni {codigo}\\aplanar_libro")
    muestras = json.loads((AQUI / "muestras.json").read_text(encoding="utf-8"))["muestras"]
    sin_aplanar = "--sin-aplanar" in sys.argv
    otros = [x for x in sys.argv[2:] if not x.startswith("--")]
    solo = otros[0].split(",") if otros else None
    # Comprobar que Python va a usar la versión pedida y no la instalada.
    entorno = {**os.environ, "PYTHONPATH": str(codigo), "PYTHONIOENCODING": "utf-8"}
    r = subprocess.run([sys.executable, "-c", f"import {paquete}; print({paquete}.__file__)"],
                       capture_output=True, text=True, env=entorno)
    usada = Path(r.stdout.strip() or ".").resolve()
    if codigo.resolve() not in usada.parents:
        sys.exit(f"Python no está usando {codigo}, sino {usada}. No se corre nada.")
    corrida = AQUI / "corridas" / (f"{datetime.now():%Y%m%d-%H%M%S}_{version}"
                                   + ("-sin-aplanar" if sin_aplanar else ""))
    corrida.mkdir(parents=True)                       # carpeta nueva: nunca se sobrescribe
    print(f"Banco con {version}. Resultados en {corrida}")
    resumen, inicio = {}, time.perf_counter()
    for m in muestras:
        if solo and m["nombre"] not in solo:
            continue
        pdf = armar_muestra(m)
        carpeta = corrida / m["nombre"]
        carpeta.mkdir()
        (carpeta / "x.pdf").write_bytes(pdf.read_bytes())
        print(f"  {m['nombre']}: corriendo…", flush=True)
        t = time.perf_counter()
        with open(carpeta / "consola.txt", "w", encoding="utf-8") as consola:
            extra = ["--solo", "aplanar", "--paginas", "0"] if sin_aplanar else []
            r = subprocess.run([sys.executable, "-m", paquete, "x.pdf", "--modo", m["modo"]] + extra,
                               cwd=carpeta, stdout=consola, stderr=subprocess.STDOUT,
                               env=entorno)
        if sin_aplanar:
            listo = r.returncode == 0 and (carpeta / "x_plano.pdf").exists()
            resumen[m["nombre"]] = {"sin_aplanar": True, "ok": listo}
            print(f"  {m['nombre']}: {'pliegos partidos, sin aplanar' if listo else 'FALLÓ (ver consola.txt)'}, "
                  f"{time.perf_counter() - t:.0f} s")
            continue
        if r.returncode != 0 or not (carpeta / "x_ocr.md").exists():
            resumen[m["nombre"]] = {"error": f"la corrida falló; ver {carpeta / 'consola.txt'}"}
            print(f"  {m['nombre']}: FALLÓ (ver consola.txt)")
            continue
        resumen[m["nombre"]] = medir(carpeta, m)
        s = resumen[m["nombre"]]
        print(f"  {m['nombre']}: {s['paginas']} páginas, {s['aplanadas']} aplanadas, "
              f"{len(s['devueltas_por_lectura'])} devueltas, {len(s['descartadas_por_tamano'])} descartadas por tamaño, "
              f"{s['marcadas_revisar']} para revisar, {s['palabras']} palabras, {time.perf_counter() - t:.0f} s")
    (corrida / "resumen.json").write_text(json.dumps(resumen, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Listo. Tiempo total del banco: {(time.perf_counter() - inicio) / 60:.1f} min")
    print(f"Resumen: {corrida / 'resumen.json'}")


if __name__ == "__main__":
    main()
