#!/bin/bash
# Script de build para deployment en Render

set -e  # Exit on any error

echo "🚀 Iniciando build para deployment..."

# Limpiar cache de Python completamente
echo "🧹 Limpiando cache de Python..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -delete 2>/dev/null || true
find . -name "*.pyo" -delete 2>/dev/null || true

# Verificar que estamos en el directorio correcto
if [ ! -f "requirements.txt" ]; then
    echo "❌ Error: requirements.txt no encontrado"
    exit 1
fi

echo "✅ Build completado exitosamente"
echo "📝 Archivos de requirements disponibles:"
ls -la requirements*

echo "🔍 Estructura de la aplicación:"
ls -la app/

echo "✅ Listo para deployment"