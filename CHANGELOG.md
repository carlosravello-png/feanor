# Registro de cambios de Feanor

Qué cambió en cada versión, qué quedó igual a propósito y con qué se probó.
Las mediciones del banco y los umbrales de las versiones 0.2.0 a 0.4.5 están
en [CALIBRACION.md](CALIBRACION.md). Las versiones anteriores a 0.4.6 están en
el historial de git, cada una con su etiqueta (`v0.1.0` a `v0.4.5`).

*In English: this changelog is kept in Spanish, the language of the code. Each
entry lists what changed, what was deliberately left unchanged, what it was
tested with and its declared limits. A summary in English is in the
[README](README.md) and in [docs/VALIDATION.md](docs/VALIDATION.md).*

## 0.6.2 · Una prueba de PowerPoint deja de depender del texto exacto del OCR (24/11/2026)

**Qué cambió**
- `test_powerpoint_numero_suelto_llega_marcado`: comprobaba que el renglón
  fuera exactamente «[?] 47»; ahora comprueba que empiece por «[?] 47». La
  primera corrida del CI (0.6.1) falló ahí: el CI instala OpenCV 5.1.0, que
  dibuja la lámina de prueba un poco distinto que la 5.0.0 (otra huella de la
  imagen), y Tesseract lee «47]». Feanor hizo lo que la prueba dice verificar:
  el renglón llegó marcado con «[?]» y no se borró.

**Qué quedó igual a propósito**
- Ningún archivo del paquete cambia, salvo `__version__`. La prueba sigue
  exigiendo el número y la marca; solo tolera ruido de OCR después del número.

**Con qué se probó**
- Las 43 pruebas, sin ninguna saltada, en dos entornos: OpenCV 5.0.0 (el del
  desarrollo y la PC del autor) y una instalación limpia en Python 3.12 con
  OpenCV 5.1.0, la misma que hace el CI, donde la 0.6.1 fallaba.

**Límites declarados**
- El texto que lee Tesseract en una imagen puede cambiar con la versión de
  OpenCV, aunque la imagen sea «la misma»: es otra razón para verificar en el
  original lo leído por OCR.

## 0.6.1 · CI público y ficha para Zenodo (24/11/2026)

**Qué cambió**
- `.github/workflows/tests.yml`: GitHub corre las 43 pruebas en cada cambio,
  con Tesseract (modelo `spa`), OCRmyPDF y Ghostscript instalados, para que no
  se salte ninguna. El badge «tests» del README muestra la última corrida.
- `.zenodo.json`: la ficha que Zenodo lee al archivar cada Release (autor con
  ORCID, afiliación Zoovet Travel, licencia MIT, palabras clave).
- Badges de las pruebas y de la licencia en los dos README.

**Qué quedó igual a propósito**
- Ningún archivo del paquete cambia, salvo `__version__`: la 0.6.1 da el mismo
  resultado que la 0.6.0.

**Con qué se probó**
- Las 43 pruebas en Linux, sin ninguna saltada.
- `tests.yml` y `.zenodo.json` se leen sin errores (YAML y JSON).

**Límites declarados**
- La primera corrida del CI se ve después del push; hasta entonces el badge no
  tiene resultado.

## 0.6.0 · Nombre nuevo del paquete y documentación bilingüe (24/11/2026)

**Qué cambió**
- El paquete se llama `feanor_el_aplasta_libros` (en pip,
  `feanor-el-aplasta-libros`); antes, `aplanar-libro` / `aplanar_libro`. La
  carpeta del código cambia de nombre con él.
- El comando instalado es `feanor` (antes `aplanar-libro`); también funciona
  `python -m feanor_el_aplasta_libros`. La ayuda (`--help`) y los mensajes de
  la consola dicen «feanor» y «Feanor <versión>».
- En `_lote.json`, `linea_de_comandos` empieza con `feanor_el_aplasta_libros`.
- Documentación: `README.md` en inglés (el que muestra GitHub) y
  `README.es.md` en español, espejo uno del otro; `docs/VALIDATION.md` y
  `docs/VALIDACION.md`, que cruzan cada resultado medido y cada comportamiento que afirma el README con la prueba o
  la medición que la respalda y dicen lo que no está validado; `CITATION.cff`
  para el botón «Cite this repository»; la licencia de cada dependencia, con
  su fuente; la URL de instalación corregida (`.../feanor.git`).
