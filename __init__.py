from .converter import convert_to_tree
from .scorm_builder import build_scorm_package, html_to_hierarchical_tree
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
    split_tags = config.get("split_tags", ["h1", "h2", "h3"])
    try:
        data = convert_to_tree(file_path, split_tags=split_tags)
        build_scorm_package(data, output_zip, course_title=config.get("course_title", "Curso"))
        return True
    except Exception as e:
        print(f"Error en doc_to_scorm: {e}")
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

def html_to_scorm(html_files: List[str], output_zip: str, config=None, assets: List[str] = None):
    config = config or DEFAULT_CONFIG
    course_title = config.get("course_title", "Curso SCORM")
    split_tags = [t.lower() for t in config.get("split_tags", ["h1", "h2", "h3"])]

    try:
        full_tree = []
        global_resources = {"css": "", "js": ""}

        for html_input in html_files:
            if not os.path.exists(html_input): 
                print(f"⚠️ Archivo no encontrado: {html_input}")
                continue
            
            with open(html_input, "r", encoding="utf-8") as f:
                html_content = f.read()

            # Convertimos y paginamos
            tree_nodes, resources = html_to_hierarchical_tree(html_content, split_tags=split_tags)
            
            full_tree.extend(tree_nodes)
            
            if resources:
                global_resources["css"] += resources["css"] + "\n"
                global_resources["js"] += resources["js"] + "\n"
        
        print(f"✅ Procesando {len(full_tree)} nodos raíz (con sub-paginación strong aplicada).")
        
        build_scorm_package(
            (full_tree, global_resources), 
            output_zip, 
            course_title=course_title,
            assets_paths=assets
        )
        return True
    except Exception as e:
        print(f"❌ Error en html_to_scorm: {e}")
        import traceback
        traceback.print_exc()
        return None