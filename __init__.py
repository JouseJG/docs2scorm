from .converter import convert_to_pages
from .scorm_builder import build_scorm_package
from .config import DEFAULT_CONFIG


def convert_to_scorm(input_file, output_zip, config=None):
    """
    Convierte un archivo .docx, .dotx o .odt en un paquete SCORM.

    :param input_file: Ruta al archivo de entrada.
    :param output_zip: Ruta donde se guardará el paquete SCORM .zip.
    :param config: Diccionario con configuración opcional:
        - split_level (int): Encabezado para dividir secciones (1 = <h1>, 2 = <h2>, etc.)
        - course_title (str): Título del curso SCORM
    """
    config = config or DEFAULT_CONFIG

    pages = convert_to_pages(input_file, split_level=config["split_level"])
    build_scorm_package(pages, output_zip, course_title=config["course_title"])
