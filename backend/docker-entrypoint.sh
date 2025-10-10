#!/bin/bash
set -e

echo "🔍 Variables de entorno disponibles:"
env | grep -iE "database|postgres|railway" || echo "Ninguna variable de DB encontrada"

# NO ejecutar migraciones por ahora
echo "⚠️  Migraciones desactivadas temporalmente"

# Iniciar aplicación directamente
echo "🚀 Iniciando aplicación..."
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8080}"
