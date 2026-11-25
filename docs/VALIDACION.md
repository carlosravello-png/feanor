# Validación de Feanor

[English](VALIDATION.md) · **Español**

Versión 0.6.2 (24/11/2026). Este documento cruza cada resultado medido y cada comportamiento que afirma el [README](../README.es.md) con lo que lo respalda. Los parámetros (umbrales, valores por defecto, máximos) son decisiones de diseño: el README dice cuáles son, y los que salen de una medición están abajo con ella. Lo que no tiene respaldo está en «Lo que no está validado».

**Tipos de respaldo**

- **Prueba:** una prueba automática de `tests/test_basico.py`. Arma un caso pequeño con texto inventado (salvo algunos fragmentos de una línea de los libros del banco, que reproducen la forma de un error real) y falla si Feanor deja de hacer lo que se afirma. Se corre con `python -m pytest -q`; son 43. Con la 0.6.0 pasaron las 43, sin ninguna saltada, en Linux (entorno de desarrollo) y en Windows (la PC del autor, 24/11/2026). Desde la 0.6.1 corren además en GitHub en cada cambio (`.github/workflows/tests.yml`); el resultado de cada corrida es público en la pestaña Actions del repositorio y en el badge «tests» del README. Una prueba muestra que la regla hace lo que dice en ese caso, no que acierte en todo material real.
- **Medición:** una medición con material real (libros, fotos de celular, tesis), con su fecha y su muestra, en [CALIBRACION.md](../CALIBRACION.md) o en la sección «Con qué se probó» de la versión en el [CHANGELOG](../CHANGELOG.md). Describe esa muestra; no es una tasa de error general.

## Afirmaciones y su respaldo

### Tipo de página y ruta

| # | Afirmación | Respaldo | Tipo |
|---|---|---|---|
| 1 | Cada página se clasifica como digital, OCR previo, dudosa, escaneada o vacía | `test_tipo_de_cada_pagina` | Prueba |
| 2 | Un PDF que ya trae texto pasa directo a Markdown, sin aplanar ni OCR, y el `.md` dice de dónde sale el texto; uno de fotos sin texto no toma esa ruta | `test_ruta_digital_de_punta_a_punta` | Prueba |

### Salida y registro

| # | Afirmación | Respaldo | Tipo |
|---|---|---|---|
| 3 | PDF, Word y PowerPoint dejan su `.md` y su `.json` en una carpeta propia; el mismo archivo reemplaza su carpeta y otro con el mismo nombre va a `_2` | `test_salida_en_su_carpeta_con_json` | Prueba |
| 4 | El `.md` marca cada página y lleva los avisos de revisión | `test_markdown_marca_paginas_y_avisos`, `test_markdown_lleva_aviso` | Prueba |
| 5 | La limpieza quita el ruido y el folio sin perder el último número de un índice | `test_limpiar_quita_ruido_y_folio`, `test_indice_que_termina_en_numero_no_pierde_datos` | Prueba |
| 6 | Las palabras cortadas con guion se unen, los compuestos se conservan y una letra suelta no rompe la unión | `test_nombre_cortado_se_une_y_compuesto_se_conserva`, `test_letra_suelta_no_rompe_la_union`, `test_letra_suelta_en_indice_se_conserva` | Prueba |
| 7 | Una URL, un DOI o un correo cortado con guion se deja tal cual | `test_enlace_cortado_con_guion_no_se_une` | Prueba |
| 8 | El folio impreso se deduce de la secuencia, no se inventa sin secuencia y aguanta saltos, «Capítulo 1» en el encabezado y «66- » en el pie | `test_folio_por_secuencia`, `test_sin_secuencia_no_inventa_folios`, `test_folio_con_salto_y_capitulo`, `test_folio_con_guion_y_espacio_no_tumba_la_corrida` | Prueba |

### Libros escaneados

