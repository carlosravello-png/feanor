# Calibración y banco de pruebas de Feanor

Hasta la 0.5.5 el paquete se llamaba `aplanar-libro`; las rutas de código de abajo usan el nombre actual.

Qué se midió para fijar cada umbral, con qué material y qué no garantiza. Índice por versión:

- **0.2.0** — aviso «REVISAR A MANO» por resto de curva (umbral 0,55): secciones «Material» a «Lo que esta calibración no garantiza».
- **0.3.0** — nota sobre JAX: cambia el aplanado y la medida.
- **0.4.3** — banco de pruebas fijo; margen del 80 % en la comparación de lectura.
- **0.4.4** — control de forma (0,5 a 3,0), pliegos con un lado vacío, registro del entorno y páginas a la vez según la máquina.

## 0.2.0 · Aviso «REVISAR A MANO» por resto de curva (14/11/2026)

## Material

Las 14 páginas de un libro fotografiado con el celular (Google Drive, filtro «Mejorar»). El libro tiene derechos de autor y no se incluye en el repositorio. Las páginas pares estaban curvas hacia el lomo.

La etiqueta de cada página viene de una auditoría independiente que leyó el `.md` producido en el PC del autor:

- **mala:** 2, 8 y 14.
- **moderada:** 10, 12 y 13.
- **limpia:** 1, 3, 4, 5, 6, 7, 9 y 11.

## Señales comparadas

| Pág. | Etiqueta | A. Curva junto al lomo (p90) | B. Confianza de Tesseract: % palabras < 60 del lado del lomo¹ | C. Finales de línea rotos² | ¿Marca con A ≥ 0,55? |
|---|---|---|---|---|---|
| 1 | limpia | sin líneas medibles | 47,4 | 0/9 | no |
| 2 | **mala** | 1,00 | 81,2 | 0/5 | **sí** |
| 3 | limpia | 0,18 | 2,8 | 1/16 | no |
| 4 | limpia | 0,76 | 1,0 | 1/33 | **sí** (falsa alarma) |
| 5 | limpia | 0,25 | 2,6 | 1/34 | no |
| 6 | limpia | 0,33 | 0,0 | 0/19 | no |
| 7 | limpia | 0,19 | 0,0 | 1/15 | no |
| 8 | **mala** | 1,06 | 9,1 | 4/32 | **sí** |
| 9 | limpia | 0,31 | 3,3 | 0/34 | no |
| 10 | moderada | 0,22 | 0,0 | 0/34 | no |
| 11 | limpia | 0,30 | 0,0 | 0/29 | no |
| 12 | moderada | 0,52 | 2,5 | 2/35 | no |
| 13 | moderada | 0,38 | 1,1 | 3/35 | no |
| 14 | **mala** | 0,66 | 0,0 | 1/33 | **sí** |

¹ Medida con Tesseract 5.3.4 y el modelo `spa` de `tessdata_fast` del entorno de desarrollo, **no** con el del PC del autor (Tesseract 5.5.3, `spa` de `tessdata`). Ver la nota de abajo.
² Última palabra de cada línea larga que no es una palabra española ni un nombre propio, número o corte con guion. Medida sobre el `.md` del PC.

### Cómo se calcula A

En `feanor_el_aplasta_libros/calidad.py`:
1. Por cada línea de texto larga, se mide la altura del texto en 8 trozos.
2. Se ajusta una recta a los trozos alejados del lomo.
3. Se mide cuánto se aparta de esa recta el extremo del lomo, en alturas de letra.
4. Se toma el percentil 90 de la página, en el peor de los dos lados.

Se calcula sobre la misma imagen que va al OCR.

## Resultado

- **Se elige A con umbral 0,55.** Marca las tres páginas malas y no deja ninguna sin marcar. Tiene una falsa alarma, la 4: su resto de curva es real y visible, pero el OCR lo aguantó. La moderada más cercana es la 12, con 0,52, así que el margen entre el umbral y las páginas buenas es estrecho.
- **B no sirvió aquí.** Marca la 2 y la 8, pero también la 1, que es limpia (un índice con números desvaídos), y no ve la 14.
- **C solo separa la 8.**

## Lo que esta calibración no garantiza

