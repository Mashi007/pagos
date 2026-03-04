#!/bin/bash

# Test: Rechazo de Documentos Duplicados
# Script Bash para validar la funcionalidad en backend disponible

set -e

BASE_URL="https://pagos-backend-ov5f.onrender.com/api/v1"
EMAIL="itmaster@rapicreditca.com"
PASSWORD="Itmaster@2024"
TMP_DIR="/tmp"

# Colores
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

log_success() {
    echo -e "${GREEN}[✓]${NC} $1"
}

log_error() {
    echo -e "${RED}[✗]${NC} ERROR: $1"
}

log_info() {
    echo -e "${YELLOW}[*]${NC} $1"
}

log_test() {
    echo -e "${CYAN}[TEST]${NC} $1"
}

# === SETUP: Autenticacion ===
echo ""
log_test "Autenticacion"

LOGIN_RESPONSE=$(curl -s -X POST "$BASE_URL/auth/login" \
    -H "Content-Type: application/json" \
    -d "{\"email\": \"$EMAIL\", \"password\": \"$PASSWORD\"}")

TOKEN=$(echo "$LOGIN_RESPONSE" | jq -r '.access_token')

if [ -z "$TOKEN" ] || [ "$TOKEN" = "null" ]; then
    log_error "No se pudo obtener token"
    exit 1
fi

log_success "Autenticado con token"

# === CREAR CLIENTE Y PRESTAMO ===
log_test "Crear cliente para pruebas"

TIMESTAMP=$(date +%s%N | cut -b1-14)
RANDOM_ID=$((RANDOM % 9000 + 1000))
CLIENTE_CEDULA="V${TIMESTAMP:8:6}"
CLIENTE_NOMBRES="Test_Dup_$RANDOM_ID"

CLIENTE_RESPONSE=$(curl -s -X POST "$BASE_URL/clientes" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d "{
        \"cedula\": \"$CLIENTE_CEDULA\",
        \"nombres\": \"$CLIENTE_NOMBRES\",
        \"apellidos\": \"Test\",
        \"direccion\": \"Calle Test\",
        \"fecha_nacimiento\": \"1990-01-01\",
        \"ocupacion\": \"Test\",
        \"usuario_registro\": \"$EMAIL\",
        \"notas\": \"Cliente para test duplicados\"
    }")

CLIENTE_ID=$(echo "$CLIENTE_RESPONSE" | jq -r '.id')

if [ -z "$CLIENTE_ID" ] || [ "$CLIENTE_ID" = "null" ]; then
    log_error "No se pudo crear cliente"
    echo "$CLIENTE_RESPONSE"
    exit 1
fi

log_success "Cliente creado: $CLIENTE_CEDULA"

# Crear prestamo
log_test "Crear prestamo"

PRESTAMO_RESPONSE=$(curl -s -X POST "$BASE_URL/prestamos" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d "{
        \"cliente_id\": $CLIENTE_ID,
        \"total_financiamiento\": 36000,
        \"numero_cuotas\": 3,
        \"usuario_proponente\": \"$EMAIL\",
        \"usuario_aprobacion\": \"$EMAIL\"
    }")

PRESTAMO_ID=$(echo "$PRESTAMO_RESPONSE" | jq -r '.id')

if [ -z "$PRESTAMO_ID" ] || [ "$PRESTAMO_ID" = "null" ]; then
    log_error "No se pudo crear prestamo"
    echo "$PRESTAMO_RESPONSE"
    exit 1
fi

log_success "Prestamo creado: $PRESTAMO_ID"

# === TEST 1: Pago Individual - Documento Original ===
echo ""
log_test "TEST 1: Pago Individual - Documento Original"

PAGO_ORIGINAL=$(curl -s -X POST "$BASE_URL/pagos" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d "{
        \"cedula_cliente\": \"$CLIENTE_CEDULA\",
        \"prestamo_id\": $PRESTAMO_ID,
        \"monto_pagado\": 12000,
        \"fecha_pago\": \"2026-03-05\",
        \"numero_documento\": \"DOC_ORIGINAL_001\"
    }")

PAGO_ID=$(echo "$PAGO_ORIGINAL" | jq -r '.id')

