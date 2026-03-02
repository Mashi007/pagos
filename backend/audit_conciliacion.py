#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Auditoria: Verifica por qué columnas E y F están vacías
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app.core.database import SessionLocal
from app.models.conciliacion_temporal import ConciliacionTemporal
from app.models.prestamo import Prestamo
from sqlalchemy import select

db = SessionLocal()

print("=" * 80)
print("AUDITORIA: CONCILIACION")
print("=" * 80)

# 1. Verificar datos en conciliacion_temporal
print("\n1. DATOS EN conciliacion_temporal:")
print("-" * 80)
concilia_records = db.execute(select(ConciliacionTemporal)).scalars().all()
print(f"Total registros: {len(concilia_records)}\n")

for rec in concilia_records:
    print(f"Cedula: {rec.cedula}")
    print(f"  Total Financiamiento: {rec.total_financiamiento}")
    print(f"  Total Abonos: {rec.total_abonos}")
    print()

# 2. Verificar datos en prestamos
print("\n2. DATOS EN prestamos:")
print("-" * 80)
prestamos = db.execute(select(Prestamo).where(Prestamo.estado == "APROBADO")).scalars().all()
print(f"Total prestamos APROBADOS: {len(prestamos)}\n")

# Mostrar solo los primeros 5 para no saturar
for p in prestamos[:5]:
    print(f"ID: {p.id}")
    print(f"  Cedula: {p.cedula}")
    print(f"  Total Financiamiento: {p.total_financiamiento}")
    print(f"  Total Abonos: {p.total_abonos}")
    print()

# 3. Comparar cédulas
print("\n3. COMPARACION DE CEDULAS:")
print("-" * 80)

concilia_cedulas = {rec.cedula: rec for rec in concilia_records}
prestamo_cedulas = {}
for p in prestamos:
    cedula_clean = (p.cedula or "").strip()
    if cedula_clean not in prestamo_cedulas:
        prestamo_cedulas[cedula_clean] = p

print(f"Cedulas en conciliacion_temporal: {list(concilia_cedulas.keys())}")
print(f"Cedulas en prestamos (primeras 10): {list(prestamo_cedulas.keys())[:10]}")

# 4. Buscar matches
print("\n4. BUSCAR MATCHES:")
print("-" * 80)

matches = 0
no_matches = 0

for cedula_concilia in concilia_cedulas.keys():
    if cedula_concilia in prestamo_cedulas:
        print(f"MATCH: {cedula_concilia}")
        matches += 1
    else:
        print(f"NO MATCH: {cedula_concilia}")
        no_matches += 1
        
        # Buscar similar
        print(f"  Buscando variantes...")
        for cedula_prestamo in prestamo_cedulas.keys():
            if cedula_concilia.upper() in cedula_prestamo.upper() or cedula_prestamo.upper() in cedula_concilia.upper():
                print(f"    Posible similar: {cedula_prestamo}")

print(f"\nTotal matches: {matches}")
print(f"Total NO matches: {no_matches}")

# 5. Revisar tabla prestamos para cédulas específicas
print("\n5. DETALLES PARA CEDULAS DEL EXCEL:")
print("-" * 80)

for cedula_excel in concilia_cedulas.keys():
    print(f"\nBuscando prestamos para cedula: {cedula_excel}")
    
    # Búsqueda exacta
    p_exacta = db.execute(
        select(Prestamo).where(Prestamo.cedula == cedula_excel)
    ).scalars().all()
    
    if p_exacta:
        print(f"  ENCONTRADO exacto: {len(p_exacta)} prestamo(s)")
        for p in p_exacta:
            print(f"    - ID: {p.id}, TF: {p.total_financiamiento}, TA: {p.total_abonos}")
    else:
        print(f"  NO ENCONTRADO (búsqueda exacta)")
        
        # Búsqueda similar
        similares = db.execute(
            select(Prestamo).where(Prestamo.cedula.like(f"%{cedula_excel}%"))
        ).scalars().all()
        
        if similares:
            print(f"  ENCONTRADO similar: {len(similares)} prestamo(s)")
            for p in similares:
                print(f"    - Cedula: {p.cedula}, TF: {p.total_financiamiento}")
        else:
            print(f"  NO ENCONTRADO (búsqueda similar)")

db.close()

print("\n" + "=" * 80)
print("FIN AUDITORIA")
print("=" * 80)
