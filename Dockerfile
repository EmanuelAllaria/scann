# Usa una imagen base con Tesseract ya instalado
FROM python:3.11-slim

# Instala dependencias del sistema
RUN apt-get update && \
    apt-get install -y tesseract-ocr libtesseract-dev poppler-utils && \
    rm -rf /var/lib/apt/lists/*

# Establece el directorio de trabajo
WORKDIR /app

# Copia los archivos del proyecto
COPY . /app

# Instala Poetry
RUN pip install --no-cache-dir poetry

# Instala las dependencias del proyecto
RUN poetry install --no-root

# Expone el puerto de Flask
EXPOSE 8000

# Comando de inicio del contenedor
CMD ["poetry", "run", "gunicorn", "-w", "4", "-b", "0.0.0.0:8000", "scan_invoice:app"]
