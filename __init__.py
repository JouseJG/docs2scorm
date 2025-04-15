from .converter import convert_to_pages
from .scorm_builder import build_scorm_package
from .html_builder import build_html

from .config import DEFAULT_CONFIG


def convert_to_scorm(file_path, output_zip, config=None):
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
        return False

def convert_to_html(file_path, output_path):
    """
    Convierte un archivo .docx a html (ACTUALMENTE SOLO SOPORTA DOCX).

    :param file_path: Ruta al archivo de entrada.
    :param output_path: Ruta del html generado.
    """
    try:
        build_html(file_path, output_path)
        return True
    except Exception as e:
        print(e)
        return False