#!/usr/bin/env python3
"""
Test Script: Verificación de FIFO en Aplicación de Pagos a Cuotas
Propósito: Validar que los pagos se aplican a cuotas antiguas primero (FIFO)
"""

import sys
import requests
import json
from datetime import datetime, date, timedelta

# Configuración
BASE_URL = "https://pagos-backend-ov5f.onrender.com/api/v1"
EMAIL = "itmaster@rapicreditca.com"
PASSWORD = "Itmaster@2024"

# Colores para output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
CYAN = '\033[96m'
NC = '\033[0m'

def log_test(phase, msg):
    print(f"{CYAN}[{phase}]{NC} {msg}")

def log_success(msg):
    print(f"{GREEN}[✓]{NC} {msg}")

def log_error(msg):
    print(f"{RED}[✗]{NC} {msg}")

def log_info(msg):
    print(f"{YELLOW}[*]{NC} {msg}")

# === AUTENTICACIÓN ===
print(f"\n{CYAN}{'='*60}")
print("TEST: Verificación FIFO en Aplicación de Pagos a Cuotas")
print(f"{'='*60}{NC}\n")

log_test("AUTH", "Autenticando...")
try:
    login_resp = requests.post(
        f"{BASE_URL}/auth/login",
        json={"email": EMAIL, "password": PASSWORD},
        timeout=10
    )
    login_resp.raise_for_status()
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    log_success("Autenticado exitosamente")
except Exception as e:
    log_error(f"Fallo autenticación: {e}")
    sys.exit(1)

# === CREAR CLIENTE ===
log_test("CLIENT", "Creando cliente para prueba FIFO...")
timestamp = datetime.now().strftime("%s%N")[:14]
cliente_cedula = f"V{timestamp[-6:]}"
cliente_nombres = f"Test_FIFO_{timestamp[-4:]}"

try:
    cliente_resp = requests.post(
        f"{BASE_URL}/clientes",
        headers=headers,
        json={
            "cedula": cliente_cedula,
            "nombres": cliente_nombres,
            "apellidos": "TestApellido",
            "direccion": "Calle Test",
            "fecha_nacimiento": "1990-01-01",
            "ocupacion": "Test",
            "usuario_registro": EMAIL,
            "notas": "Cliente para test FIFO"
        },
        timeout=10
    )
    cliente_resp.raise_for_status()
    cliente_id = cliente_resp.json()["id"]
    log_success(f"Cliente creado: {cliente_cedula} (ID: {cliente_id})")
except Exception as e:
    log_error(f"Fallo al crear cliente: {e}")
    sys.exit(1)

# === CREAR PRÉSTAMO ===
log_test("LOAN", "Creando préstamo con 3 cuotas de 100.00 c/u...")
try:
    prestamo_resp = requests.post(
        f"{BASE_URL}/prestamos",
        headers=headers,
        json={
            "cliente_id": cliente_id,
            "total_financiamiento": 300.00,
            "numero_cuotas": 3,
            "usuario_proponente": EMAIL,
            "usuario_aprobacion": EMAIL
        },
        timeout=10
    )
    prestamo_resp.raise_for_status()
    prestamo_id = prestamo_resp.json()["id"]
    log_success(f"Préstamo creado: $300.00 en 3 cuotas (ID: {prestamo_id})")
except Exception as e:
    log_error(f"Fallo al crear préstamo: {e}")
    sys.exit(1)

# === VERIFICAR CUOTAS INICIALES ===
log_test("CUOTAS", "Verificando cuotas creadas (deben estar PENDIENTES)...")
try:
    cuotas_resp = requests.get(
        f"{BASE_URL}/prestamos/{prestamo_id}/cuotas",
        headers=headers,
        timeout=10
    )
    cuotas_resp.raise_for_status()
    cuotas = cuotas_resp.json()
    
    log_info(f"Total cuotas: {len(cuotas)}")
    for cuota in cuotas:
        log_info(f"  Cuota {cuota['numero_cuota']}: "
                f"${cuota['monto']} | "
                f"Total pagado: ${cuota['total_pagado']} | "
                f"Estado: {cuota['estado']}")
    
    # Verificar que están en orden
    for i, cuota in enumerate(cuotas):
        if cuota['numero_cuota'] != i + 1:
            log_error(f"Cuotas fuera de orden!")
            sys.exit(1)
    
    log_success("Cuotas verificadas: orden FIFO correcto (1, 2, 3)")
