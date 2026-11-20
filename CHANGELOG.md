# Registro de cambios de Feanor

Qué cambió en cada versión, qué quedó igual a propósito y con qué se probó.
Las mediciones del banco y los umbrales de las versiones 0.2.0 a 0.4.5 están
en [CALIBRACION.md](CALIBRACION.md). Las versiones anteriores a 0.4.6 están en
el historial de git, cada una con su etiqueta (`v0.1.0` a `v0.4.5`).

## 0.5.2 · Carpeta de salida y registro .json en los tres formatos (19/11/2026)

**Qué cambió**
- Carpeta de salida: cada archivo deja sus resultados en una carpeta propia
  dentro de `D:\FEANOR_salida` (opción nueva `--salida` para otra). Si no
  existe el disco `D:`, en `FEANOR_salida` al lado del original. El mismo
  archivo (mismo SHA-256) reemplaza su carpeta; otro con el mismo nombre va a
  `_2`, `_3`…, y se avisa: nada se pisa en silencio.
- El `.md` de un PDF se llama ahora `libro.md`, no `libro_ocr.md`, en las dos
  rutas. `libro_tiempos.json` desaparece: su contenido va a `libro.json`.
- `libro.json` en los tres formatos (PDF, Word, PowerPoint): archivo de origen
  con su SHA-256; versión de Feanor y commit de git (con `sucio` si había
  cambios sin commitear); PyMuPDF, Tesseract y el archivo de modelo del idioma
  con tamaño y SHA-256; OCRmyPDF; Ghostscript (buscado también en
  `C:\Program Files\gs`); tiempos y resumen.
- En PDF, por página del original: el tipo y las medidas con que se decidió
  (palabras, fracción de texto invisible o tapado, cobertura de imagen), con
  los umbrales usados. Por página del `.md`: página de origen, folio y si se
  leyó o se dedujo, si se limpió, el aviso de revisión, y el **texto crudo sin
  limpiar**.
- La limpieza ya no une una palabra cortada con guion al final de la línea
  cuando el trozo de antes o el de después tiene forma de URL, DOI o correo
  (`://`, `www.`, `doi`, `@`, `10.xxxx/`): el guion puede ser parte del
  enlace, y en una referencia el enlace es la evidencia.

**Qué quedó igual a propósito**
- La lectura de PDF, PowerPoint y Word. Los umbrales de la clasificación por
  página: `tipo_pdf.py` solo devuelve además sus medidas.
- La limpieza en todo lo demás.

**Con qué se probó**
- Pruebas automáticas: 28, dos nuevas (URL, DOI y correo cortados con guion
  que no se unen, junto a una palabra que sí; y PDF, Word y PowerPoint con su
  carpeta y su `.json`, el mismo archivo que reemplaza su carpeta y otro con
  el mismo nombre que va a `_2`). La prueba de la ruta digital comprueba
  además que las medidas viajan con el tipo.
- Ruta completa (escaneo) de punta a punta con un PDF sintético de dos
  páginas: escribe sus cinco archivos en la carpeta y el texto crudo en el
  `.json`.

**Límites declarados**
- Ghostscript se busca en el PATH y en `C:\Program Files\gs`; si está en otro
  lugar, el `.json` lo deja vacío aunque OCRmyPDF lo haya usado.
- El modelo de Tesseract se identifica por su archivo y su hash, no por su
  nombre (`tessdata`, `tessdata_fast` o `tessdata_best`): el hash dice si dos
  corridas usaron el mismo, no cuál de los tres es.
- El commit solo se registra si Feanor corre desde una copia del repo
  (instalado con `pip install -e`).
- Dos archivos distintos con el mismo nombre quedan en carpetas `_2`, `_3`
  según el orden en que se conviertan; para el modo lote se nombrará por
  identificador.

## 0.5.1 · Word (.docx) a Markdown (19/11/2026)

**Qué cambió**
- Feanor acepta documentos `.docx` (módulo nuevo `documento.py`). Copia el
  texto tal cual, en el orden del documento: títulos como encabezados (por el
  estilo «Título N» o el nivel de esquema), listas con su sangría (la
  numeración puede venir del párrafo o de su estilo), tablas como tablas (una celda
  combinada se escribe una vez), cuadros de texto marcados donde están
  anclados, y notas al pie y al final con su marca `[^n]` y su texto al final.
- Las listas numeradas conservan su número, contado como lo cuenta Word (el
  inicio de cada lista, los reinicios por nivel y el rótulo: «3.», «b)»,
  «IV.», «6.2.»). Un número simple sale como lista numerada de Markdown
  («3. texto»); los demás rótulos se conservan tal cual detrás de una viñeta
  («- b) texto»), porque Markdown solo numera con cifras. Las de viñetas
  siguen como viñetas.
- Las imágenes con texto se leen con OCR, con las mismas reglas y marcas que en
  PowerPoint.
- No se incluyen: encabezados y pies de página, texto eliminado con control de
  cambios, comentarios. Un `.doc` antiguo pide guardarlo como `.docx`.
- Dependencia nueva: python-docx (licencia MIT, verificada en PyPI el
  19/11/2026, versión 1.2.0).

**Qué quedó igual a propósito**: PDF y PowerPoint.

**Con qué se probó**
- 10 documentos de Word del autor, de 20 a 12 000 palabras: tesis, análisis
  financieros con 22 tablas, un trabajo con cuadros de texto, títulos con
  estilo propio y notas al pie, un artículo de blog con 7 imágenes.
- Control de pérdidas: se contaron las palabras del documento original contra
  las del `.md`, palabra por palabra. No se pierde texto; las únicas
  diferencias son los índices, donde el título y el número de página van
  separados por un tabulador, y las notas al pie, que el `.md` incluye.
