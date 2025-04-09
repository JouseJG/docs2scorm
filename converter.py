import os
import mammoth
from odf.opendocument import load
from odf import text
from odf import teletype
from docx import Document


def read_docx_as_html(path):
    with open(path, "rb") as f:
        result = mammoth.convert_to_html(f)
        return result.value


def read_odt_as_html(path):
    odt = load(path)
    content = odt.text
    paragraphs = content.getElementsByType(text.P)
    headings = content.getElementsByType(text.H)
    html = ""

    for h in headings:
        level = h.getAttribute("outline-level")
        text_content = teletype.extractText(h)
        html += f"<h{level}>{text_content}</h{level}>\n"

    for p in paragraphs:
        text_content = teletype.extractText(p)
        html += f"<p>{text_content}</p>\n"

    return html


def extract_sections(html_content, split_level=2):
    """
    Divide el HTML en secciones según el nivel de encabezado deseado (ej: <h2>).
    Devuelve una lista de dicts con 'title' y 'html'.
    """
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html_content, "html.parser")
    pages = []
    current_section = {"title": "Introducción", "html": ""}
    current_level = f"h{split_level}"

    # En lugar de soup.body, iteramos sobre soup directamente
    for tag in soup.children:
        if getattr(tag, "name", None) == current_level:
            if current_section["html"].strip():
                pages.append(current_section)

            current_section = {
                "title": tag.get_text(),
                "html": str(tag)
            }
        else:
            current_section["html"] += str(tag)

    if current_section["html"].strip():
        pages.append(current_section)

    return pages



def convert_to_pages(input_file, split_level=2):
    ext = os.path.splitext(input_file)[1].lower()
    
    if ext in [".docx", ".dotx"]:
        html = read_docx_as_html(input_file)
    elif ext == ".odt":
        html = read_odt_as_html(input_file)
    else:
        raise ValueError("Formato no soportado: usa .docx, .dotx o .odt")

    pages = extract_sections(html, split_level=split_level)
    return pages