- `banco/muestras.json` sale del repositorio: tiene los nombres de archivo de
  las copias de los libros de prueba, que tienen derechos de autor. Queda en la
  PC del autor (en `.gitignore`) y en su lugar va `banco/muestras.ejemplo.json`,
  con las mismas listas de páginas y el archivo como «<libro A: tu copia>.pdf».
  `banco.py` sigue leyendo `muestras.json` sin cambios. Los commits anteriores
  conservan el archivo: no se reescribió el historial, porque los `.json` de la
  calibración guardan el commit con que se corrieron.
- `banco.py` acepta copias de versiones con el nombre viejo (`aplanar_libro`) y
  con el nuevo.

**Qué quedó igual a propósito**
- Ningún cálculo cambia: la 0.6.0 da el mismo resultado que la 0.5.5.
- Las claves de los registros: el `.json` de cada archivo guarda la versión en
  `"feanor"`, como desde la 0.5.2; en la ruta completa, el `.json` y el
  `_informe.json` llevan además `"aplanar_libro"`, con la misma versión, para
  comparar informes de antes y de después de la 0.6.0 con la misma clave.
- El código, sus comentarios y los mensajes de la consola siguen en español.
- Los atajos `.bat` de Windows no entran al repositorio: el README da los
  comandos equivalentes.

**Con qué se probó**
- Las 43 pruebas automáticas pasan con el nombre nuevo, sin ninguna saltada,
  en Linux y en Windows (la PC del autor), con el paquete viejo ya
  desinstalado: `find_spec('aplanar_libro')` da `None` (solo cambia la ruta
  de los `import` y el primer elemento de `linea_de_comandos`).
- El Tolkien (14 páginas, ruta completa, aplanado en paralelo en Windows) con
  la 0.5.5 y con la 0.6.0: `.md` idéntico byte a byte y las 14 imágenes
  iguales; en los PDF solo cambian el `/ID` del trailer y la fecha.
- Instalado en un entorno aparte: `feanor --help` y
  `python -m feanor_el_aplasta_libros --help` responden; `pip show` da
  `feanor-el-aplasta-libros 0.6.0`.
- 0.5.5 frente a 0.6.0 sobre el mismo material: un PDF digital de 6 páginas
  con índice, referencias y anexos (suelto y en un lote `--auto --cuerpo`), y
  un lote `--auto --cuerpo` con un Word, un PowerPoint, un PDF mixto (3
  páginas digitales y 1 escaneada) y un PDF escaneado de 2 páginas, más ese
  escaneado por la ruta completa (aplanar, OCR, Markdown). Resultado: todos los
  `.md` idénticos byte a byte; los PDF (`_plano.pdf`, `_ocr.pdf`) con el mismo
  texto y las mismas imágenes, y solo la fecha de creación distinta; en los
  `.json` y `_lote.*` solo difieren la versión, las fechas, los segundos, la
  memoria libre del momento, la carpeta de salida y el primer elemento de
  `linea_de_comandos`.
- `CITATION.cff` validado con `cffconvert` contra el esquema 1.2.0.
- Medición pendiente de la 0.5.5, hecha en la PC del autor el 24/11/2026 con
  `banco/diagnostico_output_type.py` (OCRmyPDF 17.14.1, Tesseract 5.5.3,
  Ghostscript 10.08.0). Páginas no pedidas alteradas, «auto» frente a «pdf»:
  7172, 89 (29 solo espacios, 60 con palabras) frente a 0; 4309, 4 (solo
  espacios) frente a 0; 7659, 5 (con palabras: 37, 42, 46, 47, 58) en los dos
  modos. `--output-type pdf` queda confirmado; la comprobación sigue por la
  7659.
- Licencias: metadatos de cada paquete instalado, documentación de PyMuPDF,
  página de licencias de Artifex (Ghostscript) y repositorio de Tesseract,
  consultados el 24/11/2026.

