#!/bin/bash
# Script Bash para ejecutar análisis de estructura y coherencia
# Analiza estructura de columnas, relaciones entre tablas y coherencia con endpoints

echo "========================================"
echo "  ANÁLISIS DE ESTRUCTURA Y COHERENCIA"
echo "========================================"
echo ""

# Verificar que estamos en el directorio correcto
if [ ! -d "backend" ]; then
    echo "❌ Error: Este script debe ejecutarse desde la raíz del proyecto"
    exit 1
fi

# Activar entorno virtual si existe
if [ -f "backend/.venv/bin/activate" ]; then
    echo "🔧 Activando entorno virtual..."
    source backend/.venv/bin/activate
elif [ -f ".venv/bin/activate" ]; then
    echo "🔧 Activando entorno virtual..."
    source .venv/bin/activate
fi

# Ejecutar el script de análisis
echo "🚀 Ejecutando análisis de estructura y coherencia..."
echo ""

python scripts/analisis_estructura_coherencia.py

echo ""
echo "✅ Análisis completado"
