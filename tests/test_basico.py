"""Pruebas rápidas, sin material con derechos de autor: imágenes y PDF sintéticos."""
import cv2
import pytest
import pymupdf as fitz
import numpy as np

from aplanar_libro.aplanar import recortar
from aplanar_libro.markdown import pdf_a_markdown


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
    from aplanar_libro.markdown import limpiar
    s = limpiar("\n".join(["18", "INTRODUCCIÓN", LARGA1, "|", "—", LARGA2, "1S"]))
    assert s.split("\n") == ["INTRODUCCIÓN", LARGA1, LARGA2]


def test_indice_que_termina_en_numero_no_pierde_datos(tmp_path):
    """Auditoría 14/11/2026: el folio borraba el último número de un índice."""
    from aplanar_libro.markdown import es_indice
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
    from aplanar_libro.markdown import limpiar
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
    from aplanar_libro.markdown import limpiar
    s = limpiar("\n".join(["pasaje citado de una larga carta que mi padre escri-", "l",
                           "bió en 1951, tres años antes de la publicación de la obra",
                           "conocido como tal. Por otro lado, tal como mi pa-", "1",
                           "dre observó en el mismo lugar, la historia forma parte"]))
    assert "padre escribió\nen 1951" in s and "escril" not in s
    assert "mi padre\nobservó" in s


def test_letra_suelta_en_indice_se_conserva():
    from aplanar_libro.markdown import limpiar
    s = limpiar("\n".join(["I.", "La infancia", "V.", "Túrin en Doriath", "X.", "Nargothrond"]))
    assert "V." in s and "X." in s


def test_curva_recta_vs_curva():
    from aplanar_libro.calidad import curva_p90
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
    from aplanar_libro.markdown import deducir_folios
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
    from aplanar_libro.markdown import deducir_folios
    assert deducir_folios([LARGA1, "7\n" + LARGA1, LARGA2], indices=[]) == {}


def test_folio_con_salto_y_capitulo():
    """Pliegos 1 a 4 (folios 2 a 9), falta el pliego de 12-13, siguen 14 y 15.
    «Capítulo 1» en el encabezado no debe contar como folio."""
    from aplanar_libro.markdown import deducir_folios
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
    from aplanar_libro.pliegos import preparar
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
    from aplanar_libro.aplanar import palabras_legibles, _tesseract
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
    from aplanar_libro.pliegos import corte_de_pliego
    pliego = np.full((1000, 1600), 255, np.uint8)
    for k in range(25):                                    # texto solo a la derecha
        cv2.putText(pliego, "texto de la pagina derecha del pliego", (860, 100 + 32 * k),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, 0, 2)
    x = corte_de_pliego(pliego)
    assert x is not None and 0.38 * 1600 <= x < 860
    assert (pliego[:, :x] < 128).sum() == 0              # todo el texto quedó a la derecha


def test_folio_con_guion_y_espacio_no_tumba_la_corrida():
    """«66- » en el pie de página se lee como el folio 66 (falló en un libro de 511 páginas)."""
    from aplanar_libro.markdown import _lecturas_de_folio
    assert _lecturas_de_folio("texto de la página\nmás texto\notra línea\ny otra\n66- ") == [66]
    assert _lecturas_de_folio("- 12 -\ntexto de la página\nmás texto\notra línea\nfin") == [12]
    assert _lecturas_de_folio("texto\nmás texto\notra línea\ny otra\n66- .") == [66]


def test_powerpoint_a_markdown(tmp_path):
    """Diapositiva en columnas, número dibujado junto a su renglón, tabla y notas."""
    pptx = pytest.importorskip("pptx")
    from pptx.util import Inches
    from aplanar_libro.presentacion import pptx_a_markdown

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
    from aplanar_libro.presentacion import pptx_a_markdown

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
    from aplanar_libro.entorno import ruta_tesseract
    from aplanar_libro.presentacion import pptx_a_markdown
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
    from aplanar_libro.entorno import ruta_tesseract
    from aplanar_libro.presentacion import pptx_a_markdown
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
    assert "[?] 47" in lineas
    assert "CONFIDENCIALIDAD DEL PACIENTE" in lineas          # el texto normal va sin marca


def test_forma_de_palabra():
    """Sin diccionario: «Cpg?» (sin vocal), «%00s» (cifras dentro) y «SUPoOSICION»
    (mayúsculas mezcladas) no cuentan como palabras; sí las normales."""
    from aplanar_libro.presentacion import _parece_palabra
    for w in ["Cpg?", "%00s", "SUPoOSICION", "1", "2)", "ld", "E"]:
        assert not _parece_palabra(w), w
    for w in ["CONFIDENCIALIDAD", "Beneficencia).", "información", "(Principio", "Art."]:
        assert _parece_palabra(w), w