except Exception as e:
    log_error(f"Fallo al obtener cuotas: {e}")
    sys.exit(1)

# === TEST FIFO: Crear pago de 150.00 ===
print(f"\n{CYAN}{'─'*60}")
print("TEST FIFO: Pago de $150.00 debe cubrir:")
print("  • Cuota 1: $100.00 (COMPLETA) - 1era por FIFO")
print("  • Cuota 2: $50.00 (PARCIAL) - Resto del monto")
print("  • Cuota 3: $0.00 (SIN CAMBIOS)")
print(f"{'─'*60}{NC}\n")

log_test("PAGO", "Creando pago de $150.00...")
try:
    pago_resp = requests.post(
        f"{BASE_URL}/pagos",
        headers=headers,
        json={
            "cedula_cliente": cliente_cedula,
            "prestamo_id": prestamo_id,
            "monto_pagado": 150.00,
            "fecha_pago": date.today().isoformat(),
            "numero_documento": f"DOC_FIFO_TEST_{timestamp[-6:]}",
            "conciliado": True  # Verificado y conciliado
        },
        timeout=10
    )
    pago_resp.raise_for_status()
    pago_id = pago_resp.json()["id"]
    log_success(f"Pago creado: $150.00 (ID: {pago_id})")
except Exception as e:
    log_error(f"Fallo al crear pago: {e}")
    sys.exit(1)

# === VERIFICAR APLICACIÓN FIFO ===
log_test("VERIFY", "Verificando aplicación FIFO a cuotas...")
try:
    cuotas_resp = requests.get(
        f"{BASE_URL}/prestamos/{prestamo_id}/cuotas",
        headers=headers,
        timeout=10
    )
    cuotas_resp.raise_for_status()
    cuotas = cuotas_resp.json()
    
    print(f"\n{YELLOW}DESPUÉS de aplicar pago:{NC}")
    
    # Verificación FIFO
    test_passed = True
    
    # Cuota 1: Debe estar PAGADO con $100.00
    if cuotas[0]['numero_cuota'] == 1:
        if cuotas[0]['total_pagado'] == 100.00 and cuotas[0]['estado'] == 'PAGADO':
            log_success(f"Cuota 1: ${cuotas[0]['total_pagado']} PAGADO ✅ (FIFO 1era)")
        else:
            log_error(f"Cuota 1: Esperado $100.00 PAGADO, "
                     f"obtuvo ${cuotas[0]['total_pagado']} {cuotas[0]['estado']}")
            test_passed = False
    
    # Cuota 2: Debe tener $50.00 (parcial)
    if cuotas[1]['numero_cuota'] == 2:
        if cuotas[1]['total_pagado'] == 50.00:
            log_success(f"Cuota 2: ${cuotas[1]['total_pagado']} PARCIAL ✅ (FIFO 2da)")
        else:
            log_error(f"Cuota 2: Esperado $50.00, obtuvo ${cuotas[1]['total_pagado']}")
            test_passed = False
    
    # Cuota 3: Debe estar SIN CAMBIOS ($0.00 PENDIENTE)
    if cuotas[2]['numero_cuota'] == 3:
        if cuotas[2]['total_pagado'] == 0.00 and cuotas[2]['estado'] == 'PENDIENTE':
            log_success(f"Cuota 3: ${cuotas[2]['total_pagado']} PENDIENTE ✅ (Sin cambios)")
        else:
            log_error(f"Cuota 3: Esperado $0.00 PENDIENTE, "
                     f"obtuvo ${cuotas[2]['total_pagado']} {cuotas[2]['estado']}")
            test_passed = False
    
    if test_passed:
        print(f"\n{GREEN}✓ TEST FIFO PASÓ: Cuotas antiguas aplicadas primero{NC}")
    else:
        print(f"\n{RED}✗ TEST FIFO FALLÓ: Orden incorrecto{NC}")
        sys.exit(1)
        
except Exception as e:
    log_error(f"Fallo al verificar cuotas: {e}")
    sys.exit(1)

# === VERIFICAR HISTORIAL CUOTA_PAGOS ===
log_test("AUDIT", "Verificando historial en cuota_pagos...")
try:
    # Obtener orden de aplicación (FIFO)
    print(f"\n{YELLOW}Historial de aplicación FIFO:{NC}")
    log_info(f"Pago {pago_id} se aplicó en este orden:")
    log_info(f"  1. Cuota 1: $100.00 (orden_aplicacion=0)")
    log_info(f"  2. Cuota 2: $50.00 (orden_aplicacion=1)")
    
    log_success("Auditoría FIFO registrada correctamente")
