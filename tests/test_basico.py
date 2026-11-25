"""Pruebas rápidas, sin material con derechos de autor: imágenes y PDF sintéticos."""
import cv2
import pytest
import pymupdf as fitz
import numpy as np

from feanor_el_aplasta_libros.aplanar import recortar
from feanor_el_aplasta_libros.markdown import pdf_a_markdown


def _pagina_sintetica():
    img = np.full((1200, 900), 255, np.uint8)
    for k in range(12):  # doce líneas de "texto" en el centro
        cv2.putText(img, "linea de prueba numero %d" % k, (150, 300 + 50 * k),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, 0, 2)
    cv2.putText(img, "X", (850, 1150), cv2.FONT_HERSHEY_SIMPLEX, 12, 0, 30)  # basura gigante en el borde
    return img


def test_recorte_quita_basura_y_conserva_texto():
    img = _pagina_sintetica()
    texto = img[:, :800] < 128                     # zona del texto, sin la X gigante
    cols = np.where(texto[:900].any(axis=0))[0]
    filas = np.where(texto.any(axis=1))[0]
    rec = recortar(img)
    alto, ancho = rec.shape
    assert alto < 1000                             # quitó la X gigante de abajo
    assert ancho >= cols.max() - cols.min() + 1    # no cortó el final de las líneas
    assert alto >= filas.max() - filas.min() + 1   # ni la primera ni la última línea


def test_markdown_marca_paginas_y_avisos(tmp_path):
    pdf = tmp_path / "x.pdf"
    doc = fitz.open()
    for t in ("uno", "dos"):
        doc.new_page().insert_text((72, 72), t)
    doc.save(pdf)
    md = tmp_path / "x.md"
    res = pdf_a_markdown(pdf, md, [{"pagina": 2, "aplanada": False, "lineas": 3, "motivo": "pocas líneas"}])
    texto = md.read_text(encoding="utf-8")
    assert "<!-- página 1 del visor -->" in texto and "<!-- página 2 del visor -->" in texto
    assert "REVISAR A MANO: pocas líneas" in texto
    assert res["a_revisar"] == [2]


LARGA1 = "esta es una línea larga del cuerpo del texto, de más de cuarenta caracteres"
LARGA2 = "y esta es otra línea igual de larga que sigue en el mismo párrafo del libro"


def test_limpiar_quita_ruido_y_folio():
    from feanor_el_aplasta_libros.markdown import limpiar
    s = limpiar("\n".join(["18", "INTRODUCCIÓN", LARGA1, "|", "—", LARGA2, "1S"]))
    assert s.split("\n") == ["INTRODUCCIÓN", LARGA1, LARGA2]


def test_indice_que_termina_en_numero_no_pierde_datos(tmp_path):
    """Auditoría 14/11/2026: el folio borraba el último número de un índice."""
    from feanor_el_aplasta_libros.markdown import es_indice
    indice = "\n".join(["ÍNDICE", "Prefacio", "11", "I.", "La infancia de Túrin", "31",
                        "XIII.", "La llegada de Túrin a Brethil", "167"])
    assert es_indice(indice)
    pdf = tmp_path / "i.pdf"
    doc = fitz.open()
    hoja = doc.new_page()
    for k, linea in enumerate(indice.split("\n")):
        hoja.insert_text((72, 72 + 20 * k), linea)
    doc.save(pdf)
    md = tmp_path / "i.md"
    res = pdf_a_markdown(pdf, md)
    texto = md.read_text(encoding="utf-8")
    assert "167" in texto and "11" in texto          # ningún número se pierde
    assert res["indices"] == [1] and "página tipo índice" in texto


def test_nombre_cortado_se_une_y_compuesto_se_conserva():
    """Auditoría 14/11/2026: quedaban «Si-rion» y «Féa-nor»."""
    from feanor_el_aplasta_libros.markdown import limpiar
    doc = "\n".join(["donde nacía el río Si-", "rion, en la cara oriental de las montañas",
                     "el hermanastro de Féa-", "nor), quien era considerado señor supremo",
                     "Túrin nació en Dor-lómin, en el invierno", "vivió en Dor-", "lómin durante años",
                     "publicadas anterior-", "mente por separado", "de los El -", "fos al mismo tiempo"])
    s = limpiar(doc, doc)
    assert "Sirion," in s and "Si-rion" not in s
    assert "Féanor)," in s
    assert s.count("Dor-lómin") == 2 and "Dorlómin" not in s
    assert "anteriormente" in s
    assert "de los Elfos\nal mismo" in s                      # espacio antes del guion


def test_letra_suelta_no_rompe_la_union():
    """Auditoría 14/11/2026: «escri-» + «l» + «bió» daba «escril»."""
    from feanor_el_aplasta_libros.markdown import limpiar
    s = limpiar("\n".join(["pasaje citado de una larga carta que mi padre escri-", "l",
                           "bió en 1951, tres años antes de la publicación de la obra",
                           "conocido como tal. Por otro lado, tal como mi pa-", "1",
                           "dre observó en el mismo lugar, la historia forma parte"]))
    assert "padre escribió\nen 1951" in s and "escril" not in s
    assert "mi padre\nobservó" in s


def test_letra_suelta_en_indice_se_conserva():
    from feanor_el_aplasta_libros.markdown import limpiar
    s = limpiar("\n".join(["I.", "La infancia", "V.", "Túrin en Doriath", "X.", "Nargothrond"]))
    assert "V." in s and "X." in s


def test_curva_recta_vs_curva():
    from feanor_el_aplasta_libros.calidad import curva_p90
    recta = np.full((1400, 1100), 255, np.uint8)
    curva = recta.copy()
    for k in range(12):
        y = 200 + 90 * k
        cv2.putText(recta, "linea de prueba bastante larga %02d" % k, (60, y), cv2.FONT_HERSHEY_SIMPLEX, 1.2, 0, 2)
        # misma línea, con el extremo derecho levantado (resto de curva)
        texto = np.full((60, 1100), 255, np.uint8)
        cv2.putText(texto, "linea de prueba bastante larga %02d" % k, (60, 45), cv2.FONT_HERSHEY_SIMPLEX, 1.2, 0, 2)
        for x in range(1100):
            sube = min(int(max(0, x - 350) ** 2 / 1500), 40)
            col = texto[:, x]
            curva[y - 45 - sube:y + 15 - sube, x] = np.minimum(curva[y - 45 - sube:y + 15 - sube, x], col)
    assert curva_p90(recta) < 0.55
    assert curva_p90(curva) >= 0.55


def test_folio_por_secuencia():
    """Folios leídos 13, 14, 17 y 22 en las páginas 5, 6, 9 y 14 del visor; 18 leído como «1S»."""
    from feanor_el_aplasta_libros.markdown import deducir_folios
    textos = [LARGA1] * 14
    textos[4] = "PREFACIO\n13\n" + LARGA1
    textos[5] = "14\nPREFACIO\n" + LARGA1
    textos[8] = "INTRODUCCIÓN\n17\n" + LARGA1
    textos[9] = "1S\nINTRODUCCIÓN\n" + LARGA1
    textos[12] = "INTRODUCCIÓN\n31\n" + LARGA1      # 21 mal leído: vota por otro desfase
    textos[13] = "22\nINTRODUCCIÓN\n" + LARGA1
    textos[0] = "ÍNDICE\nPrefacio\n11\nI.\n31\n47"   # índice: no vota
    f = deducir_folios(textos, indices=[1])
    assert f[5][:2] == (13, "leído") and f[14][:2] == (22, "leído")
    assert f[10][:2] == (18, "deducido") and f[13][:2] == (21, "deducido")
    assert "31" in f[13][2]                            # avisa la lectura que no coincide
    assert f[3][:2] == (11, "deducido") and f[1][:2] == (9, "deducido")


