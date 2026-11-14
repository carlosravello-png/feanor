"""Medición de PP-StructureV3 en el banco: ¿cabe en la tarjeta y qué entrega?

PP-StructureV3 no solo lee: detecta la disposición de la página (títulos,
párrafos, tablas, figuras, pies de figura) y entrega Markdown en orden de
lectura. Este script lo corre sobre las mismas páginas aplanadas del banco
y guarda tiempos, memoria de la tarjeta y cuántos bloques de cada tipo vio.

Uso (Anaconda Prompt, entorno paddle_struct):
    conda activate paddle_struct
    python D:\\PDF_A_MD\\banco\\structure_banco.py problema
    python D:\\PDF_A_MD\\banco\\structure_banco.py                (las cuatro muestras)
    python D:\\PDF_A_MD\\banco\\structure_banco.py problema --completo

Por defecto va sin fórmulas, gráficos ni sellos (lo más pesado y lo que estos
libros no necesitan). --completo los enciende.
Cada corrida va a una carpeta nueva en banco\\corridas; no sobrescribe nada.
"""
from __future__ import annotations

import json
import sys
import time
from collections import Counter
from datetime import datetime
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))

from paddle_banco import AQUI as _, MedidorVRAM, exportar_paginas, ultima_corrida  # noqa: E402


def etiquetas(dato) -> Counter:
    """Cuenta los bloques por tipo, estén donde estén dentro del JSON."""
    cuenta: Counter = Counter()
    if isinstance(dato, dict):
        for clave, valor in dato.items():
            if clave in ("block_label", "label") and isinstance(valor, str):
                cuenta[valor] += 1
            else:
                cuenta += etiquetas(valor)
    elif isinstance(dato, list):
        for valor in dato:
            cuenta += etiquetas(valor)
    return cuenta


def main() -> None:
    args = sys.argv[1:]
    completo = "--completo" in args
    pedido = [a for a in args if not a.startswith("--")]
    solo = pedido[0].split(",") if pedido else None
    fuente = ultima_corrida("_v0.4.4")
    muestras = json.loads((AQUI / "muestras.json").read_text(encoding="utf-8"))["muestras"]
    corrida = AQUI / "corridas" / f"{datetime.now():%Y%m%d-%H%M%S}_structure{'-completo' if completo else ''}"
    corrida.mkdir(parents=True)
    print(f"Banco con PP-StructureV3 ({'completo' if completo else 'sin fórmulas, gráficos ni sellos'}).")
    print(f"  páginas aplanadas: {fuente.name}\n  resultados en {corrida}")

    import paddle
    import paddleocr
    from paddleocr import PPStructureV3
    opciones = dict(lang="es", device="gpu:0", use_doc_orientation_classify=False,
                    use_doc_unwarping=False, use_textline_orientation=False)
    if not completo:
        opciones.update(use_formula_recognition=False, use_chart_recognition=False, use_seal_recognition=False)
    resumen: dict = {"fuente": fuente.name, "opciones": opciones,
                     "entorno": {"paddle": paddle.__version__, "paddleocr": paddleocr.__version__,
                                 "python": sys.version.split()[0]}}
    print("  cargando PP-StructureV3 (la primera vez descarga modelos)…", flush=True)
    carga = MedidorVRAM()
    t0 = time.perf_counter()
    lector = PPStructureV3(**opciones)
    resumen["carga"] = {"segundos": round(time.perf_counter() - t0, 1), **carga.parar()}
    print(f"  cargado en {resumen['carga']['segundos']} s, VRAM {resumen['carga']['vram_pico_mb']} MB", flush=True)

    for m in muestras:
        if solo and m["nombre"] not in solo:
            continue
        origen = fuente / m["nombre"]
        if not (origen / "x_plano.pdf").exists():
            print(f"  {m['nombre']}: falta {origen / 'x_plano.pdf'}")
            continue
        salida = corrida / m["nombre"]
        paginas = exportar_paginas(origen / "x_plano.pdf", salida / "paginas")
        medidor, partes, por_pagina, total = MedidorVRAM(), [], [], Counter()
        for i, png in enumerate(paginas, start=1):
            t = time.perf_counter()
            texto, bloques, error = "", Counter(), None
            try:
                for res in lector.predict(str(png)):
                    res.save_to_json(save_path=str(salida / "json"))
                    res.save_to_markdown(save_path=str(salida / "md"))
                hechos = sorted((salida / "md").glob(f"{png.stem}*.md"))
                texto = "\n\n".join(h.read_text(encoding="utf-8") for h in hechos)
                for j in sorted((salida / "json").glob(f"{png.stem}*.json")):
                    bloques += etiquetas(json.loads(j.read_text(encoding="utf-8")))
            except Exception as e:                     # una página que falla no tumba la corrida
                error = f"{type(e).__name__}: {str(e)[:200]}"
                print(f"    página {i}: {error}", flush=True)
            total += bloques
            partes += [f"<!-- página {i} del visor -->", "", texto.strip(), ""]
            por_pagina.append({"pagina": i, "segundos": round(time.perf_counter() - t, 2),
                               "caracteres": len(texto), "bloques": dict(bloques), "error": error})
        vram = medidor.parar()
        (salida / "x_ocr.md").write_text("\n".join(partes), encoding="utf-8")
        segundos = sum(p["segundos"] for p in por_pagina)
        resumen[m["nombre"]] = {"paginas": len(paginas), "segundos": round(segundos, 1),
                                "segundos_por_pagina": round(segundos / max(len(paginas), 1), 2),
                                "bloques": dict(total), "errores": [p for p in por_pagina if p["error"]],
                                **vram, "por_pagina": por_pagina}
        print(f"  {m['nombre']}: {len(paginas)} páginas, {segundos:.0f} s "
              f"({segundos / max(len(paginas), 1):.1f} s por página), VRAM pico {vram['vram_pico_mb']} MB "
              f"(Paddle usa {vram.get('paddle_usada_pico_mb', '?')} MB), "
              f"{len(resumen[m['nombre']]['errores'])} errores\n    bloques: {dict(total)}", flush=True)
        (corrida / "resumen.json").write_text(json.dumps(resumen, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Listo. Resumen: {corrida / 'resumen.json'}")


if __name__ == "__main__":
    main()
