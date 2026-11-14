"""Paso 2: leer el texto (OCR) con OCRmyPDF y Tesseract.

No reimplementa nada: llama a OCRmyPDF (https://github.com/ocrmypdf/OCRmyPDF),
que usa Tesseract (https://github.com/tesseract-ocr/tesseract). Lo que aporta
esta librería es la configuración que funcionó en pruebas con libros en español:

- Un solo idioma. Mezclar `spa+eng` hizo perder cerca del 40 % de las tildes y eñes;
  con `spa` volvieron todas.
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
    cmd += [str(entrada), str(salida)]
    print("  " + " ".join(cmd))
    subprocess.run(cmd, check=True)