| # | Afirmación | Respaldo | Tipo |
|---|---|---|---|
| 9 | Un pliego sale como izquierda y luego derecha; uno con un lado vacío también se parte | `test_pliego_sale_izquierda_y_luego_derecha`, `test_pliego_con_un_lado_vacio_tambien_se_parte` | Prueba |
| 10 | El recorte quita la basura del borde y conserva el texto | `test_recorte_quita_basura_y_conserva_texto` | Prueba |
| 11 | La medida de curva distingue una línea recta de una curva | `test_curva_recta_vs_curva` | Prueba |
| 12 | El aviso «REVISAR A MANO» por resto de curva marcó las 3 páginas malas de 14, con 1 falsa alarma | CALIBRACION.md, sección 0.2.0 (14/11/2026) | Medición |
| 13 | Una página con líneas de texto de la que no salió texto se marca | `test_pagina_con_lineas_y_sin_texto_se_marca` | Prueba |
| 14 | La lectura rápida que compara aplanada y original distingue una página con texto de una vacía | `test_lectura_rapida_distingue_texto_de_blanco` | Prueba |
| 15 | De 19 páginas devueltas a la original por la regla del 80 %, 14 ganaron palabras válidas y 5 perdieron algunas | CALIBRACION.md, sección 0.4.3 (8 + 8 + 3; la sección no dice en qué máquina se midió). En la PC del autor, la auditoría del 24/11/2026 contó 18 (8 + 6 + 4): el resultado cambia entre máquinas | Medición |
| 15b | Esa comprobación hizo tardar la corrida completa entre un 15 % y un 70 % más, según el libro | README desde la 0.4.3; sin tabla propia en CALIBRACION.md | Medición, sin tabla en el repositorio |
| 16 | El control de forma (0,5 a 3,0) separa la página buena más grande (2,62) de la mala más chica (3,37) | CALIBRACION.md, sección 0.4.4, «Distribución del tamaño de salida» | Medición |
| 16b | El tamaño explica 9 de las 17 páginas del banco que se leen peor aplanadas | README desde la 0.4.4; la cifra no tiene tabla propia en CALIBRACION.md | Medición, sin tabla en el repositorio |
| 16c | Una página descartada por tamaño puede leerse algo peor que su versión gigante (una pasó de 156 a 148 palabras válidas) | CALIBRACION.md, sección 0.4.4, «Banco: 0.4.3 frente a 0.4.4» | Medición |
| 16d | Con las mismas versiones, una página difícil dio resultados distintos en dos máquinas | README desde la 0.4.4; sin tabla en el repositorio | Medición, sin tabla en el repositorio |
| 16e | Las páginas giradas 90° se detectan, pero en la prueba OCRmyPDF no tuvo confianza suficiente para enderezarlas | README desde la 0.4.0; sin tabla en el repositorio | Medición, sin tabla en el repositorio |
| 17a | Libro fotografiado, 14 páginas: las planas salen casi perfectas sin aplanar; las curvas, sin aplanar, salen inservibles; aplanadas, seis de siete quedan legibles y en orden; en la página revisada a mano, cerca del 97 % de las palabras salen correctas; una página de índice no se pudo aplanar | README, «Lo que se midió» (13/11/2026) | Medición, sin tabla en el repositorio |
| 17 | Con `-l spa` vuelven las tildes y eñes que `-l spa+eng` perdía (cerca del 40 %) | README, «Lo que se midió» (13/11/2026). El README dice que volvieron «todas»; el recuento exacto no se conservó | Medición, sin tabla en el repositorio |
| 18 | Igualar la luz en fotos de celular subió las palabras válidas de 87,2 % a 89,7 % (25 pliegos) | README desde la 0.4.2 (etiqueta git `v0.4.2`); sin tabla propia en CALIBRACION.md | Medición, sin tabla en el repositorio |
| 19 | Con JAX, el aplanado baja de unos 25–30 s a unos 4 s por página, con calidad de OCR equivalente | Tiempos: README desde la 0.3.0. Calidad: CALIBRACION.md, «Nota: con JAX cambia el aplanado y la medida» (95–99 % de palabras válidas con los dos optimizadores, 6 páginas) | Medición |

