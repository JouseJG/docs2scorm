import os
import base64
from io import BytesIO
from docx import Document
from docx.oxml.ns import qn
from PIL import Image
import tempfile



def _get_image_mime_type(image_data):
    """Detect image MIME type from its magic numbers."""

    magic_numbers = {
        b'\x89PNG\r\n\x1a\n': 'image/png',
        b'\xFF\xD8\xFF': 'image/jpeg',
        b'GIF87a': 'image/gif',
        b'GIF89a': 'image/gif',
        b'\x00\x00\x01\x00': 'image/x-icon',
    }

    for magic, mime in magic_numbers.items():
        if image_data.startswith(magic):
            return mime

    return 'image/png'  # default to PNG if unknown

def _convert_image_to_base64(image_data):
    """Convert image data to base64 string with proper MIME type."""

    try:
        # Try to optimize the image
        img = Image.open(BytesIO(image_data))

        # Convert RGBA to RGB if necessary
        if img.mode in ('RGBA', 'LA'):
            background = Image.new('RGB', img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[-1])
            img = background

        # Resize image if too large

        max_width = 700  # Maximum width in pixels
        if img.size[0] > max_width:
            ratio = max_width / img.size[0]
            new_size = (max_width, int(img.size[1] * ratio))
            img = img.resize(new_size, Image.Resampling.LANCZOS)

        # Save optimized image
        output = BytesIO()
        img.save(output, format='JPEG', quality=85, optimize=True)
        image_data = output.getvalue()
        mime_type = 'image/jpeg'

    except Exception as e:
        # If optimization fails, use original image data
        mime_type = _get_image_mime_type(image_data)

    base64_data = base64.b64encode(image_data).decode('utf-8')

    return f'data:{mime_type};base64,{base64_data}'

def find_image_id(element):
    """Find image relationship ID in a drawing element."""

    blip = element.find('.//a:blip', {'a': 'http://schemas.openxmlformats.org/drawingml/2006/main'})
    if blip is not None:
        embed = blip.get(qn('r:embed'))
        if embed:
            return embed

    return None

def build_html(file_path, output_path):
    """Process DOCX file and convert to HTML with styling."""

    # # Save the file temporarily
    # temp_dir = tempfile.gettempdir()
    # temp_path = os.path.join(temp_dir, 'temp.docx')
    # file.save(temp_path)

    # Open the saved file
    doc = Document(file_path)
    html_content = []

    # Define inline styles
    styles = {
        'body': 'font-family: system-ui, -apple-system, sans-serif; max-width: 800px; margin: 20px auto; padding: 20px; background: #f8fafc; color: #333;',
        'wrapper': 'background: white; padding: 30px; border-radius: 10px;',
        'h1': 'color: #1a365d; font-size: 32px; margin: 20px 0; padding-bottom: 10px; border-bottom: 2px solid #3498db;',
        'h2': 'color: #2c5282; font-size: 24px; margin: 15px 0; padding-left: 15px; border-left: 4px solid #3498db;',
        'h3': 'color: #2b6cb0; font-size: 20px; margin: 15px 0;',
        'p': 'line-height: 1.6; margin: 15px 0; color: #2d3748;',
        'definition': 'background: #f8fafc; padding: 15px; margin: 15px 0; border-left: 4px solid #4299e1; border-radius: 4px;',
        'image': 'margin: 20px auto; text-align: center;',
        'img': 'max-width: 100%; height: auto; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);',
        'strong': 'color: #2c5282; background: #e2e8f0; padding: 2px 5px; border-radius: 3px;',
        'em': 'color: #4a5568; font-style: italic;'
    }

    # Start with complete HTML structure
    html_content.append('<!DOCTYPE html>')
    html_content.append('<html lang="es">')
    html_content.append('<head>')
    html_content.append('<meta charset="UTF-8">')
    html_content.append('<meta name="viewport" content="width=device-width, initial-scale=1.0">')
    html_content.append('<title>Documento Convertido</title>')
    html_content.append('</head>')
    html_content.append(f'<body style="{styles["body"]}">')
    html_content.append(f'<div style="{styles["wrapper"]}">')
    
    try:
        # Create a mapping of image relationships
        image_rels = {}
        for rel in doc.part.rels.values():
            if "image" in rel.reltype:
                try:
                    image_data = rel.target_part.blob
                    image_base64 = _convert_image_to_base64(image_data)
                    image_rels[rel.rId] = image_base64

                except Exception as e:
                    print(f"Error processing image: {str(e)}")
                    continue

        # Process paragraphs and inline images
        for para in doc.paragraphs:
            if para.style.name.startswith('Heading'):
                level = int(para.style.name[-1])
                html_content.append(f'<h{level} style="{styles[f"h{level}"]}">{para.text}</h{level}>')

            else:
                # Check if this paragraph looks like a definition
                text = para.text.strip()
                is_definition = text and (':' in text[:50] or text.startswith('NOTA:') or text.startswith('Definición:'))

                

                if is_definition:
                    html_content.append(f'<div style="{styles["definition"]}">')

                # Check for inline images in this paragraph
                has_images = False
                xml_element = para._element

                for element in xml_element.iter():
                    if element.tag.endswith('drawing'):
                        has_images = True
                        rel_id = find_image_id(element)

                        if rel_id and rel_id in image_rels:
                            html_content.append(f'<div style="{styles["image"]}">')
                            html_content.append(f'<img src="{image_rels[rel_id]}" alt="Document image" loading="lazy" style="{styles["img"]}">')
                            html_content.append('</div>')

                # Process text content if there is any
                if para.text.strip() or not has_images:

                    formatted_text = ""

                    for run in para.runs:
                        if run.bold and run.italic:
                            formatted_text += f'<strong style="{styles["strong"]}"><em style="{styles["em"]}">{run.text}</em></strong>'

                        elif run.bold:
                            formatted_text += f'<strong style="{styles["strong"]}">{run.text}</strong>'

                        elif run.italic:
                            formatted_text += f'<em style="{styles["em"]}">{run.text}</em>'

                        else:
                            formatted_text += run.text                 

                    if formatted_text.strip():
                        html_content.append(f'<p style="{styles["p"]}">{formatted_text}</p>')          

                if is_definition:
                    html_content.append('</div>')

    finally:
        try:
            os.remove(temp_path)

        except:
            pass

    html_content.append('</div>')
    html_content.append('</body>')
    html_content.append('</html>')
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(''.join(html_content))