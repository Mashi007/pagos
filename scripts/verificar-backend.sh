#!/bin/bash
# Script para verificar que el backend responde correctamente (health + BD)
# Uso: ./scripts/verificar-backend.sh [URL_BASE]
# Ejemplo: ./scripts/verificar-backend.sh https://pagos-backend.onrender.com

set -e
BASE_URL="${1:-http://localhost:8000}"
BASE_URL="${BASE_URL%/}"

echo "Verificando backend en: $BASE_URL"
echo ""

# Health general
echo "1. GET $BASE_URL/health"
HTTP=$(curl -s -o /tmp/health.json -w "%{http_code}" "$BASE_URL/health")
if [ "$HTTP" = "200" ]; then
  echo "   OK ($HTTP)"
  cat /tmp/health.json | head -c 100
  echo ""
else
  echo "   FALLO (HTTP $HTTP)"
  exit 1
fi

echo ""

# Health BD
echo "2. GET $BASE_URL/health/db"
HTTP=$(curl -s -o /tmp/health_db.json -w "%{http_code}" "$BASE_URL/health/db")
if [ "$HTTP" = "200" ]; then
  echo "   OK ($HTTP)"
  cat /tmp/health_db.json
  if grep -q '"database":"connected"' /tmp/health_db.json; then
    echo ""
    echo "   BD conectada correctamente."
  fi
else
  echo "   FALLO (HTTP $HTTP)"
  cat /tmp/health_db.json 2>/dev/null || true
  exit 1
fi

echo ""
echo "Verificación completada."
