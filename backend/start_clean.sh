#!/bin/bash
# Script para limpiar cache de Python y reiniciar la aplicación

# Limpiar cache de Python
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -delete 2>/dev/null || true
find . -name "*.pyo" -delete 2>/dev/null || true

# Limpiar logs locales si existen
rm -f *.log 2>/dev/null || true

echo "Cache limpiado. Iniciando aplicación..."

# Iniciar aplicación
uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}