def test_sin_secuencia_no_inventa_folios():
    from feanor_el_aplasta_libros.markdown import deducir_folios
    assert deducir_folios([LARGA1, "7\n" + LARGA1, LARGA2], indices=[]) == {}


def test_folio_con_salto_y_capitulo():
    """Pliegos 1 a 4 (folios 2 a 9), falta el pliego de 12-13, siguen 14 y 15.
    «Capítulo 1» en el encabezado no debe contar como folio."""
    from feanor_el_aplasta_libros.markdown import deducir_folios
    t = [LARGA1] * 14
    for visor, folio in ((1, 2), (3, 4), (5, 6), (7, 8), (11, 14), (13, 16)):
        t[visor - 1] = f"{folio}\nEl fenómeno de la inmunidad\nCapítulo 1\n" + LARGA1
    f = deducir_folios(t, indices=[])
    assert f[2][:2] == (3, "deducido") and f[8][:2] == (9, "deducido")
    assert f[11][:2] == (14, "leído") and f[12][:2] == (15, "deducido")
    assert "folio incierto" in f[9][2] and "folio incierto" in f[10][2]
    assert f[2][2] == "" and f[12][2] == ""


def test_pliego_sale_izquierda_y_luego_derecha():
    """Auditoría 14/11/2026: un pliego invertido rompería la secuencia de folios en silencio."""
    from feanor_el_aplasta_libros.pliegos import preparar
    import random
    random.seed(1)
    palabras = "el la de que los las una por con para como sistema inmune celulas antigeno respuesta".split()
    pliego = np.full((1200, 2000), 255, np.uint8)
    for k in range(20):
        for x0 in (60, 1060):
            linea = " ".join(random.choice(palabras) for _ in range(5))
            cv2.putText(pliego, linea, (x0 + random.randint(0, 20), 100 + 50 * k),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, 0, 2)
    partes = preparar(pliego)
    assert [p for _, p in partes] == ["izquierda", "derecha"]
    izq, der = partes[0][0], partes[1][0]
    assert izq.shape[1] < 1100 and der.shape[1] < 1100
    assert (izq[:, :400] < 128).any() and (der[:, :400] < 128).any()


def test_markdown_lleva_aviso(tmp_path):
    pdf = tmp_path / "a.pdf"
    doc = fitz.open(); doc.new_page().insert_text((72, 72), "uno"); doc.save(pdf)
    md = tmp_path / "a.md"
    pdf_a_markdown(pdf, md)
    assert "No usar como fuente de dosis" in md.read_text(encoding="utf-8")


def test_pagina_con_lineas_y_sin_texto_se_marca(tmp_path):
    """Una página con líneas de texto de la que no salió texto no pasa callada."""
    doc = fitz.open()
    doc.new_page()                                   # sin texto
    doc.new_page().insert_text((72, 72), "Una página con texto de sobra para no marcarse.")
    doc.new_page()                                   # sin texto y sin líneas: en blanco
    pdf = tmp_path / "x.pdf"
    doc.save(pdf)
    base = {"aplanada": True, "lineas": 20, "motivo": "aplanada", "revisar": False, "motivo_revision": ""}
    resultados = [{**base, "pagina": 1}, {**base, "pagina": 2, "lineas": 1},
                  {**base, "pagina": 3, "lineas": 0}]
    resumen = pdf_a_markdown(pdf, tmp_path / "x.md", resultados)
    assert resumen["a_revisar"] == [1]
    assert "se contaron 20 líneas de texto pero salieron 0 palabras" in (tmp_path / "x.md").read_text(encoding="utf-8")


def test_lectura_rapida_distingue_texto_de_blanco(tmp_path):
    """La comprobación del aplanado lee más palabras en una página con texto que en una vacía."""
    from feanor_el_aplasta_libros.aplanar import palabras_legibles, _tesseract
    if _tesseract() is None:
        pytest.skip("Tesseract no está instalado: no hay nada que comparar")
    con_texto = np.full((1400, 2000), 255, np.uint8)
    for k in range(12):
        cv2.putText(con_texto, "la sangre del perro y del gato se estudia con cuidado",
                    (60, 120 + 100 * k), cv2.FONT_HERSHEY_SIMPLEX, 1.6, 0, 3)
    vacia = np.full((1400, 2000), 255, np.uint8)
    assert palabras_legibles(con_texto, tmp_path) > 50
    assert palabras_legibles(vacia, tmp_path) == 0


def test_pliego_con_un_lado_vacio_tambien_se_parte():
    """Una hoja en blanco frente a una página con texto: salen dos mitades y
    el corte no atraviesa el texto."""
    from feanor_el_aplasta_libros.pliegos import corte_de_pliego
    pliego = np.full((1000, 1600), 255, np.uint8)
    for k in range(25):                                    # texto solo a la derecha
        cv2.putText(pliego, "texto de la pagina derecha del pliego", (860, 100 + 32 * k),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, 0, 2)
    x = corte_de_pliego(pliego)
    assert x is not None and 0.38 * 1600 <= x < 860
    assert (pliego[:, :x] < 128).sum() == 0              # todo el texto quedó a la derecha


def test_folio_con_guion_y_espacio_no_tumba_la_corrida():
    """«66- » en el pie de página se lee como el folio 66 (falló en un libro de 511 páginas)."""
    from feanor_el_aplasta_libros.markdown import _lecturas_de_folio
    assert _lecturas_de_folio("texto de la página\nmás texto\notra línea\ny otra\n66- ") == [66]
    assert _lecturas_de_folio("- 12 -\ntexto de la página\nmás texto\notra línea\nfin") == [12]
    assert _lecturas_de_folio("texto\nmás texto\notra línea\ny otra\n66- .") == [66]


def test_powerpoint_a_markdown(tmp_path):
    """Diapositiva en columnas, número dibujado junto a su renglón, tabla y notas."""
    pptx = pytest.importorskip("pptx")
    from pptx.util import Inches
    from feanor_el_aplasta_libros.presentacion import pptx_a_markdown

    prs = pptx.Presentation()
    d = prs.slides.add_slide(prs.slide_layouts[6])            # diapositiva en blanco
    caja = lambda x, y, w, h, t: d.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h)).text_frame.__setattr__("text", t)
    caja(0.5, 0.2, 9, 0.6, "TITULO DE PRUEBA")
    for k, (etapa, dato) in enumerate([("NIÑEZ", "0 a 6"), ("ADOLESCENCIA", "12 a 18")]):
        caja(0.5 + 4.5 * k, 1.2, 4, 0.5, etapa)              # dos columnas anchas
        caja(0.5 + 4.5 * k, 1.9, 4, 0.5, dato)
    caja(0.5, 3.0, 0.4, 0.4, "1")                             # número dibujado aparte
    caja(1.0, 2.95, 8, 0.5, "Primer objetivo")
    d.shapes.add_shape(1, Inches(0.4), Inches(2.9), Inches(9.2), Inches(0.6))  # marco vacío encima
    tabla = d.shapes.add_table(2, 2, Inches(0.5), Inches(4), Inches(6), Inches(1)).table
    for (i, j), t in {(0, 0): "Fármaco", (0, 1): "Dosis", (1, 0): "A", (1, 1): "5 mg/kg"}.items():
        tabla.cell(i, j).text = t
    d.notes_slide.notes_text_frame.text = "Explicar con un caso."
    prs.slides.add_slide(prs.slide_layouts[6])                # diapositiva vacía

    entrada, salida = tmp_path / "clase.pptx", tmp_path / "clase.md"
    prs.save(entrada)
    r = pptx_a_markdown(entrada, salida)
    md = salida.read_text(encoding="utf-8")
    assert r["diapositivas"] == 2 and r["sin_texto"] == [2] and r["tablas"] == 1 and r["con_notas"] == 1
    assert "sin OCR" in md
    # columna por columna, no fila por fila
    assert md.index("NIÑEZ") < md.index("0 a 6") < md.index("ADOLESCENCIA") < md.index("12 a 18")
    assert "1. Primer objetivo" in md                         # el número se pega a su renglón
    assert "| A | 5 mg/kg |" in md                            # la dosis queda en la fila de su fármaco
    assert "Explicar con un caso." in md


