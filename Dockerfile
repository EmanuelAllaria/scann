# Usa una imagen base con Python
FROM python:3.11-slim

# Instala dependencias del sistema necesarias
RUN apt-get update && \
    apt-get install -y tesseract-ocr libtesseract-dev poppler-utils && \
    rm -rf /var/lib/apt/lists/*

# Establece el directorio de trabajo
WORKDIR /app

# Copia el archivo de dependencias antes de copiar el código
COPY requirements.txt /app/

# Instala dependencias con pip
RUN pip install --no-cache-dir -r requirements.txt

# Ahora copia el resto del código fuente
COPY . /app

# Expone el puerto de Flask
EXPOSE 8000

# Comando de inicio del contenedor
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:8000", "scan_invoice:app"]
