"""Paso 2: leer el texto (OCR) con OCRmyPDF y Tesseract.

No reimplementa nada: llama a OCRmyPDF (https://github.com/ocrmypdf/OCRmyPDF),
que usa Tesseract (https://github.com/tesseract-ocr/tesseract). Lo que aporta
esta librería es la configuración que funcionó en pruebas con libros en español:

- Un solo idioma. Mezclar `spa+eng` hizo perder cerca del 40 % de las tildes y eñes;
  con `spa` volvieron todas.
- `--rotate-pages`: endereza las páginas giradas (necesita el archivo
  `osd.traineddata` de Tesseract; si no está, se lee sin girar y se avisa).
- Modo de página 6 ("un solo bloque de texto") para páginas de libro. Evita que
  Tesseract parta las líneas como si hubiera dos columnas. No conviene en
  documentos que sí tienen columnas (artículos científicos): usar `modo="auto"`.
"""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

MODOS = {"libro": "6", "auto": None}


def encontrar_ocrmypdf() -> str:
    """Busca el ejecutable de OCRmyPDF en el PATH y en la carpeta de `uv tool`."""
    en_path = shutil.which("ocrmypdf")
    if en_path:
        return en_path
    candidato = Path(os.path.expanduser("~")) / ".local" / "bin" / "ocrmypdf.exe"
    if candidato.exists():
        return str(candidato)
    raise FileNotFoundError(
        "No encuentro ocrmypdf. Instálalo con `uv tool install ocrmypdf` "
        "y corre `uv tool update-shell`."
    )


def leer_pdf(entrada: Path, salida: Path, idioma: str = "spa", modo: str = "libro",
             forzar: bool = False) -> None:
    """Pasa OCR a `entrada` y escribe un PDF con capa de texto en `salida`.

    `forzar=True` vuelve a leer páginas que ya tenían texto (útil para pruebas).
    """
    if modo not in MODOS:
        raise ValueError(f"modo debe ser uno de {list(MODOS)}")
    cmd = [encontrar_ocrmypdf(), "-l", idioma]
    if MODOS[modo]:
        cmd += ["--tesseract-pagesegmode", MODOS[modo]]
    cmd += ["--force-ocr"] if forzar else ["--skip-text"]
    con_giro = cmd + ["--rotate-pages", str(entrada), str(salida)]
    print("  " + " ".join(con_giro))
    r = subprocess.run(con_giro)
    if r.returncode != 0:
        print("  OCRmyPDF falló con --rotate-pages (¿falta osd.traineddata?). "
              "Se lee de nuevo sin enderezar páginas giradas.")
        subprocess.run(cmd + [str(entrada), str(salida)], check=True)


TIPO_DE_SALIDA = "pdf"


def ocr_paginas(entrada: Path, salida: Path, paginas: list[int], idioma: str = "spa",
                tipo_salida: str = TIPO_DE_SALIDA) -> list[str]:
    """OCR sin aplanar de las páginas indicadas, y solo de ellas (modo lote).

    --force-ocr: cada página indicada se convierte en imagen y se lee entera,
    aunque traiga algo de texto encima (un sello del repositorio): con
    --skip-text esa página se saltaba y no se leía. Las demás páginas pasan
    tal cual. Segmentación automática de Tesseract (sin --tesseract-pagesegmode).

    --output-type pdf (desde la 0.5.5): con el valor por defecto de OCRmyPDF
    («auto», PDF/A) el archivo se convierte con Ghostscript, que reescribía el
    texto de páginas que no se pidieron (en la calibración: espacios, viñetas,
    fórmulas y la capa de un OCR previo). «pdf» minimiza los cambios. La
    comprobación de páginas alteradas sigue igual.

    Devuelve el comando EXACTO que terminó bien, para guardarlo en el registro.
    """
    lista = ",".join(str(p) for p in sorted(paginas))
    base = [encontrar_ocrmypdf(), "-l", idioma, "--force-ocr", "--output-type", tipo_salida, "--pages", lista]
    con_giro = base + ["--rotate-pages", str(entrada), str(salida)]
    print("  " + " ".join(con_giro))
    if subprocess.run(con_giro).returncode == 0:
        return con_giro
    print("  OCRmyPDF falló con --rotate-pages (¿falta osd.traineddata?). Se lee sin enderezar páginas giradas.")
    sin_giro = base + [str(entrada), str(salida)]
    subprocess.run(sin_giro, check=True)
    return sin_giro
