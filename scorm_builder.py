import os
import shutil
import zipfile
from jinja2 import Environment, FileSystemLoader
from uuid import uuid4
import xml.etree.ElementTree as ET
from xml.dom.minidom import parseString
from bs4 import BeautifulSoup, NavigableString, Tag
import re
from urllib.parse import urlencode

TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "templates")

# --- BUILDER & TEMPLATE ---
def save_tree_files(tree_nodes, output_dir, resources, template_name="slides.html"):
    env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
    template = env.get_template(template_name)
    head_scripts = []

    extra_css = resources.get("css", "")
    extra_js = resources.get("js", "")
    extra_js_not_script = ""

    if template_name == "slides.html":
        soup = BeautifulSoup(extra_js, 'html.parser')

        head_scripts = []
        extra_js_not_script = ""

        for script in soup.find_all("script"):
            src = script.get("src")
            type_module = script.get("type") == "module"

            if src or type_module:
                # Scripts externos o modules van al head
                if str(script) not in head_scripts:
                    head_scripts.append(str(script))
            else:
                # Inline scripts solo si no están vacíos
                if script.string:
                    # Evitar duplicados
                    code = script.string.strip()
                    if code not in extra_js_not_script:
                        extra_js_not_script += code + "\n"

           
        # scripts = soup.find_all('script')

        # Usamos una expresión regular para encontrar la función que comienza con 'document.addEventListener'
        # pattern = re.compile(r"document.addEventListener\('DOMContentLoaded',\s*function\s*\(\)\s*{(.*)}\);", re.DOTALL)

        # Buscamos la función en el contenido de los scripts
        # for script in scripts:
        #     content = script.string
        #     if content:

        #         match = pattern.search(content)
        #         if match:
        #             extra_js_not_script = match.group(1).strip()

    # --- 1) Aplanar nodos en orden ---
    flat_list = []

    def flatten(nodes):
        for node in nodes:
            flat_list.append(node)
            if node['children']:
                flatten(node['children'])

    flatten(tree_nodes)

    # --- 2) Asignar filenames en orden ---
    for index, node in enumerate(flat_list):
        node['filename'] = f"sco_{index+1}.html"

    # --- 3) Asignar prev y next ---
    for i, node in enumerate(flat_list):
        node["prev"] = flat_list[i-1]["filename"] if i > 0 else None
        node["next"] = flat_list[i+1]["filename"] if i < len(flat_list)-1 else None

    # --- 4) Guardar archivos con la plantilla ---
    for node in flat_list:
        html = template.render(
            title=node['title'],
            content=node['content'],
            extra_css=extra_css,
            head_scripts=head_scripts,
            extra_js_not_script=extra_js_not_script,
            prev=node["prev"],
            next=node["next"]
        )
        
        path = os.path.join(output_dir, node['filename'])
        with open(path, "w", encoding="utf-8") as f:
            f.write(html)


def sanitize_title(title):
    return re.sub(r'[^\w\s\-.,;:()&/áéíóúÁÉÍÓÚñÑ]', '', title)