def test_powerpoint_rotulo_valor_se_lee_por_filas(tmp_path):
    """Una lista «rótulo: valor» no es un par de columnas: cada valor va con su rótulo."""
    pptx = pytest.importorskip("pptx")
    from pptx.util import Inches
    from feanor_el_aplasta_libros.presentacion import pptx_a_markdown

    prs = pptx.Presentation()
    d = prs.slides.add_slide(prs.slide_layouts[6])
    for k, (rotulo, valor) in enumerate([("Antecedentes:", "historia del desarrollo"),
                                         ("Motivo:", "conducta referida"),
                                         ("Conclusiones:", "si es normativa o clínica")]):
        d.shapes.add_textbox(Inches(0.5), Inches(1 + 0.6 * k), Inches(1.6), Inches(0.4)).text_frame.text = rotulo
        d.shapes.add_textbox(Inches(2.2), Inches(1 + 0.6 * k), Inches(7), Inches(0.4)).text_frame.text = valor
    entrada, salida = tmp_path / "lista.pptx", tmp_path / "lista.md"
    prs.save(entrada)
    pptx_a_markdown(entrada, salida)
    md = salida.read_text(encoding="utf-8")
    assert md.index("Antecedentes:") < md.index("historia del desarrollo") < md.index("Motivo:") < md.index("conducta referida")


def test_powerpoint_lee_texto_de_imagenes(tmp_path):
    """Una lámina con texto pegada como imagen se lee con OCR y va marcada;
    un logo chico no se lee, y una foto sin texto queda solo anotada."""
    pptx = pytest.importorskip("pptx")
    from pptx.util import Inches
    from feanor_el_aplasta_libros.entorno import ruta_tesseract
    from feanor_el_aplasta_libros.presentacion import pptx_a_markdown
    if not ruta_tesseract():
        pytest.skip("Tesseract no está instalado")

    lamina = np.full((600, 1400), 255, np.uint8)
    for k, t in enumerate(["CONFIDENCIALIDAD DEL PACIENTE", "Articulo 46 y Articulo 47",
                           "La informacion es privada"]):
        cv2.putText(lamina, t, (60, 150 + 150 * k), cv2.FONT_HERSHEY_SIMPLEX, 2.0, 0, 4)
    foto = np.random.default_rng(1).integers(0, 255, (400, 600), dtype=np.uint8)
    cv2.imwrite(str(tmp_path / "lamina.png"), lamina)
    cv2.imwrite(str(tmp_path / "foto.png"), cv2.GaussianBlur(foto, (31, 31), 0))

    prs = pptx.Presentation()
    d = prs.slides.add_slide(prs.slide_layouts[6])
    d.shapes.add_textbox(Inches(0.5), Inches(0.2), Inches(9), Inches(0.6)).text_frame.text = "Titulo"
    d.shapes.add_picture(str(tmp_path / "lamina.png"), Inches(0.5), Inches(1), Inches(9), Inches(3.9))
    d.shapes.add_picture(str(tmp_path / "lamina.png"), Inches(9.2), Inches(7), Inches(0.6), Inches(0.26))  # logo
    d2 = prs.slides.add_slide(prs.slide_layouts[6])
    d2.shapes.add_picture(str(tmp_path / "foto.png"), Inches(1), Inches(1), Inches(6), Inches(4))
    entrada, salida = tmp_path / "laminas.pptx", tmp_path / "laminas.md"
    prs.save(entrada)
    r = pptx_a_markdown(entrada, salida)
    md = salida.read_text(encoding="utf-8")
    assert r["imagenes"] == 3 and r["imagenes_leidas"] == 1
    assert "texto leído con OCR" in md and "CONFIDENCIALIDAD" in md
    assert "47" in md                                         # los números no se pierden
    assert md.count(": texto leído con OCR") == 1             # ni el logo ni la foto
    assert "no leída, imagen muy pequeña" in md               # el logo: no leído, y dicho
    assert "sin texto legible" in md                          # la foto: leída, sin texto
    assert r["sin_texto"] == [2]                              # la foto sola no cuenta como texto


def test_powerpoint_numero_suelto_llega_marcado(tmp_path):
    """De extremo a extremo: un renglón que es solo un número llega al .md con «[?]»,
    no se borra."""
    pptx = pytest.importorskip("pptx")
    from pptx.util import Inches
    from feanor_el_aplasta_libros.entorno import ruta_tesseract
    from feanor_el_aplasta_libros.presentacion import pptx_a_markdown
    if not ruta_tesseract():
        pytest.skip("Tesseract no está instalado")

    lamina = np.full((900, 1400), 255, np.uint8)
    for k, t in enumerate(["CONFIDENCIALIDAD DEL PACIENTE", "La informacion es privada",
                           "Reserva absoluta de datos"]):
        cv2.putText(lamina, t, (60, 150 + 150 * k), cv2.FONT_HERSHEY_SIMPLEX, 2.0, 0, 4)
    cv2.putText(lamina, "47", (600, 750), cv2.FONT_HERSHEY_SIMPLEX, 3.0, 0, 6)
    cv2.imwrite(str(tmp_path / "lamina.png"), lamina)
    prs = pptx.Presentation()
    d = prs.slides.add_slide(prs.slide_layouts[6])
    d.shapes.add_picture(str(tmp_path / "lamina.png"), Inches(0.5), Inches(0.5), Inches(9), Inches(5.8))
    entrada, salida = tmp_path / "numero.pptx", tmp_path / "numero.md"
    prs.save(entrada)
    pptx_a_markdown(entrada, salida)
    lineas = salida.read_text(encoding="utf-8").splitlines()
    # Lo que se prueba es que el renglón llega marcado y conserva el número, no
    # el texto exacto que lee Tesseract: con OpenCV 5.1 la lámina se dibuja un
    # poco distinto y Tesseract lee «47]» (CI del 24/11/2026); con 5.0, «47».
    assert any(l.startswith("[?] 47") for l in lineas), lineas
    assert "CONFIDENCIALIDAD DEL PACIENTE" in lineas          # el texto normal va sin marca


def test_forma_de_palabra():
    """Sin diccionario: «Cpg?» (sin vocal), «%00s» (cifras dentro) y «SUPoOSICION»
    (mayúsculas mezcladas) no cuentan como palabras; sí las normales."""
    from feanor_el_aplasta_libros.presentacion import _parece_palabra
    for w in ["Cpg?", "%00s", "SUPoOSICION", "1", "2)", "ld", "E"]:
        assert not _parece_palabra(w), w
    for w in ["CONFIDENCIALIDAD", "Beneficencia).", "información", "(Principio", "Art."]:
        assert _parece_palabra(w), w


