#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Corregir fecha de pago usando la fecha de la cuota relacionada"""

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
    print("CORRECCION DE FECHA DE PAGO DESDE cuotas")
    print("="*80)
    
    # 1. Verificar estado antes
    print("\n[ANTES] Estado actual:")
    print("-" * 80)
    query_antes = text("""
        SELECT 
            COUNT(*) as total_pagos,
            MIN(p.fecha_pago) as fecha_minima_pagos,
            MAX(p.fecha_pago) as fecha_maxima_pagos,
            COUNT(CASE WHEN c.fecha_pago IS NOT NULL THEN 1 END) as con_fecha_cuota,
            COUNT(CASE WHEN c.fecha_vencimiento IS NOT NULL THEN 1 END) as con_fecha_vencimiento
        FROM pagos p
        LEFT JOIN cuotas c ON c.prestamo_id = p.prestamo_id 
            AND c.numero_cuota = p.numero_cuota
        WHERE p.numero_documento LIKE 'ABONO_2026_%'
          AND p.activo = TRUE
    """)
    result_antes = db.execute(query_antes)
    antes_row = result_antes.fetchone()
    
    print(f"Total pagos: {antes_row[0]:,}")
    print(f"Fecha mínima en pagos: {antes_row[1]}")
    print(f"Fecha máxima en pagos: {antes_row[2]}")
    print(f"Pagos con fecha en cuotas: {antes_row[3]:,}")
    print(f"Pagos con fecha_vencimiento: {antes_row[4]:,}")
    
    # 2. Verificar qué fechas se usarán
    print("\n[VERIFICACION] Fechas que se usarán para actualizar:")
    print("-" * 80)
    query_verificar = text("""
        SELECT 
            COUNT(*) as total_a_actualizar,
            COUNT(CASE WHEN c.fecha_pago IS NOT NULL THEN 1 END) as usaran_fecha_pago_cuota,
            COUNT(CASE WHEN c.fecha_pago IS NULL AND c.fecha_vencimiento IS NOT NULL THEN 1 END) as usaran_fecha_vencimiento,
            MIN(COALESCE(c.fecha_pago, c.fecha_vencimiento)) as fecha_minima_a_usar,
            MAX(COALESCE(c.fecha_pago, c.fecha_vencimiento)) as fecha_maxima_a_usar
        FROM pagos p
        INNER JOIN cuotas c ON c.prestamo_id = p.prestamo_id 
            AND c.numero_cuota = p.numero_cuota
        WHERE p.numero_documento LIKE 'ABONO_2026_%'
          AND p.activo = TRUE
          AND c.total_pagado > 0
    """)
    result_verificar = db.execute(query_verificar)
    verificar_row = result_verificar.fetchone()
    
    print(f"Total pagos a actualizar: {verificar_row[0]:,}")
    print(f"Usarán fecha_pago de cuota: {verificar_row[1]:,}")
    print(f"Usarán fecha_vencimiento: {verificar_row[2]:,}")
    print(f"Fecha mínima a usar: {verificar_row[3]}")
    print(f"Fecha máxima a usar: {verificar_row[4]}")
    
    # 3. Ejecutar actualización
    print("\n[EJECUTANDO] Actualizando fechas de pago desde cuotas...")
    print("-" * 80)
    
    query_update = text("""
        UPDATE pagos p
        SET fecha_pago = COALESCE(
            c.fecha_pago::timestamp,
            c.fecha_vencimiento::timestamp,
            p.fecha_pago
        ),
        fecha_actualizacion = CURRENT_TIMESTAMP
        FROM cuotas c
        WHERE p.prestamo_id = c.prestamo_id
          AND p.numero_cuota = c.numero_cuota
          AND p.numero_documento LIKE 'ABONO_2026_%'
          AND p.activo = TRUE
          AND c.total_pagado > 0
    """)
    
    result_update = db.execute(query_update)
    db.commit()
    
    registros_actualizados = result_update.rowcount
    print(f"[OK] Registros actualizados: {registros_actualizados:,}")
    
    # 4. Verificar estado después
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
    
    # 5. Verificar ejemplos
    print("\n[EJEMPLOS] Algunos pagos actualizados:")
    print("-" * 80)
    query_ejemplos = text("""
        SELECT 
            p.id,
            p.cedula,
            p.fecha_pago,
            c.fecha_pago as fecha_cuota,
            c.fecha_vencimiento
        FROM pagos p
        INNER JOIN cuotas c ON c.prestamo_id = p.prestamo_id 
            AND c.numero_cuota = p.numero_cuota
        WHERE p.numero_documento LIKE 'ABONO_2026_%'
          AND p.activo = TRUE
        ORDER BY p.id
        LIMIT 5
    """)
    result_ejemplos = db.execute(query_ejemplos)
    ejemplos = result_ejemplos.fetchall()
    
    print(f"{'ID':<8} {'Cédula':<12} {'Fecha Pago (pagos)':<25} {'Fecha Cuota':<15} {'Vencimiento':<15}")
    print("-" * 75)
    for ej in ejemplos:
        fecha_pago_str = str(ej[2])[:19] if ej[2] else "NULL"
        fecha_cuota_str = str(ej[3])[:10] if ej[3] else "NULL"
        vencimiento_str = str(ej[4])[:10] if ej[4] else "NULL"
        print(f"{ej[0]:<8} {ej[1]:<12} {fecha_pago_str:<25} {fecha_cuota_str:<15} {vencimiento_str:<15}")
    
    print("\n" + "="*80)
    print("[COMPLETADO] Fechas de pago corregidas desde cuotas")
    print("="*80)
    
except Exception as e:
    db.rollback()
    print(f"\n[ERROR] Error al actualizar: {str(e)}")
    raise
finally:
    db.close()
