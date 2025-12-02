import os
import mammoth
from odf.opendocument import load
from odf import text
from odf import teletype
import base64
from bs4 import BeautifulSoup, NavigableString, Tag

def read_docx_as_html(path):
    def embed_image(image):
        try:
            with image.open() as image_bytes:
                encoded = base64.b64encode(image_bytes.read()).decode("utf-8")
                return {"src": f"data:{image.content_type};base64,{encoded}"}
        except:
            return {}
    with open(path, "rb") as f:
        result = mammoth.convert_to_html(f, convert_image=mammoth.images.inline(embed_image))
        return result.value

def read_odt_as_html(path):
    odt = load(path)
    html = ""
    for child in odt.text.childNodes:
        if child.qname == (text.H).qname:
            level = child.getAttribute("outline-level")
            html += f"<h{level}>{teletype.extractText(child)}</h{level}>\n"
        elif child.qname == (text.P).qname:
            html += f"<p>{teletype.extractText(child)}</p>\n"
    return html

def convert_to_tree(input_file, split_tags):
    ext = os.path.splitext(input_file)[1].lower()
    html = read_odt_as_html(input_file) if ext == ".odt" else read_docx_as_html(input_file)
    return html_to_hierarchical_tree(html, split_tags)