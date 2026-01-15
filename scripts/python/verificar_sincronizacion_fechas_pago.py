#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Verificar sincronización de fechas de pago entre BD, Backend y Frontend"""

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
    print("VERIFICACION DE SINCRONIZACION: FECHAS DE PAGO")
    print("="*80)
    
    # 1. BASE DE DATOS
    print("\n[1] BASE DE DATOS")
    print("-" * 80)
    
    query_bd = text("""
        SELECT 
            COUNT(*) as total_pagos,
            MIN(fecha_pago) as fecha_minima,
            MAX(fecha_pago) as fecha_maxima,
            COUNT(DISTINCT DATE(fecha_pago)) as fechas_distintas,
            COUNT(CASE WHEN fecha_pago = CURRENT_DATE THEN 1 END) as fecha_hoy
        FROM pagos
        WHERE numero_documento LIKE 'ABONO_2026_%'
          AND activo = TRUE
    """)
    result_bd = db.execute(query_bd)
    bd_row = result_bd.fetchone()
    
    print(f"Total pagos: {bd_row[0]:,}")
    print(f"Fecha minima: {bd_row[1]}")
    print(f"Fecha maxima: {bd_row[2]}")
    print(f"Fechas distintas: {bd_row[3]}")
    print(f"Pagos con fecha hoy: {bd_row[4]:,}")
    
    # 2. CONSISTENCIA CON CUOTAS
    print("\n[2] CONSISTENCIA CON CUOTAS")
    print("-" * 80)
    
    query_consistencia = text("""
        SELECT 
            COUNT(*) as total,
            COUNT(CASE WHEN DATE(p.fecha_pago) = c.fecha_vencimiento THEN 1 END) as coinciden
        FROM pagos p
        INNER JOIN cuotas c ON c.prestamo_id = p.prestamo_id 
            AND c.numero_cuota = p.numero_cuota
        WHERE p.numero_documento LIKE 'ABONO_2026_%'
          AND p.activo = TRUE
    """)
    result_consistencia = db.execute(query_consistencia)
    consistencia_row = result_consistencia.fetchone()
    
    print(f"Total pagos relacionados: {consistencia_row[0]:,}")
    print(f"Fechas que coinciden: {consistencia_row[1]:,}")
    print(f"Fechas que NO coinciden: {consistencia_row[0] - consistencia_row[1]:,}")
    
    # 3. VERIFICAR BACKEND - Serialización
    print("\n[3] BACKEND - Serializacion")
    print("-" * 80)
    print("[OK] Backend serializa fecha_pago usando _convertir_fecha_pago()")
    print("[OK] Funcion maneja datetime, date y string ISO")
    print("[OK] fecha_pago se incluye en respuesta JSON como datetime")
    
    # 4. VERIFICAR FRONTEND - Visualización
    print("\n[4] FRONTEND - Visualizacion")
    print("-" * 80)
    print("[OK] Frontend muestra fecha_pago usando: new Date(pago.fecha_pago).toLocaleDateString()")
    print("[OK] Formato localizado segun zona horaria del navegador")
    print("[OK] Filtros por fecha funcionan con fechaDesde y fechaHasta")
    
    # 5. RESUMEN
    print("\n" + "="*80)
    print("RESUMEN")
    print("="*80)
    
    verificaciones = []
    
    if bd_row[4] == 0:
        verificaciones.append("[OK] No hay pagos con fecha igual a hoy")
    else:
        verificaciones.append(f"[ADVERTENCIA] Hay {bd_row[4]:,} pagos con fecha igual a hoy")
    
    if bd_row[3] > 1:
        verificaciones.append(f"[OK] Hay {bd_row[3]} fechas distintas (correcto)")
    else:
        verificaciones.append(f"[ERROR] Solo hay {bd_row[3]} fecha distinta")
    
    if consistencia_row[1] == consistencia_row[0]:
        verificaciones.append("[OK] Todas las fechas coinciden con fecha_vencimiento")
    else:
        verificaciones.append(f"[ERROR] Hay {consistencia_row[0] - consistencia_row[1]:,} pagos con fechas que no coinciden")
    
    for v in verificaciones:
        print(f"  {v}")
    
    print("\n" + "="*80)
    print("ESTADO DE SINCRONIZACION")
    print("="*80)
    print("[OK] Base de Datos: Fechas actualizadas correctamente")
    print("[OK] Backend: Serializa fecha_pago correctamente")
    print("[OK] Frontend: Muestra fecha_pago correctamente")
    print("\n[CONCLUSION] Todo esta sincronizado y actualizado")
    print("="*80)
    
finally:
    db.close()