### Word y PowerPoint

| # | Afirmación | Respaldo | Tipo |
|---|---|---|---|
| 20 | Word: títulos, listas, tabla con celda combinada; el texto borrado con control de cambios no aparece | `test_word_a_markdown` | Prueba |
| 21 | Word: las listas numeradas conservan su número y las de viñetas siguen como viñetas | `test_word_listas_numeradas` | Prueba |
| 22 | PowerPoint: diapositiva en columnas, tabla y notas en orden de lectura; una lista «rótulo: valor» se lee por filas | `test_powerpoint_a_markdown`, `test_powerpoint_rotulo_valor_se_lee_por_filas` | Prueba |
| 23 | PowerPoint: una lámina con texto pegada como imagen se lee con OCR y va marcada; un logo chico no se lee; una foto sin texto queda anotada | `test_powerpoint_lee_texto_de_imagenes` | Prueba |
| 24 | Un renglón que es solo un número llega al `.md` marcado con «[?]», no se borra; «forma de palabra» se decide sin diccionario | `test_powerpoint_numero_suelto_llega_marcado`, `test_forma_de_palabra` | Prueba |

### Referencias

| # | Afirmación | Respaldo | Tipo |
|---|---|---|---|
| 25 | Se toma el título de referencias que corresponde (el del índice no cuenta) y la sección termina antes de los anexos; sin título, no se inventa | `test_referencias_por_titulo` | Prueba |
| 26 | La regla resuelve los casos vistos en la calibración: artículo anexado con sus referencias, índice sin números con errata en el título, página de UNMSM que dice cómo citar, años en su propia línea | `test_referencias_casos_de_la_calibracion` (texto inventado, misma forma) | Prueba |
| 27 | En las 80 tesis de calibración, la regla de la 0.5.5 cambia el corte en 16, todas correcciones; las tesis sin título bajan de 7 a 1 | CHANGELOG, 0.5.5, «Con qué se probó» | Medición |
| 27b | Una bibliografía numerada con el número de cada referencia en su propia línea sigue pareciendo un índice (1 de 80 tesis) | CHANGELOG, 0.5.5, «Límites declarados» (la tesis 12727_2897) | Medición |

### Modo lote

