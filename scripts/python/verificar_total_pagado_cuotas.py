#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para verificar el estado de total_pagado en tabla cuotas
antes de aplicar los pagos conciliados.

Este script verifica:
- Si hay datos en total_pagado
- Cuántas cuotas tienen total_pagado > 0
- Monto total almacenado en total_pagado
- Estado de las cuotas con pagos

Uso:
    python scripts/python/verificar_total_pagado_cuotas.py
"""

import sys
from pathlib import Path
from decimal import Decimal

# Agregar el directorio raíz del proyecto al path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "backend"))

from sqlalchemy import text, func
from app.db.session import SessionLocal
from app.models.amortizacion import Cuota
from app.models.prestamo import Prestamo


def verificar_total_pagado():
    """Verifica el estado de total_pagado en todas las cuotas"""
    db = SessionLocal()
    
    try:
        print("=" * 70)
        print("VERIFICACION: Estado de total_pagado en tabla cuotas")
        print("=" * 70)
        print()
        
        # ============================================
        # PASO 1: RESUMEN GENERAL
        # ============================================
        print("[PASO 1] RESUMEN GENERAL")
        print("-" * 70)
        
        query_resumen = text("""
            SELECT 
                COUNT(*) AS total_cuotas,
                COUNT(CASE WHEN total_pagado IS NULL THEN 1 END) AS cuotas_con_total_pagado_null,
                COUNT(CASE WHEN total_pagado = 0 OR total_pagado = 0.00 THEN 1 END) AS cuotas_con_total_pagado_cero,
                COUNT(CASE WHEN total_pagado > 0 THEN 1 END) AS cuotas_con_total_pagado_mayor_cero,
                SUM(CASE WHEN total_pagado > 0 THEN total_pagado ELSE 0 END) AS monto_total_en_total_pagado
            FROM cuotas
        """)
        
        resultado = db.execute(query_resumen).fetchone()
        if resultado:
            total_cuotas = resultado[0]
            cuotas_null = resultado[1]
            cuotas_cero = resultado[2]
            cuotas_con_pagos = resultado[3]
            monto_total = resultado[4] or Decimal("0.00")
            
            print(f"  Total cuotas: {total_cuotas}")
            print(f"  Cuotas con total_pagado NULL: {cuotas_null}")
            print(f"  Cuotas con total_pagado = 0: {cuotas_cero}")
            print(f"  Cuotas con total_pagado > 0: {cuotas_con_pagos}")
            print(f"  Monto total en total_pagado: ${monto_total:,.2f}")
            
            if cuotas_con_pagos > 0:
                print()
                print(f"  [ADVERTENCIA] {cuotas_con_pagos} cuotas tienen total_pagado > 0")
                print(f"     Monto total: ${monto_total:,.2f}")
                print(f"     Estas cuotas necesitan ser limpiadas antes de aplicar pagos")
            else:
                print()
                print("  [OK] Todas las cuotas tienen total_pagado = 0 o NULL")
                print("     La columna esta lista para recibir los pagos")
        
        print()
        
        # ============================================
        # PASO 2: CUOTAS CON TOTAL_PAGADO > 0
        # ============================================
        if cuotas_con_pagos > 0:
            print("[PASO 2] CUOTAS CON TOTAL_PAGADO > 0")
            print("-" * 70)
            
            query_cuotas_con_pagos = text("""
                SELECT 
                    c.id AS cuota_id,
                    c.prestamo_id,
                    c.numero_cuota,
                    c.monto_cuota,
                    c.total_pagado,
                    c.estado,
                    c.fecha_vencimiento,
                    c.fecha_pago,
                    pr.cedula,
                    pr.nombres
                FROM cuotas c
                LEFT JOIN prestamos pr ON c.prestamo_id = pr.id
                WHERE c.total_pagado > 0
                ORDER BY c.total_pagado DESC
                LIMIT 20
            """)
            
            resultados = db.execute(query_cuotas_con_pagos).fetchall()
            
            if resultados:
                print(f"  Mostrando primeras {len(resultados)} cuotas con total_pagado > 0:")
                print()
                print(f"  {'Cuota ID':<10} {'Préstamo':<10} {'Cédula':<15} {'Monto Cuota':<15} {'Total Pagado':<15} {'Estado':<15}")
                print("  " + "-" * 80)
                
                for row in resultados:
                    cuota_id = row[0]
                    prestamo_id = row[1]
                    numero_cuota = row[2]
                    monto_cuota = row[3]
                    total_pagado = row[4]
                    estado = row[5]
                    cedula = row[8] or "N/A"
                    
                    print(f"  {cuota_id:<10} {prestamo_id:<10} {cedula:<15} ${monto_cuota:<14} ${total_pagado:<14} {estado:<15}")
        
        print()
        
        # ============================================
        # PASO 3: RESUMEN POR PRESTAMO
        # ============================================
        if cuotas_con_pagos > 0:
            print("[PASO 3] RESUMEN POR PRESTAMO")
            print("-" * 70)
            
            query_por_prestamo = text("""
                SELECT 
                    c.prestamo_id,
                    pr.cedula,
                    pr.nombres,
                    COUNT(*) AS total_cuotas_prestamo,
                    COUNT(CASE WHEN c.total_pagado > 0 THEN 1 END) AS cuotas_con_pagos,
                    SUM(c.total_pagado) AS monto_total_pagado_prestamo
                FROM cuotas c
                LEFT JOIN prestamos pr ON c.prestamo_id = pr.id
                WHERE c.total_pagado > 0
                GROUP BY c.prestamo_id, pr.cedula, pr.nombres
                ORDER BY monto_total_pagado_prestamo DESC
                LIMIT 20
            """)
            
            resultados = db.execute(query_por_prestamo).fetchall()
            
            if resultados:
                print(f"  Préstamos con cuotas que tienen total_pagado > 0:")
                print()
                print(f"  {'Préstamo ID':<12} {'Cédula':<15} {'Cuotas con Pagos':<20} {'Monto Total':<15}")
                print("  " + "-" * 65)
                
                for row in resultados:
                    prestamo_id = row[0]
                    cedula = row[1] or "N/A"
                    cuotas_con_pagos_prestamo = row[4]
                    monto_total = row[5]
                    
                    print(f"  {prestamo_id:<12} {cedula:<15} {cuotas_con_pagos_prestamo:<20} ${monto_total:<14}")
        
        print()
        
        # ============================================
        # RESUMEN FINAL
        # ============================================
        print("=" * 70)
        print("RESUMEN FINAL")
        print("=" * 70)
        
        if cuotas_con_pagos > 0:
            print(f"[ESTADO] La columna total_pagado NO esta vacia")
            print(f"  - {cuotas_con_pagos} cuotas tienen total_pagado > 0")
            print(f"  - Monto total: ${monto_total:,.2f}")
            print()
            print("[ACCION REQUERIDA]")
            print("  Ejecutar script para limpiar total_pagado:")
            print("  - SQL: scripts/sql/vaciar_total_pagado_cuotas.sql")
            print("  - Python: python scripts/python/vaciar_total_pagado_cuotas.py")
        else:
            print("[ESTADO] La columna total_pagado esta vacia (lista para recibir pagos)")
            print("  - Todas las cuotas tienen total_pagado = 0 o NULL")
            print("  - Puedes proceder a aplicar los pagos conciliados")
        
        print("=" * 70)
        
    except Exception as e:
        print(f"\n[ERROR] Error en verificación: {str(e)}")
        import traceback
        traceback.print_exc()
    
    finally:
        db.close()


if __name__ == "__main__":
    verificar_total_pagado()
