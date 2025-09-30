import os
import shutil
import zipfile
from jinja2 import Environment, FileSystemLoader
from uuid import uuid4
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom.minidom import parseString

TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "templates")


def save_pages_as_html(units, ungrouped_pages, output_dir, template_name="base.html"):
    env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
    template = env.get_template(template_name)

    # Guardar páginas con unidad
    for unit_idx, unit in enumerate(units, start=1):
        for page_idx, page in enumerate(unit["pages"], start=1):
            filename = f"page_{unit_idx}_{page_idx}.html"
            html = template.render(title=page["title"], content=page["html"])
            with open(os.path.join(output_dir, filename), "w", encoding="utf-8") as f:
                f.write(html)
            page["file_name"] = filename

    # Guardar páginas sin unidad
    for idx, page in enumerate(ungrouped_pages, start=1):
        filename = f"ungrouped_{idx}.html"
        html = template.render(title=page["title"], content=page["html"])
        with open(os.path.join(output_dir, filename), "w", encoding="utf-8") as f:
            f.write(html)
        page["file_name"] = filename

    return units, ungrouped_pages


def build_imsmanifest(course_title, units, ungrouped_pages, output_dir):
    from xml.etree.ElementTree import Element, SubElement, tostring
    from xml.dom.minidom import parseString

    manifest = Element("manifest", {
        "identifier": "com.example.scormcourse",
        "version": "1.2",
        "xmlns": "http://www.imsproject.org/xsd/imscp_rootv1p1p2",
        "xmlns:adlcp": "http://www.adlnet.org/xsd/adlcp_rootv1p2",
        "xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance",
        "xsi:schemaLocation": (
            "http://www.imsproject.org/xsd/imscp_rootv1p1p2 imscp_rootv1p1p2.xsd "
            "http://www.adlnet.org/xsd/adlcp_rootv1p2 adlcp_rootv1p2.xsd"
        )
    })

    metadata = SubElement(manifest, "metadata")
    SubElement(metadata, "schema").text = "ADL SCORM"
    SubElement(metadata, "schemaversion").text = "1.2"

    organizations = SubElement(manifest, "organizations", default="org1")
    organization = SubElement(organizations, "organization", identifier="org1")
    SubElement(organization, "title").text = course_title

    resources = SubElement(manifest, "resources")
    resource_counter = 1

    # Páginas sin unidad (ungrouped)
    for idx, page in enumerate(ungrouped_pages, start=1):
        res_id = f"res_ungrouped_{idx}"
        item = SubElement(organization, "item", identifier=f"ungrouped_{idx}", identifierref=res_id)
        SubElement(item, "title").text = page["title"]

        resource = SubElement(resources, "resource", {
            "identifier": res_id,
            "type": "webcontent",
            "adlcp:scormtype": "sco",
            "href": page["file_name"]
        })
        SubElement(resource, "file", href=page["file_name"])

    # Unidades (h1)
    for unit_idx, unit in enumerate(units, start=1):
        unit_id = f"unit{unit_idx}"
        pages = unit["pages"]

        if not pages:
            continue  # unidad vacía, la saltamos

        # Página de la unidad (normalmente la introducción o contenido del h1)
        first_page = pages[0]
        file_name = first_page["file_name"]
        res_id = f"res{resource_counter}"

        unit_item = SubElement(organization, "item", identifier=unit_id, identifierref=res_id)
        SubElement(unit_item, "title").text = unit["title"]

        resource = SubElement(resources, "resource", {
            "identifier": res_id,
            "type": "webcontent",
            "adlcp:scormtype": "sco",
            "href": file_name
        })
        SubElement(resource, "file", href=file_name)
        resource_counter += 1

        # Subtemas (h2 en adelante)
        for page_idx, page in enumerate(pages[1:], start=2):
            file_name = page["file_name"]
            res_id = f"res{resource_counter}"

            page_item = SubElement(unit_item, "item", identifier=f"{unit_id}_page{page_idx}", identifierref=res_id)
            SubElement(page_item, "title").text = page["title"]

            resource = SubElement(resources, "resource", {
                "identifier": res_id,
                "type": "webcontent",
                "adlcp:scormtype": "sco",
                "href": file_name
            })
            SubElement(resource, "file", href=file_name)
            resource_counter += 1

    # Guardar imsmanifest.xml
    xml_str = tostring(manifest, encoding="utf-8")
    pretty_xml = parseString(xml_str).toprettyxml(indent="  ")

    with open(os.path.join(output_dir, "imsmanifest.xml"), "w", encoding="utf-8") as f:
        f.write(pretty_xml)

def package_scorm(output_dir, output_zip_path):
    with zipfile.ZipFile(output_zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(output_dir):
            for file in files:
                abs_path = os.path.join(root, file)
                rel_path = os.path.relpath(abs_path, output_dir)
                zipf.write(abs_path, rel_path)


def build_scorm_package(units_and_ungrouped, output_zip_path, course_title="Mi Curso SCORM"):
    """
    Construye un paquete SCORM desde unidades y páginas no agrupadas.

    :param units_and_ungrouped: Puede ser:
        - Una tupla (units, ungrouped_pages)
        - Una lista de varias tuplas [(units, ungrouped_pages), ...]
    :param output_zip_path: Ruta al archivo .zip SCORM de salida
    :param course_title: Título del curso SCORM
    """
    temp_dir = f"scorm_temp_{uuid4().hex}"
    os.makedirs(temp_dir, exist_ok=True)

    try:
        # Normalizar entrada: permitir lista de tuplas
        if isinstance(units_and_ungrouped, tuple):
            all_units, all_ungrouped = units_and_ungrouped
        elif isinstance(units_and_ungrouped, list):
            all_units, all_ungrouped = [], []
            for units, ungrouped in units_and_ungrouped:
                all_units.extend(units)
                all_ungrouped.extend(ungrouped)
        else:
            raise ValueError("units_and_ungrouped debe ser una tupla o una lista de tuplas")

        # Guardar HTMLs con plantilla
        all_units, all_ungrouped = save_pages_as_html(all_units, all_ungrouped, temp_dir)

        # Generar imsmanifest.xml
        build_imsmanifest(course_title, all_units, all_ungrouped, temp_dir)

        # Empaquetar SCORM
        package_scorm(temp_dir, output_zip_path)

    finally:
        shutil.rmtree(temp_dir)
