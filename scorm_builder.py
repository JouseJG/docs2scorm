import os
import shutil
import zipfile
from jinja2 import Environment, FileSystemLoader
from uuid import uuid4
import xml.etree.ElementTree as ET
from xml.dom.minidom import parseString

TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "templates")

def save_tree_files(tree_nodes, output_dir, resources, template_name="base.html"):
    env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
    template = env.get_template(template_name)
    
    # Pasamos las variables tal cual vienen del converter (que ya incluyen <style> o <script>)
    extra_css = resources.get("css", "")
    extra_js = resources.get("js", "")
    
    counter = 0

    def recursive_save(nodes):
        nonlocal counter
        for node in nodes:
            counter += 1
            filename = f"sco_{counter}.html"
            node['filename'] = filename
            
            html = template.render(
                title=node['title'],
                content=node['content'],
                extra_css=extra_css,
                extra_js=extra_js
            )
            
            with open(os.path.join(output_dir, filename), "w", encoding="utf-8") as f:
                f.write(html)
            
            if node['children']:
                recursive_save(node['children'])

    recursive_save(tree_nodes)

import os
import xml.etree.ElementTree as ET
from uuid import uuid4
from xml.dom.minidom import parseString
import re

def sanitize_title(title):
    """Elimina caracteres problemáticos (como emojis) del título"""
    return re.sub(r'[^\w\s\-.,;:()&]', '', title)

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

            # Crear <item>
            item = ET.SubElement(parent_xml, "item",
                                 identifier=item_id,
                                 identifierref=res_id)
            ET.SubElement(item, "title").text = sanitize_title(node["title"])

            # Crear <resource> como SCO
            res = ET.SubElement(resources_elem, "resource", {
                "identifier": res_id,
                "type": "webcontent",
                f"{{{NS_ADLCP}}}scormtype": "sco",  # <-- cambio aquí
                "href": node["filename"]
            })
            ET.SubElement(res, "file", href=node["filename"])

            if node.get("children"):
                recursive_item_builder(item, node["children"])

    recursive_item_builder(organization, tree_nodes)

    # Archivos extra como "asset"
    if extra_files:
        for filename in extra_files:
            res_id = f"RES-{uuid4().hex}"
            res = ET.SubElement(resources_elem, "resource", {
                "identifier": res_id,
                "type": "webcontent",
                f"{{{NS_ADLCP}}}scormtype": "asset",  # <-- archivos extra como asset
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
        print(f"✅ SCORM Generado (Compatible SCORM Cloud): {output_zip_path}")
        
    finally:
        if os.path.exists(temp_dir): shutil.rmtree(temp_dir)