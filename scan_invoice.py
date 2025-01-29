from flask import Flask, request, jsonify, render_template
import openai
import pdfplumber
from PIL import Image
import pytesseract
import os
import uuid
import cv2
import numpy as np
from pdf2image import convert_from_path

# Configura tu clave de API de OpenAI
openai.api_key = "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"
openai.organization = "org-DytU29Sd5oMHYt7UkTPvoRxI"

# Configura el archivo de Tesseract
# project_root = os.path.dirname(os.path.abspath(__file__))
# tesseract_path = os.path.join(project_root, "Tesseract-OCR", "tesseract.exe")

# if not os.path.exists(tesseract_path):
#     raise FileNotFoundError(f"No se encontró tesseract.exe en: {tesseract_path}")

# pytesseract.pytesseract.tesseract_cmd = tesseract_path
pytesseract.pytesseract.tesseract_cmd = "tesseract"

app = Flask(__name__)

# Definición de las propiedades de la factura
properties = {
    "id_factura": {"type": "string", "description": "Número de factura"},
    "tipo_factura": {"type": "string", "description": "Tipo de factura 'A' o 'B'"},
    "total": {"type": "string", "description": "Total de la factura"},
    "subtotal": {"type": "string", "description": "Total del subtotal de la factura"},
    "iva": {"type": "string", "description": "Total de la 'Percepción IVA' de la factura"},
    "ing_brutos": {"type": "string", "description": "Total de los 'Percepción IIBB' de la factura"},
    "cuit_cliente": {"type": "string", "description": "CUIT del cliente"},
    "cuit_proveedor": {"type": "string", "description": "CUIT del proveedor"},
    "items": {
        "type": "array",
        "description": "Productos de la factura",
        "items": {
            "type": "object",
            "properties": {
                "codigo": {"type": "string", "description": "Código del producto"},
                "price_unity": {"type": "string", "description": "Precio unitario del producto en decimal, sin redondear"},
                "cantidad": {"type": "number", "description": "Cantidad de productos"}
            }
        }
    }
}

# Preprocesamiento de imágenes
def preprocess_image(image_path):
    # Cargar la imagen en escala de grises
    image = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    
    # Aplicar un filtro de suavizado para reducir el ruido
    image = cv2.GaussianBlur(image, (5, 5), 0)
    
    # Aplicar umbralización adaptativa para mejorar el contraste
    image = cv2.adaptiveThreshold(
        image, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
    )
    
    return image

# Extraer texto de una imagen
def extract_text_from_image(image_path):
    try:
        # Preprocesar la imagen
        preprocessed_image = preprocess_image(image_path)
        
        # Convertir la imagen preprocesada a un objeto PIL
        image_pil = Image.fromarray(preprocessed_image)
        
        # Extraer texto usando Tesseract
        text = pytesseract.image_to_string(image_pil, lang='spa')
        return text.strip()
    except Exception as e:
        raise RuntimeError(f"Error al procesar la imagen: {e}")

# Extraer texto de un archivo PDF
def extract_text_from_pdf(pdf_path):
    try:
        # Convertir el PDF en una lista de imágenes
        images = convert_from_path(pdf_path)
        
        text = ""
        for image in images:
            # Guardar la imagen temporalmente
            temp_image_path = f"temp_{uuid.uuid4()}.jpg"
            image.save(temp_image_path, "JPEG")
            
            # Extraer texto de la imagen
            text += extract_text_from_image(temp_image_path) + "\n"
            
            # Eliminar la imagen temporal
            os.remove(temp_image_path)
        
        return text.strip()
    except Exception as e:
        raise RuntimeError(f"Error al procesar el PDF: {e}")

# Determinar si es PDF o imagen
def extract_text(file_path):
    if file_path.lower().endswith(".pdf"):
        return extract_text_from_pdf(file_path)
    elif file_path.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
        return extract_text_from_image(file_path)
    else:
        raise ValueError("Formato de archivo no compatible. Usa PDF o una imagen.")

# Envía el texto a ChatGPT para extraer datos
def extract_data_from_invoice(text):
    try:
        prompt = f"""
        Extrae los datos de la factura basándote en la siguiente estructura y damelo en formato json nada mas, y proporciona los valores correspondientes a cada campo y si no encontras solo pone "No encontrado":
        
        - Número de factura (id_factura)
        - Tipo de factura (tipo_factura): 'A' o 'B'
        - Total de la factura (total)
        - Subtotal de la factura (subtotal)
        - Percepción IVA (iva)
        - Percepción IIBB (ing_brutos)
        - CUIT del cliente (cuit_cliente)
        - CUIT del proveedor (cuit_proveedor)
        - Items (items): Lista de productos con código, precio unitario y cantidad.
        
        Texto de la factura:
        {text}
        """
        
        response = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "Eres un asistente que extrae datos de facturas."},
                {"role": "user", "content": prompt}
            ]
        )
        return response['choices'][0]['message']['content']
    except Exception as e:
        raise RuntimeError(f"Error al procesar la solicitud de OpenAI: {e}")

# Ruta principal para mostrar el formulario
@app.route('/')
def upload_form():
    return render_template('upload_form.html')

# Ruta para subir archivos y procesarlos
@app.route('/process-invoice', methods=['POST'])
def process_invoice():
    if 'file' not in request.files:
        return jsonify({"error": "Archivo no proporcionado"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "Nombre del archivo vacío"}), 400

    try:
        # Generar un nombre único para el archivo
        unique_filename = f"{uuid.uuid4()}_{file.filename.replace(' ', '_')}"
        temp_dir = os.path.join(os.path.abspath(os.getenv('TMPDIR', '/tmp')))
        os.makedirs(temp_dir, exist_ok=True)
        file_path = os.path.join(temp_dir, unique_filename)
        file.save(file_path)

        # Procesar el archivo
        text = extract_text(file_path)
        if text:
            extracted_data = extract_data_from_invoice(text)
            os.remove(file_path)
            return jsonify({"data": extracted_data}), 200
        else:
            os.remove(file_path)
            return jsonify({"error": "No se pudo extraer texto del archivo"}), 400
    except Exception as e:
        if os.path.exists(file_path):
            os.remove(file_path)
        return jsonify({"error": f"Error en el servidor: {str(e)}"}), 500

# Inicio de la aplicación
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)