def build_imsmanifest(course_title, tree_nodes, output_dir, extra_files=None):
    ET.register_namespace('', "http://www.imsproject.org/xsd/imscp_rootv1p1p2")
    ET.register_namespace('adlcp', "http://www.adlnet.org/xsd/adlcp_rootv1p2")
    ET.register_namespace('xsi', "http://www.w3.org/2001/XMLSchema-instance")

    NS_IMSCP = "http://www.imsproject.org/xsd/imscp_rootv1p1p2"
    NS_ADLCP = "http://www.adlnet.org/xsd/adlcp_rootv1p2"

    manifest = ET.Element(f"{{{NS_IMSCP}}}manifest", {
        "identifier": f"MANIFEST-{uuid4().hex}",
        "version": "1.1"
    })

    metadata = ET.SubElement(manifest, "metadata")
    ET.SubElement(metadata, "schema").text = "ADL SCORM"
    ET.SubElement(metadata, "schemaversion").text = "1.2"

    organizations = ET.SubElement(manifest, "organizations", default="ORG-1")
    organization = ET.SubElement(organizations, "organization", identifier="ORG-1")
    ET.SubElement(organization, "title").text = sanitize_title(course_title)

    resources_elem = ET.SubElement(manifest, "resources")

    def recursive_item_builder(parent_xml, nodes):
        for node in nodes:
            item_id = f"ITEM-{uuid4().hex}"
            res_id = f"RES-{uuid4().hex}"

            # Crear item en el árbol (menú)
            item = ET.SubElement(parent_xml, "item",
                                 identifier=item_id,
                                 identifierref=res_id)
            ET.SubElement(item, "title").text = sanitize_title(node["title"])

            # Crear resource (archivo físico)
            res = ET.SubElement(resources_elem, "resource", {
                "identifier": res_id,
                "type": "webcontent",
                f"{{{NS_ADLCP}}}scormtype": "sco",
                "href": node["filename"]
            })
            # Un SCO real sólo al nivel 1 (h1)
            # is_sco = (node["level"] == 2)

            # res = ET.SubElement(resources_elem, "resource", {
            #     "identifier": res_id,
            #     "type": "webcontent",
            #     f"{{{NS_ADLCP}}}scormtype": "sco" if is_sco else "asset",
            #     "href": node["filename"]
            # })

            ET.SubElement(res, "file", href=node["filename"])

            # Recursividad
            if node.get("children"):
                recursive_item_builder(item, node["children"])

    recursive_item_builder(organization, tree_nodes)

    if extra_files:
        for filename in extra_files:
            res_id = f"RES-{uuid4().hex}"
            res = ET.SubElement(resources_elem, "resource", {
                "identifier": res_id,
                "type": "webcontent",
                f"{{{NS_ADLCP}}}scormtype": "asset",
                "href": filename
            })
            ET.SubElement(res, "file", href=filename)

    xml_str = ET.tostring(manifest, encoding="utf-8")
    pretty_xml = parseString(xml_str).toprettyxml(indent="  ")

    os.makedirs(output_dir, exist_ok=True)
    with open(os.path.join(output_dir, "imsmanifest.xml"), "w", encoding="utf-8") as f:
        f.write(pretty_xml)

def copy_assets(assets_paths, destination_dir):
    if not assets_paths: return
    for asset in assets_paths:
        if os.path.exists(asset):
            dest = os.path.join(destination_dir, os.path.basename(asset))
            if os.path.isdir(asset):
                if os.path.exists(dest): shutil.rmtree(dest)
                shutil.copytree(asset, dest)
            else:
                shutil.copy2(asset, dest)

