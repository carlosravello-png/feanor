"""Registro del entorno en que se hizo una corrida.

El aplanado depende del optimizador que use page-dewarp (con JAX, L-BFGS-B
con derivadas; sin JAX, Powell) y, en páginas difíciles, hasta de la máquina:
el mismo libro puede dar resultados distintos en dos computadoras. Por eso
cada corrida deja escrito con qué se hizo.
"""
from __future__ import annotations

import os
import platform
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
