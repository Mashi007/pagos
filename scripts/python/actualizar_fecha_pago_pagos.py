#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Actualizar fecha de pago en tabla pagos"""

import sys
from pathlib import Path
from datetime import datetime

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "backend"))

from sqlalchemy import text
from app.db.session import SessionLocal

db = SessionLocal()
try:
    print("="*80)
    print("ACTUALIZACION DE FECHA DE PAGO EN TABLA pagos")
    print("="*80)
    
    # 1. Verificar estado antes
    query_antes = text("""
        SELECT 
            COUNT(*) as total_pagos,
            MIN(fecha_pago) as fecha_minima,
            MAX(fecha_pago) as fecha_maxima
        FROM pagos
        WHERE numero_documento LIKE 'ABONO_2026_%'
          AND activo = TRUE
    """)
    result_antes = db.execute(query_antes)
    antes_row = result_antes.fetchone()
    
    total_pagos = antes_row[0] if antes_row[0] else 0
    fecha_minima_antes = antes_row[1]
    fecha_maxima_antes = antes_row[2]
    
    print(f"\n[ANTES] Estado actual:")
    print(f"  Total de pagos a actualizar: {total_pagos:,}")
    print(f"  Fecha mínima: {fecha_minima_antes}")
    print(f"  Fecha máxima: {fecha_maxima_antes}")
    
    if total_pagos == 0:
        print("\n[ADVERTENCIA] No hay pagos para actualizar")
        sys.exit(0)
    
    # 2. Confirmar actualización
    fecha_actual = datetime.now()
    print(f"\n[ACCION] Se actualizarán {total_pagos:,} pagos con fecha: {fecha_actual.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Ejecutar directamente sin confirmación interactiva
    print("\n[EJECUTANDO] Actualizando fechas de pago...")
    
    # 3. Ejecutar actualización
    print("\n[EJECUTANDO] Actualizando fechas de pago...")
    
    query_update = text("""
        UPDATE pagos
        SET fecha_pago = CURRENT_TIMESTAMP,
            fecha_actualizacion = CURRENT_TIMESTAMP
        WHERE numero_documento LIKE 'ABONO_2026_%'
          AND activo = TRUE
    """)
    
    result_update = db.execute(query_update)
    db.commit()
    
    registros_actualizados = result_update.rowcount
    
    print(f"[OK] Registros actualizados: {registros_actualizados:,}")
    
    # 4. Verificar estado después
    query_despues = text("""
        SELECT 
            COUNT(*) as total_pagos,
            MIN(fecha_pago) as fecha_minima,
            MAX(fecha_pago) as fecha_maxima
        FROM pagos
        WHERE numero_documento LIKE 'ABONO_2026_%'
          AND activo = TRUE
    """)
    result_despues = db.execute(query_despues)
    despues_row = result_despues.fetchone()
    
    fecha_minima_despues = despues_row[1]
    fecha_maxima_despues = despues_row[2]
    
    print(f"\n[DESPUES] Estado actualizado:")
    print(f"  Total de pagos: {despues_row[0]:,}")
    print(f"  Fecha mínima: {fecha_minima_despues}")
    print(f"  Fecha máxima: {fecha_maxima_despues}")
    
    print("\n" + "="*80)
    print("[COMPLETADO] Fechas de pago actualizadas exitosamente")
    print("="*80)
    
except Exception as e:
    db.rollback()
    print(f"\n[ERROR] Error al actualizar: {str(e)}")
    raise
finally:
    db.close()