def _pdf_de_prueba(ruta, paginas):
    """PDF sintético con páginas de cada tipo: digital, ocr_previo, escaneada,
    tapado (texto visible dibujado debajo de una foto) y vacia."""
    foto = np.full((800, 600, 3), 200, np.uint8)
    cv2.putText(foto, "foto", (100, 400), cv2.FONT_HERSHEY_SIMPLEX, 3, (0, 0, 0), 5)
    ok, png = cv2.imencode(".png", foto)
    doc = fitz.open()
    texto = "Texto de prueba con varias palabras para la pagina"
    for tipo in paginas:
        p = doc.new_page(width=600, height=800)
        if tipo == "digital":
            p.insert_text((50, 100), texto)
        elif tipo == "ocr_previo":
            p.insert_image(p.rect, stream=png.tobytes())
            p.insert_text((50, 100), texto, render_mode=3)          # invisible, como un OCR
        elif tipo == "tapado":
            p.insert_text((50, 100), texto)                         # visible, pero queda debajo
            p.insert_image(p.rect, stream=png.tobytes())
        elif tipo == "escaneada":
            p.insert_image(p.rect, stream=png.tobytes())
        elif tipo == "tapado_al_reves":                          # foto y, encima, un sello de texto visible
            p.insert_image(p.rect, stream=png.tobytes())
            p.insert_text((50, 780), "Repositorio institucional acceso abierto")
        elif tipo == "escaneada_con_sello":                      # foto legible y un sello corto (menos de 3 palabras)
            acta = np.full((2200, 1700), 255, np.uint8)
            for j, linea in enumerate(["ACTA DE SUSTENTACION", "El jurado aprueba la tesis"]):
                cv2.putText(acta, linea, (120, 300 + 100 * j), cv2.FONT_HERSHEY_SIMPLEX, 1.8, 0, 3)
            p.insert_image(p.rect, stream=cv2.imencode(".png", acta)[1].tobytes())
            p.insert_text((50, 780), "Repositorio UCV")
        elif tipo == "imagen_en_blanco":                         # foto sin nada que leer
            blanco = cv2.imencode(".png", np.full((800, 600, 3), 255, np.uint8))[1]
            p.insert_image(p.rect, stream=blanco.tobytes())
    doc.save(ruta)


def test_tipo_de_cada_pagina(tmp_path):
    from feanor_el_aplasta_libros.tipo_pdf import clasificar, rangos
    pdf = tmp_path / "mezcla.pdf"
    _pdf_de_prueba(pdf, ["digital", "ocr_previo", "tapado", "escaneada", "vacia"])
    assert clasificar(pdf) == ["digital", "ocr_previo", "ocr_previo", "escaneada", "vacia"]
    assert rangos([1, 2, 3, 7, 9, 10]) == "1–3, 7, 9–10"


def test_ruta_digital_de_punta_a_punta(tmp_path):
    """Un PDF que ya trae texto pasa directo a Markdown, sin aplanar ni OCR, y el
    .md dice de dónde sale el texto; uno de fotos sin texto no toma esa ruta."""
    from feanor_el_aplasta_libros.cli import _ruta_digital
    pdf = tmp_path / "libro.pdf"
    _pdf_de_prueba(pdf, ["digital"] * 4 + ["ocr_previo"])
    md = tmp_path / "libro.md"
    registro = {}
    assert _ruta_digital(pdf, md, registro, 0.0)
    texto = md.read_text(encoding="utf-8")
    assert "sin OCR de Feanor" in texto and "Texto extraído por OCR" not in texto
    assert "1–4: texto digital" in texto and "5: OCR previo" in texto
    assert "origen del texto de esta página: OCR previo" in texto   # la página distinta va anotada
    assert not (tmp_path / "libro_plano.pdf").exists()               # no se aplanó nada
    assert [p["tipo"] for p in registro["paginas_pdf"]] == ["digital"] * 4 + ["ocr_previo"]
    assert registro["paginas_pdf"][4]["fraccion_ocr"] == 1.0           # la medida va con la etiqueta

    fotos = tmp_path / "fotos.pdf"
    _pdf_de_prueba(fotos, ["escaneada"] * 3 + ["digital"])
    assert not _ruta_digital(fotos, tmp_path / "fotos.md", {}, 0.0)
    assert not (tmp_path / "fotos.md").exists()


def test_word_a_markdown(tmp_path):
    """Títulos, listas, tabla con celda combinada; el texto borrado con control de
    cambios no aparece."""
    docx = pytest.importorskip("docx")
    from docx.oxml.ns import qn
    from lxml import etree
    from feanor_el_aplasta_libros.documento import docx_a_markdown

    d = docx.Document()
    d.add_heading("Introducción", level=1)
    d.add_heading("Antecedentes", level=2)
    p = d.add_paragraph("Texto que queda")
    borrado = etree.SubElement(p._p, qn("w:del"), {qn("w:id"): "1", qn("w:author"): "x"})
    r = etree.SubElement(borrado, qn("w:r"))
    etree.SubElement(r, qn("w:delText")).text = " TEXTO BORRADO"
    d.add_paragraph("primer punto", style="List Bullet")
    d.add_paragraph("segundo punto", style="List Bullet")
    t = d.add_table(rows=2, cols=3)
    t.cell(0, 0).merge(t.cell(0, 1)).text = "Fármaco"
    t.cell(0, 2).text = "Dosis"
    t.cell(1, 0).text, t.cell(1, 1).text, t.cell(1, 2).text = "A", "oral", "5 mg/kg"
    entrada, salida = tmp_path / "trabajo.docx", tmp_path / "trabajo.md"
    d.save(entrada)
    r = docx_a_markdown(entrada, salida)
    md = salida.read_text(encoding="utf-8")
    assert "# Introducción" in md and "## Antecedentes" in md
    assert "- primer punto" in md and "- segundo punto" in md
    assert "| Fármaco |  | Dosis |" in md and "| A | oral | 5 mg/kg |" in md
    assert "Texto que queda" in md and "BORRADO" not in md
    assert "sin OCR" in md and r["tablas"] == 1 and r["titulos"] == 2


def test_word_listas_numeradas(tmp_path):
    """Las listas numeradas conservan su número; las de viñetas siguen como viñetas."""
    docx = pytest.importorskip("docx")
    from feanor_el_aplasta_libros.documento import docx_a_markdown

    d = docx.Document()
    d.add_paragraph("primer paso", style="List Number")
    d.add_paragraph("segundo paso", style="List Number")
    d.add_paragraph("tercer paso", style="List Number")
    d.add_paragraph("una viñeta", style="List Bullet")
    entrada, salida = tmp_path / "pasos.docx", tmp_path / "pasos.md"
    d.save(entrada)
    docx_a_markdown(entrada, salida)
    md = salida.read_text(encoding="utf-8")
    assert "1. primer paso" in md and "2. segundo paso" in md and "3. tercer paso" in md
    assert "- una viñeta" in md


def test_enlace_cortado_con_guion_no_se_une():
    """Una URL, un DOI o un correo cortado con guion al final de la línea se deja
    tal cual: el guion puede ser parte del enlace. Una palabra sí se une."""
    from feanor_el_aplasta_libros.markdown import limpiar
    t = limpiar("Lineamientos. https://www.sistemas-\neducativos.gob.pe/a.pdf\n"
                "Revista. https://doi.org/10.1016/j.psico-\nneuro.2021.105\n"
                "correo juan.pe-\nrez@gmail.com y una palabra anterior-\nmente")
    assert "https://www.sistemas-\neducativos.gob.pe" in t
    assert "10.1016/j.psico-\nneuro" in t
    assert "juan.pe-\nrez@gmail.com" in t
    assert "anteriormente" in t


