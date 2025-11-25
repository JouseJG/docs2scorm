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
    for tag in soup.find_all(['style', 'script', 'link']):
        if tag.name == 'link' and 'stylesheet' in tag.get('rel', []):
             resources["css"] += str(tag) + "\n"
             tag.extract()
        elif tag.name == 'style':
            if tag.string: resources["css"] += tag.string + "\n"
            tag.extract()
        elif tag.name == 'script':
            resources["js"] += str(tag) + "\n"
            tag.extract()

    # Configuración de niveles
    header_levels = {tag: int(tag[1]) for tag in split_tags}
    
    # Estructura base
    root_node = {
        'title': 'Inicio', 
        'level': 0, 
        'content': '', 
        'children': [], 
        'filename': ''
    }
    stack = [root_node]
    
    # 2. FUNCIÓN DE DETECCIÓN DE CONTENIDO (Key Fix)
    def element_contains_header(element, tags_set):
        """Devuelve True si el elemento tiene algún header dentro de sus descendientes."""
        if not isinstance(element, Tag): return False
        return bool(element.find(tags_set))

    # 3. PROCESADOR RECURSIVO
    def process_element(element):
        """
        Analiza un elemento:
        - Si es Header: Crea nueva sección.
        - Si es Contenedor con headers dentro: Entra recursivamente (Rompe el contenedor).
        - Si es Contenido puro: Lo guarda en el nodo actual.
        """
        # A) Si es texto suelto (NavigableString)
        if not isinstance(element, Tag):
            if str(element).strip(): 
                stack[-1]['content'] += str(element)
            return

        tag_name = element.name.lower()

        # B) CASO: ES UN HEADER DE CORTE (H1, H2, H3)
        if tag_name in header_levels:
            level = header_levels[tag_name]
            title = element.get_text(strip=True) or "Sin Título"
            
            # Ajustar la pila (Stack)
            # Si el nuevo header es igual o más importante (número menor o igual) que el actual,
            # cerramos los nodos hijos para volver al padre correcto.
            while len(stack) > 1 and stack[-1]['level'] >= level:
                stack.pop()
            
            # Crear el nuevo nodo
            new_node = {
                'title': title,
                'level': level,
                'content': str(element), # El propio H se incluye al inicio de su contenido
                'children': [],
                'filename': ''
            }
            
            # Añadirlo como hijo del nodo que quedó arriba en la pila
            stack[-1]['children'].append(new_node)
            # Ahora este es el nodo activo
            stack.append(new_node)

        # C) CASO: ES UN CONTENEDOR QUE TIENE HEADERS DENTRO (Ej: un div wrapper)
        elif element_contains_header(element, split_tags):
            # No guardamos el tag <div> wrapper porque rompería la estructura al dividirlo.
            # Entramos a procesar sus hijos uno por uno.
            for child in element.children:
                process_element(child)

        # D) CASO: ES CONTENIDO NORMAL (Párrafos, Tablas, Imágenes, Divs sin headers)
        else:
            # Lo guardamos entero en el nodo activo actual
            stack[-1]['content'] += str(element)

    # 4. INICIAR EL RECORRIDO DESDE EL BODY
    start_node = soup.body if soup.body else soup
    
    # Procesamos los hijos directos del body (y la función se encargará de profundizar)
    for child in start_node.children:
        process_element(child)

    # Devolvemos los hijos del nodo raíz (ignorando el contenedor 'Inicio' vacío)
    return root_node['children'], resources

def convert_to_tree(input_file, split_tags):
    ext = os.path.splitext(input_file)[1].lower()
    html = read_odt_as_html(input_file) if ext == ".odt" else read_docx_as_html(input_file)
    return html_to_hierarchical_tree(html, split_tags)