from flask import Flask, request, render_template, jsonify
import openai
import base64
import os
from pdf2image import convert_from_path
import tempfile

app = Flask(__name__)
openai.api_key = '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'
POPPLER_PATH = r"poppler\Library\bin"

def convertir_pdf_a_imagenes(pdf_path):

    """Convierte un PDF en una lista de imágenes y devuelve las rutas de las imágenes generadas."""
    imagenes = convert_from_path(pdf_path, poppler_path=POPPLER_PATH)
    rutas_imagenes = []
    
    for i, img in enumerate(imagenes):
        ruta_img = f"pagina_{i+1}.jpeg"
        img.save(ruta_img, "JPEG")
        rutas_imagenes.append(ruta_img)
    
    return rutas_imagenes

def escanear_factura(imagenes_paths):
    """Envía las imágenes a la API de OpenAI para extraer información de la factura."""
    mensajes = [{
        "role": "user",
        "content": [{"type": "text", "text": "Extrae la información de la factura y devuélvela en formato JSON con los siguientes campos: id_factura, tipo_factura, total, subtotal, iva, ing_brutos, cuit_cliente, cuit_proveedor, items (codigo, description, price_unity, cantidad). No agregues ningún comentario adicional. Solo devuelve el JSON, no agregues texto adicional."}]
    }]
    
    for imagen_path in imagenes_paths:
        with open(imagen_path, "rb") as image_file:
            encoded_image = base64.b64encode(image_file.read()).decode('utf-8')
        mensajes[0]["content"].append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encoded_image}"}})

    payload = {"model": "gpt-4o-mini", "messages": mensajes, "max_tokens": 1000}
    response = openai.ChatCompletion.create(**payload)
    json_response = response['choices'][0]['message']['content']
    
    for imagen_path in imagenes_paths:
        os.remove(imagen_path)
    
    return json_response

@app.route('/')
def upload_form():
    return render_template('upload_form.html')

@app.route('/process-invoice', methods=['POST'])
def process_invoice():
    if 'file' not in request.files:
        return jsonify({"error": "No se proporcionó ningún archivo"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "Nombre de archivo vacío"}), 400

    # Guardar el archivo en un directorio temporal
    temp_dir = tempfile.gettempdir()
    file_path = os.path.join(temp_dir, file.filename)
    file.save(file_path)

    try:
        if file_path.lower().endswith('.pdf'):
            imagenes = convertir_pdf_a_imagenes(file_path)
        else:
            imagenes = [file_path]

        json_factura = escanear_factura(imagenes)
        return jsonify(json_factura)
    
    finally:
        # Eliminar el archivo después de su uso
        if os.path.exists(file_path):
            os.remove(file_path)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)