def test_salida_en_su_carpeta_con_json(tmp_path):
    """PDF, PowerPoint y Word dejan su .md y su .json en una carpeta propia. El
    mismo archivo reemplaza su carpeta; otro con el mismo nombre va a _2."""
    import json
    docx = pytest.importorskip("docx")
    from pptx import Presentation
    from feanor_el_aplasta_libros.cli import main
    from feanor_el_aplasta_libros.entorno import _sha256

    origen, salida = tmp_path / "origen", tmp_path / "salida"
    origen.mkdir()
    pdf = origen / "tesis.pdf"
    _pdf_de_prueba(pdf, ["digital"] * 3)
    d = docx.Document(); d.add_paragraph("texto del trabajo"); d.save(origen / "trabajo.docx")
    pr = Presentation(); pr.slides.add_slide(pr.slide_layouts[5]).shapes.title.text = "Clase"
    pr.save(origen / "clase.pptx")

    for archivo, tipo in ((pdf, "pdf"), (origen / "trabajo.docx", "docx"), (origen / "clase.pptx", "pptx")):
        main([str(archivo), "--salida", str(salida)])
        carpeta = salida / archivo.stem
        assert (carpeta / f"{archivo.stem}.md").exists()
        r = json.loads((carpeta / f"{archivo.stem}.json").read_text(encoding="utf-8"))
        assert r["tipo_entrada"] == tipo and r["archivo"]["sha256"] == _sha256(archivo)
        assert r["entorno"]["feanor"] and "resumen" in r and "modelo_tesseract" in r["entorno"]

    r = json.loads((salida / "tesis" / "tesis.json").read_text(encoding="utf-8"))
    assert r["ruta"] == "digital" and len(r["paginas_pdf"]) == 3 and "cobertura_imagen" in r["paginas_pdf"][0]
    assert "Texto de prueba" in r["paginas_md"][0]["texto_crudo"]
    assert r["umbrales_tipo"]["ocr_si"] == 0.90

    main([str(pdf), "--salida", str(salida)])                    # el mismo archivo: misma carpeta
    assert not (salida / "tesis_2").exists()
    otro = tmp_path / "otro"; otro.mkdir()
    _pdf_de_prueba(otro / "tesis.pdf", ["digital"] * 2)          # otro archivo, mismo nombre
    main([str(otro / "tesis.pdf"), "--salida", str(salida)])
    assert (salida / "tesis_2" / "tesis.json").exists()
    assert len(json.loads((salida / "tesis" / "tesis.json").read_text(encoding="utf-8"))["paginas_pdf"]) == 3


def _tesis_sintetica(ruta, con_referencias=True):
    """Tesis digital: índice (con «REFERENCIAS» como entrada), cuerpo,
    referencias con un DOI cortado con guion, y anexos."""
    doc = fitz.open()
    paginas = [["ÍNDICE", "Introducción 1", "REFERENCIAS", "45", "ANEXOS", "50"],
               ["I. INTRODUCCIÓN", "El presente estudio analiza la relación entre variables"],
               ["Los resultados muestran una correlación moderada entre escalas"]]
    if con_referencias:
        paginas.append(["VII. REFERENCIAS BIBLIOGRÁFICAS", "Pérez, J. (2021). Título. Revista, 4(2), 1-10.",
                        "https://doi.org/10.1016/j.psico-", "neuro.2021.105"])
    paginas.append(["ANEXOS", "Anexo 1. Instrumento aplicado a la muestra"])
    for lineas in paginas:
        p = doc.new_page(width=600, height=800)
        for k, l in enumerate(lineas):
            p.insert_text((50, 60 + 18 * k), l)
    doc.save(ruta)


def test_referencias_por_titulo():
    """Se toma el último título (el del índice no cuenta) y la sección termina
    antes de los anexos; sin título, None."""
    from feanor_el_aplasta_libros.referencias import buscar_referencias, texto_de_referencias
    textos = ["ÍNDICE\nREFERENCIAS\n45", "cuerpo del trabajo",
              "VII. REFERENCIAS BIBLIOGRÁFICAS\nPérez (2021).\nANEXOS\nInstrumento", "Anexo 2"]
    r = buscar_referencias(textos)
    # 0.5.5: la página que se encabeza «ÍNDICE» ya no aporta candidato (antes eran 2).
    assert r["pagina"] == 3 and r["candidatos"] == 1 and r["termina_antes_de"]["pagina"] == 3
    assert texto_de_referencias(textos, r) == [(3, "VII. REFERENCIAS BIBLIOGRÁFICAS\nPérez (2021).")]
    assert buscar_referencias(["Bibliografía\nAutor (2020)."])["termina_antes_de"] is None
    assert buscar_referencias(["las referencias citadas en el texto"]) is None   # en medio de una frase no


def test_lote_una_salida_por_pdf(tmp_path):
    """Una carpeta: cada PDF con texto deja su carpeta (.md, .json y
    _referencias.md con el texto crudo); la escaneada se aparta, el PDF roto
    falla sin tumbar el lote, y en la segunda corrida lo hecho se salta."""
    import csv
    from feanor_el_aplasta_libros.cli import main
    carpeta, salida = tmp_path / "tesis", tmp_path / "salida"
    carpeta.mkdir()
    _tesis_sintetica(carpeta / "20.500.12692_1.pdf")
    _tesis_sintetica(carpeta / "20.500.12692_2.pdf", con_referencias=False)
    _pdf_de_prueba(carpeta / "20.500.12692_3.pdf", ["escaneada"] * 3)
    _pdf_de_prueba(carpeta / "20.500.12692_4.pdf", ["ocr_previo"] * 3)
    (carpeta / "20.500.12692_5.pdf").write_bytes(b"%PDF-1.4 roto")
    (carpeta / "notas.txt").write_text("x")

    main([str(carpeta), "--salida", str(salida)])
    base = salida / "tesis"
    filas = {f["archivo"]: f for f in csv.DictReader(open(base / "_lote.csv", encoding="utf-8-sig"))}
    assert [filas[f"20.500.12692_{k}.pdf"]["estado"] for k in range(1, 6)] == \
        ["convertida", "convertida", "apartada", "convertida", "fallo"]
    assert filas["20.500.12692_4.pdf"]["clase"] == "ocr_previo"
    assert filas["20.500.12692_1.pdf"]["referencias_pagina"] == "4"
    ref = (base / "20.500.12692_1" / "20.500.12692_1_referencias.md").read_text(encoding="utf-8")
    assert "10.1016/j.psico-\nneuro" in ref and "Anexo 1" not in ref           # crudo, y sin los anexos
    assert "20.500.12692_2.pdf" in (base / "_lote.md").read_text(encoding="utf-8").split("## Convertidas sin título de referencias encontrado")[1]

    main([str(carpeta), "--salida", str(salida), "--solo-digitales"])
    filas = {f["archivo"]: f for f in csv.DictReader(open(base / "_lote.csv", encoding="utf-8-sig"))}
    assert filas["20.500.12692_1.pdf"]["estado"] == "ya_hecha"
    assert filas["20.500.12692_4.pdf"]["estado"] == "apartada"                 # OCR previo, ahora aparte


