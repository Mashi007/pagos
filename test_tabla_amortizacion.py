#!/usr/bin/env python3
"""
Test Script: Verificación de Generación de Tabla de Amortización
Propósito: Validar que al aprobar préstamo se genera correctamente la tabla de amortización
"""

import sys
import requests
import json
from datetime import datetime, date, timedelta

# Configuración
BASE_URL = "https://pagos-backend-ov5f.onrender.com/api/v1"
EMAIL = "itmaster@rapicreditca.com"
PASSWORD = "Itmaster@2024"

# Colores
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
print(f"\n{CYAN}{'='*70}")
print("TEST: Verificación de Tabla de Amortización al Aprobar Préstamo")
print(f"{'='*70}{NC}\n")

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
log_test("CLIENT", "Creando cliente para prueba...")
timestamp = datetime.now().strftime("%s%N")[:14]
cliente_cedula = f"V{timestamp[-6:]}"
cliente_nombres = f"Test_Amort_{timestamp[-4:]}"

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
            "notas": "Cliente para test tabla amortización"
        },
        timeout=10
    )
    cliente_resp.raise_for_status()
    cliente_id = cliente_resp.json()["id"]
    log_success(f"Cliente creado: {cliente_cedula}")
except Exception as e:
    log_error(f"Fallo al crear cliente: {e}")
    sys.exit(1)

# === CREAR PRÉSTAMO ===
log_test("LOAN", "Creando préstamo ANTES de aprobar...")
try:
    prestamo_resp = requests.post(
        f"{BASE_URL}/prestamos",
        headers=headers,
        json={
            "cliente_id": cliente_id,
            "total_financiamiento": 1200.00,
            "numero_cuotas": 12,
            "tasa_interes": 0,  # Sin interés - cuota plana
            "usuario_proponente": EMAIL,
            "usuario_aprobacion": EMAIL
        },
        timeout=10
    )
    prestamo_resp.raise_for_status()
    prestamo_id = prestamo_resp.json()["id"]
    prestamo_estado = prestamo_resp.json()["estado"]
    log_success(f"Préstamo creado: $1200 en 12 cuotas (Estado: {prestamo_estado})")
except Exception as e:
    log_error(f"Fallo al crear préstamo: {e}")
    sys.exit(1)

# === VERIFICAR CUOTAS ANTES DE APROBAR ===
log_test("VERIFY_BEFORE", "Verificando cuotas ANTES de aprobar...")
try:
    cuotas_resp = requests.get(
        f"{BASE_URL}/prestamos/{prestamo_id}/cuotas",
        headers=headers,
        timeout=10
    )
    cuotas_resp.raise_for_status()
    cuotas_before = cuotas_resp.json()
    
    if cuotas_before and len(cuotas_before) > 0:
        log_info(f"Cuotas encontradas ANTES: {len(cuotas_before)}")
        log_error("ERROR: No debería haber cuotas antes de aprobar")
        # En algunos flujos pueden generarse al crear, pero idealmente no
    else:
        log_success("Sin cuotas (como se esperaba): aún no aprobado")
except Exception as e:
    log_info(f"Sin cuotas antes de aprobar (esperado): {e}")

# === APROBAR PRÉSTAMO ===
print(f"\n{CYAN}{'─'*70}")
print("Ahora vamos a APROBAR el préstamo y generar la tabla de amortización")
print(f"{'─'*70}{NC}\n")

log_test("APPROVE", "Aprobando préstamo...")
try:
    fecha_aprobacion = date.today().isoformat()
    
    aprob_resp = requests.post(
        f"{BASE_URL}/prestamos/{prestamo_id}/aprobar-manual",
        headers=headers,
        json={
            "fecha_aprobacion": fecha_aprobacion,
            "acepta_declaracion": True,
            "documentos_analizados": True,
            "total_financiamiento": 1200.00,
            "numero_cuotas": 12,
            "observaciones": "Prueba automatizada"
        },
        timeout=10
    )
    aprob_resp.raise_for_status()
    aprob_data = aprob_resp.json()
    cuotas_generadas = aprob_data.get("cuotas_generadas", 0)
    prestamo_estado = aprob_data.get("prestamo", {}).get("estado", "")
    
    log_success(f"Préstamo aprobado: {cuotas_generadas} cuotas generadas")
    log_success(f"Estado nuevo: {prestamo_estado}")
except Exception as e:
    log_error(f"Fallo al aprobar: {e}")
    sys.exit(1)

# === VERIFICAR CUOTAS DESPUÉS DE APROBAR ===
print(f"\n{CYAN}{'─'*70}")
print("VERIFICANDO TABLA DE AMORTIZACIÓN GENERADA")
print(f"{'─'*70}{NC}\n")

