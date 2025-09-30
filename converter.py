import os
import mammoth
from odf.opendocument import load
from odf import text
from odf import teletype
from docx import Document
import base64
from bs4 import BeautifulSoup

def read_docx_as_html(path):
    def embed_image(image):
        try:
            with image.open() as image_bytes:
                encoded = base64.b64encode(image_bytes.read()).decode("utf-8")
                return {
                    "src": f"data:{image.content_type};base64,{encoded}"
                }
        except Exception as e:
            print(f"⚠️ Imagen no disponible: {e}")
            return {}

    with open(path, "rb") as f:
        result = mammoth.convert_to_html(
            f,
            convert_image=mammoth.images.inline(embed_image)
        )
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


def extract_hierarchical_sections(html_content, ignore_empty_titles=True, include_heading_in_intro=True):
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html_content, "html.parser")
    units = []
    ungrouped_pages = []
    current_unit = None
    current_page = None
    current_intro = ""
    pending_h1_tag = None

    for tag in soup.find_all(True, recursive=True):
        tag_name = tag.name

        if tag_name == "h1":
            # Guardar contenido de la unidad anterior como página si existe
            if current_unit and current_intro.strip():
                html_intro = f"{pending_h1_tag}\n{current_intro.strip()}" if include_heading_in_intro and pending_h1_tag else current_intro.strip()
                current_unit["pages"].insert(0, {
                    "title": current_unit["title"],
                    "html": html_intro
                })

            title = tag.get_text(strip=True)
            if ignore_empty_titles and not title:
                continue

            current_unit = {"title": title, "pages": []}
            units.append(current_unit)

            pending_h1_tag = str(tag)
            current_intro = ""
            current_page = None

        elif tag_name and tag_name.startswith("h"):
            # Si hay texto entre h1 y h2 → crear página para el h1
            if current_unit and current_intro.strip():
                html_intro = f"{pending_h1_tag}\n{current_intro.strip()}" if include_heading_in_intro and pending_h1_tag else current_intro.strip()
                current_unit["pages"].insert(0, {
                    "title": current_unit["title"],
                    "html": html_intro
                })
                current_intro = ""
                pending_h1_tag = None

            if tag_name == "h2":
                title = tag.get_text(strip=True)
                if ignore_empty_titles and not title:
                    continue

                page = {"title": title, "html": str(tag)}
                if current_unit:
                    current_unit["pages"].append(page)
                else:
                    ungrouped_pages.append(page)

                current_page = page

        elif current_page:
            current_page["html"] += str(tag)

        elif current_unit:
            if tag.name or str(tag).strip():
                current_intro += str(tag)

    # Último contenido pendiente
    if current_unit and current_intro.strip():
        html_intro = f"{pending_h1_tag}\n{current_intro.strip()}" if include_heading_in_intro and pending_h1_tag else current_intro.strip()
        current_unit["pages"].insert(0, {
            "title": current_unit["title"],
            "html": html_intro
        })

    return units, ungrouped_pages

def extract_sections(html_content, split_level=2):
    """
    Divide el HTML en secciones según el nivel de encabezado deseado (ej: <h2>).
    Devuelve una lista de dicts con 'title' y 'html'.
    """

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



def convert_to_pages(input_file, split_level=2, ignore_empty_titles=True, hierarchical=True):
    ext = os.path.splitext(input_file)[1].lower()

    if ext in [".docx", ".dotx"]:
        html = read_docx_as_html(input_file)
    elif ext == ".odt":
        html = read_odt_as_html(input_file)
    else:
        raise ValueError("Formato no soportado: usa .docx, .dotx o .odt")

    if hierarchical:
        return extract_hierarchical_sections(html, ignore_empty_titles)
    else:
        return extract_sections(html, split_level, ignore_empty_titles)

