#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Verificar que las fechas de pago se actualizaron correctamente"""

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
    print("VERIFICACION DE FECHAS DE PAGO ACTUALIZADAS")
    print("="*80)
    
    # Verificar distribución de fechas
    query_fechas = text("""
        SELECT 
            DATE(fecha_pago) as fecha,
            COUNT(*) as cantidad_pagos,
            MIN(fecha_pago) as fecha_minima,
            MAX(fecha_pago) as fecha_maxima
        FROM pagos
        WHERE numero_documento LIKE 'ABONO_2026_%'
          AND activo = TRUE
        GROUP BY DATE(fecha_pago)
        ORDER BY fecha DESC
    """)
    result_fechas = db.execute(query_fechas)
    fechas = result_fechas.fetchall()
    
    print("\nDistribución de fechas de pago:")
    print(f"{'Fecha':<15} {'Cantidad Pagos':<18} {'Fecha Mínima':<25} {'Fecha Máxima':<25}")
    print("-" * 83)
    for fecha_row in fechas:
        fecha_str = str(fecha_row[0])
        cantidad = fecha_row[1]
        fecha_min = str(fecha_row[2])[:19] if fecha_row[2] else "NULL"
        fecha_max = str(fecha_row[3])[:19] if fecha_row[3] else "NULL"
        print(f"{fecha_str:<15} {cantidad:>16,}  {fecha_min:<25} {fecha_max:<25}")
    
    # Verificar algunos ejemplos
    query_ejemplos = text("""
        SELECT 
            id,
            cedula,
            fecha_pago,
            numero_documento
        FROM pagos
        WHERE numero_documento LIKE 'ABONO_2026_%'
          AND activo = TRUE
        ORDER BY id
        LIMIT 5
    """)
    result_ejemplos = db.execute(query_ejemplos)
    ejemplos = result_ejemplos.fetchall()
    
    print("\n\nEjemplos de pagos actualizados:")
    print(f"{'ID':<8} {'Cédula':<15} {'Fecha Pago':<25} {'Número Documento':<35}")
    print("-" * 83)
    for ej in ejemplos:
        fecha_str = str(ej[2])[:19] if ej[2] else "NULL"
        print(f"{ej[0]:<8} {ej[1]:<15} {fecha_str:<25} {ej[3][:35]:<35}")
    
    print("\n" + "="*80)
    print("[OK] Verificación completada")
    print("="*80)
    
finally:
    db.close()