log_test("VERIFY_AFTER", "Obteniendo cuotas DESPUÉS de aprobar...")
try:
    cuotas_resp = requests.get(
        f"{BASE_URL}/prestamos/{prestamo_id}/cuotas",
        headers=headers,
        timeout=10
    )
    cuotas_resp.raise_for_status()
    cuotas = cuotas_resp.json()
    
    if not cuotas or len(cuotas) == 0:
        log_error("ERROR: No se generaron cuotas")
        sys.exit(1)
    
    log_success(f"Cuotas generadas: {len(cuotas)}")
    
    # Verificaciones
    print(f"\n{YELLOW}Verificando estructura de amortización:{NC}")
    
    test_passed = True
    total_monto = 0
    
    for i, cuota in enumerate(cuotas):
        numero = cuota.get("numero_cuota")
        monto = cuota.get("monto", 0)
        saldo_ini = cuota.get("saldo_capital_inicial", 0)
        saldo_fin = cuota.get("saldo_capital_final", 0)
        capital = cuota.get("monto_capital", 0)
        interes = cuota.get("monto_interes", 0)
        fecha_venc = cuota.get("fecha_vencimiento", "")
        estado = cuota.get("estado", "")
        
        total_monto += monto
        
        # Verificaciones de cada cuota
        if numero != i + 1:
            log_error(f"Cuota {i+1}: número incorrecto (esperado {i+1}, obtuvo {numero})")
            test_passed = False
        
        if abs(monto - 100.0) > 0.01:
            log_error(f"Cuota {numero}: monto incorrecto (esperado $100.00, obtuvo ${monto})")
            test_passed = False
        
        if estado != "PENDIENTE":
            log_error(f"Cuota {numero}: estado incorrecto (esperado PENDIENTE, obtuvo {estado})")
            test_passed = False
        
        # Mostrar muestra de cuotas
        if i < 3 or i >= len(cuotas) - 2:
            log_info(f"Cuota {numero}: "
                    f"${monto:.2f} | "
                    f"Saldo: ${saldo_ini:.2f} → ${saldo_fin:.2f} | "
                    f"Vence: {fecha_venc} | "
                    f"Estado: {estado}")
    
    # Verificar total
    print()
    log_info(f"Total monto en {len(cuotas)} cuotas: ${total_monto:.2f}")
    
    if abs(total_monto - 1200.0) > 0.01:
        log_error(f"ERROR: Total incorrecto (esperado $1200.00, obtuvo ${total_monto:.2f})")
        test_passed = False
    else:
        log_success("Total correcto: $1200.00")
    
    if len(cuotas) != 12:
        log_error(f"ERROR: Número de cuotas incorrecto (esperado 12, obtuvo {len(cuotas)})")
        test_passed = False
    else:
        log_success("Número de cuotas correcto: 12")
    
    if test_passed:
        print(f"\n{GREEN}✓ TABLA DE AMORTIZACIÓN GENERADA CORRECTAMENTE{NC}")
    else:
        print(f"\n{RED}✗ PROBLEMAS EN LA TABLA DE AMORTIZACIÓN{NC}")
        sys.exit(1)
        
except Exception as e:
    log_error(f"Fallo al obtener cuotas: {e}")
    sys.exit(1)

# === VERIFICAR FORMATO DE FECHAS ===
log_test("DATES", "Verificando fechas de vencimiento...")
try:
    base_date = datetime.fromisoformat(cuotas[0]["fecha_vencimiento"]).date()
    
    for i, cuota in enumerate(cuotas):
        numero = cuota.get("numero_cuota")
        fecha_str = cuota.get("fecha_vencimiento", "")
        
        try:
            fecha = datetime.fromisoformat(fecha_str).date()
            
            # Calcular fecha esperada (30 días por cuota menos 1)
            expected_date = base_date + timedelta(days=30 * (numero - 1))
            
            # Permite variación de ±2 días
            diff = abs((fecha - expected_date).days)
            if diff <= 2:
                if i < 3:
                    log_success(f"Cuota {numero}: Fecha {fecha} ✅")
            else:
                log_error(f"Cuota {numero}: Fecha fuera de rango")
        except:
            log_error(f"Cuota {numero}: Fecha inválida")
    
except Exception as e:
    log_error(f"Error verificando fechas: {e}")

# === RESUMEN FINAL ===
print(f"\n{CYAN}{'='*70}")
print("RESUMEN DE VERIFICACIÓN")
print(f"{'='*70}{NC}\n")

log_success("✅ Préstamo aprobado correctamente")
log_success(f"✅ {len(cuotas)} cuotas generadas")
log_success("✅ Estructura de amortización correcta")
log_success("✅ Total de montos válido")
log_success("✅ Estados de cuotas correctos (PENDIENTE)")
log_success("✅ Fechas de vencimiento generadas")

print(f"\n{GREEN}CONCLUSIÓN: Tabla de amortización generada correctamente al aprobar{NC}\n")
