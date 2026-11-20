# Registro de cambios de Feanor

Qué cambió en cada versión, qué quedó igual a propósito y con qué se probó.
Las mediciones del banco y los umbrales de las versiones 0.2.0 a 0.4.5 están
en [CALIBRACION.md](CALIBRACION.md). Las versiones anteriores a 0.4.6 están en
el historial de git, cada una con su etiqueta (`v0.1.0` a `v0.4.5`).

## 0.5.3 · Modo lote y sección de referencias (19/11/2026)

**Qué cambió**
- Modo lote (módulo nuevo `lote.py`): si la entrada es una carpeta, Feanor
  convierte cada PDF de ella (sin entrar en subcarpetas) por la ruta digital,
  con **una salida por archivo**, nombrada como el archivo. Todo va a
  `<salida>\<nombre de la carpeta>\`.
  - En el lote no se hace OCR: los escaneados se apartan y se listan. Opción
    nueva `--solo-digitales`: aparta también los que traen OCR previo.
  - Clase de cada PDF según el tipo de sus páginas (digital, ocr_previo,
    escaneada, vacía), con una regla estricta que va escrita en el resumen.
  - Un PDF roto queda como «fallo», con su motivo y el detalle en
    `_errores.txt`, y el lote sigue.
  - Retomar: los PDF ya convertidos con la misma versión (mismo SHA-256) se
    saltan; con `--solo-digitales`, uno convertido antes con OCR previo pasa a
    apartado.
  - Resumen del lote: `_lote.md`, `_lote.csv` (una fila por PDF) y
    `_lote.json`.
- Sección de referencias (módulo nuevo `referencias.py`): en todo PDF, por el
  título de la sección, el último fuera de las páginas tipo índice, hasta el
  primer título de anexos o apéndices. El `.md` marca dónde empieza y dónde
  termina, y la sección se copia a `<nombre>_referencias.md` con el texto
  crudo, sin limpiar. El `.json` dice título, página, línea, cuántos
  candidatos hubo y dónde termina.
- Lote con metadatos, para un corpus muestreado: `--metadatos` une cada PDF
  con su fila de un CSV por el nombre del archivo (obligatorias: `archivo`,
  `handle`, `universidad`, `carrera`, `anio`) y lleva esos datos al
  `_lote.csv` y al `.json` de cada tesis. No se procesa un PDF que no esté en
  el CSV, cuyo SHA-256 no coincida con el anotado al bajarlo o cuya descarga
  figure como fallida. `--anios` (candado): tampoco uno de un año fuera del
  rango. Las filas del CSV sin su PDF se listan. `--destino`: todo en una
  carpeta exacta.
- Cuerpo para análisis léxico (módulo nuevo `cuerpo.py`, opción `--cuerpo` del
  lote): `<nombre>_cuerpo.md` sin referencias ni anexos, sin páginas de índice
  y sin encabezados ni pies repetidos (línea de las 3 primeras o 3 últimas que,
  normalizada, aparece en el margen de más de la mitad de las páginas; solo se
  quita en el margen). El `.md` de siempre no cambia. El `.json` cuenta lo
  quitado.
- Marcas «para revisar» en el lote, que no sacan la tesis: texto visible sobre
  fotos de página completa (¿sello sobre un escaneo?), menos de 100 palabras
  por página en el cuerpo, sin título de referencias, o referencias que
  empiezan antes de la mitad del documento (se informa el porcentaje). Van en
  `_lote.csv`, en el `.json` de cada tesis y en una sección de `_lote.md`.
- Referencias: no cuentan las páginas de índice con líneas que terminan en un
  número de página («Referencias ........ 45»), además de las que son
  mayormente números sueltos.
- `FEANOR.bat` acepta carpetas.
- `FEANOR Y SU NAVAJA.bat`: atajo solo para las tesis de calibración del
  léxico (2015–2017). Corre el lote con `--solo-digitales`, `--cuerpo`, `--metadatos
  calibracion.csv`, `--anios 2015-2017` y `--destino "D:\tesis calibracion"`;
  sin `calibracion.csv` en la carpeta, se niega. No es otra copia de Feanor:
  llama al mismo código con las opciones fijadas.

**Qué quedó igual a propósito**
- La conversión de cada PDF: el lote usa la misma ruta digital que un archivo
  suelto. La clasificación por página y sus umbrales.

**Con qué se probó**
- Pruebas automáticas: 33, cinco nuevas; las pruebas que ya existían no
  cambian (a la función que arma los PDF de prueba se le agregó un tipo de
  página, sin tocar los demás). Una prueba la búsqueda de referencias:
  el título del índice no cuenta, termina antes de los anexos, sin título da
  None y una mención en medio de una frase no cuenta. La otra prueba un lote
  sintético con una tesis con referencias, una sin ellas, una escaneada, una
  con OCR previo, un PDF roto y un archivo que no es PDF; comprueba el estado
  de cada una, el texto crudo del DOI cortado en `_referencias.md` y la
  segunda corrida con `--solo-digitales`. La tercera prueba el lote con
  metadatos: una tesis de 2016 que pasa, una de 2019 que el candado detiene,
  una con SHA-256 distinto, una con descarga fallida, un PDF sin fila en el
  CSV y una fila sin su PDF, todo en una carpeta exacta con espacio en el
  nombre. La cuarta prueba el cuerpo: fuera el encabezado repetido del margen
  pero no la misma frase dentro del texto, fuera el índice con puntos guía,
  las referencias y los anexos. La quinta, una tesis con un sello de texto
  sobre fotos de página completa: sale «digital» y queda marcada para revisar.
- Cuerpo en 13 PDF reales del autor: quita los encabezados y pies repetidos
  («Metacognición», «Ravello Joo, C. E.», «Page X of Y», títulos corrientes)
  y deja entre 249 y 565 palabras por página. El informe de MyLoft, con las
  referencias en la página 11 de 23 seguidas de anexos, queda marcado para
  revisar (44 %): por eso no se exige que las referencias estén en la segunda
  mitad, que lo habría dejado sin referencias.
- Búsqueda de referencias en 12 documentos reales del autor (preprints, un
  foro y un informe, de 7 a 27 páginas): encontró la sección en los 12; en dos
  detectó además dónde termina (antes de «Appendix A» y de «Anexos»).

**Límites declarados**
- Las referencias se buscan solo por el título. Una tesis cuyo título no esté
  en la lista, o que lo tenga partido en dos líneas, sale «sin referencias» y
  se lista. No se validó todavía con tesis: falta medir cuántas encuentra bien
  en un conjunto revisado a mano.
- Si las referencias siguen después de un anexo, o hay un anexo con título
  «Referencias», se toma lo que dice la regla, no lo que quiso el autor.
- En el lote no se hace OCR; las escaneadas solo se listan.
- El CSV de metadatos se lee como UTF-8. Si se guarda desde Excel en otra
  codificación, los acentos pueden salir mal; los nombres de archivo, que son
  handles, no se afectan.
- `FEANOR Y SU NAVAJA.bat` no se pudo correr aquí (es de Windows); se probó
  el comando que llama, con las mismas opciones.
- Un título de sección que coincida con el encabezado repetido y caiga en
  las 3 primeras líneas de una página se quita del cuerpo junto con él.
- El cuerpo incluye la portada, las dedicatorias y la hoja de jurado si tienen
  texto digital; solo se quitan el índice, las referencias, los anexos y los
  márgenes repetidos.
- La regla de clase es estricta: una sola página dudosa saca un PDF de los
  digitales. Los conteos por tipo de página van en `_lote.csv` para poder
  aplicar otra regla.

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