if [ "$PAGO_ID" != "null" ] && [ ! -z "$PAGO_ID" ]; then
    log_success "Pago original creado: ID=$PAGO_ID"
    TEST1_PASS=1
else
    log_error "No se pudo crear pago"
    echo "$PAGO_ORIGINAL"
    TEST1_PASS=0
fi

# === TEST 2: Pago Individual - Documento DUPLICADO ===
echo ""
log_test "TEST 2: Pago Individual - Documento DUPLICADO (debe rechazarse)"

PAGO_DUP=$(curl -s -X POST "$BASE_URL/pagos" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d "{
        \"cedula_cliente\": \"$CLIENTE_CEDULA\",
        \"prestamo_id\": $PRESTAMO_ID,
        \"monto_pagado\": 8000,
        \"fecha_pago\": \"2026-03-10\",
        \"numero_documento\": \"DOC_ORIGINAL_001\"
    }" -w "\n%{http_code}")

HTTP_CODE=$(echo "$PAGO_DUP" | tail -n 1)
PAGO_DUP_BODY=$(echo "$PAGO_DUP" | head -n -1)

if [ "$HTTP_CODE" = "409" ]; then
    log_success "Pago duplicado rechazado con 409 CONFLICT"
    ERROR_MSG=$(echo "$PAGO_DUP_BODY" | jq -r '.detail')
    log_info "Mensaje: $ERROR_MSG"
    TEST2_PASS=1
else
    log_error "Se esperaba 409, se obtuvo $HTTP_CODE"
    echo "$PAGO_DUP_BODY"
    TEST2_PASS=0
fi

# === TEST 3: Carga Masiva - Doc NUEVO + DUPLICADO en BD ===
echo ""
log_test "TEST 3: Carga Masiva - Doc NUEVO + DUPLICADO en BD"

# Crear archivo CSV
EXCEL_FILE="$TMP_DIR/test_dup_db_${TIMESTAMP}.csv"
cat > "$EXCEL_FILE" << EOF
cedula,prestamo_id,fecha_pago,monto_pagado,numero_documento
$CLIENTE_CEDULA,$PRESTAMO_ID,2026-03-10,8000,DOC_NEW_001
$CLIENTE_CEDULA,$PRESTAMO_ID,2026-03-15,5000,DOC_ORIGINAL_001
EOF

log_info "Archivo CSV creado: $EXCEL_FILE"

# Intentar convertir a XLSX (si tiene ssconvert o libreoffice)
if command -v ssconvert &> /dev/null; then
    XLSX_FILE="${EXCEL_FILE%.csv}.xlsx"
    ssconvert "$EXCEL_FILE" "$XLSX_FILE" 2>/dev/null || XLSX_FILE="$EXCEL_FILE"
elif command -v libreoffice &> /dev/null; then
    XLSX_FILE="${EXCEL_FILE%.csv}.xlsx"
    libreoffice --headless --convert-to xlsx:"MS Excel 2007 XML" "$EXCEL_FILE" --outdir "$TMP_DIR" 2>/dev/null || XLSX_FILE="$EXCEL_FILE"
else
    log_info "No converter available, using CSV"
    XLSX_FILE="$EXCEL_FILE"
fi

# Subir archivo
UPLOAD_RESPONSE=$(curl -s -X POST "$BASE_URL/pagos/upload" \
    -H "Authorization: Bearer $TOKEN" \
    -F "file=@$XLSX_FILE")

REGISTROS_CREADOS=$(echo "$UPLOAD_RESPONSE" | jq -r '.registros_creados')
REGISTROS_ERROR=$(echo "$UPLOAD_RESPONSE" | jq -r '.registros_con_error')

log_info "Registros creados: $REGISTROS_CREADOS"
log_info "Registros con error: $REGISTROS_ERROR"

if [ "$REGISTROS_CREADOS" = "1" ] && [ "$REGISTROS_ERROR" = "1" ]; then
    log_success "Carga masiva: 1 creado, 1 rechazado (duplicado en BD)"
    TEST3_PASS=1
else
    log_error "Se esperaba 1 creado y 1 error, se obtuvo: $REGISTROS_CREADOS/$REGISTROS_ERROR"
    TEST3_PASS=0
