from flask import Flask, request, jsonify, render_template
import openai
import pdfplumber
from PIL import Image
import pytesseract
import os
import uuid

# Configura tu clave de API de OpenAI
openai.api_key = "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"
openai.organization = "org-DytU29Sd5oMHYt7UkTPvoRxI"

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

# Extraer texto de un archivo PDF
def extract_text_from_pdf(pdf_path):
    try:
        with pdfplumber.open(pdf_path) as pdf:
            text = "".join(page.extract_text() for page in pdf.pages if page.extract_text())
        return text.strip()
    except Exception as e:
        raise RuntimeError(f"Error al procesar el PDF: {e}")

# Extraer texto de una imagen
def extract_text_from_image(image_path):
    try:
        image = Image.open(image_path)
        return pytesseract.image_to_string(image).strip()
    except Exception as e:
        raise RuntimeError(f"Error al procesar la imagen: {e}")

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
        response = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "Eres un asistente que extrae datos de facturas."},
                {"role": "user", "content": f"Extrae los datos de la factura basándote en la siguiente estructura:\n\n{properties}\n\nTexto:\n\n{text}"}
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

        # Crear el directorio temporal si no existe
        os.makedirs(temp_dir, exist_ok=True)

        file_path = os.path.join(temp_dir, unique_filename)

        # Guardar el archivo en la ruta
        file.save(file_path)

        # Procesar el archivo
        text = extract_text(file_path)
        if text:
            extracted_data = extract_data_from_invoice(text)
            # Eliminar el archivo temporal después del procesamiento
            os.remove(file_path)
            return jsonify({"data": extracted_data}), 200
        else:
            # Eliminar el archivo temporal si el procesamiento falla
            os.remove(file_path)
            return jsonify({"error": "No se pudo extraer texto del archivo"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Inicio de la aplicación
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