**Límites declarados**
- Quien tenga instalada una versión anterior debe desinstalar `aplanar-libro`
  antes de instalar la 0.6.0; si no, quedan los dos paquetes y el comando
  `aplanar-libro` sigue apuntando a la versión vieja.
- Los atajos `.bat` que llamaban a `python -m aplanar_libro` dejan de
  funcionar hasta cambiarlos a `python -m feanor_el_aplasta_libros`.
- Si el lote se vuelve a correr sobre una carpeta ya procesada con la 0.5.5,
  todo se procesa de nuevo: el salto de lo ya hecho compara la versión.

## 0.5.5 · Referencias más robustas, OCR con --output-type pdf, comando del lote registrado (20/11/2026)

**Qué cambió**
- Referencias (`referencias.py`), por lo visto en las 80 tesis de calibración:
  - si hay varios títulos, se toma el último que esté antes del primer título
    de anexos de una página posterior a la del primero (antes, el último a
    secas): en la UCV se anexa un «artículo científico» con sus propias
    referencias, y un programa anexado puede traer su bibliografía;
  - erratas del autor: «Referencias» seguido de cualquier palabra que empiece
    por «bibliog» («BIBLIOGÁFICAS»), «Bibliog…» con cualquier terminación
    («BIBLIOGRÁFIA», «BIBLIOGRAFÍCAS»), punto final («BIBLIOGRAFÍA.») y, con
    numeración de capítulo delante, el singular («VII. REFERENCIA
    BIBLIOGRAFICA»); la línea se compara en NFC (la «Í» puede venir con tilde
    combinante);
  - es índice también una página encabezada «Índice», «Esquema», «Contenido»,
    «Tabla de contenido» o «Sumario», aunque no tenga números;
  - en una bibliografía con el año en su propia línea, los años 1900–2099 no
    cuentan como números de página (antes la página parecía un índice y se
    saltaba);
  - un título o un «Anexos» cuenta solo si empieza con mayúscula: una línea de
    prosa cortada en «referencias bibliográficas» no es la sección;
  - «Referencia bibliográfica» en singular sin numeración no cuenta: es la
    página que UNMSM agrega a cada tesis para indicar cómo citarla.
- OCR del lote con `--output-type pdf` (`leer.ocr_paginas`, parámetro
  `tipo_salida`): con el valor por defecto («auto», PDF/A con Ghostscript), la
  reescritura cambiaba el texto de páginas no pedidas. La comprobación sigue,
  y ahora separa las páginas que cambiaron solo espacios de las que cambiaron
  palabras (`ocr.paginas_alteradas_solo_espacios`, `…_palabras`), con una
  alerta para cada caso.
- `_lote.json` guarda la línea de comandos (`linea_de_comandos`).
- Script nuevo `banco/diagnostico_output_type.py`: pasa cada PDF por los dos
  modos y cuenta las páginas alteradas, sin escribir junto a los PDF.

**Qué quedó igual a propósito**
- La conversión, la clasificación por página y sus umbrales, el cuerpo, la
  limpieza y el resto del lote.

**Con qué se probó**
- Las 80 tesis de calibración (texto crudo de sus `.json` de la 0.5.4),
  regla vieja contra nueva: el corte cambia en 16, todas correcciones (8 de la
  UCV que tomaban las referencias del artículo anexado, 1 de UNMSM que tomaba
  las de un programa anexado, 3 con errata en el título, 4 que quedaban sin
  título por el punto final, el singular o los años en su línea). Sin título:
  de 7 a 1. Marcadas «antes de la mitad»: 0. En las 16, la sección empieza con
  referencias reales y termina antes de «Anexos».
- En el camino hubo tres intentos que rompían tesis y se descartaron: tomar el
  límite de anexos en la misma página (4 índices sin detectar), aceptar el
  singular sin numeración (6 de UNMSM) y aceptar títulos en minúscula (1).
- Pruebas automáticas: 43, tres nuevas (casos de referencias de la
  calibración; OCR con `--output-type pdf` sin páginas alteradas en un PDF
  mixto; comando en `_lote.json` y alerta separada). De las anteriores cambia
  una sola aserción: en la prueba de referencias de la 0.5.3, la página
  encabezada «ÍNDICE» ya no aporta candidato (de 2 a 1); el resultado (página
  3) es el mismo.