- **El umbral está ajustado sobre la muestra, sin validación externa.** Se eligió y se evaluó con las mismas 14 páginas, y las etiquetas salieron de la lectura del texto por un solo auditor. «Marca las tres malas» describe esta muestra; no es una medida de precisión.
- **Son 14 páginas de un solo libro.** El umbral es provisional hasta medirlo con otros libros.
- **El modelo de Tesseract cambia qué páginas salen malas.** Las imágenes que van al OCR resultaron idénticas en los dos entornos (diferencia máxima de 1 nivel de gris por píxel). Aun así, la página 14 salió casi limpia con `tessdata_fast` (entorno de desarrollo) y mala con `tessdata` (PC del autor). Por eso B no se pudo comparar con justicia en la 14. Hipótesis sin probar: el modelo `fast` u otro modelo lee mejor las líneas con resto de curva.
- **A mide la forma de las líneas, no los errores del OCR.** Una página puede salir mal por sombra o por baja resolución con las líneas rectas, y A no la verá.

## Nota: con JAX cambia el aplanado y la medida (14/11/2026)

Con JAX instalado, page-dewarp usa otro optimizador (L-BFGS-B con derivadas en vez de Powell): unas 8 veces más rápido y con mejor ajuste (objetivo final 0,0052 frente a 0,0078 en la página 8). La curva medida después de aplanar cambia:

| Pág. | Etiqueta | Curva con Powell | Curva con JAX |
|---|---|---|---|
| 4 | limpia | 0,76 (marcada) | bajo 0,55 (no marcada) |
| 8 | mala | 1,06 | 0,68 |
| 14 | mala | 0,66 | 0,70 |

Con JAX y el mismo umbral de 0,55, se marcan la 2, la 8 y la 14, sin la falsa alarma de la 4. La calidad del OCR (Tesseract en el entorno de desarrollo, 6 páginas pares) fue equivalente: palabras en minúscula válidas entre 95 y 99 % con los dos optimizadores. Esto es una medida más sobre la misma muestra; no cambia la salvedad de arriba.

## Banco de pruebas fijo (14/11/2026, versión 0.4.3)

Desde la 0.4.3, cada cambio se mide contra el mismo material antes de darse por bueno. El material es privado (libros con derechos) y no está en el repositorio.

| Material | Páginas | Palabras válidas 0.4.2 | 0.4.3 | Devueltas a la original | Páginas que no cuadran sin aviso: 0.4.2 → 0.4.3 |
|---|---|---|---|---|---|
| Tolkien, 14 páginas, fotos de celular | 14 | 3238 | 3238 | 0 | 0 → 0 |
| Tizard, 25 pliegos, origen no verificado | 43 | 18 844 | 19 279 | 8 | 0 → 0 |
| Hematología, 25 pliegos en foto | 46 | 4445 | 4589 | 8 | 6 → 0 |
| Páginas problema, 5 pliegos en foto | 9 | 584 | 837 | 3 | 4 → 0 |

«Palabras válidas»: palabras en minúscula de dos letras o más que existen en español según `wordfreq`. «No cuadra»: el paso 1 contó más líneas de texto que palabras sacó el OCR.

- **Lo que no cambió:** el texto de las 93 páginas que la 0.4.3 no devolvió a la original es idéntico, carácter por carácter, al de la 0.4.2.
- **El margen del 80 %** se eligió con este banco. Con comparación estricta (aplanada < original), el ruido de la lectura rápida devolvía a la original 33 de 38 páginas del Tizard y 5 de 14 del Tolkien. Con 80 % se devuelven 19 en total: 14 ganan palabras válidas y 5 pierden (la peor, de 61 a 16).
- **Salvedad:** el margen está ajustado sobre este mismo material. Falta medirlo con un libro que no se haya usado para ajustar nada.

Corrección del 14/11/2026 a la tabla de arriba: el Tolkien figuraba como «escáner» y son fotos de celular (el PDF lo generó `mlkit`, 258 ppp); el Tizard figuraba como «fotocopiado» y su origen no está verificado (el archivo no trae datos; 235 ppp). Esa tabla se midió en el entorno de desarrollo, con JAX 0.12.0.1, dato que entonces no se registró.

## 0.4.4 · Control de forma, pliegos con un lado vacío y registro del entorno (14/11/2026)

Desde esta versión el banco corre en la PC del autor (Windows 11, Intel Core i5-10400F, 32 GB, Python 3.13.5, JAX 0.12.0.1, optimizador L-BFGS-B, Tesseract 5.5.3). Cuatro muestras, 128 páginas de PDF: Tolkien (14, fotos de celular), Tizard (25 pliegos, origen no verificado), hematología (25 pliegos, fotos de 180 ppp) y páginas problema (7 pliegos de hematología; los pliegos 29 y 30 se agregaron este día). Las listas de páginas están en `muestras.json` del banco, fuera del repositorio.

