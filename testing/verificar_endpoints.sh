#!/bin/bash

# Script de verificación de endpoints - Sistema de Préstamos y Cobranza
# Fecha: 2025-10-10

# Colores para output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# URL base de la API (ajustar según tu deployment)
API_URL="${API_URL:-https://tu-app.railway.app}"

echo -e "${BLUE}=================================================="
echo "🔍 VERIFICACIÓN DE ENDPOINTS"
echo "=================================================="
echo -e "API URL: ${API_URL}${NC}\n"

# Función para hacer requests y mostrar resultados
test_endpoint() {
    local method=$1
    local endpoint=$2
    local description=$3
    local data=$4
    local token=$5
    
    echo -e "${YELLOW}Testing:${NC} ${method} ${endpoint}"
    echo -e "${BLUE}Descripción:${NC} ${description}"
    
    if [ -n "$token" ]; then
        HEADERS="-H 'Authorization: Bearer ${token}'"
    else
        HEADERS=""
    fi
    
    if [ "$method" == "GET" ]; then
        response=$(curl -s -w "\n%{http_code}" ${HEADERS} "${API_URL}${endpoint}")
    elif [ "$method" == "POST" ]; then
        response=$(curl -s -w "\n%{http_code}" -X POST ${HEADERS} \
            -H "Content-Type: application/json" \
            -d "${data}" \
            "${API_URL}${endpoint}")
    elif [ "$method" == "PUT" ]; then
        response=$(curl -s -w "\n%{http_code}" -X PUT ${HEADERS} \
            -H "Content-Type: application/json" \
            -d "${data}" \
            "${API_URL}${endpoint}")
    elif [ "$method" == "DELETE" ]; then
        response=$(curl -s -w "\n%{http_code}" -X DELETE ${HEADERS} \
            "${API_URL}${endpoint}")
    fi
    
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')
    
    if [ "$http_code" -ge 200 ] && [ "$http_code" -lt 300 ]; then
        echo -e "${GREEN}✅ Status: ${http_code}${NC}"
        echo -e "Response: ${body}" | jq '.' 2>/dev/null || echo "$body"
    else
        echo -e "${RED}❌ Status: ${http_code}${NC}"
        echo -e "Response: ${body}"
    fi
    
    echo -e "\n---\n"
}

# ==============================================
# 1. HEALTH CHECK
# ==============================================
echo -e "${BLUE}📊 1. HEALTH CHECK${NC}\n"

test_endpoint "GET" "/health" "Verificar estado del servidor"

test_endpoint "GET" "/api/v1/health" "Health check de la API v1"

# ==============================================
# 2. DOCUMENTACIÓN
# ==============================================
echo -e "${BLUE}📚 2. DOCUMENTACIÓN${NC}\n"

echo -e "${YELLOW}Acceder a documentación interactiva:${NC}"
echo -e "  • Swagger UI: ${API_URL}/docs"
echo -e "  • ReDoc: ${API_URL}/redoc"
echo -e "  • OpenAPI JSON: ${API_URL}/openapi.json\n"

# ==============================================
# 3. AUTENTICACIÓN (Si está implementada)
# ==============================================
echo -e "${BLUE}🔐 3. AUTENTICACIÓN${NC}\n"

# Test login (ajustar credenciales según tu setup)
LOGIN_DATA='{
  "email": "admin@example.com",
  "password": "admin123"
}'

test_endpoint "POST" "/api/v1/auth/login" "Login de usuario" "$LOGIN_DATA"

# Si el login funciona, guardar el token
# TOKEN=$(echo "$response" | jq -r '.access_token')

# ==============================================
# 4. CLIENTES
# ==============================================
echo -e "${BLUE}👥 4. ENDPOINTS DE CLIENTES${NC}\n"

test_endpoint "GET" "/api/v1/clientes" "Listar todos los clientes"

test_endpoint "GET" "/api/v1/clientes/1" "Obtener cliente por ID"

CLIENT_DATA='{
  "nombre": "Juan",
  "apellido": "Pérez",
  "dni": "12345678",
  "telefono": "+51999999999",
  "email": "juan.perez@example.com",
  "direccion": "Av. Principal 123"
}'

test_endpoint "POST" "/api/v1/clientes" "Crear nuevo cliente" "$CLIENT_DATA"

# ==============================================
# 5. PRÉSTAMOS
# ==============================================
echo -e "${BLUE}💰 5. ENDPOINTS DE PRÉSTAMOS${NC}\n"

test_endpoint "GET" "/api/v1/prestamos" "Listar todos los préstamos"

test_endpoint "GET" "/api/v1/prestamos/1" "Obtener préstamo por ID"

PRESTAMO_DATA='{
  "cliente_id": 1,
  "monto": 5000.00,
  "tasa_interes": 15.0,
  "plazo_dias": 90,
  "fecha_desembolso": "2025-10-10",
  "tipo_prestamo": "PERSONAL"
}'

test_endpoint "POST" "/api/v1/prestamos" "Crear nuevo préstamo" "$PRESTAMO_DATA"

test_endpoint "GET" "/api/v1/prestamos/cliente/1" "Obtener préstamos de un cliente"

test_endpoint "GET" "/api/v1/prestamos/1/cuotas" "Obtener cuotas de un préstamo"

# ==============================================
# 6. PAGOS
# ==============================================
echo -e "${BLUE}💳 6. ENDPOINTS DE PAGOS${NC}\n"

test_endpoint "GET" "/api/v1/pagos" "Listar todos los pagos"

test_endpoint "GET" "/api/v1/pagos/1" "Obtener pago por ID"

PAGO_DATA='{
  "prestamo_id": 1,
  "monto": 500.00,
  "metodo_pago": "EFECTIVO",
  "fecha_pago": "2025-10-10"
}'

test_endpoint "POST" "/api/v1/pagos" "Registrar nuevo pago" "$PAGO_DATA"

test_endpoint "GET" "/api/v1/pagos/prestamo/1" "Obtener pagos de un préstamo"

# ==============================================
# 7. USUARIOS (Si está implementado)
# ==============================================
echo -e "${BLUE}👤 7. ENDPOINTS DE USUARIOS${NC}\n"

test_endpoint "GET" "/api/v1/users" "Listar usuarios"

test_endpoint "GET" "/api/v1/users/me" "Obtener perfil del usuario actual"

USER_DATA='{
  "email": "nuevo.usuario@example.com",
  "nombre": "Nuevo",
  "apellido": "Usuario",
  "rol": "ASESOR",
  "password": "password123"
}'

test_endpoint "POST" "/api/v1/users" "Crear nuevo usuario" "$USER_DATA"

# ==============================================
# RESUMEN
# ==============================================
echo -e "${BLUE}=================================================="
echo "✅ VERIFICACIÓN COMPLETADA"
echo "==================================================${NC}"
echo ""
echo -e "${YELLOW}Próximos pasos:${NC}"
echo "1. Revisar endpoints que fallaron"
echo "2. Verificar autenticación si está implementada"
echo "3. Probar flujos completos en Swagger UI: ${API_URL}/docs"
echo "4. Verificar logs del servidor para más detalles"
echo ""