- `--output-type`, en este entorno sin Ghostscript: la tesis 4309 no altera
  ninguna página en los dos modos (en la PC del autor, con Ghostscript y
  «auto», alteró 4, solo espacios); la 7659 altera las mismas 5 en los dos
  modos (la viñeta `U+F0B7` de Times New Roman desaparece al reescribir).

**Límites declarados**
- `--output-type pdf` no evita todas las alteraciones (7659): la comprobación
  de páginas alteradas sigue siendo necesaria. La medición que decide es el
  diagnóstico en la PC del autor, con Ghostscript.
- Una bibliografía numerada con el número de cada referencia en su propia
  línea sigue pareciendo un índice (1 de 80, la 12727_2897).
- El cambio de regla de referencias cambia el corte respecto de la 0.5.4 en
  PDF con anexos que traen sus propias referencias; un PDF cuyas referencias
  vienen después de los anexos tomaría ahora las del primer bloque.

## 0.5.4 · Lote automático con OCR sin aplanar y comparación forzada de OCR (19/11/2026)

**Qué cambió**
- Lote automático, opción nueva `--auto` (es la que usa `FEANOR.bat` con una
  carpeta): todos los archivos de la carpeta, cada uno con su método.
  - PDF digital: texto nativo. PDF con OCR previo: esa capa, marcada.
  - PDF mixto: texto nativo donde lo hay y OCR de Feanor **sin aplanar** en
    las páginas que son solo imagen (la hoja de aprobación escaneada queda
    leída). PDF escaneado: OCR sin aplanar. Los dos con OCRmyPDF
    `--force-ocr --pages <solo las páginas imagen>` y la segmentación
    automática de Tesseract (ruta nueva `_ruta_ocr_directo`, solo en el lote;
    función `leer.ocr_paginas`). Con `--skip-text`, una hoja escaneada con un
    sello de texto encima se saltaba y quedaba rotulada como leída.
  - Después del OCR se comprueba cada página pedida: si su texto no cambió, se
    rotula «no se leyó» y va a las alertas. Y al revés: OCRmyPDF reescribe el
    PDF entero (por defecto, `--output-type auto`, intenta PDF/A y, si no
    valida, lo convierte con Ghostscript), así que toda página NO pedida debe
    tener en el intermedio el mismo texto que en el original; si difiere, su
    texto se toma del original, se lista en `ocr.paginas_alteradas` y va a las
    alertas. El `.json` guarda el comando exacto (`ocr.comando`) y las páginas
    pedidas, leídas, no leídas y alteradas.
  - Word y PowerPoint: su ruta de siempre.
  - `.doc`, `.ppt`, otro tipo o archivo dañado: a «fallos» con el motivo.
  - Las páginas leídas así llevan en el `.md` el origen «OCR de Feanor sin
    aplanar» y un aviso propio en el encabezado.
- El resumen del lote cuenta archivos por tipo y por método, y `_lote.csv`
  suma las columnas `tipo`, `metodo` y `palabras`.
- Comparación forzada de OCR, opciones nuevas `--comparar-ocr N`,
  `--paginas-comparacion` (10) y `--semilla` (20261119), en el módulo nuevo
  `comparacion.py`: N PDF digitales al azar y, de cada uno, páginas del
  cuerpo con 150 palabras o más (nunca portada, índice, referencias ni
  anexos), convertidas en imagen a 300 ppp en grises, leídas con el mismo OCR
  sin aplanar (comando exacto de cada PDF en `_comparacion.json`, porque
  `--rotate-pages` puede usarse en uno y no en otro) y comparadas con su
  texto nativo. Los dos textos se normalizan igual antes de comparar: NFKC
  (ligaduras «ﬁ», «ﬂ» → letras), guion de fin de línea unido, minúsculas.
  Tasa de error por palabra (distancia de edición entre listas de palabras,
  dividida por las nativas) y similitud de caracteres. Un PDF sin páginas de
  cuerpo se reemplaza por el siguiente del orden al azar; el resumen dice
  cuántos se pidieron y cuántos se midieron.
