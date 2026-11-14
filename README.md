# aplanar-libro

Rescata el texto de libros escaneados o fotografiados en español, incluidas las páginas que se curvan hacia el lomo, y lo deja en Markdown listo para trabajar.

Hace tres pasos en fila:

1. **Aplanar**: endereza las páginas curvas antes del OCR.
2. **Leer**: pasa OCR con la configuración que funciona para el español.
3. **Markdown**: escribe el texto página por página, con el número del visor y avisos en las páginas que hay que revisar a mano.

## Créditos

Esta librería no hace OCR ni inventa el aplanado. Se apoya en:

- **[page-dewarp](https://github.com/lmmx/page-dewarp)** (licencia MIT), de Louis Maddox, sobre el método de [Matt Zucker (2016)](https://github.com/mzucker/page_dewarp). Hace el aplanado. Se usa como dependencia, sin copiar su código.
- **[OCRmyPDF](https://github.com/ocrmypdf/OCRmyPDF)** (MPL-2.0) y **[Tesseract](https://github.com/tesseract-ocr/tesseract)** (Apache-2.0). Hacen el OCR. Se llaman como programas externos.
- **[PyMuPDF](https://github.com/pymupdf/PyMuPDF)** para leer y escribir PDF, y **[OpenCV](https://opencv.org/)** para el recorte.

Lo que aporta `aplanar-libro`:
- El flujo completo.
- El recorte automático de la página aplanada.
- La corrección del recuadro de page-dewarp, que cortaba el final de las líneas junto al lomo.
- La regla que deja sin aplanar las páginas con poco texto.
- La configuración de OCR probada con libros en español.
- Las marcas de revisión en el Markdown.

## Cómo se hizo

Autor: Carlos Eduardo Ravello Joo ([ORCID 0009-0007-5631-7436](https://orcid.org/0009-0007-5631-7436)). El autor definió el problema, dirigió el desarrollo y validó los resultados con material real. Se usó Claude (Anthropic) como asistente de programación.

## Lo que se midió

Pruebas del 13/11/2026 con un libro fotografiado con el celular (14 páginas; el libro tiene derechos de autor y no se incluye en el repositorio):

- **Páginas planas:** el OCR sale casi perfecto sin aplanar.
- **Páginas curvas hacia el lomo:** sin aplanar, el OCR es inservible (letras sueltas, líneas partidas). Aplanadas y leídas en modo libro, seis de siete quedaron legibles y en orden. En la página revisada a mano, cerca del 97 % de las palabras salieron correctas.
- **Idioma:** con `-l spa+eng` se perdió cerca del 40 % de las tildes y eñes; con `-l spa` volvieron todas (prueba sobre un PDF tipeado leído como imagen).
- **Una página con poco texto (un índice):** no se pudo aplanar. La librería la deja como está y la marca para revisión.

## Instalación (Windows, Anaconda Prompt)

Requisitos externos (una vez):

```
winget install -e --id tesseract-ocr.tesseract
winget install -e --id astral-sh.uv
uv tool install ocrmypdf
uv tool update-shell
```

- **Ghostscript (64 bits, licencia AGPL):** se instala a mano desde [ghostscript.com](https://ghostscript.com/releases/gsdnld.html).
- **Idioma español:** si `C:\Program Files\Tesseract-OCR\tessdata\spa.traineddata` no existe, bájalo de [tesseract-ocr/tessdata](https://github.com/tesseract-ocr/tessdata) y cópialo ahí. Hacen falta permisos de administrador.

La librería:

```
python -m pip install git+https://github.com/carlosravello-png/aplanar-libro.git
```

## Uso

```
aplanar-libro "libro.pdf"
```

Deja al lado del original:

| Archivo | Para qué |
|---|---|
| `libro_plano.pdf` | Las páginas aplanadas, como imágenes |
| `libro_ocr.pdf` | El PDF con texto seleccionable. Es el que se usa para verificar folios |
| `libro_ocr.md` | El texto en Markdown, para trabajar. Cada página lleva el número del visor y, si se pudo deducir, el folio impreso del libro. En el cuerpo del libro se quita el ruido de la sombra del lomo y los folios, y se unen las palabras cortadas con guion. Las páginas tipo índice quedan sin limpiar |
| `libro_informe.json` | Qué páginas se aplanaron y por qué no las demás |

Opciones:

```
aplanar-libro "libro.pdf" --paginas pares        # aplanar solo las pares (o: impares, o 2,4,6)
aplanar-libro "libro.pdf" --solo aplanar         # un solo paso: aplanar | leer | markdown
aplanar-libro "articulo.pdf" --modo auto         # documentos a dos columnas
aplanar-libro "book.pdf" --idioma eng            # otro idioma (uno solo, no mezclar)
aplanar-libro "libro.pdf" --nucleos 4            # páginas que se aplanan a la vez (por defecto: núcleos − 1, máx. 8)
```

## Límites conocidos

- **Curva muy cerrada junto al lomo:** el aplanado puede dejar las primeras líneas todavía un poco curvas, y entonces se pierde alguna palabra al final. Desde la versión 0.2.0 la librería mide ese resto de curva y marca la página con «REVISAR A MANO». En las 14 páginas de prueba marcó las tres malas y dio una falsa alarma. El umbral es provisional: ver [CALIBRACION.md](CALIBRACION.md).
- **Errores sin curva:** una página que sale mal por sombra o por baja resolución, con las líneas rectas, no se marca.
- **Páginas con poco texto** (índices, portadas, páginas con figuras): no se aplanan.
- **Índices:** es lo que peor sale. El OCR separa cada título de su número y lee mal los números romanos. La librería detecta las páginas tipo índice, no las limpia y las marca siempre con «REVISAR A MANO».
- **Nombres con guion propio** («Gil-galad»): se conservan solo si en algún lugar del libro aparecen a mitad de línea. Si el único lugar donde aparecen está cortado justo en su guion, se unen mal («Gilgalad»).
- **Tablas de datos:** una página con muchas líneas que son solo un número (una tabla, frecuente en libros de psicología) puede tomarse por índice. El error va en la dirección segura: queda sin limpiar y marcada.
- **Folio impreso:** se deduce suponiendo una sola numeración seguida. Si el libro cambia de numeración (romanos en las páginas preliminares, láminas sin numerar intercaladas), los folios deducidos después del cambio salen corridos. Los que dicen «deducido» se verifican en la imagen antes de citar.
- **Limpieza conservadora:** una letra suelta junto a una línea corta (un final de párrafo) no se borra. Una palabra cortada entre dos páginas no se une.
- **Modo `libro`:** desordena documentos a dos columnas. Para esos, `--modo auto`.
- **Números, símbolos y DOI:** el OCR los confunde (`I`/`1`, `T`/`7`, `&`, `Ω`). **El OCR sirve para leer y buscar; las cifras y las citas se verifican siempre en la imagen.**
- **Lento sin JAX:** aplanar cuesta unos 25–30 segundos por página curva y por núcleo. Con JAX instalado (`python -m pip install "jax[cpu]"`), page-dewarp optimiza con derivadas en lugar de tanteo y baja a unos 4 segundos por página, con una calidad de OCR equivalente en las pruebas. Desde la versión 0.3.0 además se procesan varias páginas a la vez.
- **Archivos pesados:** `libro_plano.pdf` puede ocupar mucho, porque guarda imágenes sin pérdida.

## Licencia

MIT. Ver [LICENSE](LICENSE). Las dependencias conservan sus propias licencias.
