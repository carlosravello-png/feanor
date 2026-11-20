# Registro de cambios de Feanor

Qué cambió en cada versión, qué quedó igual a propósito y con qué se probó.
Las mediciones del banco y los umbrales de las versiones 0.2.0 a 0.4.5 están
en [CALIBRACION.md](CALIBRACION.md). Las versiones anteriores a 0.4.6 están en
el historial de git, cada una con su etiqueta (`v0.1.0` a `v0.4.5`).

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