### Distribución del tamaño de salida

Proporción entre el tamaño de la página aplanada y el de la entrada (la mayor de alto y ancho), en las 113 páginas donde page-dewarp llegó a calcularlo, con el control desactivado:

| Grupo | Páginas | Proporción |
|---|---|---|
| Aplanadas y aceptadas | 88 | mínima 0,90 · mediana 1,06 · percentil 90: 1,35 · máxima 2,62 |
| Desbocadas | 9 | 0,28 (con ancho 2,86) · 3,37 · 4,0 · 4,2 · 6,1 · 7,7 · 8,2 · 26 · 231 millones |

Las aceptadas más grandes son legítimas: las cuatro páginas curvas del Tolkien (1,75 a 1,98) y una del Tizard (2,62, que lee 131 palabras contra 133 de la original). El rango elegido, **0,5 a 3,0**, deja dentro las 88 y fuera las 9. El margen por arriba es estrecho (2,62 frente a 3,37) y está ajustado sobre este mismo material.

### Banco: 0.4.3 frente a 0.4.4

| Muestra | Páginas de salida | Aplanadas | Devueltas por lectura | Descartadas por tamaño | Errores de memoria | Marcadas | Palabras válidas | Tiempo (s) |
|---|---|---|---|---|---|---|---|---|
| Tolkien | 14 → 14 | 14 → 14 | 0 → 0 | 0 | 0 → 0 | 4 → 4 | 3220 → 3220 | 51 → 61 |
| Tizard | 43 → 47 | 30 → 33 | 8 → 3 | 3 | 0 → 0 | 12 → 9 | 18 889 → 18 890 | 320 → 162 |
| Hematología | 46 → 48 | 33 → 34 | 6 → 4 | 1 | 0 → 0 | 18 → 19 | 4429 → 4436 | 118 → 125 |
| Páginas problema | 13 → 14 | 7 → 7 | 4 → 1 | 5 | 2 → 0 | 8 → 9 | 1364 → 1350 | 56 → 41 |
| **Total** | 116 → 123 | 84 → 88 | 18 → 8 | 9 | 2 → 0 | 42 → 41 | 27 902 → 27 896 | 545 → 388 |

- **Lo que no cambió:** de las 109 páginas de salida que conservan la misma estructura, 103 tienen el texto idéntico, carácter por carácter. Las 6 que difieren son las que pasaron de «aceptada» o «devuelta por lectura» a «descartada por tamaño». Páginas donde se contaron más líneas que palabras y quedaron sin aviso: 0 en las dos versiones.
- **Palabras válidas:** no mejoran (−6 en 27 902). La 0.4.4 no lee más; evita construir páginas inservibles, parte bien los pliegos y tarda un 29 % menos en este banco.
- **Las 14 palabras válidas que pierde «páginas problema»:** el pliego 29 izquierda (−8) se aceptaba aplanado con tamaño ×6,1 y esa versión gigante se leía algo mejor que la original (156 frente a 148); el pliego 118 (−3) antes fallaba por memoria y se leía entero, y ahora se parte; el resto son diferencias de 1 o 2 palabras.
- **Por qué difieren en 1 o 2 palabras las páginas que usan la original en las dos versiones:** una página devuelta por lectura conserva la imagen original tal cual; una descartada por tamaño conserva la original con el marco del color del papel que se le agrega antes de aplanar. Es la misma página con un borde distinto. Queda como está y se declara.
- **Pliegos que ahora se parten:** 4 del Tizard (páginas 1, 6, 10 y 60 del PDF; la 1 es la portada), 2 de hematología (104 y 110) y 1 de páginas problema (118). En el libro de hematología completo son 26 de 145; en el Tolkien, ninguno. Las páginas 1 y 2 de hematología (portada y portadilla) no cambian.
- **Páginas a la vez:** Tolkien 3 (límite: memoria libre, por sus páginas de 12 megapíxeles), Tizard 6 y páginas problema 6 (núcleos físicos), hematología 5 (memoria libre). Antes eran 8 siempre. El Tolkien tarda 10 s más por eso.
- **Lo que falta:** 8 páginas del banco se leen peor aplanadas con tamaño normal (por ejemplo, hematología pliego 80 izquierda: proporción 1,04, 0 palabras contra 85). La causa no está identificada; las cubre la comparación de lectura de la 0.4.3.

