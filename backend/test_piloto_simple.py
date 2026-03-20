#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Testing: Validacion rapida del piloto (prestamos 2, 7, 8)
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.database import SessionLocal
from sqlalchemy import text

def test_piloto():
    """Validar piloto ejecutando SQL directo"""
    db = SessionLocal()
    try:
        print("\n" + "=" * 80)
        print("VALIDACION PILOTO: Prestamos 2, 7, 8")
        print("=" * 80 + "\n")
        
        tests_passed = 0
        tests_total = 0
        
        # Test 1: Cobertura
        tests_total += 1
        result = db.execute(text("""
            SELECT
              COUNT(*) AS total_prestamos,
              COUNT(*) FILTER (WHERE (SELECT COUNT(*) FROM cuotas c WHERE c.prestamo_id = p.id) > 0) AS con_cuotas
            FROM prestamos p
            WHERE p.id IN (2, 7, 8)
        """)).fetchone()
        
        if result[0] == 3 and result[1] == 3:
            print("[OK] TEST 1: Cobertura de Cuotas (3/3 prestamos con cuotas)")
            tests_passed += 1
        else:
            print(f"[FAIL] TEST 1: {result}")
        
        # Test 2: Sin duplicados
        tests_total += 1
        result = db.execute(text("""
            SELECT COUNT(*)
            FROM cuotas
            WHERE prestamo_id IN (2, 7, 8)
            GROUP BY prestamo_id, numero_cuota
            HAVING COUNT(*) > 1
        """)).fetchall()
        
        if len(result) == 0:
            print("[OK] TEST 2: Sin Duplicados numero_cuota")
            tests_passed += 1
        else:
            print(f"[FAIL] TEST 2: {len(result)} duplicados encontrados")
        
        # Test 3: Cuota 1 alineada
        tests_total += 1
        result = db.execute(text("""
            WITH p AS (
              SELECT
                pr.id AS prestamo_id,
                UPPER(COALESCE(NULLIF(TRIM(pr.modalidad_pago), ''), 'MENSUAL')) AS modalidad,
                pr.fecha_aprobacion::date AS fecha_aprob,
                c.fecha_vencimiento AS venc_actual
              FROM prestamos pr
              JOIN cuotas c ON c.prestamo_id = pr.id AND c.numero_cuota = 1
              WHERE pr.id IN (2, 7, 8)
                AND pr.fecha_aprobacion IS NOT NULL
                AND pr.numero_cuotas >= 1
            ),
            esp AS (
              SELECT
                p.*,
                CASE
                  WHEN p.modalidad = 'MENSUAL' THEN fn_add_months_keep_day(p.fecha_aprob, 1)
                  WHEN p.modalidad = 'QUINCENAL' THEN (p.fecha_aprob + 14 * INTERVAL '1 day')::date
                  WHEN p.modalidad = 'SEMANAL' THEN (p.fecha_aprob + 6 * INTERVAL '1 day')::date
                  ELSE fn_add_months_keep_day(p.fecha_aprob, 1)
                END AS venc_esperado
              FROM p
            )
            SELECT COUNT(*) FILTER (WHERE esp.venc_actual IS DISTINCT FROM esp.venc_esperado) AS desalineados
            FROM esp
        """)).fetchone()
        
        if result[0] == 0:
            print("[OK] TEST 3: Cuota 1 Alineada (0 desalineados)")
            tests_passed += 1
        else:
            print(f"[FAIL] TEST 3: {result[0]} desalineados")
        
        # Test 4: Numero de cuotas consistente
        tests_total += 1
        result = db.execute(text("""
            SELECT COUNT(*)
            FROM prestamos pr
            LEFT JOIN cuotas c ON c.prestamo_id = pr.id
            WHERE pr.id IN (2, 7, 8) AND pr.numero_cuotas >= 1
            GROUP BY pr.id, pr.numero_cuotas
            HAVING COUNT(c.id) <> pr.numero_cuotas
        """)).fetchall()
        
        if len(result) == 0:
            print("[OK] TEST 4: Numero de Cuotas Consistente (0 desajustes)")
            tests_passed += 1
        else:
            print(f"[FAIL] TEST 4: {len(result)} desajustes")
        
        # Test 5: Links en cuota_pagos
        tests_total += 1
        result = db.execute(text("""
            SELECT COUNT(*)
            FROM cuota_pagos cp
            JOIN cuotas c ON c.id = cp.cuota_id
            WHERE c.prestamo_id IN (2, 7, 8)
        """)).fetchone()
        
        if result[0] > 0:
            print(f"[OK] TEST 5: Links en cuota_pagos ({result[0]} aplicados)")
            tests_passed += 1
        else:
            print(f"[FAIL] TEST 5: {result[0]} links (esperado > 0)")
        
        # Test 6: Montos pagados
        tests_total += 1
        result = db.execute(text("""
            SELECT COALESCE(SUM(total_pagado), 0)::numeric(14,2)
            FROM cuotas
            WHERE prestamo_id IN (2, 7, 8)
        """)).fetchone()
        
        if result[0] > 0:
            print(f"[OK] TEST 6: Montos Pagados ({result[0]} ECU aplicados)")
            tests_passed += 1
        else:
            print(f"[FAIL] TEST 6: {result[0]} pagados (esperado > 0)")
        
        print("\n" + "-" * 80)
        print(f"Resultado: {tests_passed}/{tests_total} tests pasaron\n")
        
        if tests_passed == tests_total:
            print("[OK] PILOTO VALIDADO EXITOSAMENTE\n")
            return 0
        else:
            print("[WARNING] Algunos tests fallaron\n")
            return 1
            
    except Exception as e:
        print(f"[ERROR] {e}\n")
        return 1
    finally:
        db.close()

if __name__ == "__main__":
    sys.exit(test_piloto())
