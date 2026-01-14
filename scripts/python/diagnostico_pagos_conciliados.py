#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de diagnóstico completo para verificar el estado de pagos conciliados
y su aplicación a cuotas antes de importar/aplicar.

Este script:
- Verifica pagos conciliados que deberían estar aplicados a cuotas
- Identifica pagos que no fueron aplicados
- Verifica la consistencia entre pagos y cuotas
- Genera reporte detallado

Uso:
    python scripts/python/diagnostico_pagos_conciliados.py
"""

import sys
from pathlib import Path
from datetime import date, datetime
from decimal import Decimal

# Agregar el directorio raíz del proyecto al path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "backend"))

from sqlalchemy import text, func
from app.db.session import SessionLocal
from app.models.prestamo import Prestamo
from app.models.pago import Pago
from app.models.amortizacion import Cuota


def diagnostico_completo():
    """Realiza diagnóstico completo de TODOS los pagos activos y cuotas"""
    db = SessionLocal()
    
    try:
        print("=" * 70)
        print("DIAGNOSTICO COMPLETO: TODOS LOS PAGOS ACTIVOS Y CUOTAS")
        print("=" * 70)
        print()
        
        # ============================================
        # PASO 1: RESUMEN GENERAL DE TODOS LOS PAGOS
        # ============================================
        print("[PASO 1] RESUMEN GENERAL DE TODOS LOS PAGOS ACTIVOS")
        print("-" * 70)
        
        query_resumen = text("""
            SELECT 
                COUNT(*) AS total_pagos,
                COUNT(CASE WHEN conciliado = TRUE THEN 1 END) AS pagos_conciliados_true,
                COUNT(CASE WHEN verificado_concordancia = 'SI' THEN 1 END) AS pagos_verificado_si,
                COUNT(CASE WHEN (conciliado = TRUE OR verificado_concordancia = 'SI') THEN 1 END) AS pagos_conciliados_total,
                COUNT(CASE WHEN (conciliado = FALSE OR conciliado IS NULL) AND (verificado_concordancia IS NULL OR verificado_concordancia != 'SI') THEN 1 END) AS pagos_no_conciliados,
                COUNT(CASE WHEN prestamo_id IS NOT NULL THEN 1 END) AS pagos_con_prestamo_id,
                COUNT(CASE WHEN prestamo_id IS NULL THEN 1 END) AS pagos_sin_prestamo_id,
                COUNT(CASE WHEN (conciliado = TRUE OR verificado_concordancia = 'SI') AND prestamo_id IS NOT NULL THEN 1 END) AS pagos_listos_para_aplicar,
                COUNT(CASE WHEN (conciliado = FALSE OR conciliado IS NULL) AND (verificado_concordancia IS NULL OR verificado_concordancia != 'SI') AND prestamo_id IS NOT NULL THEN 1 END) AS pagos_no_conciliados_con_prestamo
            FROM pagos
            WHERE activo = TRUE
        """)
        
        resultado = db.execute(query_resumen).fetchone()
        if resultado:
            print(f"  Total pagos activos: {resultado[0]}")
            print(f"  Pagos conciliados (conciliado=True): {resultado[1]}")
            print(f"  Pagos verificados (verificado_concordancia='SI'): {resultado[2]}")
            print(f"  Total pagos conciliados: {resultado[3]}")
            print(f"  Pagos NO conciliados: {resultado[4]}")
            print(f"  Pagos con prestamo_id: {resultado[5]}")
            print(f"  Pagos sin prestamo_id: {resultado[6]}")
            print(f"  Pagos conciliados listos para aplicar: {resultado[7]}")
            print(f"  Pagos NO conciliados con prestamo_id: {resultado[8]}")
        
        print()
        
        # ============================================
        # PASO 2: COMPARACION TODOS LOS PAGOS VS CUOTAS
        # ============================================
        print("[PASO 2] COMPARACION: TODOS LOS PAGOS VS CUOTAS")
        print("-" * 70)
        
        query_comparacion = text("""
            WITH todos_los_pagos_por_prestamo AS (
                SELECT 
                    p.prestamo_id,
                    COUNT(*) AS cantidad_total_pagos,
                    SUM(p.monto_pagado) AS monto_total_todos_los_pagos,
                    COUNT(CASE WHEN (p.conciliado = TRUE OR p.verificado_concordancia = 'SI') THEN 1 END) AS cantidad_pagos_conciliados,
                    SUM(CASE WHEN (p.conciliado = TRUE OR p.verificado_concordancia = 'SI') THEN p.monto_pagado ELSE 0 END) AS monto_total_pagos_conciliados,
                    COUNT(CASE WHEN (p.conciliado = FALSE OR (p.conciliado IS NULL AND (p.verificado_concordancia IS NULL OR p.verificado_concordancia != 'SI'))) THEN 1 END) AS cantidad_pagos_no_conciliados,
                    SUM(CASE WHEN (p.conciliado = FALSE OR (p.conciliado IS NULL AND (p.verificado_concordancia IS NULL OR p.verificado_concordancia != 'SI'))) THEN p.monto_pagado ELSE 0 END) AS monto_total_pagos_no_conciliados
                FROM pagos p
                WHERE p.activo = TRUE
                  AND p.prestamo_id IS NOT NULL
                GROUP BY p.prestamo_id
            ),
            cuotas_por_prestamo AS (
                SELECT 
                    c.prestamo_id,
                    COUNT(*) AS cantidad_cuotas,
                    SUM(c.total_pagado) AS monto_total_pagado_cuotas,
                    SUM(c.monto_cuota) AS monto_total_cuotas
                FROM cuotas c
                GROUP BY c.prestamo_id
            )
            SELECT 
                COALESCE(p.prestamo_id, c.prestamo_id) AS prestamo_id,
                COALESCE(p.cantidad_total_pagos, 0) AS cantidad_total_pagos,
                COALESCE(p.monto_total_todos_los_pagos, 0) AS monto_total_todos_los_pagos,
                COALESCE(p.cantidad_pagos_conciliados, 0) AS cantidad_pagos_conciliados,
                COALESCE(p.monto_total_pagos_conciliados, 0) AS monto_total_pagos_conciliados,
                COALESCE(p.cantidad_pagos_no_conciliados, 0) AS cantidad_pagos_no_conciliados,
                COALESCE(p.monto_total_pagos_no_conciliados, 0) AS monto_total_pagos_no_conciliados,
                COALESCE(c.cantidad_cuotas, 0) AS cantidad_cuotas,
                COALESCE(c.monto_total_pagado_cuotas, 0) AS monto_total_pagado_cuotas,
                COALESCE(c.monto_total_cuotas, 0) AS monto_total_cuotas,
                CASE 
                    WHEN p.prestamo_id IS NULL THEN 'NO_HAY_PAGOS'
                    WHEN c.prestamo_id IS NULL THEN 'NO_HAY_CUOTAS'
                    WHEN ABS(COALESCE(p.monto_total_pagos_conciliados, 0) - COALESCE(c.monto_total_pagado_cuotas, 0)) < 0.01 THEN 'PAGOS_CONCILIADOS_APLICADOS'
                    WHEN COALESCE(p.monto_total_pagos_conciliados, 0) > COALESCE(c.monto_total_pagado_cuotas, 0) THEN 'PAGOS_CONCILIADOS_NO_APLICADOS'
                    WHEN COALESCE(p.monto_total_pagos_no_conciliados, 0) > 0 THEN 'TIENE_PAGOS_NO_CONCILIADOS'
                    ELSE 'CUOTAS_MAYOR_PAGOS'
                END AS estado_comparacion,
                ABS(COALESCE(p.monto_total_pagos_conciliados, 0) - COALESCE(c.monto_total_pagado_cuotas, 0)) AS diferencia_conciliados,
                COALESCE(p.monto_total_pagos_no_conciliados, 0) AS monto_pagos_no_conciliados
            FROM todos_los_pagos_por_prestamo p
            FULL OUTER JOIN cuotas_por_prestamo c ON p.prestamo_id = c.prestamo_id
            WHERE ABS(COALESCE(p.monto_total_pagos_conciliados, 0) - COALESCE(c.monto_total_pagado_cuotas, 0)) > 0.01
               OR COALESCE(p.monto_total_pagos_no_conciliados, 0) > 0
               OR p.prestamo_id IS NULL
               OR c.prestamo_id IS NULL
            ORDER BY diferencia_conciliados DESC, monto_pagos_no_conciliados DESC
            LIMIT 50
        """)
        
        resultados = db.execute(query_comparacion).fetchall()
        
        aplicados_correctamente = 0
        no_aplicados = 0
        sin_cuotas = 0
        sin_pagos = 0
        con_pagos_no_conciliados = 0
        otros = 0
        
        for row in resultados:
            estado = row[10]
            if estado == 'PAGOS_CONCILIADOS_APLICADOS':
                aplicados_correctamente += 1
            elif estado == 'PAGOS_CONCILIADOS_NO_APLICADOS':
                no_aplicados += 1
            elif estado == 'TIENE_PAGOS_NO_CONCILIADOS':
                con_pagos_no_conciliados += 1
            elif estado == 'NO_HAY_CUOTAS':
                sin_cuotas += 1
            elif estado == 'NO_HAY_PAGOS':
                sin_pagos += 1
            else:
                otros += 1
        
        print(f"  Préstamos con pagos conciliados aplicados: {aplicados_correctamente}")
        print(f"  Préstamos con pagos conciliados NO aplicados: {no_aplicados}")
        print(f"  Préstamos con pagos NO conciliados: {con_pagos_no_conciliados}")
        print(f"  Préstamos sin cuotas: {sin_cuotas}")
        print(f"  Préstamos sin pagos: {sin_pagos}")
        print(f"  Otros casos: {otros}")
        
        if no_aplicados > 0:
            print(f"\n  [ADVERTENCIA] {no_aplicados} prestamos tienen pagos conciliados no aplicados")
            print(f"     Estos pagos necesitan ser aplicados a cuotas")
        
        if con_pagos_no_conciliados > 0:
            print(f"\n  [INFO] {con_pagos_no_conciliados} prestamos tienen pagos NO conciliados")
            print(f"     Estos pagos NO se pueden aplicar hasta que se concilien")
        
        print()
        
        # ============================================
        # PASO 3: PAGOS CONCILIADOS NO APLICADOS
        # ============================================
        print("[PASO 3] PAGOS CONCILIADOS QUE NO ESTAN APLICADOS")
        print("-" * 70)
        
        query_no_aplicados = text("""
            WITH pagos_conciliados_por_prestamo AS (
                SELECT 
                    p.prestamo_id,
                    SUM(p.monto_pagado) AS monto_total_pagos_conciliados
                FROM pagos p
                WHERE p.activo = TRUE
                  AND (p.conciliado = TRUE OR p.verificado_concordancia = 'SI')
                  AND p.prestamo_id IS NOT NULL
                GROUP BY p.prestamo_id
            ),
            cuotas_por_prestamo AS (
                SELECT 
                    c.prestamo_id,
                    SUM(c.total_pagado) AS monto_total_pagado_cuotas
                FROM cuotas c
                GROUP BY c.prestamo_id
            )
            SELECT 
                p.prestamo_id,
                pr.cedula,
                pr.nombres,
                p.monto_total_pagos_conciliados,
                COALESCE(c.monto_total_pagado_cuotas, 0) AS monto_total_pagado_cuotas,
                (p.monto_total_pagos_conciliados - COALESCE(c.monto_total_pagado_cuotas, 0)) AS monto_no_aplicado,
                CASE 
                    WHEN c.prestamo_id IS NULL THEN 'NO_HAY_CUOTAS'
                    WHEN (p.monto_total_pagos_conciliados - COALESCE(c.monto_total_pagado_cuotas, 0)) > 0.01 THEN 'PAGOS_PENDIENTES_APLICAR'
                    ELSE 'OK'
                END AS estado
            FROM pagos_conciliados_por_prestamo p
            LEFT JOIN cuotas_por_prestamo c ON p.prestamo_id = c.prestamo_id
            LEFT JOIN prestamos pr ON p.prestamo_id = pr.id
            WHERE (p.monto_total_pagos_conciliados - COALESCE(c.monto_total_pagado_cuotas, 0)) > 0.01
            ORDER BY monto_no_aplicado DESC
            LIMIT 20
        """)
        
        resultados = db.execute(query_no_aplicados).fetchall()
        
        if resultados:
            print(f"  Encontrados {len(resultados)} préstamos con pagos no aplicados:")
            print()
            print(f"  {'Préstamo ID':<12} {'Cédula':<15} {'Monto Pagos':<15} {'Monto Cuotas':<15} {'Diferencia':<15} {'Estado':<25}")
            print("  " + "-" * 95)
            
            total_no_aplicado = Decimal("0.00")
            for row in resultados:
                prestamo_id = row[0]
                cedula = row[1] or "N/A"
                monto_pagos = row[3]
                monto_cuotas = row[4]
                diferencia = row[5]
                estado = row[6]
                
                total_no_aplicado += diferencia
                
                print(f"  {prestamo_id:<12} {cedula:<15} ${monto_pagos:<14} ${monto_cuotas:<14} ${diferencia:<14} {estado:<25}")
            
            print()
            print(f"  Total monto no aplicado: ${total_no_aplicado}")
        else:
            print("  ✅ No se encontraron préstamos con pagos no aplicados")
        
        print()
        
        # ============================================
        # PASO 4: VALIDACIONES DE INTEGRIDAD
        # ============================================
        print("[PASO 4] VALIDACIONES DE INTEGRIDAD")
        print("-" * 70)
        
        # Pagos con prestamo_id que no existe
        query_prestamo_no_existe = text("""
            SELECT COUNT(*)
            FROM pagos p
            WHERE p.activo = TRUE
              AND (p.conciliado = TRUE OR p.verificado_concordancia = 'SI')
              AND p.prestamo_id IS NOT NULL
              AND NOT EXISTS (SELECT 1 FROM prestamos WHERE id = p.prestamo_id)
        """)
        prestamos_no_existen = db.execute(query_prestamo_no_existe).scalar() or 0
        
        # Pagos con cédula que no coincide
        query_cedula_no_coincide = text("""
            SELECT COUNT(*)
            FROM pagos p
            INNER JOIN prestamos pr ON p.prestamo_id = pr.id
            WHERE p.activo = TRUE
              AND (p.conciliado = TRUE OR p.verificado_concordancia = 'SI')
              AND p.prestamo_id IS NOT NULL
              AND p.cedula != pr.cedula
        """)
        cedulas_no_coinciden = db.execute(query_cedula_no_coincide).scalar() or 0
        
        # Préstamos sin cuotas con pagos conciliados
        query_sin_cuotas = text("""
            SELECT COUNT(DISTINCT p.prestamo_id)
            FROM pagos p
            WHERE p.activo = TRUE
              AND (p.conciliado = TRUE OR p.verificado_concordancia = 'SI')
              AND p.prestamo_id IS NOT NULL
              AND NOT EXISTS (SELECT 1 FROM cuotas WHERE prestamo_id = p.prestamo_id)
        """)
        prestamos_sin_cuotas = db.execute(query_sin_cuotas).scalar() or 0
        
        print(f"  Pagos con prestamo_id que no existe: {prestamos_no_existen}")
        print(f"  Pagos con cédula que no coincide: {cedulas_no_coinciden}")
        print(f"  Préstamos sin cuotas (con pagos conciliados): {prestamos_sin_cuotas}")
        
        if prestamos_no_existen > 0 or cedulas_no_coinciden > 0 or prestamos_sin_cuotas > 0:
            print(f"\n  [ADVERTENCIA] Se encontraron problemas de integridad que deben corregirse")
        
        print()
        
        # ============================================
        # RESUMEN FINAL
        # ============================================
        print("=" * 70)
        print("RESUMEN FINAL")
        print("=" * 70)
        
        total_pagos_activos = resultado[0] if resultado else 0
        total_pagos_listos = resultado[7] if resultado else 0
        total_pagos_no_conciliados = resultado[4] if resultado else 0
        
        print(f"Total pagos activos: {total_pagos_activos}")
        print(f"Total pagos conciliados listos para aplicar: {total_pagos_listos}")
        print(f"Total pagos NO conciliados: {total_pagos_no_conciliados}")
        print(f"Préstamos con pagos conciliados no aplicados: {no_aplicados}")
        print(f"Préstamos con pagos NO conciliados: {con_pagos_no_conciliados}")
        print(f"Préstamos sin cuotas: {sin_cuotas}")
        print(f"Problemas de integridad: {prestamos_no_existen + cedulas_no_coinciden}")
        
        print()
        
        print("[CLARIDAD EN REGLAS DE NEGOCIO]")
        print("  SI - Las reglas estan claras y documentadas")
        print()
        print("  REGLA PRINCIPAL:")
        print("    Los pagos SOLO se aplican a cuotas cuando estan conciliados")
        print("    (conciliado = True O verificado_concordancia = 'SI')")
        print()
        
        if no_aplicados > 0:
            print("[RECOMENDACIONES PARA PAGOS CONCILIADOS]")
            print("   1. Ejecutar script de aplicacion de pagos conciliados pendientes")
            print("   2. Usar: python scripts/python/aplicar_pagos_conciliados_pendientes.py")
            print("   3. O usar endpoint API: POST /api/v1/pagos/{pago_id}/aplicar-a-cuotas")
        
        if total_pagos_no_conciliados > 0:
            print()
            print("[RECOMENDACIONES PARA PAGOS NO CONCILIADOS]")
            print("   1. Estos pagos NO se pueden aplicar hasta que se concilien")
            print("   2. Primero conciliar los pagos (marcar conciliado=True)")
            print("   3. Despues se aplicaran automaticamente a cuotas")
        
        if no_aplicados == 0 and total_pagos_no_conciliados == 0:
            print("[OK] Todos los pagos estan correctamente procesados")
        
        print("=" * 70)
        
    except Exception as e:
        print(f"\n[ERROR] Error en diagnóstico: {str(e)}")
        import traceback
        traceback.print_exc()
    
    finally:
        db.close()


if __name__ == "__main__":
    diagnostico_completo()
