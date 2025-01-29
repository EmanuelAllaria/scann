#!/bin/bash
# build.sh
chmod +x build.sh

# Instala Tesseract y sus dependencias
echo "Installing Tesseract..."
sudo apt-get update
sudo apt-get install -y tesseract-ocr

# Instala las dependencias de Python usando Poetry
echo "Installing Python dependencies..."
poetry install --no-root