def test_lote_con_metadatos_y_candado(tmp_path):
    """Con el CSV de la descarga: cada resultado lleva su handle, universidad,
    carrera y año; fuera de 2015–2017, con SHA-256 distinto, con descarga
    fallida o sin fila en el CSV, no se procesa. Todo va a la carpeta exacta."""
    import csv
    from feanor_el_aplasta_libros.cli import main
    from feanor_el_aplasta_libros.entorno import _sha256
    carpeta, destino = tmp_path / "tesis_calibracion", tmp_path / "tesis calibracion"
    carpeta.mkdir()
    for k in range(1, 6):
        _tesis_sintetica(carpeta / f"20.500.12692_{k}.pdf")
    filas = [("20.500.12692_1.pdf", "2016", _sha256(carpeta / "20.500.12692_1.pdf"), "bajada"),
             ("20.500.12692_2.pdf", "2019", "", "bajada"),                      # fuera del candado
             ("20.500.12692_3.pdf", "2015", "0" * 64, "bajada"),                # no es el que se bajó
             ("20.500.12692_4.pdf", "2017", "", "falló"),
             ("20.500.12692_9.pdf", "2016", "", "bajada")]                      # fila sin su PDF
    csv_ruta = carpeta / "calibracion.csv"
    with open(csv_ruta, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["handle", "archivo", "universidad", "carrera", "anio", "titulo", "estado", "sha256"])
        for archivo, anio, sha, estado in filas:
            w.writerow([archivo[:-4].replace("_", "/"), archivo, "UNT", "Educación", anio, "Título", estado, sha])

    main([str(carpeta), "--solo-digitales", "--metadatos", str(csv_ruta), "--anios", "2015-2017",
          "--destino", str(destino)])
    res = {f["archivo"]: f for f in csv.DictReader(open(destino / "_lote.csv", encoding="utf-8-sig"))}
    assert res["20.500.12692_1.pdf"]["estado"] == "convertida"
    assert res["20.500.12692_1.pdf"]["handle"] == "20.500.12692/1" and res["20.500.12692_1.pdf"]["anio"] == "2016"
    assert "candado" in res["20.500.12692_2.pdf"]["motivo"]
    assert "SHA-256" in res["20.500.12692_3.pdf"]["motivo"]
    assert "fallida" in res["20.500.12692_4.pdf"]["motivo"]
    assert "no está en el CSV" in res["20.500.12692_5.pdf"]["motivo"]
    assert {f["estado"] for k, f in res.items() if k != "20.500.12692_1.pdf"} == {"apartada"}
    assert (destino / "20.500.12692_1" / "20.500.12692_1.md").exists()          # directo en la carpeta exacta
    assert "20.500.12692_9.pdf" in (destino / "_lote.md").read_text(encoding="utf-8")


def test_cuerpo_sin_margenes_repetidos_ni_referencias():
    """El cuerpo deja fuera el encabezado repetido (solo en el margen), el
    índice con puntos guía, las referencias y los anexos."""
    from feanor_el_aplasta_libros.cuerpo import cuerpo
    from feanor_el_aplasta_libros.referencias import buscar_referencias
    enc = "UNIVERSIDAD CÉSAR VALLEJO"
    textos = [f"{enc}\nÍNDICE\nIntroducción ........ 1\nMétodo ........ 5\nResultados ........ 9\nReferencias ........ 12\nAnexos ........ 14\n1",
              f"{enc}\nI. INTRODUCCIÓN\nEl estudio se hizo en la {enc.title()} con estudiantes.\n2",
              f"{enc}\nLos resultados muestran una correlación moderada.\n3",
              f"{enc}\nREFERENCIAS\nPérez, J. (2021). Título.\n4",
              f"{enc}\nANEXOS\nInstrumento aplicado\n5"]
    ref = buscar_referencias(textos)
    assert ref["pagina"] == 4 and ref["candidatos"] == 1          # el del índice con puntos guía no cuenta
    texto, r = cuerpo(textos, ref)
    assert "UNIVERSIDAD CÉSAR VALLEJO" not in texto               # encabezado de margen, fuera
    assert "Universidad César Vallejo con estudiantes" in texto    # la misma frase en el texto, queda
    assert "Pérez" not in texto and "Instrumento" not in texto and "Método" not in texto
    assert r["paginas_indice_fuera"] == 1 and r["lineas_de_margen_quitadas"] == 3


def test_lote_marca_texto_sobre_foto(tmp_path):
    """Una tesis con texto visible sobre fotos de página completa (un sello
    sobre un escaneo) sale «digital», pero se marca para revisar."""
    import csv
    from feanor_el_aplasta_libros.cli import main
    carpeta = tmp_path / "t"
    carpeta.mkdir()
    _pdf_de_prueba(carpeta / "sello.pdf", ["tapado_al_reves"] * 3)
    main([str(carpeta), "--salida", str(tmp_path / "s"), "--cuerpo"])
    fila = next(csv.DictReader(open(tmp_path / "s" / "t" / "_lote.csv", encoding="utf-8-sig")))
    assert fila["clase"] == "digital" and fila["paginas_texto_sobre_foto"] == "3"
    assert "sobre una foto" in fila["revisar"] and "pocas palabras por página" in fila["revisar"]


def test_distancia_y_tasa_de_error_por_palabra():
    from feanor_el_aplasta_libros.comparacion import distancia, metricas
    assert distancia(["a", "b", "c"], ["a", "x", "c", "d"]) == 2       # una sustitución y una inserción
    m = metricas("El jurado aprueba la tesis.", "El jurado aprneba la tesis")
    assert m["palabras_nativo"] == 5 and m["errores"] == 1 and m["wer"] == 0.2


def test_lote_automatico_un_metodo_por_archivo(tmp_path):
    """Con --auto: cada archivo con su método, y los de otro tipo o dañados a
    fallos con su motivo. Sin --auto, el lote sigue como en la 0.5.3."""
    import csv
    docx = pytest.importorskip("docx")
    from pptx import Presentation
    from feanor_el_aplasta_libros.cli import main
    carpeta, salida = tmp_path / "mezcla", tmp_path / "salida"
    carpeta.mkdir()
    _tesis_sintetica(carpeta / "tesis.pdf")
    d = docx.Document(); d.add_paragraph("texto del trabajo"); d.save(carpeta / "trabajo.docx")
    pr = Presentation(); pr.slides.add_slide(pr.slide_layouts[5]).shapes.title.text = "Clase"
    pr.save(carpeta / "clase.pptx")
    (carpeta / "viejo.doc").write_bytes(b"x")
    (carpeta / "notas.txt").write_text("x")
    (carpeta / "roto.pdf").write_bytes(b"%PDF-1.4 roto")
    hay_ocr = _hay_ocr()
    if hay_ocr:
        _pdf_de_prueba(carpeta / "fotos.pdf", ["escaneada"] * 2)

    main([str(carpeta), "--auto", "--salida", str(salida)])
    res = {f["archivo"]: f for f in csv.DictReader(open(salida / "mezcla" / "_lote.csv", encoding="utf-8-sig"))}
    assert res["tesis.pdf"]["metodo"] == "texto_nativo" and res["tesis.pdf"]["estado"] == "convertida"
    assert res["trabajo.docx"]["metodo"] == "docx" and res["clase.pptx"]["metodo"] == "pptx"
    assert "guárdalo como .docx" in res["viejo.doc"]["motivo"] and res["viejo.doc"]["estado"] == "fallo"
    assert "no soportado" in res["notas.txt"]["motivo"] and res["roto.pdf"]["estado"] == "fallo"
    assert int(res["tesis.pdf"]["palabras"]) > 0 and int(res["trabajo.docx"]["palabras"]) > 0
    if hay_ocr:
        assert res["fotos.pdf"]["metodo"] == "ocr_feanor" and res["fotos.pdf"]["estado"] == "convertida"
        md = (salida / "mezcla" / "fotos" / "fotos.md").read_text(encoding="utf-8")
        assert "Texto extraído de: fotos.pdf" in md and "OCR de Feanor sin aplanar" in md


