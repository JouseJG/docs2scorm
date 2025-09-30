from .converter import convert_to_pages, extract_hierarchical_sections
from .scorm_builder import build_scorm_package
from .html_builder import build_html
import os
from .config import DEFAULT_CONFIG

from typing import List


def doc_to_scorm(file_path, output_zip, config=None):
    """
    Convierte un archivo .docx, .dotx o .odt en un paquete SCORM.

    :param file_path: Ruta al archivo de entrada.
    :param output_zip: Ruta donde se guardará el paquete SCORM .zip.
    :param config: Diccionario con configuración opcional:
        - split_level (int): Encabezado para dividir secciones (1 = <h1>, 2 = <h2>, etc.)
        - course_title (str): Título del curso SCORM
    """
    config = config or DEFAULT_CONFIG

    try:
        units_and_ungrouped = convert_to_pages(file_path, split_level=config["split_level"])
        build_scorm_package(units_and_ungrouped, output_zip, course_title=config["course_title"])
        return True
    except Exception as e:
        print(e)
        return None

def doc_to_html(file_path, output_path=None):
    """
    Convierte un archivo .docx a html (ACTUALMENTE SOLO SOPORTA DOCX).

    :param file_path: Ruta al archivo de entrada.
    :param output_path: Ruta del html generado.
    """
    try:
        return build_html(file_path, output_path)
    except Exception as e:
        print(e)
        return None

def html_to_scorm(html_files: List[str], output_zip: str, config=None):
    """
    Convierte uno o varios archivos HTML en un paquete SCORM.

    :param html_files: Lista de rutas a archivos HTML.
    :param output_zip: Ruta donde se guardará el paquete SCORM .zip.
    :param config: Diccionario con configuración opcional:
        - course_title (str): Título del curso SCORM
    """
    config = config or DEFAULT_CONFIG
    course_title = config.get("course_title", "Curso SCORM")

    try:
        all_units = []
        all_ungrouped = []

        for html_input in html_files:
            with open(html_input, "r", encoding="utf-8") as f:
                html_content = f.read()

            units, ungrouped = extract_hierarchical_sections(
                html_content, ignore_empty_titles=True
            )
            all_units.extend(units)
            all_ungrouped.extend(ungrouped)
        print("Units:", all_units)
        print("Ungrouped:", all_ungrouped)
        build_scorm_package((all_units, all_ungrouped), output_zip, course_title=course_title)
        return True
    except Exception as e:
        print(f"❌ Error en html_to_scorm: {e}")
        return None