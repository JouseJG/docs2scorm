import os
import shutil
import zipfile
from jinja2 import Environment, FileSystemLoader
from uuid import uuid4
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom.minidom import parseString

TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "templates")


def save_pages_as_html(pages, output_dir, template_name="base.html"):
    env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
    template = env.get_template(template_name)

    filenames = []
    for i, page in enumerate(pages):
        filename = f"page_{i+1}.html"
        html = template.render(title=page["title"], content=page["html"])
        with open(os.path.join(output_dir, filename), "w", encoding="utf-8") as f:
            f.write(html)
        filenames.append((page["title"], filename))
    return filenames


def build_imsmanifest(course_title, page_info, output_dir):
    manifest = Element("manifest", {
        "identifier": "com.example.scormcourse",
        "version": "1.2",
        "xmlns": "http://www.imsproject.org/xsd/imscp_rootv1p1p2",
        "xmlns:adlcp": "http://www.adlnet.org/xsd/adlcp_rootv1p2",
        "xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance",
        "xsi:schemaLocation": (
            "http://www.imsproject.org/xsd/imscp_rootv1p1p2 "
            "imscp_rootv1p1p2.xsd "
            "http://www.adlnet.org/xsd/adlcp_rootv1p2 "
            "adlcp_rootv1p2.xsd"
        )
    })

    # Metadata
    metadata = SubElement(manifest, "metadata")
    schema = SubElement(metadata, "schema")
    schema.text = "ADL SCORM"
    schemaversion = SubElement(metadata, "schemaversion")
    schemaversion.text = "1.2"

    # Organizations
    organizations = SubElement(manifest, "organizations", default="org1")
    organization = SubElement(organizations, "organization", identifier="org1")
    title = SubElement(organization, "title")
    title.text = course_title

    for i, (page_title, filename) in enumerate(page_info):
        item = SubElement(organization, "item", identifier=f"item{i+1}", identifierref=f"res{i+1}")
        item_title = SubElement(item, "title")
        item_title.text = page_title

    # Resources
    resources = SubElement(manifest, "resources")
    for i, (page_title, filename) in enumerate(page_info):
        resource = SubElement(resources, "resource", {
            "identifier": f"res{i+1}",
            "type": "webcontent",
            "adlcp:scormtype": "sco",
            "href": filename
        })
        SubElement(resource, "file", href=filename)

    # Pretty XML
    xml_str = tostring(manifest, encoding="utf-8")
    pretty_xml = parseString(xml_str).toprettyxml(indent="  ")

    manifest_path = os.path.join(output_dir, "imsmanifest.xml")
    with open(manifest_path, "w", encoding="utf-8") as f:
        f.write(pretty_xml)

    return manifest_path


def package_scorm(output_dir, output_zip_path):
    with zipfile.ZipFile(output_zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(output_dir):
            for file in files:
                abs_path = os.path.join(root, file)
                rel_path = os.path.relpath(abs_path, output_dir)
                zipf.write(abs_path, rel_path)


def build_scorm_package(pages, output_zip_path, course_title="Mi Curso SCORM"):
    temp_dir = f"scorm_temp_{uuid4().hex}"
    os.makedirs(temp_dir, exist_ok=True)

    try:
        page_info = save_pages_as_html(pages, temp_dir)
        build_imsmanifest(course_title, page_info, temp_dir)
        package_scorm(temp_dir, output_zip_path)
    finally:
        shutil.rmtree(temp_dir)
