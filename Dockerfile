# Usa una imagen de Python con soporte para Tesseract
FROM ubuntu:20.04

# Instala Tesseract y Python
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    python3 \
    python3-pip \
    libtesseract-dev

# Copia los archivos de la aplicación (incluyendo scan_invoice.py)
COPY . .

# Instala las dependencias de Python
RUN pip install --no-cache-dir -r requirements.txt

# Expone el puerto
EXPOSE 5000

# Comando para ejecutar la aplicación
CMD ["python3", "scan_invoice.py"]