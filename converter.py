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

def html_to_hierarchical_tree(html_content, split_tags=['h1', 'h2', 'h3']):
    soup = BeautifulSoup(html_content, "html.parser")
    resources = {"css": "", "js": ""}

    # 1. Extraer Assets Globales
    # IMPORTANTE: Aquí guardamos str(tag), que incluye <style> y <script>
    for tag in soup.find_all(['style', 'script', 'link']):
        if tag.name == 'link' and 'stylesheet' in tag.get('rel', []):
             resources["css"] += str(tag) + "\n"
             tag.extract()
        elif tag.name == 'style':
            if tag.string: resources["css"] += str(tag) + "\n" # Guardamos el tag completo
            tag.extract()
        elif tag.name == 'script':
            resources["js"] += str(tag) + "\n" # Guardamos el tag completo
            tag.extract()

    header_levels = {tag: int(tag[1]) for tag in split_tags}
    
    root_node = {
        'title': 'Inicio', 'level': 0, 'content': '', 'children': [], 'filename': ''
    }
    stack = [root_node]
    
    def element_contains_header(element, tags_set):
        if not isinstance(element, Tag): return False
        return bool(element.find(tags_set))

    def process_element(element):
        if not isinstance(element, Tag):
            if str(element).strip(): 
                stack[-1]['content'] += str(element)
            return

        tag_name = element.name.lower()

        if tag_name in header_levels:
            level = header_levels[tag_name]
            title = element.get_text(strip=True) or "Sin Título"
            
            while len(stack) > 1 and stack[-1]['level'] >= level:
                stack.pop()
            
            new_node = {
                'title': title,
                'level': level,
                'content': str(element), 
                'children': [],
                'filename': ''
            }
            stack[-1]['children'].append(new_node)
            stack.append(new_node)

        elif element_contains_header(element, split_tags):
            for child in element.children:
                process_element(child)

        else:
            stack[-1]['content'] += str(element)

    start_node = soup.body if soup.body else soup
    for child in start_node.children:
        process_element(child)

    if root_node['content'].strip():
        intro_node = {
            'title': 'Introducción',
            'level': 1,
            'content': root_node['content'],
            'children': [],
            'filename': ''
        }
        root_node['children'].insert(0, intro_node)

    return root_node['children'], resources

def convert_to_tree(input_file, split_tags):
    ext = os.path.splitext(input_file)[1].lower()
    html = read_odt_as_html(input_file) if ext == ".odt" else read_docx_as_html(input_file)
    return html_to_hierarchical_tree(html, split_tags)