- Listas numeradas: en los 10 documentos, la versión con números contra la
  versión sin ellos no pierde ninguna palabra; solo suma los rótulos (en la
  tesis, los romanos del índice; en la evaluación financiera, «a)» a «e)»).
- Pruebas automáticas: 26, dos nuevas (títulos, listas, tabla con celda
  combinada y texto borrado con control de cambios que no debe aparecer; y
  listas numeradas con su número).

**Límites declarados**
- Las tablas de Markdown no tienen celdas combinadas: la combinada se escribe
  una vez y las que ocupa quedan vacías.
- En los índices, el título y el número de página quedan separados.
- Los formatos de numeración raros (ordinales en palabras, numeración china u
  otros) salen como cifras.
- Las imágenes que son capturas de pantalla dan mucho ruido de OCR, aunque
  marcado.

## 0.5.0 · Ruta digital: Feanor mira de dónde sale el texto de cada página (19/11/2026)

**Qué cambió**
- Antes de nada, Feanor clasifica cada página del PDF: digital (texto de
  origen), OCR previo (foto con texto puesto por otro programa), dudosa
  (mezcla de las dos), escaneada (foto sin texto) o vacía. Solo lee la
  estructura del PDF: qué se dibuja, en qué orden y si es visible. No abre
  ninguna imagen (módulo nuevo `tipo_pdf.py`).
- Si la mayoría de las páginas ya traen texto, toma la ruta digital: copia el
  texto directo al `.md`, sin aplanar ni OCR. Si la mayoría son fotos sin
  texto, toma la ruta completa, como hasta ahora.
- El `.md` de la ruta digital ya no dice «texto obtenido por OCR»: dice de
  dónde sale el texto, por rangos de páginas, y anota cada página de un tipo
  distinto del mayoritario.
- Opción nueva `--releer`: lee con el OCR de Feanor aunque el PDF ya traiga
  texto (por ejemplo, un OCR previo malo).

**Qué quedó igual a propósito**
- La ruta completa por dentro (pliegos, aplanado, lectura, Markdown).
- `--solo` y `--paginas` siguen manuales: con ellas no se clasifica nada.
- El nombre del resultado sigue siendo `_ocr.md`.

**Con qué se probó**
- 17 PDF de la computadora del autor, todos bien clasificados: 6 digitales
  (entre ellos una tesis, un artículo de EBSCO y un clasificador de 496
  páginas), 7 fotos sin texto y 4 con OCR previo puesto por el propio Feanor,
  usados como control seguro.
- Caso mixto: el clasificador de 496 páginas tiene 4 páginas que son solo
  imagen (portadas). Toma la ruta digital y las anota como «solo imagen, no
  se leyó».
- Pruebas automáticas: 24, dos nuevas (clasificación de cada tipo con un PDF
  sintético, y la ruta digital de punta a punta).

**Límites declarados**
- En un PDF mixto, las pocas páginas que son foto no se leen: solo se anotan.
- Pendiente: probar con un PDF grande con OCR previo (el manual Plumb, 1222
  páginas) y correr el banco, porque ahora hay una decisión antes de la ruta
  completa.

## 0.4.8 · Cada imagen de PowerPoint dice qué pasó con ella (19/11/2026)

**Qué cambió** (observaciones del revisor sobre la 0.4.7)
- Ninguna imagen se pierde en silencio. Cada una deja su nota: leída con OCR,
  no leída por ser muy pequeña (logo o ícono), no leída por un formato que no
  se puede abrir, con texto escaso o sin texto legible. Dice además cuántos
  renglones se descartaron por baja confianza.
- Texto escaso (2 a 5 palabras): se conserva entero, marcado con `[?]`. Una
  sola palabra suelta se descarta, y se dice.
- Prueba de punta a punta: un renglón que es solo un número llega al `.md`
  como `[?] 47`.

**Con qué se probó**: 5 presentaciones reales. En una aparecieron un cuadro
FODA y un título que antes se perdían sin aviso. Pruebas: 22.

## 0.4.7 · OCR en las imágenes de PowerPoint (19/11/2026)

**Qué cambió**
- Si una imagen de una diapositiva trae texto (una lámina armada como foto, un
  esquema), se lee con Tesseract y ese texto va entre marcas propias, «texto
  leído con OCR», aparte del texto copiado.
- Los renglones sin ninguna palabra con forma de palabra (un número suelto,
  restos de un ícono) se conservan marcados con `[?]` en vez de borrarse. Se
  borran solo los que no tienen ni letras ni cifras.
- «Forma de palabra», sin diccionario: solo letras, al menos tres, alguna
  vocal y mayúsculas coherentes.

**Con qué se probó**: el revisor comparó el resultado contra las láminas
originales. Una sale completa y fiel; la otra, un esquema con flechas, sale
con huecos y ruido. Queda como límite de Tesseract.

## 0.4.6 · PowerPoint (.pptx) a Markdown (19/11/2026)

**Qué cambió**
- Feanor acepta presentaciones `.pptx`: copia el texto de cada diapositiva en
  orden de lectura (columna por columna si está armada en columnas), con sus
  tablas y las notas del orador. Un `.ppt` antiguo hay que guardarlo antes
  como `.pptx`.
- Dependencia nueva: python-pptx (licencia MIT, verificada en PyPI el
  19/11/2026).

**Qué quedó igual a propósito**: todo lo de PDF.

**Con qué se probó**: dos presentaciones reales, con las mismas tres trampas
de orden resueltas (un cuadro en columnas, números dibujados junto a su
renglón y listas de «rótulo: valor»). Pruebas: 19.
