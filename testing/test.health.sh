#!/bin/bash

# Script para verificar health endpoint
# Uso: ./test_health.sh [URL_opcional]

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

URL="${1:-http://localhost:8080}"

echo "=========================================="
echo "Testing Health Endpoint"
echo "=========================================="
echo "URL: $URL/health"
echo ""

# Test 1: Health endpoint responde
echo "Test 1: Verificando que /health responde..."
RESPONSE=$(curl -s -w "\n%{http_code}" "$URL/health" 2>/dev/null)
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | head -n-1)

if [ "$HTTP_CODE" -eq 200 ]; then
    echo -e "${GREEN}✓ PASS${NC} - Health endpoint responde 200 OK"
    echo "Response: $BODY"
else
    echo -e "${RED}✗ FAIL${NC} - Health endpoint responde $HTTP_CODE"
    echo "Response: $BODY"
    exit 1
fi

echo ""

# Test 2: Response contiene status
echo "Test 2: Verificando estructura de respuesta..."
if echo "$BODY" | grep -q '"status"'; then
    echo -e "${GREEN}✓ PASS${NC} - Respuesta contiene campo 'status'"
else
    echo -e "${RED}✗ FAIL${NC} - Respuesta no contiene campo 'status'"
fi

# Test 3: Status es healthy
if echo "$BODY" | grep -q '"status".*"healthy"'; then
    echo -e "${GREEN}✓ PASS${NC} - Status es 'healthy'"
else
    echo -e "${YELLOW}⚠ WARNING${NC} - Status no es 'healthy'"
fi

# Test 4: Database check (si existe)
if echo "$BODY" | grep -q '"database"'; then
    echo -e "${GREEN}✓ PASS${NC} - Respuesta incluye estado de base de datos"
    if echo "$BODY" | grep -q '"database".*"connected"'; then
        echo -e "${GREEN}✓ PASS${NC} - Base de datos conectada"
    else
        echo -e "${RED}✗ FAIL${NC} - Base de datos desconectada"
    fi
else
    echo -e "${YELLOW}⚠ INFO${NC} - Respuesta no incluye estado de BD (opcional)"
fi

echo ""
echo "=========================================="

# Test 5: Tiempo de respuesta
echo "Test 5: Verificando tiempo de respuesta..."
TIME_START=$(date +%s%N)
curl -s "$URL/health" > /dev/null 2>&1
TIME_END=$(date +%s%N)
TIME_DIFF=$(( (TIME_END - TIME_START) / 1000000 ))

echo "Tiempo de respuesta: ${TIME_DIFF}ms"

if [ "$TIME_DIFF" -lt 1000 ]; then
    echo -e "${GREEN}✓ PASS${NC} - Tiempo de respuesta < 1000ms"
elif [ "$TIME_DIFF" -lt 5000 ]; then
    echo -e "${YELLOW}⚠ WARNING${NC} - Tiempo de respuesta entre 1-5s"
else
    echo -e "${RED}✗ FAIL${NC} - Tiempo de respuesta > 5s"
fi

echo ""
echo "=========================================="
echo "Resumen"
echo "=========================================="
echo "Health endpoint está funcionando correctamente"
echo ""
echo "Para Railway, asegúrate de tener en railway.json:"
echo '{
  "deploy": {
    "healthcheckPath": "/health",
    "healthcheckTimeout": 100
  }
}'
echo ""
echo "=========================================="