def build_scorm_package(tree_data, output_zip_path, course_title="Curso SCORM", assets_paths=None):
    temp_dir = f"scorm_temp_{uuid4().hex}"
    os.makedirs(temp_dir, exist_ok=True)
    try:
        tree_nodes, global_resources = tree_data
        
        if assets_paths: copy_assets(assets_paths, temp_dir)
        save_tree_files(tree_nodes, temp_dir, global_resources)
        build_imsmanifest(course_title, tree_nodes, temp_dir)
        
        with zipfile.ZipFile(output_zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, _, files in os.walk(temp_dir):
                for file in files:
                    abs_path = os.path.join(root, file)
                    rel_path = os.path.relpath(abs_path, temp_dir)
                    zipf.write(abs_path, rel_path)
        print(f"✅ SCORM Generado: {output_zip_path}")
        
    finally:
        if os.path.exists(temp_dir): shutil.rmtree(temp_dir)

# --- LOGICA DE PAGINACIÓN (RENOMBRADO) ---
def process_pagination_titles(nodes):
    """
    Recorre los nodos hermanos. Si encuentra títulos idénticos consecutivos (generados por splits),
    los renombra añadiendo (x/y).
    Ejemplo: "Cosméticos" -> "Cosméticos (1/2)" y "Cosméticos (2/2)"
    """
    if not nodes:
        return

    # Agrupar nodos consecutivos con el mismo título base
    groups = []
    if nodes:
        current_group = [nodes[0]]
        for i in range(1, len(nodes)):
            if nodes[i]['title'] == nodes[i-1]['title']:
                current_group.append(nodes[i])
            else:
                groups.append(current_group)
                current_group = [nodes[i]]
        groups.append(current_group)

    # Renombrar grupos
    for group in groups:
        total = len(group)
        if total > 1:
            for index, node in enumerate(group):
                # Añadimos el contador al título
                node['title'] = f"{node['title']} ({index + 1}/{total})"

        # Recursividad para los hijos de cada nodo
        for node in group:
            if node['children']:
                process_pagination_titles(node['children'])

# --- CONVERTER (CON LOGICA DE STRONG) ---
def html_to_hierarchical_tree(html_content, split_tags=['h1', 'h2', 'h3']):
    soup = BeautifulSoup(html_content, "html.parser")
    resources = {"css": "", "js": ""}

    # 1. Extraer Assets
    for tag in soup.find_all(['style', 'script', 'link']):
        if tag.name == 'link' and 'stylesheet' in tag.get('rel', []):
             resources["css"] += str(tag) + "\n"
             tag.extract()
        elif tag.name == 'style':
            if tag.string: resources["css"] += str(tag) + "\n"
            tag.extract()
        elif tag.name == 'script':
            resources["js"] += str(tag) + "\n"
            tag.extract()

    header_levels = {tag: int(tag[1]) for tag in split_tags}
    
    # Nodo raíz invisible
    root_node = {
        'title': 'Inicio', 'level': 0, 'content': '', 'children': [], 'filename': ''
    }
    stack = [root_node]
    
    # Tags que provocan un split normal (headers) o forzado (strong)
    # Strong no tiene nivel numérico en header_levels, se maneja especial.
    
    def element_contains_splitters(element):
        """Revisa si el elemento contiene headers O strongs dentro."""
        if not isinstance(element, Tag): return False
        # Buscamos headers definidos o strong
        return bool(element.find(split_tags)) # + ['strong']))

    def process_element(element):
        if not isinstance(element, Tag):
            if str(element).strip(): 
                stack[-1]['content'] += str(element)
            return

        tag_name = element.name.lower()

        # CASO A: Es un HEADER (H1, H2, H3...)
        if tag_name in header_levels:
            level = header_levels[tag_name]
            title = element.get_text(strip=True) or "Sin Título"
            
            # Cerrar niveles más profundos o iguales
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

        # CASO C: Contenedor con headers o strongs dentro (Drill down)
        elif element_contains_splitters(element):
            # No guardamos el tag wrapper, entramos en sus hijos
            for child in element.children:
                process_element(child)

        # CASO D: Contenido normal
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

    # 2. PROCESAR PAGINACIÓN (1/X)
    # Antes de devolver el árbol, renombramos los nodos repetidos
    process_pagination_titles(root_node['children'])

    return root_node['children'], resources

def build_scorm_wrapper_package(output_zip_path, course_title, curso_id, visor_url_base, extra_params=None, assets_paths=None):
    """
    Genera un SCORM 'ligero' que apunta a la nube.
    NO procesa HTML, NO parte en trozos. Solo crea el puente.
    """
    
    extra_params = extra_params or {}
    temp_dir = f"scorm_wrapper_temp_{uuid4().hex}"
    os.makedirs(temp_dir, exist_ok=True)
    
    try:
        query_params = {
            "curso_id": curso_id,
            **extra_params
        }
        visor_full_url = f"{visor_url_base}?{urlencode(query_params)}"

        src_js = os.path.join(TEMPLATE_DIR, "scorm_wrapper.js")
        dst_js = os.path.join(temp_dir, "scorm_wrapper.js")
        
        if os.path.exists(src_js):
            shutil.copy(src_js, dst_js)
        else:
            print(f"❌ ERROR: No encuentro scorm_wrapper.js en {TEMPLATE_DIR}")
        
        shutil.copy(os.path.join(TEMPLATE_DIR, "scorm_wrapper.js"), os.path.join(temp_dir, "scorm_wrapper.js"))

        env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
        template = env.get_template("wrapper.html")
        
        html_content = template.render(
            title=course_title,
            visor_url=visor_full_url # Ej: https://app.tuempresa.com/visor
        )
        
        with open(os.path.join(temp_dir, "index.html"), "w", encoding="utf-8") as f:
            f.write(html_content)

        dummy_node = [{
            "title": course_title,
            "filename": "index.html",
            "children": []
        }]
        
        build_imsmanifest(course_title, dummy_node, temp_dir)

        with zipfile.ZipFile(output_zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, _, files in os.walk(temp_dir):
                for file in files:
                    abs_path = os.path.join(root, file)
                    rel_path = os.path.relpath(abs_path, temp_dir)
                    zipf.write(abs_path, rel_path)
                    
        print(f"✅ SCORM wrapper (Nube) Generado: {output_zip_path}")
        
    finally:
        if os.path.exists(temp_dir): shutil.rmtree(temp_dir)