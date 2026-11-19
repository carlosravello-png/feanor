# aplanar-libro

Rescata el texto de libros escaneados o fotografiados en español, incluidas las páginas que se curvan hacia el lomo, y lo deja en Markdown listo para trabajar.

Hace tres pasos en fila:

0. **Preparar** (desde la versión 0.4.0): parte en dos las páginas escaneadas con el libro abierto (pliegos), deja sin tocar las páginas en blanco y marca las que vienen giradas 90°.
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
| `libro_informe.json` | Con qué se hizo la corrida (versión, optimizador, librerías, sistema) y, por página, si se aplanó, por qué no, de qué tamaño salía y cuánto se leía antes y después |
| `libro_tiempos.json` | Cuánto tardó cada paso, el entorno, y cuántas páginas se procesaron a la vez y por qué límite |

Con una presentación de PowerPoint (`.pptx`) no hay nada que aplanar ni leer: se copia el texto que trae cada diapositiva, en orden de lectura (columna por columna si la diapositiva está armada en columnas), con sus tablas y las notas del orador. Deja `clase.md` al lado del original. Si una imagen trae texto (una lámina armada como foto, un esquema), se lee con OCR y ese texto va entre marcas propias, «texto leído con OCR», porque puede tener errores; dentro de ese texto, los renglones que no tienen ninguna palabra con forma de palabra (un número suelto, restos de un ícono) van marcados con «[?]» en vez de borrarse. Cada imagen deja anotado qué pasó con ella: leída, no leída por ser muy pequeña (logos), con poco texto (que se conserva entero marcado con «[?]»), sin texto legible, y cuántos renglones se descartaron por baja confianza. Los logos chicos no se leen, y las fotos sin texto legible y los gráficos solo quedan anotados. En un esquema con flechas el orden del texto leído puede no seguir el del dibujo. Un `.ppt` antiguo hay que guardarlo antes como `.pptx`.

Opciones:

```
aplanar-libro "libro.pdf" --paginas pares        # aplanar solo las pares (o: impares, o 2,4,6)
aplanar-libro "libro.pdf" --solo aplanar         # un solo paso: aplanar | leer | markdown
aplanar-libro "articulo.pdf" --modo auto         # documentos a dos columnas
aplanar-libro "book.pdf" --idioma eng            # otro idioma (uno solo, no mezclar)
aplanar-libro "clase.pptx"                       # PowerPoint a Markdown
aplanar-libro "libro.pdf" --nucleos 4            # páginas que se aplanan a la vez (por defecto: según núcleos físicos y memoria libre, máx. 8)
```

## Límites conocidos

- **Uso clínico y con IA:** esta herramienta no produce texto verificado. Dosis, valores de referencia, nombres de fármacos y cualquier cifra que vaya a usarse en una decisión clínica o en una publicación se comprueban en la fuente original. Lo mismo si el `.md` se le pasa a una IA: la IA no puede detectar un error de OCR en una cifra. Cada `.md` lleva este aviso en la cabecera.
- **Curva muy cerrada junto al lomo:** el aplanado puede dejar las primeras líneas todavía un poco curvas, y entonces se pierde alguna palabra al final. Desde la versión 0.2.0 la librería mide ese resto de curva y marca la página con «REVISAR A MANO». En las 14 páginas de prueba marcó las tres malas y dio una falsa alarma. El umbral es provisional: ver [CALIBRACION.md](CALIBRACION.md).
- **Aplanado que empeora la página:** desde la versión 0.4.3, cada página aplanada se compara con su original en una lectura rápida de Tesseract. Si la aplanada lee menos del 80 % de las palabras, se usa la original y la página se marca. Es una aproximación, no una garantía: la lectura rápida no siempre coincide con el OCR final. En el banco de pruebas, de 19 páginas devueltas a la original, 14 ganaron palabras válidas y 5 perdieron algunas. Esta comprobación cuesta tiempo: en las pruebas, la corrida completa tardó entre un 15 % y un 70 % más según el libro.
- **Página que no cuadra:** si el paso 1 contó líneas de texto en una página y el OCR sacó menos palabras que líneas, la página se marca. Una página sin líneas detectadas (una figura, una foto muy mala) no se marca por esta regla.
- **Errores sin curva:** una página que sale mal por sombra o por baja resolución, con las líneas rectas, no se marca.
- **Páginas con poco texto** (índices, portadas, páginas con figuras): no se aplanan.
- **Pliegos:** el corte se busca cerca del centro, en la franja vacía o en la sombra del lomo. Desde la versión 0.4.4, un pliego con un lado vacío (la hoja en blanco frente a un inicio de capítulo, una hoja de «Notas») también se parte; antes se aplanaba entero como una sola página ancha y salía mal. Consecuencia: una portada apaisada con el título a un lado sale como dos páginas, una en blanco. La mitad vacía no se descarta: sigue en el PDF y se lee. Una mitad con unas pocas líneas pegadas al borde superior o inferior puede quedar rotulada como «en blanco», aunque su texto se lee igual.
- **Aplanado que se desboca:** en algunas páginas el cálculo de la curva termina en una solución absurda y la página saldría varias veces más grande y deformada. Desde la versión 0.4.4 se mide el tamaño de salida antes de construir la imagen; si el alto o el ancho quedan fuera de 0,5 a 3,0 veces el de la entrada, el aplanado se descarta, se usa la original y la página se marca. El rango sale del banco de pruebas (ver [CALIBRACION.md](CALIBRACION.md)) y el margen por arriba es estrecho: la página buena más grande midió 2,62 y la mala más chica, 3,37. Tiene un costo: una página descartada puede leerse algo peor que su versión gigante (en el banco, una pasó de 156 a 148 palabras válidas). No resuelve todos los fallos: de 17 páginas del banco que se leen peor aplanadas, el tamaño explica 9.
- **Resultados distintos entre computadoras:** con la misma versión de la librería y de JAX, una página difícil dio resultados distintos en dos máquinas. El cálculo es inestable en esas páginas y no se puede prometer que dos computadoras den exactamente lo mismo. Cada corrida deja escrito su entorno en `libro_informe.json` y `libro_tiempos.json` para poder compararlas.
- **Memoria:** la librería elige cuántas páginas aplanar a la vez según los núcleos físicos (máximo 8) y la memoria libre, y lo dice en la consola. La memoria por página es una estimación prudente (0,3 GB más 0,05 GB por megapíxel de la página más grande, si saliera del tamaño máximo permitido); en una computadora con poca RAM irá más lento, no debería colgarse. Requiere `psutil`; sin él, usa un valor fijo y lo avisa.
- **Páginas giradas 90°** (una tabla impresa de costado): se detectan y se marcan, pero no se enderezan bien. Se le pide a OCRmyPDF que las gire, y en la prueba no tuvo confianza suficiente para hacerlo. Hay que leerlas en la imagen.
- **Folio al costado:** solo se buscan folios en el encabezado y el pie. Un libro que imprime el número de página en un recuadro al costado, a media altura, queda sin folios deducidos.
- **Fotos de celular:** desde la versión 0.4.2 se iguala la luz (se quitan sombras y fondo gris) y las fotos se rasterizan a su resolución real. En una muestra de 25 pliegos fotografiados, las palabras válidas pasaron de 87,2 % a 89,7 %.
- **Folio con pliegos y saltos:** cada mitad cuenta como una página. Si el escaneo salta páginas o el OCR lee mal un folio, el `.md` lo avisa con «OJO con el folio».
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