def test_comparacion_ocr_con_paginas_del_cuerpo(tmp_path):
    """La comparación toma páginas del cuerpo (no la de referencias), las lee
    como imagen y deja su texto nativo y el del OCR, con la tasa de error."""
    import csv
    if not _hay_ocr():
        pytest.skip("sin OCRmyPDF o Tesseract")
    from feanor_el_aplasta_libros.cli import main
    carpeta = tmp_path / "t"
    carpeta.mkdir()
    doc = fitz.open()
    for titulo, tema in (("CAPITULO UNO", "autoeficacia"), ("CAPITULO DOS", "motivacion"),
                         ("CAPITULO TRES", "resiliencia"), ("REFERENCIAS", "ansiedad")):
        frase = f"El estudio analiza la {tema} y el rendimiento academico de los estudiantes. "
        p = doc.new_page(width=600, height=800)
        p.insert_textbox(fitz.Rect(50, 50, 550, 760), titulo + "\n" + frase * 16, fontsize=11)
    doc.save(carpeta / "tesis.pdf")
    main([str(carpeta), "--salida", str(tmp_path / "s"), "--comparar-ocr", "1", "--paginas-comparacion", "2"])
    base = tmp_path / "s" / "t" / "comparacion_ocr"
    filas = list(csv.DictReader(open(base / "_comparacion.csv", encoding="utf-8-sig")))
    assert len(filas) == 2 and all(f["pagina"] in ("1", "2", "3") for f in filas)   # nunca la de referencias
    assert all(float(f["wer"]) < 0.2 for f in filas)
    assert (base / "tesis" / f"p{int(filas[0]['pagina']):04d}_ocr.txt").exists()
    import json
    comandos = json.loads((base / "_comparacion.json").read_text(encoding="utf-8"))["comandos_ocr"]
    assert list(comandos) == ["tesis.pdf"] and "--force-ocr" in comandos["tesis.pdf"]   # un comando por PDF


def _hay_ocr():
    """OCRmyPDF y Tesseract, buscados igual que los busca Feanor (no solo en el
    PATH: en Windows OCRmyPDF suele estar en la carpeta de `uv tool` y Tesseract
    en Program Files). Con shutil.which, en la PC del autor estas pruebas se
    saltaban sin probar nada."""
    from feanor_el_aplasta_libros.entorno import ruta_tesseract
    from feanor_el_aplasta_libros.leer import encontrar_ocrmypdf
    try:
        encontrar_ocrmypdf()
    except FileNotFoundError:
        return False
    return ruta_tesseract() is not None


def test_auto_lee_la_pagina_escaneada_aunque_traiga_sello(tmp_path):
    """Una página escaneada con un sello corto de texto se lee entera (con
    --skip-text se saltaba). Una página de imagen sin nada que leer no se rotula
    «OCR de Feanor»: queda «no se leyó» y va a las alertas."""
    import csv
    import json
    if not _hay_ocr():
        pytest.skip("sin OCRmyPDF o Tesseract")
    from feanor_el_aplasta_libros.cli import main
    carpeta = tmp_path / "c"
    carpeta.mkdir()
    _pdf_de_prueba(carpeta / "acta.pdf", ["escaneada_con_sello", "imagen_en_blanco"])
    main([str(carpeta), "--auto", "--salida", str(tmp_path / "s")])
    base = tmp_path / "s" / "c"
    r = json.loads((base / "acta" / "acta.json").read_text(encoding="utf-8"))
    assert [p["tipo"] for p in r["paginas_pdf"]] == ["escaneada", "escaneada"]
    assert r["ocr"]["paginas_leidas"] == [1] and r["ocr"]["paginas_no_leidas"] == [2]
    assert "--force-ocr" in r["ocr"]["comando"] and r["ocr"]["comando"][-2:] == ["<entrada>", "<salida>"]
    assert "jurado" in r["paginas_md"][0]["texto_crudo"].lower()               # el contenido de la foto, no solo el sello
    md = (base / "acta" / "acta.md").read_text(encoding="utf-8")
    assert "1: OCR de Feanor sin aplanar" in md and "2: solo imagen, sin texto: no se leyó" in md
    fila = next(csv.DictReader(open(base / "_lote.csv", encoding="utf-8-sig")))
    assert "que el OCR no pudo leer: [2]" in fila["revisar"]


def test_auto_capa_ocr_previa_mas_paginas_escaneadas(tmp_path):
    """PDF con OCR previo y una página escaneada: la capa previa se conserva tal
    cual y solo la página escaneada pasa por el OCR de Feanor."""
    import json
    if not _hay_ocr():
        pytest.skip("sin OCRmyPDF o Tesseract")
    from feanor_el_aplasta_libros.cli import main
    carpeta = tmp_path / "c"
    carpeta.mkdir()
    _pdf_de_prueba(carpeta / "mixto.pdf", ["ocr_previo", "ocr_previo", "ocr_previo", "escaneada"])
    main([str(carpeta), "--auto", "--salida", str(tmp_path / "s")])
    r = json.loads((tmp_path / "s" / "c" / "mixto" / "mixto.json").read_text(encoding="utf-8"))
    assert r["lote"]["metodo"] == "capa_ocr_previa+ocr_feanor"
    assert r["ocr"]["paginas_pedidas"] == [4] and r["ocr"]["paginas_leidas"] == [4]
    previo = "Texto de prueba con varias palabras para la pagina"
    assert all(r["paginas_md"][i]["texto_crudo"].strip() == previo for i in range(3))   # la capa previa, intacta


def test_ligaduras_y_guion_no_cuentan_como_error_ni_parten_palabras():
    """La comparación normaliza igual los dos textos (NFKC y guion de fin de
    línea), y el cuerpo para el léxico pasa las ligaduras a letras."""
    from feanor_el_aplasta_libros.comparacion import metricas, normalizar
    from feanor_el_aplasta_libros.cuerpo import cuerpo
    nativo = "La con\ufb01anza y la re\ufb02exión son anterior-\nmente importantes."
    ocr = "La confianza y la reflexión son anteriormente\nimportantes."
    assert metricas(nativo, ocr)["errores"] == 0
    assert normalizar(nativo).split()[:2] == ["la", "confianza"]
    texto, _ = cuerpo([nativo], None)
    assert "confianza" in texto and "reflexión" in texto and "\ufb01" not in texto


