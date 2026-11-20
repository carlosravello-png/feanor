"""Registro del entorno en que se hizo una corrida.

El aplanado depende del optimizador que use page-dewarp (con JAX, L-BFGS-B
con derivadas; sin JAX, Powell) y, en páginas difíciles, hasta de la máquina:
el mismo libro puede dar resultados distintos en dos computadoras. Por eso
cada corrida deja escrito con qué se hizo.
"""
from __future__ import annotations

import hashlib
import os
import platform
import re
import shutil
import subprocess
from importlib import metadata
from pathlib import Path


def _version(paquete: str) -> str | None:
    try:
        return metadata.version(paquete)
    except metadata.PackageNotFoundError:
        return None


def ruta_tesseract() -> str | None:
    """Ruta de Tesseract: en el PATH o en su carpeta habitual de Windows."""
    ruta = shutil.which("tesseract")
    if ruta:
        return ruta
    habitual = Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe")
    return str(habitual) if habitual.exists() else None


def _version_tesseract() -> str | None:
    exe = ruta_tesseract()
    if exe is None:
        return None
    try:
        r = subprocess.run([exe, "--version"], capture_output=True, text=True, timeout=30)
    except Exception:
        return None
    lineas = (r.stdout or r.stderr).splitlines()
    return lineas[0].strip() if lineas else None


def _primera_linea(cmd: list[str]) -> str | None:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    except Exception:
        return None
    lineas = (r.stdout or r.stderr).splitlines()
    return lineas[0].strip() if lineas else None


def _version_ocrmypdf() -> str | None:
    from .leer import encontrar_ocrmypdf
    try:
        exe = encontrar_ocrmypdf()
    except FileNotFoundError:
        return None
    return _primera_linea([exe, "--version"])


def _version_ghostscript() -> str | None:
    """Versión de Ghostscript. En Windows suele no estar en el PATH (OCRmyPDF lo
    busca por su cuenta), así que se mira también en C:\\Program Files\\gs."""
    candidatos = [shutil.which(exe) for exe in ("gswin64c", "gswin32c", "gs")]
    candidatos += sorted(str(p) for p in Path(r"C:\Program Files\gs").glob("*/bin/gswin64c.exe"))[::-1]
    for ruta in filter(None, candidatos):
        v = _primera_linea([ruta, "--version"])
        if v:
            return f"{v} ({ruta})"
    return None


def _sha256(ruta: Path) -> str:
    h = hashlib.sha256()
    with open(ruta, "rb") as f:
        for bloque in iter(lambda: f.read(1 << 20), b""):
            h.update(bloque)
    return h.hexdigest()


def modelo_tesseract(idioma: str = "spa") -> dict | None:
    """El archivo de modelo que usa Tesseract para ese idioma: carpeta, tamaño y
    SHA-256. Dos modelos con el mismo nombre (tessdata, tessdata_fast,
    tessdata_best) dan textos distintos; el hash dice cuál fue."""
    exe = ruta_tesseract()
    if exe is None:
        return None
    carpeta = os.environ.get("TESSDATA_PREFIX")
    if not carpeta:
        try:
            r = subprocess.run([exe, "--list-langs"], capture_output=True, text=True, timeout=30)
            m = re.search(r'"(.+?)"', r.stdout + r.stderr)
            carpeta = m.group(1) if m else None
        except Exception:
            carpeta = None
    if not carpeta:
        return {"idioma": idioma, "archivo": None}
    archivo = Path(carpeta) / f"{idioma}.traineddata"
    if not archivo.exists():
        return {"idioma": idioma, "archivo": str(archivo), "existe": False}
    return {"idioma": idioma, "archivo": str(archivo), "bytes": archivo.stat().st_size,
            "sha256": _sha256(archivo)}


def commit_feanor() -> dict:
    """Commit de git del código que corre, si es una copia de trabajo del repo.
    «sucio» = hay cambios sin commitear: el resultado no es reproducible desde
    ese commit."""
    raiz = Path(__file__).resolve().parent.parent
    try:
        c = subprocess.run(["git", "-C", str(raiz), "rev-parse", "HEAD"],
                           capture_output=True, text=True, timeout=30)
        if c.returncode != 0:
            return {"commit": None}
        e = subprocess.run(["git", "-C", str(raiz), "status", "--porcelain", "--untracked-files=no"],
                           capture_output=True, text=True, timeout=30)
        return {"commit": c.stdout.strip(), "sucio": bool(e.stdout.strip())}
    except Exception:
        return {"commit": None}


def entorno_ocr(idioma: str = "spa") -> dict:
    """Lo que hace falta para repetir una lectura: Feanor y su commit, y las
    versiones de las herramientas de OCR con el modelo del idioma. No carga
    page-dewarp ni JAX, así que sirve también para la ruta digital."""
    from . import __version__
    return {
        "feanor": __version__,
        **commit_feanor(),
        "pymupdf": _version("pymupdf"),
        "tesseract": _version_tesseract(),
        "modelo_tesseract": modelo_tesseract(idioma),
        "ocrmypdf": _version_ocrmypdf(),
        "ghostscript": _version_ghostscript(),
        "python": platform.python_version(),
        "sistema": platform.platform(),
    }


def optimizador() -> str:
    """Qué optimizador usará page-dewarp en esta máquina."""
    from page_dewarp.backends import HAS_JAX, get_default_method
    from page_dewarp.options import Config

    metodo = Config().OPT_METHOD
    if metodo == "auto":
        metodo = get_default_method()
    return f"{metodo} (JAX)" if HAS_JAX and metodo == "L-BFGS-B" else f"{metodo} (SciPy)"


def entorno() -> dict:
    """Versiones y máquina de esta corrida, para escribir en los informes."""
    from . import __version__

    return {
        "aplanar_libro": __version__,
        "optimizador": optimizador(),
        "jax": _version("jax"),
        "numpy": _version("numpy"),
        "scipy": _version("scipy"),
        "opencv": _version("opencv-python-headless") or _version("opencv-python"),
        "pymupdf": _version("pymupdf"),
        "page_dewarp": _version("page-dewarp"),
        "tesseract": _version_tesseract(),
        "python": platform.python_version(),
        "sistema": platform.platform(),
        "procesador": platform.machine(),
        "nucleos_logicos": os.cpu_count(),
    }
