# Feanor

[English](README.md) · **Español**

[![tests](https://github.com/carlosravello-png/feanor/actions/workflows/tests.yml/badge.svg)](https://github.com/carlosravello-png/feanor/actions/workflows/tests.yml) [![Licencia: MIT](https://img.shields.io/badge/licencia-MIT-blue)](LICENSE) [![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.24522078.svg)](https://doi.org/10.5281/zenodo.24522078) [![Software Heritage](https://archive.softwareheritage.org/badge/origin/https://github.com/carlosravello-png/feanor/)](https://archive.softwareheritage.org/swh:1:rev:80263c049ce1dbb60eb7e22b61fd408f29839176)

Feanor pasa a Markdown libros escaneados o fotografiados, tesis en PDF, documentos de Word y presentaciones de PowerPoint en español, para leerlos, buscarlos o dárselos a una IA. En las fotos de libros endereza las páginas que se curvan hacia el lomo antes de leerlas.

- **Versión:** 0.6.2 (24/11/2026). Historial en [CHANGELOG.md](CHANGELOG.md).
- **Nombre:** la herramienta se llama **Feanor**; el paquete de Python, `feanor_el_aplasta_libros` (en pip, `feanor-el-aplasta-libros`). Hasta la 0.5.5 se llamó `aplanar-libro`.
- **Estado:** software de investigación, en uso en un estudio propio de tesis en español. Lo que garantiza y lo que no está en [Verificación](#verificación) y en [Límites conocidos](#límites-conocidos).
- **Lo más importante:** Feanor no produce texto verificado. Las cifras, las dosis, las citas y los nombres se comprueban siempre en el original.
- **Idioma:** el código, sus comentarios y los mensajes que Feanor muestra están en español, porque la herramienta está hecha para material en español. Este README y [docs/VALIDACION.md](docs/VALIDACION.md) tienen versión en inglés; los demás documentos están en español.

## Qué hace

| Entrada | Qué hace Feanor | Salida |
|---|---|---|
| PDF con texto (digital o con OCR previo) | Copia el texto que ya trae, sin OCR, y dice de dónde sale cada página | `.md` + `.json` |
| PDF escaneado o fotos de un libro | Prepara, aplana y lee con OCR en español | `.md` + `.json` + PDF aplanado y PDF con OCR |
| PDF mixto (en el modo lote `--auto`) | Texto nativo donde lo hay y OCR sin aplanar solo en las páginas que son imagen | `.md` + `.json` |
| Word (`.docx`) | Copia el texto en orden, con títulos, listas, tablas y notas al pie | `.md` + `.json` |
| PowerPoint (`.pptx`) | Copia el texto de cada diapositiva y sus notas; lee con OCR las imágenes con texto | `.md` + `.json` |
| Una carpeta entera | Un resultado por archivo y un resumen del lote | una carpeta por archivo + `_lote.md`, `_lote.csv`, `_lote.json` |

Con un libro escaneado hace estos pasos en fila:

0. **Preparar** (desde la versión 0.4.0): parte en dos las páginas escaneadas con el libro abierto (pliegos), deja sin tocar las páginas en blanco y marca las que vienen giradas 90°.
1. **Aplanar**: endereza las páginas curvas antes del OCR.
2. **Leer**: pasa OCR con la configuración que funciona para el español.
3. **Markdown**: escribe el texto página por página, con el número del visor y avisos en las páginas que hay que revisar a mano.

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

Feanor:

```
python -m pip install git+https://github.com/carlosravello-png/feanor.git
```

Si tenías instalada una versión anterior con el nombre `aplanar-libro`, desinstálala antes: `python -m pip uninstall aplanar-libro`.

Para aplanar más rápido (de unos 25–30 segundos a unos 4 por página curva; ver [Límites conocidos](#límites-conocidos)): `python -m pip install "jax[cpu]"`.

## Uso

```
feanor "libro.pdf"
```

Es lo mismo que `python -m feanor_el_aplasta_libros "libro.pdf"`.

### Tipo de cada página

Antes de nada, Feanor mira de dónde sale el texto de cada página:

| Tipo de página | Qué es | Qué hace Feanor |
|---|---|---|
| digital | El texto viene de origen (Word, la editorial) | Lo copia tal cual |
| OCR previo | Una foto a la que otro programa ya le puso texto | Lo copia y avisa que puede traer errores |
| dudosa | Mezcla de las dos anteriores | Lo copia y avisa |
| escaneada | Una foto sin texto | La aplana y la lee |
| vacía | Ni texto ni imágenes | Nada |

Si la mayoría de las páginas ya traen texto, toma la **ruta digital**: pasa directo a Markdown, en segundos, sin aplanar ni OCR, y el `.md` dice en su encabezado qué páginas son de cada tipo (las que son solo imagen quedan anotadas como no leídas). Si la mayoría son fotos sin texto, toma la ruta completa. Para leer con el OCR de Feanor un PDF que ya trae texto (por ejemplo, un OCR previo malo): `--releer`. Con `--solo` o `--paginas` no se hace esta revisión.

### Dónde quedan los resultados

Cada archivo deja sus resultados en una carpeta propia dentro de **`D:\FEANOR_salida`** (otra con `--salida <carpeta>`; si no existe el disco `D:`, en una carpeta `FEANOR_salida` al lado del original). Para `libro.pdf`, la carpeta es `D:\FEANOR_salida\libro\`. Si se convierte de nuevo el mismo archivo (mismo SHA-256), su carpeta se reemplaza; si es otro archivo con el mismo nombre, va a `libro_2`, y se avisa.

| Archivo | Para qué |
|---|---|
| `libro.md` | El texto en Markdown, para trabajar. Cada página lleva el número del visor y, si se pudo deducir, el folio impreso del libro. En el cuerpo se quita el ruido de la sombra del lomo y los folios, y se unen las palabras cortadas con guion, salvo dentro de una URL, un DOI o un correo. Las páginas tipo índice quedan sin limpiar |
| `libro.json` | El registro de la corrida (ver abajo). Lo dejan los tres formatos: PDF, Word y PowerPoint |
| `libro_referencias.md` | Si se encontró: la sección de referencias, con el texto crudo |
| `libro_plano.pdf` | Solo en la ruta completa: las páginas aplanadas, como imágenes |
| `libro_ocr.pdf` | Solo en la ruta completa: el PDF con texto seleccionable. Es el que se usa para verificar folios |
| `libro_informe.json` | Solo en la ruta completa: por página, si se aplanó, por qué no, de qué tamaño salía y cuánto se leía antes y después |

### Qué lleva el `.json`

- El archivo de origen: nombre, ruta, tamaño y SHA-256, de modo que el resultado se puede atar al archivo aunque este ya no se conserve.
- Con qué se hizo: la versión de Feanor y su commit de git (con la marca `sucio` si había cambios sin commitear), PyMuPDF, Tesseract y el archivo de modelo del idioma con su tamaño y SHA-256 (dos modelos con el mismo nombre leen distinto), OCRmyPDF, Ghostscript, Python y el sistema. La versión de Feanor va en la clave `feanor`. En la ruta completa, el `.json` y `libro_informe.json` llevan además la clave `aplanar_libro`, con la misma versión: conserva el nombre anterior del paquete para comparar informes de antes y de después de la 0.6.0.
- En PDF, por cada página del original: su tipo y las medidas con que se decidió (palabras, fracción de texto invisible o tapado, cobertura de la imagen más grande), y los umbrales usados, para poder recalcular la clasificación con otros umbrales sin abrir el PDF.
- En PDF, por cada página del `.md`: de qué página del original sale, el folio y si se leyó o se dedujo, si se limpió, el aviso de revisión si lo hay, y **el texto crudo, sin ninguna limpieza**.
- En Word y PowerPoint: el resumen (párrafos, títulos, tablas, notas, imágenes leídas, escasas o no leídas).
- Cuánto tardó.

### Referencias

En un PDF, Feanor busca el título de la sección de referencias («Referencias», «Referencias bibliográficas», «Bibliografía», «Fuentes consultadas», «Literatura citada», «References», «Bibliography», con o sin numeración delante, y con erratas como «Bibliogáficas»). No cuentan las páginas de índice (con números de página o encabezadas «Índice», «Esquema», «Contenido»), ni una línea de prosa en minúscula, ni la página de UNMSM que dice cómo citar la tesis. Si hay varios títulos, toma el último que esté antes del primer «Anexos» de una página posterior: un anexo puede traer sus propias referencias (en la UCV, el artículo científico anexado). La sección termina antes del primer título de anexos o apéndices. Si lo encuentra, el `.md` marca dónde empiezan y dónde terminan, y la sección se copia a `libro_referencias.md` con el **texto crudo**, sin ninguna limpieza. Si no lo encuentra, lo dice. Solo mira el título: no separa ni interpreta las referencias una por una.

### Word

Con un documento de Word (`.docx`) pasa lo mismo que con PowerPoint: se copia el texto tal cual, en el orden del documento, con los títulos como encabezados de Markdown, las listas con su viñeta o su número, las tablas como tablas, los cuadros de texto marcados en su sitio y las notas al pie con su marca en el texto y su contenido al final. Las imágenes con texto se leen con OCR y van marcadas, como en PowerPoint. No se incluyen encabezados ni pies de página, ni texto eliminado con control de cambios, ni comentarios. Un `.doc` antiguo hay que guardarlo antes como `.docx`.

### PowerPoint

Con una presentación de PowerPoint (`.pptx`) no hay nada que aplanar ni leer: se copia el texto que trae cada diapositiva, en orden de lectura (columna por columna si la diapositiva está armada en columnas), con sus tablas y las notas del orador. Deja `clase.md` y `clase.json` en su carpeta de salida. Si una imagen trae texto (una lámina armada como foto, un esquema), se lee con OCR y ese texto va entre marcas propias, «texto leído con OCR», porque puede tener errores; dentro de ese texto, los renglones que no tienen ninguna palabra con forma de palabra (un número suelto, restos de un ícono) van marcados con «[?]» en vez de borrarse. Cada imagen deja anotado qué pasó con ella: leída, no leída por ser muy pequeña (logos), con poco texto (que se conserva entero marcado con «[?]»), sin texto legible, y cuántos renglones se descartaron por baja confianza. Los logos chicos no se leen, y las fotos sin texto legible y los gráficos solo quedan anotados. En un esquema con flechas el orden del texto leído puede no seguir el del dibujo. Un `.ppt` antiguo hay que guardarlo antes como `.pptx`.

### Opciones

```
feanor "libro.pdf" --paginas pares        # aplanar solo las pares (o: impares, o 2,4,6)
feanor "libro.pdf" --releer               # leer con el OCR de Feanor aunque ya traiga texto
feanor "libro.pdf" --solo aplanar         # un solo paso: aplanar | leer | markdown
feanor "articulo.pdf" --modo auto         # documentos a dos columnas
feanor "book.pdf" --idioma eng            # otro idioma (uno solo, no mezclar)
feanor "clase.pptx"                       # PowerPoint a Markdown
feanor "trabajo.docx"                     # Word a Markdown
feanor "libro.pdf" --nucleos 4            # páginas que se aplanan a la vez (por defecto: según núcleos físicos y memoria libre, máx. 8)
```

## Modo lote: una carpeta entera

```
feanor "C:\ruta\carpeta_de_tesis"
feanor "C:\ruta\carpeta_de_tesis" --solo-digitales
feanor "C:\ruta\carpeta_de_tesis" --auto
```

Cada PDF de la carpeta (sin entrar en subcarpetas) deja su propia carpeta de salida, igual que un archivo suelto: su `.md`, su `.json` y, si se encontró, su `_referencias.md`. **Un resultado por archivo**, con el nombre del archivo: si los PDF se guardan con su handle (`20.500.12692_12345.pdf`), los resultados quedan nombrados por handle. Todo va a `D:\FEANOR_salida\<nombre de la carpeta>\`.

- Sin `--auto`, en el lote **nunca se hace OCR**: un PDF escaneado se aparta y se lista, sin procesarlo. Con `--solo-digitales` se apartan también los que traen OCR previo de otro programa.
- Clase de cada PDF, por el tipo de sus páginas: **digital** si ninguna página tiene OCR previo ni es dudosa y hay más páginas con texto que escaneadas (una hoja escaneada suelta, como la de aprobación, no lo saca: esa página no se lee y queda anotada); **ocr_previo** si alguna página tiene OCR previo o es dudosa; **escaneada** si hay más páginas escaneadas que con texto.
- Un PDF roto no detiene el lote: queda como «fallo», con el motivo, y el detalle técnico en `_errores.txt`.
- Si el lote se corta, se vuelve a correr igual: los PDF ya convertidos con la misma versión de Feanor (mismo SHA-256) se saltan.
- Al final deja el resumen del lote: `_lote.md` (para leer), `_lote.csv` (para Excel o R: una fila por PDF con su estado, clase, páginas de cada tipo, página y título de las referencias, tiempo y SHA-256) y `_lote.json`, que guarda también la línea de comandos usada.

**Lote automático (`--auto`).** Toma todos los archivos de la carpeta y usa con cada uno el método que le corresponde: PDF digital → texto nativo; PDF con OCR previo → esa capa, marcada; PDF mixto → texto nativo donde lo hay y OCR de Feanor **sin aplanar** en las páginas que son solo imagen (por ejemplo, la hoja de aprobación escaneada); PDF escaneado → OCR sin aplanar; Word y PowerPoint → su ruta de siempre. Un `.doc`, un `.ppt`, otro tipo de archivo o uno dañado no se procesa y va a «fallos» con el motivo. El resumen cuenta archivos por tipo y por método, y da las palabras de cada uno. Sin `--auto`, el lote hace lo de la 0.5.3: solo PDF y sin OCR.

El OCR sin aplanar usa OCRmyPDF con `--force-ocr` solo en las páginas que son solo imagen (`--pages`), con la segmentación automática de Tesseract: así una hoja escaneada con un sello de texto encima se lee entera. Después se comprueba cada una: si su texto no cambió, no se rotula «OCR de Feanor» sino «no se leyó», y va a las alertas. Y al revés: como OCRmyPDF reescribe el PDF entero, cada página que no se pidió debe salir con el mismo texto que en el original; si cambió, se usa la del original y va a las alertas. El comando exacto queda en el `.json`. Desde la 0.5.5 se usa `--output-type pdf`, que reescribe el PDF lo menos posible; aun así, la comprobación de páginas alteradas sigue, y separa las que cambiaron solo espacios de las que cambiaron palabras. El aplanado no se usa: está hecho para fotos de libros curvos y empeora los documentos planos.

**Comparación forzada de OCR (`--comparar-ocr N`).** Al final del lote toma al azar (`--semilla`, por defecto 20261119) N PDF digitales y, de cada uno, `--paginas-comparacion` páginas del cuerpo (por defecto 10; páginas que quedan en el cuerpo con 150 palabras o más, así que nunca la portada, el índice, las referencias ni los anexos). Las convierte en imagen, las lee con el mismo OCR sin aplanar (el comando exacto queda registrado) y las compara con su texto nativo, después de normalizar los dos igual (NFKC para las ligaduras, guion de fin de línea unido): tasa de error por palabra y similitud de caracteres, en `comparacion_ocr/`, con el texto de cada página al lado. Si un PDF elegido no tiene páginas de cuerpo, se reemplaza por el siguiente del orden al azar, y el resumen dice cuántos se pidieron y cuántos se midieron.

**Lote con metadatos (para un corpus muestreado).** Con `--metadatos lista.csv`, cada PDF se une con su fila del CSV por el nombre del archivo (columnas obligatorias: `archivo`, `handle`, `universidad`, `carrera`, `anio`; opcionales: `titulo`, `estado`, `sha256`), y el `_lote.csv` y el `.json` de cada tesis llevan esos datos. No se procesa ningún PDF que no esté en el CSV, cuyo SHA-256 no coincida con el anotado al bajarlo, o cuya descarga figure como fallida. Con `--anios 2015-2017`, tampoco uno cuyo año quede fuera del rango (candado). Las filas del CSV sin su PDF se listan. `--destino` pone todo en una carpeta exacta.

**Cuerpo para análisis léxico (`--cuerpo`).** En el lote, escribe además `<nombre>_cuerpo.md`: el texto desde el inicio hasta el título de referencias (sin referencias ni anexos), sin las páginas de índice y sin los encabezados y pies repetidos (una línea de las 3 primeras o las 3 últimas de la página que aparece, sin números ni signos, en el margen de más de la mitad de las páginas; la misma frase dentro del texto se conserva). El cuerpo se normaliza con NFKC (las ligaduras «ﬁ», «ﬂ» pasan a sus letras); el `.md` de siempre no cambia y conserva el texto tal cual. Con menos de 3 páginas con texto no se quita ningún margen. El `.json` dice cuántas palabras y páginas quedaron, cuántas líneas de margen se quitaron y cuáles. **Para revisar a mano**, sin sacarlas del lote, se marcan las tesis con texto visible sobre fotos de página completa (un sello sobre un escaneo), con menos de 100 palabras por página en el cuerpo, sin título de referencias (el cuerpo llega entonces hasta el final) o con las referencias empezando antes de la mitad del documento.

**Ejemplo: el lote de calibración del léxico.** Es la corrida con que se preparan las tesis de calibración del estudio del autor (la carpeta de tesis bajadas, con su `calibracion.csv`):

```
feanor "C:\ruta\tesis_calibracion" --solo-digitales --cuerpo --metadatos "C:\ruta\tesis_calibracion\calibracion.csv" --anios 2015-2017 --comparar-ocr 20 --paginas-comparacion 10 --semilla 20261119 --destino "D:\tesis calibracion"
```

## Verificación

Feanor se prueba en dos niveles, y cada uno dice algo distinto:

1. **Pruebas automáticas** (`tests/test_basico.py`, 43 en la versión 0.6.2). Cada una arma un caso pequeño (un PDF, un Word, un PowerPoint, una carpeta de tesis) con texto inventado, salvo algunos fragmentos de una línea de los libros del banco (títulos de capítulo con su folio, una frase), que reproducen la forma de un error real. Comprueba que Feanor hace lo que este README dice. Ningún libro con derechos de autor entra en el repositorio: solo esos fragmentos. Las que necesitan Tesseract, OCRmyPDF, `python-docx` o `python-pptx` se saltan si no están instalados. Desde la 0.6.1 corren también en GitHub en cada cambio, con Tesseract, OCRmyPDF y Ghostscript instalados; el badge «tests» de arriba muestra el resultado de la última corrida. Para correrlas:

   ```
   python -m pip install pytest
   python -m pytest -q
   ```

2. **Mediciones con material real** (libros, fotos de celular, tesis). Están en [CALIBRACION.md](CALIBRACION.md) y en la sección «Con qué se probó» de cada versión del [CHANGELOG.md](CHANGELOG.md), con el material, la fecha y lo que no garantizan.


[docs/VALIDACION.md](docs/VALIDACION.md) cruza cada resultado medido y cada comportamiento que afirma este README con la prueba o la medición que lo respalda, y lista lo que **no** está validado.

## Lo que se midió

Pruebas del 13/11/2026 con un libro fotografiado con el celular (14 páginas; el libro tiene derechos de autor y no se incluye en el repositorio):

- **Páginas planas:** el OCR sale casi perfecto sin aplanar.
- **Páginas curvas hacia el lomo:** sin aplanar, el OCR es inservible (letras sueltas, líneas partidas). Aplanadas y leídas en modo libro, seis de siete quedaron legibles y en orden. En la página revisada a mano, cerca del 97 % de las palabras salieron correctas.
- **Idioma:** con `-l spa+eng` se perdió cerca del 40 % de las tildes y eñes; con `-l spa` volvieron todas (prueba sobre un PDF tipeado leído como imagen).
- **Una página con poco texto (un índice):** no se pudo aplanar. Feanor la deja como está y la marca para revisión.

## Límites conocidos

- **Uso clínico y con IA:** esta herramienta no produce texto verificado. Dosis, valores de referencia, nombres de fármacos y cualquier cifra que vaya a usarse en una decisión clínica o en una publicación se comprueban en la fuente original. Lo mismo si el `.md` se le pasa a una IA: la IA no puede detectar un error de OCR en una cifra. Cada `.md` lleva este aviso en la cabecera.
- **Curva muy cerrada junto al lomo:** el aplanado puede dejar las primeras líneas todavía un poco curvas, y entonces se pierde alguna palabra al final. Desde la versión 0.2.0 Feanor mide ese resto de curva y marca la página con «REVISAR A MANO». En las 14 páginas de prueba marcó las tres malas y dio una falsa alarma. El umbral es provisional: ver [CALIBRACION.md](CALIBRACION.md).
- **Aplanado que empeora la página:** desde la versión 0.4.3, cada página aplanada se compara con su original en una lectura rápida de Tesseract. Si la aplanada lee menos del 80 % de las palabras, se usa la original y la página se marca. Es una aproximación, no una garantía: la lectura rápida no siempre coincide con el OCR final. En el banco de pruebas, de 19 páginas devueltas a la original, 14 ganaron palabras válidas y 5 perdieron algunas. Esta comprobación cuesta tiempo: en las pruebas, la corrida completa tardó entre un 15 % y un 70 % más según el libro.
- **Página que no cuadra:** si el paso 1 contó líneas de texto en una página y el OCR sacó menos palabras que líneas, la página se marca. Una página sin líneas detectadas (una figura, una foto muy mala) no se marca por esta regla.
- **Errores sin curva:** una página que sale mal por sombra o por baja resolución, con las líneas rectas, no se marca.
- **Páginas con poco texto** (índices, portadas, páginas con figuras): no se aplanan.
- **Pliegos:** el corte se busca cerca del centro, en la franja vacía o en la sombra del lomo. Desde la versión 0.4.4, un pliego con un lado vacío (la hoja en blanco frente a un inicio de capítulo, una hoja de «Notas») también se parte; antes se aplanaba entero como una sola página ancha y salía mal. Consecuencia: una portada apaisada con el título a un lado sale como dos páginas, una en blanco. La mitad vacía no se descarta: sigue en el PDF y se lee. Una mitad con unas pocas líneas pegadas al borde superior o inferior puede quedar rotulada como «en blanco», aunque su texto se lee igual.
- **Aplanado que se desboca:** en algunas páginas el cálculo de la curva termina en una solución absurda y la página saldría varias veces más grande y deformada. Desde la versión 0.4.4 se mide el tamaño de salida antes de construir la imagen; si el alto o el ancho quedan fuera de 0,5 a 3,0 veces el de la entrada, el aplanado se descarta, se usa la original y la página se marca. El rango sale del banco de pruebas (ver [CALIBRACION.md](CALIBRACION.md)) y el margen por arriba es estrecho: la página buena más grande midió 2,62 y la mala más chica, 3,37. Tiene un costo: una página descartada puede leerse algo peor que su versión gigante (en el banco, una pasó de 156 a 148 palabras válidas). No resuelve todos los fallos: de 17 páginas del banco que se leen peor aplanadas, el tamaño explica 9.
- **Resultados distintos entre computadoras:** con la misma versión de Feanor y de JAX, una página difícil dio resultados distintos en dos máquinas. El cálculo es inestable en esas páginas y no se puede prometer que dos computadoras den exactamente lo mismo. Cada corrida deja escrito su entorno en `libro.json` para poder compararlas.
- **Memoria:** Feanor elige cuántas páginas aplanar a la vez según los núcleos físicos (máximo 8) y la memoria libre, y lo dice en la consola. La memoria por página es una estimación prudente (0,3 GB más 0,05 GB por megapíxel de la página más grande, si saliera del tamaño máximo permitido); en una computadora con poca RAM irá más lento, no debería colgarse. Requiere `psutil`; sin él, usa un valor fijo y lo avisa.
- **Páginas giradas 90°** (una tabla impresa de costado): se detectan y se marcan, pero no se enderezan bien. Se le pide a OCRmyPDF que las gire, y en la prueba no tuvo confianza suficiente para hacerlo. Hay que leerlas en la imagen.
- **Folio al costado:** solo se buscan folios en el encabezado y el pie. Un libro que imprime el número de página en un recuadro al costado, a media altura, queda sin folios deducidos.
- **Fotos de celular:** desde la versión 0.4.2 se iguala la luz (se quitan sombras y fondo gris) y las fotos se rasterizan a su resolución real. En una muestra de 25 pliegos fotografiados, las palabras válidas pasaron de 87,2 % a 89,7 %.
- **Folio con pliegos y saltos:** cada mitad cuenta como una página. Si el escaneo salta páginas o el OCR lee mal un folio, el `.md` lo avisa con «OJO con el folio».
- **Índices:** es lo que peor sale. El OCR separa cada título de su número y lee mal los números romanos. Feanor detecta las páginas tipo índice, no las limpia y las marca siempre con «REVISAR A MANO».
- **Nombres con guion propio** («Gil-galad»): se conservan solo si en algún lugar del libro aparecen a mitad de línea. Si el único lugar donde aparecen está cortado justo en su guion, se unen mal («Gilgalad»).
- **Tablas de datos:** una página con muchas líneas que son solo un número (una tabla, frecuente en libros de psicología) puede tomarse por índice. El error va en la dirección segura: queda sin limpiar y marcada.
- **Folio impreso:** se deduce suponiendo una sola numeración seguida. Si el libro cambia de numeración (romanos en las páginas preliminares, láminas sin numerar intercaladas), los folios deducidos después del cambio salen corridos. Los que dicen «deducido» se verifican en la imagen antes de citar.
- **Limpieza conservadora:** una letra suelta junto a una línea corta (un final de párrafo) no se borra. Una palabra cortada entre dos páginas no se une.
- **Modo `libro`:** desordena documentos a dos columnas. Para esos, `--modo auto`.
- **Números, símbolos y DOI:** el OCR los confunde (`I`/`1`, `T`/`7`, `&`, `Ω`). **El OCR sirve para leer y buscar; las cifras y las citas se verifican siempre en la imagen.**
- **OCR del lote que altera páginas:** `--output-type pdf` no evita todas las alteraciones de las páginas no pedidas (en una tesis de la calibración, una viñeta del tipo de letra desaparece al reescribir); por eso la comprobación de páginas alteradas sigue en pie.
- **Referencias con el número de cada una en su propia línea:** una bibliografía numerada así sigue pareciendo un índice (1 de 80 tesis de la calibración).
- **Lento sin JAX:** aplanar cuesta unos 25–30 segundos por página curva y por núcleo. Con JAX instalado (`python -m pip install "jax[cpu]"`), page-dewarp optimiza con derivadas en lugar de tanteo y baja a unos 4 segundos por página, con una calidad de OCR equivalente en las pruebas. Desde la versión 0.3.0 además se procesan varias páginas a la vez.
- **Archivos pesados:** `libro_plano.pdf` puede ocupar mucho, porque guarda imágenes sin pérdida.

## Créditos

Feanor no hace OCR ni inventa el aplanado. Se apoya en:

- **[page-dewarp](https://github.com/lmmx/page-dewarp)** (licencia MIT), de Louis Maddox, sobre el método de [Matt Zucker (2016)](https://github.com/mzucker/page_dewarp). Hace el aplanado. Se usa como dependencia, sin copiar su código.
- **[OCRmyPDF](https://github.com/ocrmypdf/OCRmyPDF)** (MPL-2.0) y **[Tesseract](https://github.com/tesseract-ocr/tesseract)** (Apache-2.0). Hacen el OCR. Se llaman como programas externos.
- **[PyMuPDF](https://github.com/pymupdf/PyMuPDF)** para leer y escribir PDF, y **[OpenCV](https://opencv.org/)** para el recorte.
- **[python-docx](https://github.com/python-openxml/python-docx)** y **[python-pptx](https://github.com/scanny/python-pptx)** para leer Word y PowerPoint.

Lo que aporta Feanor:
- El flujo completo, y la elección de ruta según el tipo de cada página.
- El recorte automático de la página aplanada.
- La corrección del recuadro de page-dewarp, que cortaba el final de las líneas junto al lomo.
- La regla que deja sin aplanar las páginas con poco texto.
- La configuración de OCR probada con libros en español.
- Las marcas de revisión en el Markdown.
- El modo lote para corpus de tesis: un resultado por archivo, metadatos con candado, sección de referencias, cuerpo para el léxico y comparación forzada de OCR.

## Cómo se hizo

Autor: Carlos Eduardo Ravello Joo ([ORCID 0009-0007-5631-7436](https://orcid.org/0009-0007-5631-7436)). El autor definió el problema, dirigió el desarrollo y validó los resultados con material real. Se usó Claude (Anthropic) como asistente de programación.

## Cómo citar

GitHub muestra el botón «Cite this repository» a partir de [CITATION.cff](CITATION.cff). En texto:

> Ravello Joo, C. E. (2026). *Feanor* (versión 0.6.2) [Software]. Zenodo. https://doi.org/10.5281/zenodo.24522079

Para citar todas las versiones: [10.5281/zenodo.24522078](https://doi.org/10.5281/zenodo.24522078). Archivo permanente del código de la v0.6.2 en Software Heritage: [swh:1:rev:80263c049ce1dbb60eb7e22b61fd408f29839176](https://archive.softwareheritage.org/swh:1:rev:80263c049ce1dbb60eb7e22b61fd408f29839176).

## Licencia

El código de Feanor es MIT: ver [LICENSE](LICENSE). Las dependencias conservan sus propias licencias:

| Dependencia | Licencia | Cómo la usa Feanor |
|---|---|---|
| PyMuPDF | AGPL-3.0 o licencia comercial de Artifex | Se importa (biblioteca de Python) |
| Ghostscript | AGPL-3.0 o licencia comercial de Artifex | Programa externo, lo llama OCRmyPDF |
| OCRmyPDF | MPL-2.0 | Programa externo |
| Tesseract | Apache-2.0 | Programa externo |
| page-dewarp | MIT | Se importa |
| OpenCV (`opencv-python-headless`) | Apache-2.0 | Se importa |
| python-docx, python-pptx | MIT | Se importan |
| NumPy | BSD-3-Clause (con partes en 0BSD, MIT, Zlib y CC0-1.0) | Se importa |
| msgspec, psutil | BSD-3-Clause | Se importan |

Fuentes: los metadatos de cada paquete instalado, la documentación de PyMuPDF, la página de licencias de Artifex y el repositorio de Tesseract, consultados el 24/11/2026.

PyMuPDF se importa, así que quien redistribuya Feanor junto con PyMuPDF, o lo ofrezca como servicio en red, tiene que cumplir también la AGPL de PyMuPDF o conseguir su licencia comercial. Esto es una descripción, no asesoría legal.