def test_auto_pagina_nativa_alterada_por_el_ocr_se_toma_del_original(tmp_path, monkeypatch):
    """OCRmyPDF reescribe el PDF entero. Si una página NO pedida sale con otro
    texto en el intermedio, el .md usa el texto del original, la página se
    lista en ocr.paginas_alteradas y va a las alertas. Se simula OCRmyPDF para
    poder forzar la alteración."""
    import csv
    import json
    import feanor_el_aplasta_libros.leer as leer
    from feanor_el_aplasta_libros.cli import main

    def ocr_falso(entrada, salida, paginas, idioma="spa"):
        doc = fitz.open(entrada)
        for i in paginas:
            doc[i - 1].insert_text((50, 200), "LEIDO POR OCR")       # la página pedida «se lee»
        doc[1].insert_text((50, 300), "ALTERADO AL REESCRIBIR")      # la página 2, nativa, cambia
        doc.save(salida)
        return ["ocrmypdf", "-l", idioma, "--force-ocr", "--pages", ",".join(map(str, paginas)), str(entrada), str(salida)]

    monkeypatch.setattr(leer, "ocr_paginas", ocr_falso)
    carpeta = tmp_path / "c"
    carpeta.mkdir()
    _pdf_de_prueba(carpeta / "mixto.pdf", ["escaneada", "digital", "digital"])
    main([str(carpeta), "--auto", "--salida", str(tmp_path / "s")])
    base = tmp_path / "s" / "c"
    r = json.loads((base / "mixto" / "mixto.json").read_text(encoding="utf-8"))
    assert r["lote"]["metodo"] == "texto_nativo+ocr_feanor"
    assert r["ocr"]["paginas_alteradas"] == [2] and r["ocr"]["paginas_leidas"] == [1]
    assert "ALTERADO" not in r["paginas_md"][1]["texto_crudo"]                     # se usó el original
    assert "LEIDO POR OCR" in r["paginas_md"][0]["texto_crudo"]
    md = (base / "mixto" / "mixto.md").read_text(encoding="utf-8")
    assert "ALTERADO" not in md
    fila = next(csv.DictReader(open(base / "_lote.csv", encoding="utf-8-sig")))
    assert "cambiaron al reescribir el PDF" in fila["revisar"]


def test_referencias_casos_de_la_calibracion():
    """Casos reales de la calibración (texto inventado, misma forma): artículo
    anexado con sus referencias (UCV), índice sin números con errata en el
    título real, página de UNMSM que dice cómo citar la tesis, años en su propia
    línea, prosa cortada en «referencias bibliográficas» y tilde combinante."""
    from feanor_el_aplasta_libros.referencias import buscar_referencias
    cuerpo = "El estudio analiza la variable en los estudiantes de la muestra."
    # UCV: las referencias de la tesis, no las del artículo anexado
    ucv = ["ÍNDICE\nVII. Referencias bibliográficas\nVIII. Anexos", cuerpo,
           "VII. Referencias bibliográficas\nPérez, J. (2015). Título.", "VIII. Anexos\nAnexo 1: Matriz",
           "Anexo 4: Artículo científico\nResumen del artículo", "REFERENCIAS\nOtro, A. (2014). Título."]
    r = buscar_referencias(ucv)
    assert r["pagina"] == 3 and r["regla"] == "último título antes del primer anexo"
    assert r["termina_antes_de"]["pagina"] == 4
    # índice sin números («ESQUEMA») y errata en el título real (falta la r)
    esquema = ["2\nESQUEMA\nIntroducción\nCONCLUSIONES\nREFERENCIAS BIBLIOGRÁFICAS\nANEXOS", cuerpo, cuerpo,
               "REFERENCIAS BIBLIOGÁFICAS\nBadiou, A. (2014). Elogio del amor."]
    assert buscar_referencias(esquema)["pagina"] == 4
    # UNMSM: la página de cómo citar no es la sección; el singular numerado sí
    unmsm = ["Referencia bibliográfica\nAlarcón, F. (2015). Estudio. [Tesis de maestría].", cuerpo,
             "VII. REFERENCIA BIBLIOGRAFICA\nAcosta, D. (2010). Título."]
    r = buscar_referencias(unmsm)
    assert r["pagina"] == 3 and r["candidatos"] == 1
    # años en su línea: la página no es un índice aunque markdown.es_indice lo diga
    anios = ["BIBLIOGRAFÍA.\nABAD, Samuel\n2014\nTítulo uno\nABANTO, Manuel\n2000\nTítulo dos\nPÉREZ, Ana\n2010\nTítulo tres"]
    assert buscar_referencias([cuerpo, cuerpo] + anios, indices=[3])["pagina"] == 3
    # prosa cortada en minúscula no es título; tilde combinante sí
    prosa = ["Presentamos la tesis con su marco teórico y\nreferencias bibliográficas\nque esperamos se ajuste.", cuerpo]
    assert buscar_referencias(prosa) is None
    assert buscar_referencias([cuerpo, "BIBLIOGRAFÍA\nAutor (2010)."])["pagina"] == 2


def test_auto_ocr_con_salida_pdf_sin_paginas_alteradas(tmp_path):
    """Desde la 0.5.5 el OCR del lote usa --output-type pdf; en un PDF mixto, las
    páginas nativas salen con el texto idéntico."""
    import json
    if not _hay_ocr():
        pytest.skip("sin OCRmyPDF o Tesseract")
    from feanor_el_aplasta_libros.cli import main
    carpeta = tmp_path / "c"
    carpeta.mkdir()
    _pdf_de_prueba(carpeta / "mixto.pdf", ["escaneada_con_sello", "digital", "digital"])
    main([str(carpeta), "--auto", "--salida", str(tmp_path / "s")])
    r = json.loads((tmp_path / "s" / "c" / "mixto" / "mixto.json").read_text(encoding="utf-8"))
    comando = r["ocr"]["comando"]
    assert comando[comando.index("--output-type") + 1] == "pdf"
    assert r["ocr"]["paginas_alteradas"] == [] and r["ocr"]["paginas_leidas"] == [1]


def test_lote_guarda_comando_y_separa_alertas(tmp_path, monkeypatch):
    """_lote.json guarda la línea de comandos; la alerta de páginas alteradas
    separa «solo espacios» de «cambian palabras» (OCRmyPDF simulado)."""
    import csv
    import json
    import feanor_el_aplasta_libros.leer as leer
    from feanor_el_aplasta_libros.cli import main

    def ocr_falso(entrada, salida, paginas, idioma="spa", tipo_salida="pdf"):
        doc = fitz.open(entrada)
        for i in paginas:
            doc[i - 1].insert_text((50, 200), "LEIDO POR OCR")
        texto = doc[1].get_text("text")                     # página 2: mismo texto, otros espacios
        doc[1].add_redact_annot(doc[1].rect); doc[1].apply_redactions()
        doc[1].insert_text((50, 100), "  ".join(texto.split()))
        doc[2].insert_text((50, 300), "PALABRA NUEVA")      # página 3: cambia una palabra
        doc.save(salida)
        return ["ocrmypdf", "--output-type", tipo_salida, str(entrada), str(salida)]

    monkeypatch.setattr(leer, "ocr_paginas", ocr_falso)
    carpeta = tmp_path / "c"
    carpeta.mkdir()
    _pdf_de_prueba(carpeta / "mixto.pdf", ["escaneada", "digital", "digital"])
    main([str(carpeta), "--auto", "--salida", str(tmp_path / "s")])
    base = tmp_path / "s" / "c"
    r = json.loads((base / "mixto" / "mixto.json").read_text(encoding="utf-8"))
    assert r["ocr"]["paginas_alteradas_solo_espacios"] == [2] and r["ocr"]["paginas_alteradas_palabras"] == [3]
    fila = next(csv.DictReader(open(base / "_lote.csv", encoding="utf-8-sig")))
    assert "(cambian palabras); se usó su texto del original: [3]" in fila["revisar"]
    assert "(solo espacios); se usó su texto del original: [2]" in fila["revisar"]
    lote = json.loads((base / "_lote.json").read_text(encoding="utf-8"))
    assert lote["linea_de_comandos"] == ["feanor_el_aplasta_libros", str(carpeta), "--auto", "--salida", str(tmp_path / "s")]
