#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Corregir fecha de pago usando fecha_vencimiento de la cuota"""

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
    print("CORRECCION DE FECHA DE PAGO USANDO fecha_vencimiento")
    print("="*80)
    
    # 1. Verificar estado antes
    print("\n[ANTES] Estado actual:")
    print("-" * 80)
    query_antes = text("""
        SELECT 
            COUNT(*) as total_pagos,
            MIN(p.fecha_pago) as fecha_minima_pagos,
            MAX(p.fecha_pago) as fecha_maxima_pagos,
            COUNT(DISTINCT DATE(p.fecha_pago)) as fechas_distintas_pagos,
            MIN(c.fecha_vencimiento) as fecha_minima_vencimiento,
            MAX(c.fecha_vencimiento) as fecha_maxima_vencimiento,
            COUNT(DISTINCT c.fecha_vencimiento) as fechas_distintas_vencimiento
        FROM pagos p
        INNER JOIN cuotas c ON c.prestamo_id = p.prestamo_id 
            AND c.numero_cuota = p.numero_cuota
        WHERE p.numero_documento LIKE 'ABONO_2026_%'
          AND p.activo = TRUE
          AND c.total_pagado > 0
    """)
    result_antes = db.execute(query_antes)
    antes_row = result_antes.fetchone()
    
    print(f"Total pagos: {antes_row[0]:,}")
    print(f"Fecha mínima en pagos: {antes_row[1]}")
    print(f"Fecha máxima en pagos: {antes_row[2]}")
    print(f"Fechas distintas en pagos: {antes_row[3]}")
    print(f"\nFecha mínima vencimiento: {antes_row[4]}")
    print(f"Fecha máxima vencimiento: {antes_row[5]}")
    print(f"Fechas distintas vencimiento: {antes_row[6]}")
    
    # 2. Ejecutar actualización usando fecha_vencimiento
    print("\n[EJECUTANDO] Actualizando fechas de pago usando fecha_vencimiento...")
    print("-" * 80)
    
    query_update = text("""
        UPDATE pagos p
        SET fecha_pago = c.fecha_vencimiento::timestamp,
            fecha_actualizacion = CURRENT_TIMESTAMP
        FROM cuotas c
        WHERE p.prestamo_id = c.prestamo_id
          AND p.numero_cuota = c.numero_cuota
          AND p.numero_documento LIKE 'ABONO_2026_%'
          AND p.activo = TRUE
          AND c.total_pagado > 0
          AND c.fecha_vencimiento IS NOT NULL
    """)
    
    result_update = db.execute(query_update)
    db.commit()
    
    registros_actualizados = result_update.rowcount
    print(f"[OK] Registros actualizados: {registros_actualizados:,}")
    
    # 3. Verificar estado después
    print("\n[DESPUES] Estado actualizado:")
    print("-" * 80)
    query_despues = text("""
        SELECT 
            COUNT(*) as total_pagos,
            MIN(p.fecha_pago) as fecha_minima,
            MAX(p.fecha_pago) as fecha_maxima,
            COUNT(DISTINCT DATE(p.fecha_pago)) as fechas_distintas
        FROM pagos p
        WHERE p.numero_documento LIKE 'ABONO_2026_%'
          AND p.activo = TRUE
    """)
    result_despues = db.execute(query_despues)
    despues_row = result_despues.fetchone()
    
    print(f"Total pagos: {despues_row[0]:,}")
    print(f"Fecha mínima: {despues_row[1]}")
    print(f"Fecha máxima: {despues_row[2]}")
    print(f"Fechas distintas: {despues_row[3]}")
    
    # 4. Verificar distribución de fechas
    print("\n[DISTRIBUCION] Fechas de pago por fecha:")
    print("-" * 80)
    query_distribucion = text("""
        SELECT 
            DATE(p.fecha_pago) as fecha,
            COUNT(*) as cantidad_pagos
        FROM pagos p
        WHERE p.numero_documento LIKE 'ABONO_2026_%'
          AND p.activo = TRUE
        GROUP BY DATE(p.fecha_pago)
        ORDER BY fecha
        LIMIT 20
    """)
    result_distribucion = db.execute(query_distribucion)
    distribuciones = result_distribucion.fetchall()
    
    print(f"{'Fecha':<15} {'Cantidad Pagos':<18}")
    print("-" * 33)
    for dist in distribuciones:
        print(f"{str(dist[0]):<15} {dist[1]:>16,}")
    
    # 5. Verificar ejemplos
    print("\n[EJEMPLOS] Algunos pagos actualizados:")
    print("-" * 80)
    query_ejemplos = text("""
        SELECT 
            p.id,
            p.cedula,
            p.numero_cuota,
            DATE(p.fecha_pago) as fecha_pago,
            c.fecha_vencimiento
        FROM pagos p
        INNER JOIN cuotas c ON c.prestamo_id = p.prestamo_id 
            AND c.numero_cuota = p.numero_cuota
        WHERE p.numero_documento LIKE 'ABONO_2026_%'
          AND p.activo = TRUE
        ORDER BY p.fecha_pago, p.cedula, p.numero_cuota
        LIMIT 10
    """)
    result_ejemplos = db.execute(query_ejemplos)
    ejemplos = result_ejemplos.fetchall()
    
    print(f"{'ID':<8} {'Cédula':<12} {'Cuota':<8} {'Fecha Pago':<15} {'Vencimiento':<15}")
    print("-" * 58)
    for ej in ejemplos:
        fecha_pago_str = str(ej[3])[:10] if ej[3] else "NULL"
        vencimiento_str = str(ej[4])[:10] if ej[4] else "NULL"
        print(f"{ej[0]:<8} {ej[1]:<12} {ej[2]:<8} {fecha_pago_str:<15} {vencimiento_str:<15}")
    
    print("\n" + "="*80)
    print("[COMPLETADO] Fechas de pago corregidas usando fecha_vencimiento")
    print("="*80)
    print("\n[NOTA] Ahora cada pago tiene la fecha de vencimiento de su cuota correspondiente,")
    print("       que representa la fecha programada real para el pago de esa cuota.")
    print("="*80)
    
except Exception as e:
    db.rollback()
    print(f"\n[ERROR] Error al actualizar: {str(e)}")
    raise
finally:
    db.close()