| # | Afirmación | Respaldo | Tipo |
|---|---|---|---|
| 28 | Un resultado por PDF; la escaneada se aparta, el PDF roto falla sin tumbar el lote y en la segunda corrida lo hecho se salta | `test_lote_una_salida_por_pdf` | Prueba |
| 29 | Con el CSV: cada resultado lleva sus metadatos; no se procesa lo que está fuera de 2015–2017, con SHA-256 distinto, con descarga fallida o sin fila; todo va a la carpeta exacta | `test_lote_con_metadatos_y_candado` | Prueba |
| 30 | El cuerpo deja fuera el encabezado repetido, el índice, las referencias y los anexos | `test_cuerpo_sin_margenes_repetidos_ni_referencias` | Prueba |
| 31 | Una tesis con texto visible sobre fotos de página completa sale «digital», pero se marca para revisar | `test_lote_marca_texto_sobre_foto` | Prueba |
| 32 | Con `--auto`, cada archivo con su método; los de otro tipo o dañados van a fallos con su motivo; sin `--auto`, el lote sigue como en la 0.5.3 | `test_lote_automatico_un_metodo_por_archivo` | Prueba |
| 33 | Una página escaneada con un sello corto se lee entera; una imagen sin nada que leer queda «no se leyó» y va a las alertas | `test_auto_lee_la_pagina_escaneada_aunque_traiga_sello` | Prueba |
| 34 | En un PDF con OCR previo y una página escaneada, la capa previa se conserva y solo la escaneada pasa por el OCR de Feanor | `test_auto_capa_ocr_previa_mas_paginas_escaneadas` | Prueba |
| 35 | Si una página no pedida sale con otro texto tras el OCR, el `.md` usa la del original y va a las alertas | `test_auto_pagina_nativa_alterada_por_el_ocr_se_toma_del_original` (OCRmyPDF simulado) | Prueba |
| 36 | Con `--output-type pdf`, en un PDF mixto, las páginas nativas salen con el texto idéntico | `test_auto_ocr_con_salida_pdf_sin_paginas_alteradas` | Prueba |
| 37 | `_lote.json` guarda la línea de comandos; la alerta separa «solo espacios» de «cambian palabras» | `test_lote_guarda_comando_y_separa_alertas` (OCRmyPDF simulado) | Prueba |
| 37b | `--output-type pdf` no evita todas las alteraciones: en una tesis de la calibración, una viñeta del tipo de letra desaparece al reescribir | CHANGELOG, 0.5.5, «Con qué se probó» (la tesis 7659, 5 páginas en los dos modos) | Medición |
| 37c | En la PC del autor, con Ghostscript, `--output-type pdf` deja intactas las páginas no pedidas que «auto» alteraba: 7172, de 89 alteradas a 0; 4309, de 4 a 0; 7659 sigue con las mismas 5 en los dos modos (la viñeta) | `banco/diagnostico_output_type.py`, corrido el 24/11/2026 (Feanor 0.5.5, OCRmyPDF 17.14.1, Tesseract 5.5.3, Ghostscript 10.08.0); salida guardada por el autor | Medición |
| 38 | La comparación forzada toma páginas del cuerpo, las lee como imagen y da la tasa de error por palabra | `test_comparacion_ocr_con_paginas_del_cuerpo`, `test_distancia_y_tasa_de_error_por_palabra` | Prueba |
| 39 | Ligaduras y guion de fin de línea no cuentan como error ni parten palabras | `test_ligaduras_y_guion_no_cuentan_como_error_ni_parten_palabras` | Prueba |

## Lo que no está validado

- **Ninguna tasa de error general.** Las mediciones describen su muestra (14 páginas de un libro, 25 pliegos, 80 tesis de tres años). No dicen cuánto se equivoca Feanor con otro libro, otra cámara u otro repositorio.
- **Los umbrales están ajustados sobre la misma muestra con que se evaluaron** (curva 0,55; lectura 80 %; forma 0,5 a 3,0), sin validación externa. Ver CALIBRACION.md.
- **El OCR de las páginas escaneadas en el lote** se comprueba en las pruebas con casos pequeños. En las tesis reales solo se mide con la comparación forzada, que lee como imagen páginas que tienen texto nativo: es una aproximación del error, no el error de las páginas escaneadas.
- **`--output-type pdf` en otras tesis.** La medición en la PC del autor (fila 37c) cubre 3 tesis. Por eso la comprobación de páginas alteradas sigue en cada corrida.
- **Reproducibilidad entre computadoras.** En páginas difíciles, el aplanado dio resultados distintos en dos máquinas con las mismas versiones. Por eso cada `.json` guarda el entorno completo.
- **macOS.** Las pruebas automáticas se corren en Linux (entorno de desarrollo) y en Windows (la PC del autor, donde se usa). macOS no se ha probado.
- **Idiomas distintos del español.** `--idioma` existe, pero las mediciones son todas en español.
- **Las referencias una por una.** Feanor solo localiza la sección; no separa ni verifica cada referencia.

## Cómo reproducir

```
python -m pip install pytest
python -m pytest -q
```

Para el diagnóstico de `--output-type` con tus propios PDF (no escribe junto a ellos):

```
python banco\diagnostico_output_type.py "ruta\a\uno.pdf" "ruta\a\otro.pdf"
```

El material de las mediciones (libros y tesis) no está en el repositorio: los libros tienen derechos de autor, y las tesis se bajan de sus repositorios institucionales con su handle.
