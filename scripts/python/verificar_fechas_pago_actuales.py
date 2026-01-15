#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Verificar las fechas de pago actuales en la tabla pagos"""

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
    print("VERIFICACION DE FECHAS DE PAGO ACTUALES")
    print("="*80)
    
    # Verificar fechas distintas
    query_fechas = text("""
        SELECT 
            DATE(fecha_pago) as fecha,
            COUNT(*) as cantidad_pagos,
            MIN(fecha_pago) as fecha_minima,
            MAX(fecha_pago) as fecha_maxima
        FROM pagos
        WHERE numero_documento LIKE 'ABONO_2026_%'
        GROUP BY DATE(fecha_pago)
        ORDER BY fecha DESC
    """)
    result_fechas = db.execute(query_fechas)
    fechas = result_fechas.fetchall()
    
    print("\nFechas de pago encontradas:")
    print(f"{'Fecha':<15} {'Cantidad Pagos':<18} {'Fecha Mínima':<25} {'Fecha Máxima':<25}")
    print("-" * 83)
    for fecha_row in fechas:
        fecha_str = str(fecha_row[0])
        cantidad = fecha_row[1]
        fecha_min = str(fecha_row[2])[:19] if fecha_row[2] else "NULL"
        fecha_max = str(fecha_row[3])[:19] if fecha_row[3] else "NULL"
        print(f"{fecha_str:<15} {cantidad:>16,}  {fecha_min:<25} {fecha_max:<25}")
    
    # Verificar si hay fecha en abono_2026
    query_abono = text("""
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_name = 'abono_2026'
        ORDER BY ordinal_position
    """)
    result_abono = db.execute(query_abono)
    columnas = result_abono.fetchall()
    
    print("\n\nColumnas en tabla abono_2026:")
    print("-" * 80)
    for col in columnas:
        print(f"  - {col[0]} ({col[1]})")
    
    # Verificar si hay alguna fecha en abono_2026
    if any('fecha' in col[0].lower() for col in columnas):
        columna_fecha = next((col[0] for col in columnas if 'fecha' in col[0].lower()), None)
        if columna_fecha:
            query_fecha_abono = text(f"""
                SELECT DISTINCT {columna_fecha}
                FROM abono_2026
                LIMIT 10
            """)
            result_fecha_abono = db.execute(query_fecha_abono)
            fechas_abono = result_fecha_abono.fetchall()
            print(f"\nEjemplos de fechas en abono_2026.{columna_fecha}:")
            for fecha_abono in fechas_abono:
                print(f"  - {fecha_abono[0]}")
    
    print("\n" + "="*80)
    
finally:
    db.close()
