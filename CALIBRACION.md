# Calibración del aviso «REVISAR A MANO» (v0.2.0, 14/11/2026)

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

En `aplanar_libro/calidad.py`:
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
