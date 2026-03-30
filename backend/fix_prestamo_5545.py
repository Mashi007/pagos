#!/usr/bin/env python
"""Script para limpiar datos inconsistentes de fecha_requerimiento."""
import os
from dotenv import load_dotenv

load_dotenv()

from sqlalchemy import create_engine, text
from app.core.config import settings

engine = create_engine(settings.DATABASE_URL)

print("\n" + "=" * 100)
print("LIMPIEZA DE DATOS: Préstamo 5545")
print("=" * 100 + "\n")

with engine.begin() as conn:
    # Obtener datos actuales
    result = conn.execute(text("""
        SELECT id, cedula, nombres, fecha_aprobacion, fecha_requerimiento, estado
        FROM prestamos
        WHERE id = 5545
    """))
    
    row = result.fetchone()
    print("ESTADO ACTUAL:")
    print(f"  ID: {row[0]}")
    print(f"  Cedula: {row[1]}")
    print(f"  Nombres: {row[2]}")
    print(f"  fecha_aprobacion: {row[3]}")
    print(f"  fecha_requerimiento: {row[4]} (POSTERIOR A APROBACION - INCORRECTO)")
    print(f"  estado: {row[5]}\n")
    
    # Corregir: usar fecha_aprobacion menos 1 día como fecha_requerimiento
    print("CORRIGIENDO: Asignando fecha_requerimiento = fecha_aprobacion - 1 día")
    
    conn.execute(text("""
        UPDATE prestamos
        SET fecha_requerimiento = (fecha_aprobacion::date - INTERVAL '1 day')::date
        WHERE id = 5545
    """))
    
    # Verificar
    result = conn.execute(text("""
        SELECT id, cedula, nombres, fecha_aprobacion, fecha_requerimiento, estado
        FROM prestamos
        WHERE id = 5545
    """))
    
    row = result.fetchone()
    print("ESTADO DESPUES DE LA CORRECCION:")
    print(f"  ID: {row[0]}")
    print(f"  Cedula: {row[1]}")
    print(f"  Nombres: {row[2]}")
    print(f"  fecha_aprobacion: {row[3]}")
    print(f"  fecha_requerimiento: {row[4]} (Ahora es ANTERIOR)")
    print(f"  estado: {row[5]}")
    
    print("\n" + "=" * 100)
    print("LIMPIEZA COMPLETADA")
    print("=" * 100 + "\n")
    print("El prestamo ahora tiene una relacion logica correcta entre fechas:")
    print("  - fecha_requerimiento < fecha_aprobacion (CORRECTO)")
    print("\nAhora puedes cambiar fecha_aprobacion sin problemas.")
