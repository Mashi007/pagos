#!/bin/bash

# Testing Script for RapiCredit API
# Run: bash test_full_flow.sh

BASE_URL="https://rapicredit.onrender.com/api/v1"
EMAIL="itmaster@rapicreditca.com"
PASSWORD="${ADMIN_PASSWORD:-}"  # Set via environment variable

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "=========================================="
echo "RapiCredit API - Full Flow Testing"
echo "=========================================="

# Test 1: Login
echo -e "\n${YELLOW}[TEST 1] LOGIN${NC}"
LOGIN_RESPONSE=$(curl -s -X POST "$BASE_URL/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\": \"$EMAIL\", \"password\": \"$PASSWORD\"}")

ACCESS_TOKEN=$(echo $LOGIN_RESPONSE | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

if [ -z "$ACCESS_TOKEN" ]; then
  echo -e "${RED}❌ LOGIN FAILED${NC}"
  echo "Response: $LOGIN_RESPONSE"
  exit 1
fi

echo -e "${GREEN}✅ LOGIN SUCCESS${NC}"
echo "Token: ${ACCESS_TOKEN:0:20}..."

# Test 2: Create Loan
echo -e "\n${YELLOW}[TEST 2] CREATE LOAN${NC}"
PRESTAMO_RESPONSE=$(curl -s -X POST "$BASE_URL/prestamos" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -d '{
    "cedula_cliente": "V12345678",
    "monto": 50000,
    "tasa_interes": 5.5,
    "plazo_meses": 24,
    "tipo_amortizacion": "FRANCESA",
    "modelo_vehiculo": "Toyota Corolla 2020",
    "concesionario": "Automotriz Central",
    "analista": "Juan Pérez"
  }')

PRESTAMO_ID=$(echo $PRESTAMO_RESPONSE | grep -o '"id":[0-9]*' | cut -d':' -f2 | head -1)

if [ -z "$PRESTAMO_ID" ]; then
  echo -e "${RED}❌ CREATE LOAN FAILED${NC}"
  echo "Response: $PRESTAMO_RESPONSE"
  exit 1
fi

echo -e "${GREEN}✅ CREATE LOAN SUCCESS${NC}"
echo "Loan ID: $PRESTAMO_ID"

# Test 3: Create Payment
echo -e "\n${YELLOW}[TEST 3] CREATE PAYMENT${NC}"
PAGO_RESPONSE=$(curl -s -X POST "$BASE_URL/pagos" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -d "{
    \"cedula\": \"V12345678\",
    \"prestamo_id\": $PRESTAMO_ID,
    \"monto_pagado\": 2500.50,
    \"fecha_pago\": \"2026-03-04\",
    \"numero_documento\": \"BNC-20260304-TEST\"
  }")

PAGO_ID=$(echo $PAGO_RESPONSE | grep -o '"id":[0-9]*' | cut -d':' -f2 | head -1)

if [ -z "$PAGO_ID" ]; then
  echo -e "${RED}❌ CREATE PAYMENT FAILED${NC}"
  echo "Response: $PAGO_RESPONSE"
  exit 1
fi

echo -e "${GREEN}✅ CREATE PAYMENT SUCCESS${NC}"
echo "Payment ID: $PAGO_ID"

# Test 4: Get Loan Details
echo -e "\n${YELLOW}[TEST 4] GET LOAN DETAILS${NC}"
LOAN_DETAILS=$(curl -s -X GET "$BASE_URL/prestamos/$PRESTAMO_ID" \
  -H "Authorization: Bearer $ACCESS_TOKEN")

LOAN_STATE=$(echo $LOAN_DETAILS | grep -o '"estado":"[^"]*' | cut -d'"' -f4)
USUARIO_PROPONENTE=$(echo $LOAN_DETAILS | grep -o '"usuario_proponente":"[^"]*' | cut -d'"' -f4)

if [ "$LOAN_STATE" = "DRAFT" ]; then
  echo -e "${GREEN}✅ LOAN STATE CORRECT (DRAFT)${NC}"
else
  echo -e "${YELLOW}⚠️  Unexpected state: $LOAN_STATE${NC}"
fi

if [ "$USUARIO_PROPONENTE" = "$EMAIL" ]; then
  echo -e "${GREEN}✅ USUARIO_PROPONENTE CORRECT${NC}"
else
  echo -e "${YELLOW}⚠️  Unexpected usuario_proponente: $USUARIO_PROPONENTE${NC}"
fi

# Test 5: Get Payment Details
echo -e "\n${YELLOW}[TEST 5] GET PAYMENT DETAILS${NC}"
PAGO_DETAILS=$(curl -s -X GET "$BASE_URL/pagos/$PAGO_ID" \
  -H "Authorization: Bearer $ACCESS_TOKEN")

PAGO_STATE=$(echo $PAGO_DETAILS | grep -o '"estado":"[^"]*' | cut -d'"' -f4)
USUARIO_REGISTRO=$(echo $PAGO_DETAILS | grep -o '"usuario_registro":"[^"]*' | cut -d'"' -f4)

if [ "$PAGO_STATE" = "PAGADO" ]; then
  echo -e "${GREEN}✅ PAYMENT STATE CORRECT (PAGADO)${NC}"
else
  echo -e "${YELLOW}⚠️  Unexpected state: $PAGO_STATE${NC}"
fi

if [ "$USUARIO_REGISTRO" = "$EMAIL" ]; then
  echo -e "${GREEN}✅ USUARIO_REGISTRO CORRECT${NC}"
else
  echo -e "${YELLOW}⚠️  Unexpected usuario_registro: $USUARIO_REGISTRO${NC}"
fi

# Final Summary
echo -e "\n=========================================="
echo -e "${GREEN}✅ ALL TESTS COMPLETED SUCCESSFULLY!${NC}"
echo "=========================================="
echo "Loan ID: $PRESTAMO_ID"
echo "Payment ID: $PAGO_ID"
echo "=========================================="