fi

# === TEST 4: Carga Masiva - Documentos DUPLICADOS en ARCHIVO ===
echo ""
log_test "TEST 4: Carga Masiva - Documentos DUPLICADOS DENTRO del archivo"

# Crear archivo CSV con duplicados internos
EXCEL_FILE2="$TMP_DIR/test_dup_internal_${TIMESTAMP}.csv"
cat > "$EXCEL_FILE2" << EOF
cedula,prestamo_id,fecha_pago,monto_pagado,numero_documento
$CLIENTE_CEDULA,$PRESTAMO_ID,2026-03-10,8000,DOC_INT_001
$CLIENTE_CEDULA,$PRESTAMO_ID,2026-03-15,5000,DOC_INT_002
$CLIENTE_CEDULA,$PRESTAMO_ID,2026-03-20,5000,DOC_INT_001
EOF

log_info "Archivo CSV creado con 3 filas (2 con mismo documento)"

# Convertir a XLSX si es posible
if command -v ssconvert &> /dev/null; then
    XLSX_FILE2="${EXCEL_FILE2%.csv}.xlsx"
    ssconvert "$EXCEL_FILE2" "$XLSX_FILE2" 2>/dev/null || XLSX_FILE2="$EXCEL_FILE2"
elif command -v libreoffice &> /dev/null; then
    XLSX_FILE2="${EXCEL_FILE2%.csv}.xlsx"
    libreoffice --headless --convert-to xlsx:"MS Excel 2007 XML" "$EXCEL_FILE2" --outdir "$TMP_DIR" 2>/dev/null || XLSX_FILE2="$EXCEL_FILE2"
else
    XLSX_FILE2="$EXCEL_FILE2"
fi

# Subir archivo
UPLOAD_RESPONSE2=$(curl -s -X POST "$BASE_URL/pagos/upload" \
    -H "Authorization: Bearer $TOKEN" \
    -F "file=@$XLSX_FILE2")

REGISTROS_CREADOS2=$(echo "$UPLOAD_RESPONSE2" | jq -r '.registros_creados')
REGISTROS_ERROR2=$(echo "$UPLOAD_RESPONSE2" | jq -r '.registros_con_error')

log_info "Registros creados: $REGISTROS_CREADOS2"
log_info "Registros con error: $REGISTROS_ERROR2"

if [ "$REGISTROS_CREADOS2" = "2" ] && [ "$REGISTROS_ERROR2" = "1" ]; then
    log_success "Carga masiva: 2 creados, 1 rechazado (duplicado en archivo)"
    TEST4_PASS=1
else
    log_error "Se esperaba 2 creados y 1 error, se obtuvo: $REGISTROS_CREADOS2/$REGISTROS_ERROR2"
    TEST4_PASS=0
fi

# === CLEANUP ===
rm -f "$EXCEL_FILE" "$EXCEL_FILE2" "${EXCEL_FILE%.csv}.xlsx" "${EXCEL_FILE2%.csv}.xlsx" 2>/dev/null

# === RESUMEN ===
echo ""
echo "====== RESUMEN DE RESULTADOS ======"
log_success "TEST 1: Pago original aceptado"
[ $TEST2_PASS -eq 1 ] && log_success "TEST 2: Documento duplicado rechazado con 409" || log_error "TEST 2: FALLO"
[ $TEST3_PASS -eq 1 ] && log_success "TEST 3: Carga masiva rechaza duplicado en BD" || log_error "TEST 3: FALLO"
[ $TEST4_PASS -eq 1 ] && log_success "TEST 4: Carga masiva rechaza duplicado en archivo" || log_error "TEST 4: FALLO"

echo ""
if [ $TEST1_PASS -eq 1 ] && [ $TEST2_PASS -eq 1 ] && [ $TEST3_PASS -eq 1 ] && [ $TEST4_PASS -eq 1 ]; then
    echo -e "${GREEN}CONCLUSIÓN: ¡Todos los tests pasaron!${NC}"
    exit 0
else
    echo -e "${RED}CONCLUSIÓN: Algunos tests fallaron${NC}"
    exit 1
fi
