#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Investigar qué fecha de pago deberían tener los pagos"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "backend"))

from sqlalchemy import text
from app.db.session import SessionLocal

db = SessionLocal()
try:
    print("="*80)
    print("INVESTIGACION: FECHA DE PAGO CORRECTA")
    print("="*80)
    
    # 1. Verificar fecha actual en pagos
    print("\n[1] FECHA ACTUAL EN pagos")
    print("-" * 80)
    query_pagos = text("""
        SELECT 
            MIN(fecha_pago) as fecha_minima,
            MAX(fecha_pago) as fecha_maxima,
            COUNT(*) as total
        FROM pagos
        WHERE numero_documento LIKE 'ABONO_2026_%'
          AND activo = TRUE
    """)
    result_pagos = db.execute(query_pagos)
    pagos_row = result_pagos.fetchone()
    print(f"Fecha mínima en pagos: {pagos_row[0]}")
    print(f"Fecha máxima en pagos: {pagos_row[1]}")
    print(f"Total pagos: {pagos_row[2]:,}")
    
    # 2. Verificar fecha en cuotas relacionadas
    print("\n[2] FECHA EN cuotas RELACIONADAS CON ESTOS PAGOS")
    print("-" * 80)
    query_cuotas = text("""
        SELECT 
            MIN(c.fecha_pago) as fecha_minima_cuota,
            MAX(c.fecha_pago) as fecha_maxima_cuota,
            MIN(c.fecha_vencimiento) as fecha_minima_vencimiento,
            MAX(c.fecha_vencimiento) as fecha_maxima_vencimiento,
            COUNT(DISTINCT c.id) as cuotas_con_pagos
        FROM cuotas c
        INNER JOIN pagos p ON p.prestamo_id = c.prestamo_id 
            AND p.numero_cuota = c.numero_cuota
        WHERE p.numero_documento LIKE 'ABONO_2026_%'
          AND p.activo = TRUE
          AND c.total_pagado > 0
    """)
    result_cuotas = db.execute(query_cuotas)
    cuotas_row = result_cuotas.fetchone()
    print(f"Fecha mínima en cuotas.fecha_pago: {cuotas_row[0]}")
    print(f"Fecha máxima en cuotas.fecha_pago: {cuotas_row[1]}")
    print(f"Fecha mínima vencimiento: {cuotas_row[2]}")
    print(f"Fecha máxima vencimiento: {cuotas_row[3]}")
    print(f"Cuotas con pagos: {cuotas_row[4]:,}")
    
    # 3. Comparar pagos vs cuotas
    print("\n[3] COMPARACION: pagos.fecha_pago vs cuotas.fecha_pago")
    print("-" * 80)
    query_comparacion = text("""
        SELECT 
            p.id as pago_id,
            p.cedula,
            p.fecha_pago as fecha_pago_pagos,
            c.fecha_pago as fecha_pago_cuotas,
            c.fecha_vencimiento,
            ABS(EXTRACT(EPOCH FROM (p.fecha_pago - c.fecha_pago))) / 86400 as diferencia_dias
        FROM pagos p
        INNER JOIN cuotas c ON c.prestamo_id = p.prestamo_id 
            AND c.numero_cuota = p.numero_cuota
        WHERE p.numero_documento LIKE 'ABONO_2026_%'
          AND p.activo = TRUE
          AND c.total_pagado > 0
        ORDER BY diferencia_dias DESC
        LIMIT 10
    """)
    result_comparacion = db.execute(query_comparacion)
    comparaciones = result_comparacion.fetchall()
    
    print(f"{'Pago ID':<10} {'Cédula':<12} {'Fecha pagos':<20} {'Fecha cuotas':<20} {'Vencimiento':<15} {'Diferencia (días)':<18}")
    print("-" * 95)
    for comp in comparaciones:
        fecha_pagos_str = str(comp[2])[:19] if comp[2] else "NULL"
        fecha_cuotas_str = str(comp[3])[:19] if comp[3] else "NULL"
        vencimiento_str = str(comp[4])[:10] if comp[4] else "NULL"
        diferencia = comp[5] if comp[5] else 0
        print(f"{comp[0]:<10} {comp[1]:<12} {fecha_pagos_str:<20} {fecha_cuotas_str:<20} {vencimiento_str:<15} {diferencia:>15,.1f}")
    
    # 4. Verificar si debería usar fecha_vencimiento
    print("\n[4] ANALISIS: ¿Debería usar fecha_vencimiento de la cuota?")
    print("-" * 80)
    query_vencimiento = text("""
        SELECT 
            COUNT(*) as total_pagos,
            COUNT(CASE WHEN c.fecha_vencimiento IS NOT NULL THEN 1 END) as con_fecha_vencimiento,
            MIN(c.fecha_vencimiento) as fecha_min_vencimiento,
            MAX(c.fecha_vencimiento) as fecha_max_vencimiento
        FROM pagos p
        INNER JOIN cuotas c ON c.prestamo_id = p.prestamo_id 
            AND c.numero_cuota = p.numero_cuota
        WHERE p.numero_documento LIKE 'ABONO_2026_%'
          AND p.activo = TRUE
    """)
    result_vencimiento = db.execute(query_vencimiento)
    vencimiento_row = result_vencimiento.fetchone()
    print(f"Total pagos con cuotas: {vencimiento_row[0]:,}")
    print(f"Pagos con fecha_vencimiento: {vencimiento_row[1]:,}")
    print(f"Fecha mínima vencimiento: {vencimiento_row[2]}")
    print(f"Fecha máxima vencimiento: {vencimiento_row[3]}")
    
    print("\n" + "="*80)
    print("CONCLUSION:")
    print("="*80)
    print("La fecha de pago debería ser la fecha real cuando se efectuó el pago.")
    print("Si no hay fecha específica del abono, podría usar:")
    print("  1. fecha_vencimiento de la cuota (fecha programada)")
    print("  2. fecha_pago de la cuota (si ya está establecida)")
    print("  3. Una fecha específica del proceso de abono_2026")
    print("="*80)
    
finally:
    db.close()
