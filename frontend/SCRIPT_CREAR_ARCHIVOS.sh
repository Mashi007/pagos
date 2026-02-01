#!/bin/bash
# Script para crear todos los archivos necesarios

echo "🚀 Creando estructura de directorios..."

cd frontend/src

# Crear directorios
mkdir -p config
mkdir -p services
mkdir -p utils
mkdir -p components

echo "✅ Directorios creados"

echo "📝 Nota: Los archivos deben crearse manualmente copiando el código desde CODIGO_COMPLETO_SEGURO.md"
echo ""
echo "Archivos a crear:"
echo "  - src/config/api.js"
echo "  - src/services/api.js"
echo "  - src/services/auth.js"
echo "  - src/utils/errorHandler.js"
echo "  - src/components/Login.jsx"
echo "  - src/components/Login.css"
echo "  - src/components/Dashboard.jsx"
echo "  - src/components/Dashboard.css"
echo ""
echo "Luego ejecuta: npm install axios react-router-dom"
