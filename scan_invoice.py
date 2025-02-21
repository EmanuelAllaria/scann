from flask import Flask, request, render_template, jsonify
import openai
import base64
import os
from pdf2image import convert_from_path
import tempfile
import cv2

app = Flask(__name__)
openai.api_key = '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'
POPPLER_PATH = r"poppler\Library\bin"

def convertir_pdf_a_imagenes(pdf_path):
    imagenes = convert_from_path(pdf_path, poppler_path=POPPLER_PATH)
    rutas_imagenes = []
    
    for i, img in enumerate(imagenes):
        ruta_img = f"pagina_{i+1}.jpeg"
        img.save(ruta_img, "JPEG")

        imagen_cv = cv2.imread(ruta_img, cv2.IMREAD_GRAYSCALE)
        _, imagen_binaria = cv2.threshold(imagen_cv, 150, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        imagen_resaltada = cv2.bitwise_not(imagen_binaria)
        cv2.imwrite(ruta_img, imagen_resaltada)

        rutas_imagenes.append(ruta_img)
    
    return rutas_imagenes

def escanear_factura(imagenes_paths):
    mensajes = [{
        "role": "user",
        "content": [
            {
                "type": "text",
                "text": (
                    "Analiza la factura en la imagen adjunta y extrae toda la información relevante. Devuelve un objeto JSON con los siguientes campos:"

                    "- `id_factura`: Número de factura."
                    "- `tipo_factura`: Tipo de factura (A, B, C, etc.)."
                    "- `total`: Monto total de la factura."
                    "- `subtotal`: Importe neto antes de impuestos."
                    "- `iva`: Importe del IVA discriminado."
                    "- `ing_brutos`: Percepción de ingresos brutos (si existe, sino dejar en `null`)."
                    "- `cuit_cliente`: CUIT del cliente."
                    "- `cuit_proveedor`: CUIT del proveedor."
                    "- `items`: Lista con los productos detallados en la factura. Cada ítem debe contener:"
                    "- `codigo`: Código de producto."
                    "- `descripcion`: Descripción del producto."
                    "- `precio_unitario`: Precio unitario sin impuestos."
                    "- `cantidad`: Cantidad de unidades compradas."

                    "Si algún dato no está presente en la factura, déjalo como `null` o en vacío dentro del JSON. No incluyas ningún otro texto fuera del JSON."
                )
            }
        ]
    }]
    
    for imagen_path in imagenes_paths:
        with open(imagen_path, "rb") as archivo_imagen:
            imagen_codificada = base64.b64encode(archivo_imagen.read()).decode()
        mensajes[0]["content"].append({
            "type": "image_url",
            "image_url": {
                "url": f"data:image/jpeg;base64,{imagen_codificada}"
            }
        })

    payload = {
        "model": "gpt-4o-mini",
        "messages": mensajes,
        "temperature": 0.2,
        "top_p": 1,
        "frequency_penalty": 0,
        "presence_penalty": 0
    }
    respuesta = openai.ChatCompletion.create(**payload)
    json_respuesta = respuesta['choices'][0]['message']['content']
    
    for imagen_path in imagenes_paths:
        os.remove(imagen_path)
    
    return json_respuesta

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

    temp_dir = tempfile.gettempdir()
    file_path = os.path.join(temp_dir, file.filename)
    file.save(file_path)

    try:
        if file_path.lower().endswith('.pdf'):
            imagenes = convertir_pdf_a_imagenes(file_path)
        else:
            imagen_cv = cv2.imread(file_path, cv2.IMREAD_GRAYSCALE)
            _, imagen_binaria = cv2.threshold(imagen_cv, 150, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            imagen_resaltada = cv2.bitwise_not(imagen_binaria)
            cv2.imwrite(file_path, imagen_resaltada)
            
            imagenes = [file_path]

        json_factura = escanear_factura(imagenes)
        
        return jsonify(json_factura)

    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)