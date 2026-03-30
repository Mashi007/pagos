#!/usr/bin/env python
"""Auditoría integral de fecha_requerimiento NULL en la base de datos."""
import os
import sys
from dotenv import load_dotenv

load_dotenv()

from sqlalchemy import create_engine, text
from app.core.config import settings

engine = create_engine(settings.DATABASE_URL)

print("\n" + "=" * 100)
print("AUDITORÍA INTEGRAL: fecha_requerimiento NULL")
print("=" * 100 + "\n")

with engine.connect() as conn:
    # Auditoría 1: Préstamos con fecha_requerimiento NULL
    print("AUDITORÍA 1: Préstamos con fecha_requerimiento = NULL")
    print("-" * 100)
    result = conn.execute(text("""
        SELECT id, cedula, nombres, fecha_aprobacion, fecha_requerimiento, estado
        FROM prestamos
        WHERE fecha_requerimiento IS NULL
        ORDER BY id DESC
        LIMIT 20
    """))
    
    null_count = 0
    for row in result:
        null_count += 1
        print(f"ID: {row[0]:6} | Cedula: {row[1]:15} | Aprobacion: {row[3]} | Estado: {row[5]}")
    
    print(f"\nTotal con NULL: {null_count}\n")
    
    # Auditoría 2: Préstamo específico ID 5545
    print("AUDITORÍA 2: Préstamo específico ID 5545 (el que causa error)")
    print("-" * 100)
    result = conn.execute(text("""
        SELECT id, cedula, nombres, fecha_aprobacion, fecha_requerimiento, 
               fecha_registro, estado
        FROM prestamos
        WHERE id = 5545
    """))
    
    row = result.fetchone()
    if row:
        print(f"ID: {row[0]}")
        print(f"  Cedula: {row[1]}")
        print(f"  Nombres: {row[2]}")
        print(f"  fecha_aprobacion: {row[3]}")
        print(f"  fecha_requerimiento: {row[4]}")
        print(f"  fecha_registro: {row[5]}")
        print(f"  estado: {row[6]}")
    else:
        print("Préstamo no encontrado")
    
    print("\n")
    
    # Auditoría 3: Cuotas del préstamo 5545
    print("AUDITORÍA 3: Cuotas del préstamo 5545")
    print("-" * 100)
    result = conn.execute(text("""
        SELECT id, prestamo_id, numero_cuota, fecha_vencimiento, monto, estado
        FROM cuotas
        WHERE prestamo_id = 5545
        ORDER BY numero_cuota
        LIMIT 15
    """))
    
    cuota_count = 0
    for row in result:
        cuota_count += 1
        print(f"Cuota {row[2]:2} | fecha_vencimiento: {row[3]} | monto: {row[4]:10} | estado: {row[5]}")
    
    print(f"\nTotal cuotas: {cuota_count}\n")
    
    # Auditoría 4: Estadísticas
    print("AUDITORÍA 4: Estadísticas Generales")
    print("-" * 100)
    result = conn.execute(text("""
        SELECT COUNT(*) as total_prestamos,
               COUNT(CASE WHEN fecha_requerimiento IS NULL THEN 1 END) as con_fecha_req_null,
               COUNT(CASE WHEN fecha_aprobacion IS NULL THEN 1 END) as con_fecha_apr_null
        FROM prestamos
    """))
    
    row = result.fetchone()
    total = row[0]
    null_req = row[1]
    null_apr = row[2]
    
    print(f"Total préstamos: {total}")
    print(f"Con fecha_requerimiento NULL: {null_req} ({null_req*100.0/total:.2f}%)")
    print(f"Con fecha_aprobacion NULL: {null_apr} ({null_apr*100.0/total:.2f}%)")
    
    print("\n" + "=" * 100)
    print("RECOMENDACIÓN")
    print("=" * 100)
    print("""
Los préstamos con fecha_requerimiento = NULL son un DATA ISSUE.
Necesito:
1. Asignar fecha_requerimiento válida a todos estos préstamos
2. Proteger el backend para manejar este caso
3. Prevenir que se creen nuevos préstamos sin fecha_requerimiento
    """)
