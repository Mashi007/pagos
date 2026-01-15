#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Confirmar que la información está guardada en tablas cuotas y pagos"""

import sys
from pathlib import Path
from decimal import Decimal

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "backend"))

from sqlalchemy import text
from app.db.session import SessionLocal

db = SessionLocal()
try:
    print("="*80)
    print("CONFIRMACION DE DATOS GUARDADOS EN cuotas Y pagos")
    print("="*80)
    
    # 1. Verificar tabla pagos
    print("\n[1] TABLA pagos")
    print("-" * 80)
    
    query_pagos = text("""
        SELECT 
            COUNT(*) as total_pagos,
            COUNT(CASE WHEN conciliado = TRUE OR verificado_concordancia = 'SI' THEN 1 END) as pagos_conciliados,
            COUNT(CASE WHEN prestamo_id IS NOT NULL THEN 1 END) as pagos_con_prestamo,
            SUM(monto_pagado) as monto_total,
            MIN(fecha_pago) as fecha_minima,
            MAX(fecha_pago) as fecha_maxima
        FROM pagos
        WHERE numero_documento LIKE 'ABONO_2026_%'
    """)
    result_pagos = db.execute(query_pagos)
    pagos_row = result_pagos.fetchone()
    
    total_pagos = pagos_row[0] if pagos_row[0] else 0
    pagos_conciliados = pagos_row[1] if pagos_row[1] else 0
    pagos_con_prestamo = pagos_row[2] if pagos_row[2] else 0
    monto_total_pagos = Decimal(str(pagos_row[3])) if pagos_row[3] else Decimal("0")
    fecha_minima = pagos_row[4]
    fecha_maxima = pagos_row[5]
    
    print(f"Total de pagos (ABONO_2026): {total_pagos:,}")
    print(f"Pagos conciliados: {pagos_conciliados:,}")
    print(f"Pagos con préstamo: {pagos_con_prestamo:,}")
    print(f"Monto total: Bs. {monto_total_pagos:,.2f}")
    print(f"Fecha mínima: {fecha_minima}")
    print(f"Fecha máxima: {fecha_maxima}")
    
    if total_pagos > 0:
        print(f"[OK] La tabla pagos tiene {total_pagos:,} registros guardados")
    else:
        print(f"[ERROR] La tabla pagos está vacía")
    
    # 2. Verificar tabla cuotas
    print("\n[2] TABLA cuotas")
    print("-" * 80)
    
    query_cuotas = text("""
        SELECT 
            COUNT(*) as total_cuotas,
            COUNT(CASE WHEN total_pagado > 0 THEN 1 END) as cuotas_con_pagos,
            COUNT(CASE WHEN estado = 'PAGADO' THEN 1 END) as cuotas_pagadas,
            COUNT(CASE WHEN estado = 'PARCIAL' THEN 1 END) as cuotas_parciales,
            SUM(COALESCE(total_pagado, 0)) as monto_total_pagado,
            SUM(monto_cuota) as monto_total_cuotas
        FROM cuotas
    """)
    result_cuotas = db.execute(query_cuotas)
    cuotas_row = result_cuotas.fetchone()
    
    total_cuotas = cuotas_row[0] if cuotas_row[0] else 0
    cuotas_con_pagos = cuotas_row[1] if cuotas_row[1] else 0
    cuotas_pagadas = cuotas_row[2] if cuotas_row[2] else 0
    cuotas_parciales = cuotas_row[3] if cuotas_row[3] else 0
    monto_total_pagado_cuotas = Decimal(str(cuotas_row[4])) if cuotas_row[4] else Decimal("0")
    monto_total_cuotas = Decimal(str(cuotas_row[5])) if cuotas_row[5] else Decimal("0")
    
    print(f"Total de cuotas: {total_cuotas:,}")
    print(f"Cuotas con pagos aplicados: {cuotas_con_pagos:,}")
    print(f"Cuotas PAGADAS: {cuotas_pagadas:,}")
    print(f"Cuotas PARCIALES: {cuotas_parciales:,}")
    print(f"Monto total pagado en cuotas: Bs. {monto_total_pagado_cuotas:,.2f}")
    print(f"Monto total de cuotas: Bs. {monto_total_cuotas:,.2f}")
    
    if total_cuotas > 0:
        print(f"[OK] La tabla cuotas tiene {total_cuotas:,} registros guardados")
    else:
        print(f"[ERROR] La tabla cuotas está vacía")
    
    # 3. Verificar consistencia entre pagos y cuotas
    print("\n[3] CONSISTENCIA ENTRE pagos Y cuotas")
    print("-" * 80)
    
    query_consistencia = text("""
        SELECT 
            (SELECT SUM(monto_pagado) FROM pagos 
             WHERE (conciliado = TRUE OR verificado_concordancia = 'SI') 
               AND prestamo_id IS NOT NULL) as monto_pagos_conciliados,
            (SELECT SUM(COALESCE(total_pagado, 0)) FROM cuotas) as monto_cuotas_total_pagado
    """)
    result_consistencia = db.execute(query_consistencia)
    consistencia_row = result_consistencia.fetchone()
    
    monto_pagos_conciliados = Decimal(str(consistencia_row[0])) if consistencia_row[0] else Decimal("0")
    monto_cuotas_total = Decimal(str(consistencia_row[1])) if consistencia_row[1] else Decimal("0")
    
    diferencia = abs(monto_pagos_conciliados - monto_cuotas_total)
    
    print(f"Monto en pagos conciliados: Bs. {monto_pagos_conciliados:,.2f}")
    print(f"Monto en cuotas (total_pagado): Bs. {monto_cuotas_total:,.2f}")
    print(f"Diferencia: Bs. {diferencia:,.2f}")
    
    if diferencia <= Decimal("0.01"):
        print(f"[OK] Los montos coinciden perfectamente")
    else:
        print(f"[ADVERTENCIA] Hay una diferencia de Bs. {diferencia:,.2f}")
    
    # 4. Verificar ejemplos específicos
    print("\n[4] EJEMPLOS DE DATOS GUARDADOS")
    print("-" * 80)
    
    # Ejemplo de pagos
    query_ejemplo_pagos = text("""
        SELECT 
            id,
            cedula,
            prestamo_id,
            numero_cuota,
            monto_pagado,
            fecha_pago,
            conciliado,
            estado
        FROM pagos
        WHERE numero_documento LIKE 'ABONO_2026_%'
        ORDER BY id
        LIMIT 5
    """)
    result_ejemplo_pagos = db.execute(query_ejemplo_pagos)
    ejemplos_pagos = result_ejemplo_pagos.fetchall()
    
    print("Ejemplos de pagos guardados:")
    print(f"{'ID':<8} {'Cédula':<12} {'Préstamo':<10} {'Cuota':<8} {'Monto':<15} {'Fecha':<12} {'Conciliado':<12} {'Estado':<12}")
    print("-" * 95)
    for p in ejemplos_pagos:
        print(f"{p[0]:<8} {p[1]:<12} {p[2]:<10} {p[3]:<8} Bs. {float(p[4]):>12,.2f} {str(p[5])[:10]:<12} {str(p[6]):<12} {p[7]:<12}")
    
    # Ejemplo de cuotas con pagos aplicados
    query_ejemplo_cuotas = text("""
        SELECT 
            id,
            prestamo_id,
            numero_cuota,
            monto_cuota,
            COALESCE(total_pagado, 0) as total_pagado,
            estado,
            fecha_pago
        FROM cuotas
        WHERE total_pagado > 0
        ORDER BY id
        LIMIT 5
    """)
    result_ejemplo_cuotas = db.execute(query_ejemplo_cuotas)
    ejemplos_cuotas = result_ejemplo_cuotas.fetchall()
    
    print("\nEjemplos de cuotas con pagos aplicados:")
    print(f"{'ID':<8} {'Préstamo':<10} {'Cuota':<8} {'Monto Cuota':<15} {'Total Pagado':<15} {'Estado':<12} {'Fecha Pago':<12}")
    print("-" * 90)
    for c in ejemplos_cuotas:
        fecha_pago_str = str(c[6])[:10] if c[6] else "NULL"
        print(f"{c[0]:<8} {c[1]:<10} {c[2]:<8} Bs. {float(c[3]):>12,.2f} Bs. {float(c[4]):>12,.2f} {c[5]:<12} {fecha_pago_str:<12}")
    
    # 5. Verificar relación entre pagos y cuotas
    print("\n[5] VERIFICACION DE RELACION pagos -> cuotas")
    print("-" * 80)
    
    query_relacion = text("""
        SELECT 
            COUNT(DISTINCT p.id) as pagos_con_cuota,
            COUNT(DISTINCT c.id) as cuotas_con_pagos,
            SUM(p.monto_pagado) as monto_total_relacionado
        FROM pagos p
        INNER JOIN cuotas c ON c.prestamo_id = p.prestamo_id 
            AND c.numero_cuota = p.numero_cuota
        WHERE (p.conciliado = TRUE OR p.verificado_concordancia = 'SI')
          AND p.prestamo_id IS NOT NULL
    """)
    result_relacion = db.execute(query_relacion)
    relacion_row = result_relacion.fetchone()
    
    pagos_con_cuota = relacion_row[0] if relacion_row[0] else 0
    cuotas_con_pagos = relacion_row[1] if relacion_row[1] else 0
    monto_relacionado = Decimal(str(relacion_row[2])) if relacion_row[2] else Decimal("0")
    
    print(f"Pagos relacionados con cuotas: {pagos_con_cuota:,}")
    print(f"Cuotas relacionadas con pagos: {cuotas_con_pagos:,}")
    print(f"Monto total relacionado: Bs. {monto_relacionado:,.2f}")
    
    # Conclusión final
    print("\n" + "="*80)
    print("CONCLUSION FINAL")
    print("="*80)
    
    confirmaciones = []
    
    if total_pagos > 0:
        confirmaciones.append(f"[OK] Tabla pagos: {total_pagos:,} registros guardados")
    else:
        confirmaciones.append(f"[ERROR] Tabla pagos está vacía")
    
    if total_cuotas > 0:
        confirmaciones.append(f"[OK] Tabla cuotas: {total_cuotas:,} registros guardados")
    else:
        confirmaciones.append(f"[ERROR] Tabla cuotas está vacía")
    
    if pagos_conciliados == total_pagos:
        confirmaciones.append(f"[OK] Todos los pagos están conciliados")
    
    if cuotas_con_pagos > 0:
        confirmaciones.append(f"[OK] {cuotas_con_pagos:,} cuotas tienen pagos aplicados")
    
    if diferencia <= Decimal("0.01"):
        confirmaciones.append(f"[OK] Consistencia perfecta entre pagos y cuotas (diferencia: Bs. {diferencia:,.2f})")
    
    print("\nConfirmaciones:")
    for conf in confirmaciones:
        print(f"  {conf}")
    
    print("\n" + "="*80)
    
finally:
    db.close()
