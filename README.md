# Feanor

**English** · [Español](README.es.md)

[![tests](https://github.com/carlosravello-png/feanor/actions/workflows/tests.yml/badge.svg)](https://github.com/carlosravello-png/feanor/actions/workflows/tests.yml) [![License: MIT](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

Feanor turns scanned or photographed books, thesis PDFs, Word documents and PowerPoint presentations in Spanish into Markdown, so they can be read, searched or handed to an AI. With photos of books, it straightens pages that curve towards the spine before reading them.

- **Version:** 0.6.2 (2026-11-24). History in [CHANGELOG.md](CHANGELOG.md) (in Spanish).
- **Name:** the tool is called **Feanor**; the Python package is `feanor_el_aplasta_libros` (on pip, `feanor-el-aplasta-libros`; the name means "Feanor, the book flattener"). Up to 0.5.5 it was called `aplanar-libro`.
- **Status:** research software, in use in the author's own study of Spanish-language theses. What it guarantees and what it does not is under [Verification](#verification) and [Known limits](#known-limits).
- **Most important:** Feanor does not produce verified text. Figures, doses, quotations and names must always be checked against the original.
- **Language:** the code, its comments and the messages Feanor prints are in Spanish, because the tool is built for Spanish-language material. This README and [docs/VALIDATION.md](docs/VALIDATION.md) are in English; the other documents are in Spanish.

## What it does

| Input | What Feanor does | Output |
|---|---|---|
| PDF with text (born-digital or with an earlier OCR layer) | Copies the text it already has, without OCR, and records where each page's text comes from | `.md` + `.json` |
| Scanned PDF or photos of a book | Prepares, flattens and OCRs the pages in Spanish | `.md` + `.json` + flattened PDF and OCR'd PDF |
| Mixed PDF (in batch mode `--auto`) | Native text where there is any, and OCR without flattening only on the image-only pages | `.md` + `.json` |
| Word (`.docx`) | Copies the text in order, with headings, lists, tables and footnotes | `.md` + `.json` |
| PowerPoint (`.pptx`) | Copies the text of each slide and its notes; OCRs images that contain text | `.md` + `.json` |
| A whole folder | One result per file plus a batch summary | one folder per file + `_lote.md`, `_lote.csv`, `_lote.json` |

For a scanned book it runs these steps in a row:

0. **Prepare** (since version 0.4.0): splits two-page spreads scanned with the book open, leaves blank pages untouched and flags pages rotated by 90°.
1. **Flatten**: straightens curved pages before OCR.
2. **Read**: runs OCR with the settings that work for Spanish.
3. **Markdown**: writes the text page by page, with the viewer page number and warnings on pages that need checking by hand.

## Installation (Windows, Anaconda Prompt)

External requirements (once):

```
winget install -e --id tesseract-ocr.tesseract
winget install -e --id astral-sh.uv
uv tool install ocrmypdf
uv tool update-shell
```

- **Ghostscript (64-bit, AGPL licence):** install it by hand from [ghostscript.com](https://ghostscript.com/releases/gsdnld.html).
- **Spanish language data:** if `C:\Program Files\Tesseract-OCR\tessdata\spa.traineddata` does not exist, download it from [tesseract-ocr/tessdata](https://github.com/tesseract-ocr/tessdata) and copy it there. Administrator rights are needed.

Feanor:

```
python -m pip install git+https://github.com/carlosravello-png/feanor.git
```

If you had an earlier version installed under the name `aplanar-libro`, uninstall it first: `python -m pip uninstall aplanar-libro`.

To flatten faster (from about 25–30 seconds to about 4 per curved page; see [Known limits](#known-limits)): `python -m pip install "jax[cpu]"`.

## Usage

```
feanor "libro.pdf"
```

This is the same as `python -m feanor_el_aplasta_libros "libro.pdf"`.

### Type of each page

Before anything else, Feanor checks where the text of each page comes from:

| Page type (as written in the output) | What it is | What Feanor does |
|---|---|---|
| digital | The text is original (Word, the publisher) | Copies it as is |
| OCR previo (earlier OCR) | A photo that another program already put text on | Copies it and warns that it may contain errors |
| dudosa (uncertain) | A mix of the two above | Copies it and warns |
| escaneada (scanned) | A photo with no text | Flattens it and reads it |
| vacía (empty) | Neither text nor images | Nothing |

If most pages already have text, it takes the **digital route**: straight to Markdown, in seconds, with no flattening and no OCR, and the header of the `.md` says which pages are of each type (image-only pages are recorded as not read). If most pages are photos without text, it takes the full route. To read a PDF that already has text with Feanor's own OCR (for example, a poor earlier OCR): `--releer`. With `--solo` or `--paginas` this check is not done.

### Where the results go

Each file leaves its results in its own folder inside **`D:\FEANOR_salida`** (another one with `--salida <folder>`; if there is no `D:` drive, in a `FEANOR_salida` folder next to the original). For `libro.pdf`, the folder is `D:\FEANOR_salida\libro\`. If the same file (same SHA-256) is converted again, its folder is replaced; if it is a different file with the same name, it goes to `libro_2`, with a warning.

| File | Purpose |
|---|---|
| `libro.md` | The text in Markdown, to work with. Each page carries the viewer page number and, when it could be deduced, the printed folio of the book. In the body, spine-shadow noise and folios are removed, and words split by a hyphen are joined, except inside a URL, a DOI or an e-mail address. Table-of-contents pages are left uncleaned |
| `libro.json` | The record of the run (see below). All three formats leave it: PDF, Word and PowerPoint |
| `libro_referencias.md` | If found: the references section, as raw text |
| `libro_plano.pdf` | Full route only: the flattened pages, as images |
| `libro_ocr.pdf` | Full route only: the PDF with selectable text. This is the one used to check folios |
| `libro_informe.json` | Full route only: per page, whether it was flattened, why not, what size it came out and how much could be read before and after |

### What the `.json` contains

- The source file: name, path, size and SHA-256, so the result can be tied to the file even if the file is no longer kept.
- What it was made with: the Feanor version and its git commit (marked `sucio`, "dirty", if there were uncommitted changes), PyMuPDF, Tesseract and the language model file with its size and SHA-256 (two models with the same name read differently), OCRmyPDF, Ghostscript, Python and the operating system. The Feanor version is stored under the key `feanor`. On the full route, the `.json` and `libro_informe.json` also carry the key `aplanar_libro`, with the same version: it keeps the package's former name so that reports from before and after 0.6.0 can be compared with the same key.
- For PDFs, for each page of the original: its type and the measures behind the decision (words, fraction of invisible or covered text, coverage of the largest image), and the thresholds used, so the classification can be recomputed with other thresholds without opening the PDF.
- For PDFs, for each page of the `.md`: which page of the original it comes from, the folio and whether it was read or deduced, whether it was cleaned, the review warning if any, and **the raw text, with no cleaning at all**.
- For Word and PowerPoint: the summary (paragraphs, headings, tables, notes, images read, sparse or not read).
- How long it took.

### References

In a PDF, Feanor looks for the heading of the references section («Referencias», «Referencias bibliográficas», «Bibliografía», «Fuentes consultadas», «Literatura citada», «References», «Bibliography», with or without numbering in front, and with typos such as «Bibliogáficas»). These do not count: table-of-contents pages (with page numbers, or headed «Índice», «Esquema», «Contenido»), a line of lower-case prose, or the UNMSM page that says how to cite the thesis. If there are several headings, it takes the last one before the first «Anexos» (appendices) heading on a later page: an appendix can carry its own references (at UCV, the attached scientific article). The section ends before the first appendix heading. If found, the `.md` marks where the references start and end, and the section is copied to `libro_referencias.md` as **raw text**, with no cleaning. If not found, it says so. It only looks at the heading: it does not split or interpret the references one by one.

### Word

A Word document (`.docx`) is treated like a PowerPoint: the text is copied as is, in document order, with headings as Markdown headings, lists with their bullet or number, tables as tables, text boxes marked in place, and footnotes with their mark in the text and their content at the end. Images with text are OCR'd and marked, as in PowerPoint. Headers and footers, text deleted with track changes, and comments are not included. An old `.doc` must first be saved as `.docx`.

### PowerPoint

A PowerPoint presentation (`.pptx`) has nothing to flatten or OCR: the text of each slide is copied in reading order (column by column if the slide is laid out in columns), with its tables and the speaker notes. It leaves `clase.md` and `clase.json` in its output folder. If an image contains text (a slide made as a picture, a diagram), it is OCR'd and that text goes between its own markers, «texto leído con OCR» ("text read with OCR"), because it may contain errors; within that text, lines that contain no word-shaped word (a lone number, remains of an icon) are marked with «[?]» instead of being deleted. Each image records what happened to it: read, not read because it is very small (logos), with little text (kept whole, marked with «[?]»), without legible text, and how many lines were dropped for low confidence. Small logos are not read, and photos without legible text and charts are only recorded. In a diagram with arrows, the order of the text read may not follow the drawing. An old `.ppt` must first be saved as `.pptx`.

### Options

```
feanor "libro.pdf" --paginas pares        # flatten only even pages (or: impares, or 2,4,6)
feanor "libro.pdf" --releer               # read with Feanor's OCR even if the PDF already has text
feanor "libro.pdf" --solo aplanar         # a single step: aplanar | leer | markdown
feanor "articulo.pdf" --modo auto         # two-column documents
feanor "book.pdf" --idioma eng            # another language (only one, do not mix)
feanor "clase.pptx"                       # PowerPoint to Markdown
feanor "trabajo.docx"                     # Word to Markdown
feanor "libro.pdf" --nucleos 4            # pages flattened at once (default: by physical cores and free memory, max. 8)
```

## Batch mode: a whole folder

```
feanor "C:\path\thesis_folder"
feanor "C:\path\thesis_folder" --solo-digitales
feanor "C:\path\thesis_folder" --auto
```

Each PDF in the folder (subfolders are not entered) leaves its own output folder, just like a single file: its `.md`, its `.json` and, if found, its `_referencias.md`. **One result per file**, named after the file: if the PDFs are saved by their handle (`20.500.12692_12345.pdf`), the results are named by handle. Everything goes to `D:\FEANOR_salida\<folder name>\`.

- Without `--auto`, batch mode **never runs OCR**: a scanned PDF is set aside and listed, without being processed. With `--solo-digitales`, PDFs carrying an earlier OCR layer from another program are set aside too.
- Class of each PDF, from the type of its pages: **digital** if no page has an earlier OCR layer or is uncertain and there are more pages with text than scanned pages (a single scanned sheet, such as the approval page, does not change this: that page is not read and is recorded); **ocr_previo** if any page has an earlier OCR layer or is uncertain; **escaneada** if there are more scanned pages than pages with text.
- A broken PDF does not stop the batch: it is recorded as a failure, with the reason, and the technical details in `_errores.txt`.
- If the batch is interrupted, run it again the same way: PDFs already converted with the same Feanor version (same SHA-256) are skipped.
- At the end it leaves the batch summary: `_lote.md` (to read), `_lote.csv` (for Excel or R: one row per PDF with its status, class, pages of each type, page and heading of the references, time and SHA-256) and `_lote.json`, which also stores the command line used.

**Automatic batch (`--auto`).** Takes every file in the folder and uses the right method for each: born-digital PDF → native text; PDF with earlier OCR → that layer, marked; mixed PDF → native text where there is any and Feanor's OCR **without flattening** on the image-only pages (for example, the scanned approval page); scanned PDF → OCR without flattening; Word and PowerPoint → their usual route. A `.doc`, a `.ppt`, another file type or a damaged file is not processed and goes to the failures with the reason. The summary counts files by type and by method, and gives the word count of each. Without `--auto`, batch mode does what it did in 0.5.3: PDFs only and no OCR.

OCR without flattening uses OCRmyPDF with `--force-ocr` only on the image-only pages (`--pages`), with Tesseract's automatic page segmentation, so a scanned sheet with a text stamp on top is read in full. Each of those pages is then checked: if its text did not change, it is labelled not «OCR de Feanor» but «no se leyó» ("not read"), and goes to the alerts. And the other way round: since OCRmyPDF rewrites the whole PDF, every page that was not requested must come out with the same text as in the original; if it changed, the original's page is used and it goes to the alerts. The exact command is stored in the `.json`. Since 0.5.5, `--output-type pdf` is used, which rewrites the PDF as little as possible; even so, the check for altered pages stays, and it separates pages where only spacing changed from pages where words changed. Flattening is not used here: it is designed for photos of curved books and makes flat documents worse.

**Forced OCR comparison (`--comparar-ocr N`).** At the end of the batch it picks at random (`--semilla`, default 20261119) N born-digital PDFs and, from each, `--paginas-comparacion` body pages (default 10; pages that remain in the body with 150 words or more, so never the title page, the table of contents, the references or the appendices). It renders them as images, reads them with the same OCR without flattening (the exact command is recorded) and compares them with their native text, after normalising both in the same way (NFKC for ligatures, end-of-line hyphens joined): word error rate and character similarity, in `comparacion_ocr/`, with the text of each page alongside. If a chosen PDF has no body pages, it is replaced by the next one in the random order, and the summary says how many were requested and how many were measured.

**Batch with metadata (for a sampled corpus).** With `--metadatos lista.csv`, each PDF is joined to its CSV row by file name (required columns: `archivo`, `handle`, `universidad`, `carrera`, `anio`; optional: `titulo`, `estado`, `sha256`), and the `_lote.csv` and each thesis's `.json` carry those fields. No PDF is processed if it is not in the CSV, if its SHA-256 does not match the one recorded at download, or if its download is marked as failed. With `--anios 2015-2017`, neither is one whose year falls outside the range (the year lock). CSV rows without their PDF are listed. `--destino` puts everything in an exact folder.

**Body for lexical analysis (`--cuerpo`).** In batch mode, it also writes `<name>_cuerpo.md`: the text from the start up to the references heading (no references, no appendices), without table-of-contents pages and without repeated headers and footers (a line among the first 3 or last 3 of the page that appears, ignoring numbers and punctuation, in the margin of more than half of the pages; the same sentence inside the text is kept). The body is normalised with NFKC (the ligatures «ﬁ», «ﬂ» become their letters); the usual `.md` does not change and keeps the text as it is. With fewer than 3 pages of text no margin is removed. The `.json` says how many words and pages remained, how many margin lines were removed and which ones. **For manual review**, without removing them from the batch, these theses are flagged: those with visible text over full-page photos (a stamp over a scan), with fewer than 100 words per page in the body, without a references heading (the body then runs to the end), or with the references starting before the middle of the document.

**Example: the lexicon calibration batch.** This is the run that prepares the calibration theses for the author's study (the folder of downloaded theses, with its `calibracion.csv`):

```
feanor "C:\path\tesis_calibracion" --solo-digitales --cuerpo --metadatos "C:\path\tesis_calibracion\calibracion.csv" --anios 2015-2017 --comparar-ocr 20 --paginas-comparacion 10 --semilla 20261119 --destino "D:\tesis calibracion"
```

## Verification

Feanor is tested at two levels, and each one says something different:

1. **Automated tests** (`tests/test_basico.py`, 43 in version 0.6.2). Each builds a small case (a PDF, a Word file, a PowerPoint, a folder of theses) with invented text, except for a few one-line fragments from the bench books (chapter titles with their folio, one sentence) that reproduce the shape of a real error. It checks that Feanor does what this README says. No copyrighted book goes into the repository: only those fragments. Tests that need Tesseract, OCRmyPDF, `python-docx` or `python-pptx` are skipped if those are not installed. Since 0.6.1 they also run on GitHub on every change, with Tesseract, OCRmyPDF and Ghostscript installed; the «tests» badge at the top shows the result of the latest run. To run them:

   ```
   python -m pip install pytest
   python -m pytest -q
   ```

2. **Measurements with real material** (books, phone photos, theses). They are in [CALIBRACION.md](CALIBRACION.md) and in the «Con qué se probó» ("what it was tested with") section of each version in [CHANGELOG.md](CHANGELOG.md), with the material, the date and what they do not guarantee.


[docs/VALIDATION.md](docs/VALIDATION.md) maps each measured result and each behaviour claimed in this README to the test or measurement behind it, and lists what is **not** validated.

## What was measured

Tests on 2026-11-13 with a book photographed with a phone (14 pages; the book is copyrighted and is not included in the repository):

- **Flat pages:** OCR is almost perfect without flattening.
- **Pages curving towards the spine:** without flattening, OCR is useless (stray letters, broken lines). Flattened and read in book mode, six out of seven came out legible and in order. On the page checked by hand, about 97% of the words were correct.
- **Language:** with `-l spa+eng`, about 40% of the accents and ñ were lost; with `-l spa` they all came back (test on a typed PDF read as an image).
- **A page with little text (a table of contents):** could not be flattened. Feanor leaves it as it is and flags it for review.

## Known limits

- **Clinical use and use with AI:** this tool does not produce verified text. Doses, reference values, drug names and any figure that will be used in a clinical decision or a publication must be checked against the original source. The same applies if the `.md` is given to an AI: the AI cannot detect an OCR error in a figure. Every `.md` carries this warning in its header.
- **Very tight curve near the spine:** flattening may leave the first lines still slightly curved, and then a word at the end may be lost. Since version 0.2.0 Feanor measures that remaining curve and flags the page with «REVISAR A MANO» ("check by hand"). On the 14 test pages it flagged the three bad ones and gave one false alarm. The threshold is provisional: see [CALIBRACION.md](CALIBRACION.md).
- **Flattening that makes the page worse:** since version 0.4.3, each flattened page is compared with its original in a quick Tesseract read. If the flattened page reads fewer than 80% of the words, the original is used and the page is flagged. This is an approximation, not a guarantee: the quick read does not always match the final OCR. In the test bench, of 19 pages sent back to the original, 14 gained valid words and 5 lost some. This check costs time: in the tests, the full run took between 15% and 70% longer depending on the book.
- **Page that does not add up:** if step 1 counted lines of text on a page and OCR produced fewer words than lines, the page is flagged. A page with no lines detected (a figure, a very bad photo) is not flagged by this rule.
- **Errors without curvature:** a page that comes out badly because of shadow or low resolution, with straight lines, is not flagged.
- **Pages with little text** (tables of contents, title pages, pages with figures): are not flattened.
- **Two-page spreads:** the cut is searched near the centre, in the empty strip or in the spine shadow. Since version 0.4.4, a spread with one empty side (the blank page facing a chapter opening, a «Notas» page) is also split; before, it was flattened whole as one wide page and came out badly. Consequence: a landscape title page with the title on one side comes out as two pages, one of them blank. The empty half is not discarded: it stays in the PDF and is read. A half with a few lines stuck to the top or bottom edge may be labelled «en blanco» ("blank"), although its text is still read.
- **Flattening that runs away:** on some pages the curve fit ends in an absurd solution and the page would come out several times larger and distorted. Since version 0.4.4 the output size is measured before the image is built; if the height or width falls outside 0.5 to 3.0 times the input, the flattening is discarded, the original is used and the page is flagged. The range comes from the test bench (see [CALIBRACION.md](CALIBRACION.md)) and the upper margin is narrow: the largest good page measured 2.62 and the smallest bad one, 3.37. It has a cost: a discarded page may read slightly worse than its giant version (in the bench, one went from 156 to 148 valid words). It does not fix every failure: of 17 bench pages that read worse when flattened, size explains 9.
- **Different results on different computers:** with the same version of Feanor and of JAX, a difficult page gave different results on two machines. The computation is unstable on those pages, and it cannot be promised that two computers give exactly the same result. Each run records its environment in `libro.json` so runs can be compared.
- **Memory:** Feanor chooses how many pages to flatten at once from the physical cores (maximum 8) and the free memory, and says so in the console. Memory per page is a cautious estimate (0.3 GB plus 0.05 GB per megapixel of the largest page, if it exceeded the maximum allowed size); on a computer with little RAM it will be slower, it should not hang. It requires `psutil`; without it, it uses a fixed value and says so.
- **Pages rotated by 90°** (a table printed sideways): they are detected and flagged, but not straightened well. OCRmyPDF is asked to rotate them, and in the test it was not confident enough to do so. They must be read from the image.
- **Folio on the side:** folios are only searched in the header and footer. A book that prints the page number in a box on the side, half-way down, ends up with no deduced folios.
- **Phone photos:** since version 0.4.2 the lighting is evened out (shadows and grey background removed) and photos are rasterised at their real resolution. On a sample of 25 photographed spreads, valid words went from 87.2% to 89.7%.
- **Folios with spreads and gaps:** each half counts as one page. If the scan skips pages or OCR misreads a folio, the `.md` warns with «OJO con el folio» ("watch the folio").
- **Tables of contents:** they come out worst. OCR separates each title from its number and misreads Roman numerals. Feanor detects table-of-contents pages, does not clean them and always flags them with «REVISAR A MANO».
- **Names with their own hyphen** («Gil-galad»): they are kept only if they appear somewhere in the book in the middle of a line. If the only place they appear is split right at their hyphen, they are joined wrongly («Gilgalad»).
- **Data tables:** a page with many lines that are just a number (a table, common in psychology books) may be taken for a table of contents. The error goes in the safe direction: it is left uncleaned and flagged.
- **Printed folio:** it is deduced assuming a single continuous numbering. If the book changes numbering (Roman numerals in the front matter, unnumbered plates in between), the folios deduced after the change are shifted. Those marked «deducido» ("deduced") must be checked in the image before citing.
- **Conservative cleaning:** a stray letter next to a short line (the end of a paragraph) is not deleted. A word split across two pages is not joined.
- **`libro` mode:** scrambles two-column documents. For those, `--modo auto`.
- **Numbers, symbols and DOIs:** OCR confuses them (`I`/`1`, `T`/`7`, `&`, `Ω`). **OCR is for reading and searching; figures and quotations are always checked in the image.**
- **Batch OCR that alters pages:** `--output-type pdf` does not prevent every alteration of the pages that were not requested (in one calibration thesis, a bullet from the font disappears on rewriting); that is why the altered-page check stays in place.
- **References with each entry's number on its own line:** a bibliography numbered that way still looks like a table of contents (1 of 80 calibration theses).
- **Slow without JAX:** flattening takes about 25–30 seconds per curved page per core. With JAX installed (`python -m pip install "jax[cpu]"`), page-dewarp optimises with derivatives instead of trial and error and drops to about 4 seconds per page, with equivalent OCR quality in the tests. Since version 0.3.0, several pages are also processed at once.
- **Large files:** `libro_plano.pdf` can be very large, because it stores lossless images.

## Credits

Feanor does not do OCR itself and does not invent the flattening. It relies on:

- **[page-dewarp](https://github.com/lmmx/page-dewarp)** (MIT licence), by Louis Maddox, based on the method of [Matt Zucker (2016)](https://github.com/mzucker/page_dewarp). It does the flattening. It is used as a dependency, without copying its code.
- **[OCRmyPDF](https://github.com/ocrmypdf/OCRmyPDF)** (MPL-2.0) and **[Tesseract](https://github.com/tesseract-ocr/tesseract)** (Apache-2.0). They do the OCR. They are called as external programs.
- **[PyMuPDF](https://github.com/pymupdf/PyMuPDF)** to read and write PDFs, and **[OpenCV](https://opencv.org/)** for cropping.
- **[python-docx](https://github.com/python-openxml/python-docx)** and **[python-pptx](https://github.com/scanny/python-pptx)** to read Word and PowerPoint.

What Feanor contributes:
- The complete workflow, and the choice of route by the type of each page.
- Automatic cropping of the flattened page.
- The fix to page-dewarp's bounding box, which cut off the end of lines near the spine.
- The rule that leaves pages with little text unflattened.
- The OCR settings tested on books in Spanish.
- The review marks in the Markdown.
- Batch mode for thesis corpora: one result per file, metadata with a year lock, references section, body for lexical analysis and forced OCR comparison.

## How it was made

Author: Carlos Eduardo Ravello Joo ([ORCID 0009-0007-5631-7436](https://orcid.org/0009-0007-5631-7436)). The author defined the problem, directed the development and validated the results with real material. Claude (Anthropic) was used as a programming assistant.

## How to cite

GitHub shows the «Cite this repository» button from [CITATION.cff](CITATION.cff). In text:

> Ravello Joo, C. E. (2026). *Feanor* (Version 0.6.2) [Computer software]. https://github.com/carlosravello-png/feanor

## Licence

Feanor's code is MIT: see [LICENSE](LICENSE). Dependencies keep their own licences:

| Dependency | Licence | How Feanor uses it |
|---|---|---|
| PyMuPDF | AGPL-3.0 or Artifex commercial licence | Imported (Python library) |
| Ghostscript | AGPL-3.0 or Artifex commercial licence | External program, called by OCRmyPDF |
| OCRmyPDF | MPL-2.0 | External program |
| Tesseract | Apache-2.0 | External program |
| page-dewarp | MIT | Imported |
| OpenCV (`opencv-python-headless`) | Apache-2.0 | Imported |
| python-docx, python-pptx | MIT | Imported |
| NumPy | BSD-3-Clause (with parts under 0BSD, MIT, Zlib and CC0-1.0) | Imported |
| msgspec, psutil | BSD-3-Clause | Imported |

Sources: the metadata of each installed package, the PyMuPDF documentation, the Artifex licensing page and the Tesseract repository, consulted on 2026-11-24.

PyMuPDF is imported, so anyone who redistributes Feanor together with PyMuPDF, or offers it as a network service, must also comply with PyMuPDF's AGPL or obtain its commercial licence. This is a description, not legal advice.