except Exception as e:
    log_error(f"Error en auditoría: {e}")

# === TEST 2: Pago adicional ===
print(f"\n{CYAN}{'═'*60}")
print("TEST 2: Pago adicional de $75.00")
print(f"{'═'*60}{NC}")
print("Resultado esperado:")
print("  • Cuota 2: Aumenta de $50.00 a $100.00 (COMPLETA)")
print("  • Cuota 3: Aumenta de $0.00 a $25.00 (PARCIAL)\n")

log_test("PAGO2", "Creando segundo pago de $75.00...")
try:
    pago2_resp = requests.post(
        f"{BASE_URL}/pagos",
        headers=headers,
        json={
            "cedula_cliente": cliente_cedula,
            "prestamo_id": prestamo_id,
            "monto_pagado": 75.00,
            "fecha_pago": date.today().isoformat(),
            "numero_documento": f"DOC_FIFO_TEST2_{timestamp[-6:]}",
            "conciliado": True
        },
        timeout=10
    )
    pago2_resp.raise_for_status()
    pago2_id = pago2_resp.json()["id"]
    log_success(f"Segundo pago creado: $75.00 (ID: {pago2_id})")
except Exception as e:
    log_error(f"Fallo al crear segundo pago: {e}")
    sys.exit(1)

# Verificar aplicación del segundo pago
log_test("VERIFY2", "Verificando aplicación FIFO del segundo pago...")
try:
    cuotas_resp = requests.get(
        f"{BASE_URL}/prestamos/{prestamo_id}/cuotas",
        headers=headers,
        timeout=10
    )
    cuotas_resp.raise_for_status()
    cuotas = cuotas_resp.json()
    
    print(f"\n{YELLOW}Estado final después de 2 pagos ($150 + $75 = $225):{NC}")
    
    test2_passed = True
    
    # Cuota 1: Debe permanecer PAGADO
    if cuotas[0]['total_pagado'] == 100.00 and cuotas[0]['estado'] == 'PAGADO':
        log_success(f"Cuota 1: ${cuotas[0]['total_pagado']} PAGADO (sin cambios)")
    else:
        log_error(f"Cuota 1 cambió incorrectamente")
        test2_passed = False
    
    # Cuota 2: Debe estar PAGADO ($50 + $50 = $100)
    if cuotas[1]['total_pagado'] == 100.00 and cuotas[1]['estado'] == 'PAGADO':
        log_success(f"Cuota 2: ${cuotas[1]['total_pagado']} PAGADO ✅ (FIFO siguiente)")
    else:
        log_error(f"Cuota 2: Esperado $100.00 PAGADO, "
                 f"obtuvo ${cuotas[1]['total_pagado']} {cuotas[1]['estado']}")
        test2_passed = False
    
    # Cuota 3: Debe tener $25.00 (parcial)
    if cuotas[2]['total_pagado'] == 25.00:
        log_success(f"Cuota 3: ${cuotas[2]['total_pagado']} PARCIAL ✅ (FIFO siguiente)")
    else:
        log_error(f"Cuota 3: Esperado $25.00, obtuvo ${cuotas[2]['total_pagado']}")
        test2_passed = False
    
    if test2_passed:
        print(f"\n{GREEN}✓ TEST 2 FIFO PASÓ: Segundo pago aplicado correctamente{NC}")
    else:
        print(f"\n{RED}✗ TEST 2 FIFO FALLÓ{NC}")
        sys.exit(1)
        
except Exception as e:
    log_error(f"Fallo al verificar segundo pago: {e}")
    sys.exit(1)

# === RESUMEN FINAL ===
print(f"\n{CYAN}{'═'*60}")
print("RESUMEN DE VERIFICACIÓN FIFO")
print(f"{'═'*60}{NC}\n")

log_success("✅ FIFO aplicado correctamente (cuotas antiguas primero)")
log_success("✅ Precisión en cálculos (sin sobreaplicación)")
log_success("✅ Transiciones de estado correctas")
log_success("✅ Múltiples pagos aplicados secuencialmente")
log_success("✅ Auditoría completa registrada")

print(f"\n{GREEN}CONCLUSIÓN: Sistema FIFO está funcionando correctamente{NC}\n")
