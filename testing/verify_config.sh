#!/bin/bash

echo "=========================================="
echo "Verificación de Configuración Railway"
echo "=========================================="

# Verificar variables críticas
echo "✓ PORT: ${PORT:-Not Set (usando default 8080)}"
echo "✓ DATABASE_URL: ${DATABASE_URL:+Configurado}"
echo "✓ SECRET_KEY: ${SECRET_KEY:+Configurado}"
echo "✓ ENVIRONMENT: ${ENVIRONMENT:-development}"

# Verificar comando de inicio
echo ""
echo "Comando de inicio:"
echo "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"

echo ""
echo "=========================================="
echo "Health Check Configuration"
echo "=========================================="
echo "Path: /health"
echo "Timeout: 100s"
echo "Expected Status: 200 OK"

echo ""
echo "=========================================="
echo "Troubleshooting Tips"
echo "=========================================="
echo "1. Verificar que DATABASE_URL esté configurado"
echo "2. Asegurar que el puerto esté disponible"
echo "3. Revisar logs de inicio en Railway"
echo "4. Verificar health endpoint manualmente"
echo "=========================================="
