# Feanor validation

**English** · [Español](VALIDACION.md)

Version 0.6.0 (2026-11-24). This document maps each measured result and each behaviour claimed in the [README](../README.md) to what supports it. Parameters (thresholds, defaults, maximums) are design decisions: the README states them, and those that come from a measurement are listed below with it. What has no support is under «What is not validated».

**Types of support**

- **Test:** an automated test in `tests/test_basico.py`. It builds a small case with invented text (except for a few one-line fragments from the bench books, which reproduce the shape of a real error) and fails if Feanor stops doing what is claimed. Run with `python -m pytest -q`; in 0.6.0 there are 43 and all 43 pass, none skipped, on Linux (development environment) and on Windows (the author's PC, 2026-11-24). On Windows the author runs them before each commit. A test shows that the rule does what it says in that case, not that it is right on all real material.
- **Measurement:** a measurement with real material (books, phone photos, theses), with its date and sample, in [CALIBRACION.md](../CALIBRACION.md) or in the «Con qué se probó» ("what it was tested with") section of the version in the [CHANGELOG](../CHANGELOG.md) (both in Spanish). It describes that sample; it is not a general error rate.

Test names are in Spanish, as in the code.

## Claims and their support

### Page type and route

| # | Claim | Support | Type |
|---|---|---|---|
| 1 | Each page is classified as digital, earlier OCR, uncertain, scanned or empty | `test_tipo_de_cada_pagina` | Test |
| 2 | A PDF that already has text goes straight to Markdown, without flattening or OCR, and the `.md` says where the text comes from; one made of photos without text does not take that route | `test_ruta_digital_de_punta_a_punta` | Test |

### Output and record

| # | Claim | Support | Type |
|---|---|---|---|
| 3 | PDF, Word and PowerPoint leave their `.md` and `.json` in their own folder; the same file replaces its folder and a different one with the same name goes to `_2` | `test_salida_en_su_carpeta_con_json` | Test |
| 4 | The `.md` marks each page and carries the review warnings | `test_markdown_marca_paginas_y_avisos`, `test_markdown_lleva_aviso` | Test |
| 5 | Cleaning removes noise and the folio without losing the last number of a table of contents | `test_limpiar_quita_ruido_y_folio`, `test_indice_que_termina_en_numero_no_pierde_datos` | Test |
| 6 | Words split by a hyphen are joined, compounds are kept, and a stray letter does not break the join | `test_nombre_cortado_se_une_y_compuesto_se_conserva`, `test_letra_suelta_no_rompe_la_union`, `test_letra_suelta_en_indice_se_conserva` | Test |
| 7 | A URL, DOI or e-mail address split by a hyphen is left as is | `test_enlace_cortado_con_guion_no_se_une` | Test |
| 8 | The printed folio is deduced from the sequence, is not invented without a sequence, and withstands gaps, «Capítulo 1» in the header and «66- » in the footer | `test_folio_por_secuencia`, `test_sin_secuencia_no_inventa_folios`, `test_folio_con_salto_y_capitulo`, `test_folio_con_guion_y_espacio_no_tumba_la_corrida` | Test |

### Scanned books

| # | Claim | Support | Type |
|---|---|---|---|
| 9 | A spread comes out as left then right; one with an empty side is also split | `test_pliego_sale_izquierda_y_luego_derecha`, `test_pliego_con_un_lado_vacio_tambien_se_parte` | Test |
| 10 | Cropping removes junk at the edge and keeps the text | `test_recorte_quita_basura_y_conserva_texto` | Test |
| 11 | The curvature measure tells a straight line from a curved one | `test_curva_recta_vs_curva` | Test |
| 12 | The «REVISAR A MANO» warning for remaining curvature flagged the 3 bad pages out of 14, with 1 false alarm | CALIBRACION.md, section 0.2.0 (2026-11-14) | Measurement |
| 13 | A page with lines of text that produced no text is flagged | `test_pagina_con_lineas_y_sin_texto_se_marca` | Test |
| 14 | The quick read comparing flattened and original pages tells a page with text from a blank one | `test_lectura_rapida_distingue_texto_de_blanco` | Test |
| 15 | Of 19 pages sent back to the original by the 80% rule, 14 gained valid words and 5 lost some | CALIBRACION.md, section 0.4.3 (8 + 8 + 3; the section does not say which machine it was measured on). On the author's PC, the 2026-11-24 audit counted 18 (8 + 6 + 4): the result changes between machines | Measurement |
| 15b | That check made the full run take between 15% and 70% longer, depending on the book | README since 0.4.3; no table of its own in CALIBRACION.md | Measurement, no table in the repository |
| 16 | The shape check (0.5 to 3.0) separates the largest good page (2.62) from the smallest bad one (3.37) | CALIBRACION.md, section 0.4.4, «Distribución del tamaño de salida» | Measurement |
| 16b | Size explains 9 of the 17 bench pages that read worse when flattened | README since 0.4.4; the figure has no table of its own in CALIBRACION.md | Measurement, no table in the repository |
| 16c | A page discarded for size may read slightly worse than its giant version (one went from 156 to 148 valid words) | CALIBRACION.md, section 0.4.4, «Banco: 0.4.3 frente a 0.4.4» | Measurement |
| 16d | With the same versions, a difficult page gave different results on two machines | README since 0.4.4; no table in the repository | Measurement, no table in the repository |
| 16e | Pages rotated by 90° are detected, but in the test OCRmyPDF was not confident enough to straighten them | README since 0.4.0; no table in the repository | Measurement, no table in the repository |
| 17a | Phone-photographed book, 14 pages: flat pages come out almost perfect without flattening; curved ones, unflattened, come out useless; flattened, six of seven are legible and in order; on the page checked by hand, about 97% of the words are correct; one table-of-contents page could not be flattened | README, «What was measured» (2026-11-13) | Measurement, no table in the repository |
| 17 | With `-l spa`, the accents and ñ that `-l spa+eng` lost (about 40%) come back | README, «What was measured» (2026-11-13). The README says «all» came back; the exact count was not kept | Measurement, no table in the repository |
| 18 | Evening out the lighting in phone photos raised valid words from 87.2% to 89.7% (25 spreads) | README since 0.4.2 (git tag `v0.4.2`); no table of its own in CALIBRACION.md | Measurement, no table in the repository |
| 19 | With JAX, flattening drops from about 25–30 s to about 4 s per page, with equivalent OCR quality | Times: README since 0.3.0. Quality: CALIBRACION.md, «Nota: con JAX cambia el aplanado y la medida» (95–99% valid words with both optimisers, 6 pages) | Measurement |

### Word and PowerPoint

| # | Claim | Support | Type |
|---|---|---|---|
| 20 | Word: headings, lists, a table with a merged cell; text deleted with track changes does not appear | `test_word_a_markdown` | Test |
| 21 | Word: numbered lists keep their number and bulleted lists stay bulleted | `test_word_listas_numeradas` | Test |
| 22 | PowerPoint: a slide in columns, a table and notes in reading order; a «label: value» list is read row by row | `test_powerpoint_a_markdown`, `test_powerpoint_rotulo_valor_se_lee_por_filas` | Test |
| 23 | PowerPoint: a slide with text pasted as an image is OCR'd and marked; a small logo is not read; a photo without text is only recorded | `test_powerpoint_lee_texto_de_imagenes` | Test |
| 24 | A line that is just a number reaches the `.md` marked with «[?]», not deleted; "word shape" is decided without a dictionary | `test_powerpoint_numero_suelto_llega_marcado`, `test_forma_de_palabra` | Test |

### References

| # | Claim | Support | Type |
|---|---|---|---|
| 25 | The right references heading is taken (the one in the table of contents does not count) and the section ends before the appendices; without a heading, nothing is invented | `test_referencias_por_titulo` | Test |
| 26 | The rule handles the cases seen in calibration: an attached article with its own references, a table of contents without numbers and a typo in the real heading, the UNMSM page saying how to cite, years on their own line | `test_referencias_casos_de_la_calibracion` (invented text, same shape) | Test |
| 27 | On the 80 calibration theses, the 0.5.5 rule changes the cut in 16, all of them corrections; theses without a heading drop from 7 to 1 | CHANGELOG, 0.5.5, «Con qué se probó» | Measurement |
| 27b | A bibliography numbered with each entry's number on its own line still looks like a table of contents (1 of 80 theses) | CHANGELOG, 0.5.5, «Límites declarados» (thesis 12727_2897) | Measurement |

### Batch mode

| # | Claim | Support | Type |
|---|---|---|---|
| 28 | One result per PDF; the scanned one is set aside, the broken PDF fails without stopping the batch, and on the second run finished work is skipped | `test_lote_una_salida_por_pdf` | Test |
| 29 | With the CSV: each result carries its metadata; nothing outside 2015–2017, with a different SHA-256, with a failed download or without a row is processed; everything goes to the exact folder | `test_lote_con_metadatos_y_candado` | Test |
| 30 | The body leaves out the repeated header, the table of contents, the references and the appendices | `test_cuerpo_sin_margenes_repetidos_ni_referencias` | Test |
| 31 | A thesis with visible text over full-page photos comes out «digital» but is flagged for review | `test_lote_marca_texto_sobre_foto` | Test |
| 32 | With `--auto`, each file gets its method; files of another type or damaged go to failures with their reason; without `--auto`, batch mode works as in 0.5.3 | `test_lote_automatico_un_metodo_por_archivo` | Test |
| 33 | A scanned page with a short stamp is read in full; an image with nothing to read stays «no se leyó» and goes to the alerts | `test_auto_lee_la_pagina_escaneada_aunque_traiga_sello` | Test |
| 34 | In a PDF with earlier OCR and one scanned page, the earlier layer is kept and only the scanned page goes through Feanor's OCR | `test_auto_capa_ocr_previa_mas_paginas_escaneadas` | Test |
| 35 | If a page that was not requested comes out with different text after OCR, the `.md` uses the original's page and it goes to the alerts | `test_auto_pagina_nativa_alterada_por_el_ocr_se_toma_del_original` (OCRmyPDF simulated) | Test |
| 36 | With `--output-type pdf`, in a mixed PDF, the native pages come out with identical text | `test_auto_ocr_con_salida_pdf_sin_paginas_alteradas` | Test |
| 37 | `_lote.json` stores the command line; the alert separates «solo espacios» (spacing only) from «cambian palabras» (words change) | `test_lote_guarda_comando_y_separa_alertas` (OCRmyPDF simulated) | Test |
| 37b | `--output-type pdf` does not prevent every alteration: in one calibration thesis, a bullet from the font disappears on rewriting | CHANGELOG, 0.5.5, «Con qué se probó» (thesis 7659, 5 pages in both modes) | Measurement |
| 37c | On the author's PC, with Ghostscript, `--output-type pdf` leaves untouched the non-requested pages that «auto» altered: 7172, from 89 altered to 0; 4309, from 4 to 0; 7659 still has the same 5 in both modes (the bullet) | `banco/diagnostico_output_type.py`, run on 2026-11-24 (Feanor 0.5.5, OCRmyPDF 17.14.1, Tesseract 5.5.3, Ghostscript 10.08.0); output kept by the author | Measurement |
| 38 | The forced comparison takes body pages, reads them as images and gives the word error rate | `test_comparacion_ocr_con_paginas_del_cuerpo`, `test_distancia_y_tasa_de_error_por_palabra` | Test |
| 39 | Ligatures and end-of-line hyphens neither count as errors nor split words | `test_ligaduras_y_guion_no_cuentan_como_error_ni_parten_palabras` | Test |

## What is not validated

- **No general error rate.** The measurements describe their sample (14 pages of one book, 25 spreads, 80 theses from three years). They do not say how wrong Feanor is with another book, another camera or another repository.
- **The thresholds were tuned on the same sample they were evaluated on** (curvature 0.55; reading 80%; shape 0.5 to 3.0), with no external validation. See CALIBRACION.md.
- **OCR of scanned pages in batch mode** is checked in the tests with small cases. On real theses it is only measured with the forced comparison, which reads as images pages that do have native text: an approximation of the error, not the error on scanned pages.
- **`--output-type pdf` on other theses.** The measurement on the author's PC (row 37c) covers 3 theses. That is why the altered-page check still runs on every batch.
- **Reproducibility across computers.** On difficult pages, flattening gave different results on two machines with the same versions. That is why each `.json` stores the full environment.
- **macOS.** The automated tests are run on Linux (development environment) and on Windows (the author's PC, where Feanor is used). macOS has not been tested.
- **Languages other than Spanish.** `--idioma` exists, but all measurements are in Spanish.
- **References one by one.** Feanor only locates the section; it does not split or check each reference.

## How to reproduce

```
python -m pip install pytest
python -m pytest -q
```

For the `--output-type` diagnostic with your own PDFs (it does not write next to them):

```
python banco\diagnostico_output_type.py "path\to\one.pdf" "path\to\another.pdf"
```

The material behind the measurements (books and theses) is not in the repository: the books are copyrighted, and the theses are downloaded from their institutional repositories by handle.