- Cuerpo para el léxico (`--cuerpo`): normalizado con NFKC, para que
  «conﬁanza» con ligadura y «confianza» cuenten como la misma palabra (el
  texto nativo de PyMuPDF conserva las ligaduras). El `.md` no se normaliza.
- Corrección de la 0.5.3: con menos de 3 páginas con texto, el filtro de
  encabezados repetidos borraba todo el cuerpo (en una sola página cada línea
  «se repite en más de la mitad»). Ahora no quita nada por debajo de 3
  páginas, y una línea debe repetirse al menos 2 veces.
- `FEANOR Y SU NAVAJA.bat` agrega la comparación: 20 tesis, 10 páginas cada
  una, semilla 20261119.

**Qué quedó igual a propósito**
- Un archivo suelto se convierte como antes: el OCR sin aplanar solo existe
  en el lote. Sin `--auto`, el lote decide lo mismo que en la 0.5.3 (solo PDF,
  sin OCR, las escaneadas apartadas), pero no es idéntico: `_lote.csv` suma
  las columnas `tipo`, `metodo` y `palabras`, el motivo de una escaneada dice
  «en el lote no se hace OCR (con --auto, sí)», y el cuerpo cambia en
  documentos de menos de 3 páginas y en los que traen ligaduras. `--auto` no se combina con `--solo-digitales` ni con
  `--metadatos`, que son para un corpus muestreado.

**Con qué se probó**
- Pruebas automáticas: 40, siete nuevas (la séptima simula un OCRmyPDF que
  altera una página nativa: el `.md` usa el texto del original, la página va a
  `ocr.paginas_alteradas` y a las alertas); de las de antes no se cambió ni quitó
  ninguna línea (a la función que arma los PDF de prueba se le agregaron dos
  tipos de página). Las nuevas, además de las tres de abajo: una página
  escaneada con un sello corto se lee entera y una de imagen en blanco queda
  «no se leyó» y en las alertas; un PDF con OCR previo y una página escaneada
  conserva la capa previa intacta y solo lee la escaneada; las ligaduras y el
  guion de fin de línea no cuentan como error ni parten palabras en el cuerpo. Una
  prueba la tasa de error con casos a mano. Otra, el lote automático con una
  tesis digital, un Word, un PowerPoint, un `.doc`, un `.txt`, un PDF roto y,
  si hay OCR instalado, un PDF escaneado. La tercera, la comparación de punta
  a punta: dos páginas del cuerpo, nunca la de referencias, con su texto
  nativo y el del OCR.
- Lote automático de punta a punta con una carpeta sintética de 8 archivos:
  la tesis digital por texto nativo, el acta escaneada leída entera, la hoja
  de aprobación del PDF mixto leída y el resto con su texto nativo, Word y
  PowerPoint por su ruta, y `.doc`, `.txt` y el PDF roto en fallos con su
  motivo.

**Límites declarados**
- Una página escaneada con un sello de 3 palabras o más se clasifica
  «digital» (los umbrales no cambiaron) y no pasa por OCR: queda marcada para
  revisar («texto visible sobre una foto de página completa»), pero su
  contenido no se lee.
- La normalización NFKC del cuerpo cambia también otros caracteres de
  compatibilidad (superíndices, fracciones, «…»).
- En las corridas de prueba, OCRmyPDF no alteró ninguna página nativa, pero
  avisó que convertía con Ghostscript: no se sabe si con tesis reales altera
  alguna. La comprobación lo detecta y lo corrige; no se cambió el
  `--output-type`.
- El OCR sin aplanar no está medido todavía con tesis reales: para eso es la
  comparación forzada. Las páginas con tablas o fórmulas pueden dar una tasa
  alta por el orden de lectura, no por mal OCR.
- La comparación mide el OCR sobre páginas digitales convertidas en imagen,
  que son más limpias que un escaneo real (sin manchas, inclinación ni
  sombras): es una cota optimista del error en escaneos.
- Una tesis en la que todas las páginas son casi iguales (por ejemplo, un
  acta repetida) puede quedar sin cuerpo: sus líneas cuentan como
  encabezados repetidos.
- El `.md` de un PDF leído por OCR sin aplanar viene de un PDF intermedio
  (`<nombre>_ocr.pdf`, en su carpeta), que ocupa espacio.

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
