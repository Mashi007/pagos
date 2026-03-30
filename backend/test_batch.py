#!/usr/bin/env python
"""Simular la llamada batch y ver que devuelve."""
import os
from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import create_engine, text, select, or_, func
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.database import SessionLocal
from app.models.prestamo import Prestamo
from app.models.cliente import Cliente

db = SessionLocal()

cedulas_clean = ["V28480006", "V123947215", "V17042162", "V160607306", "V26948420",
                  "V29950324", "V30427075", "V17457231", "V12782609", "V12782669",
                  "V14312485", "V127180717", "V12058084"]

resultado = {c: [] for c in cedulas_clean}
cedulas_encontradas = set()

# PASO 1: Busqueda exacta
q_exacto = (
    select(Prestamo.id, Prestamo.cliente_id, Prestamo.estado, Prestamo.cedula, Cliente.cedula)
    .select_from(Prestamo)
    .join(Cliente, Prestamo.cliente_id == Cliente.id)
    .where(or_(
        Cliente.cedula.in_(cedulas_clean),
        Prestamo.cedula.in_(cedulas_clean),
    ))
    .order_by(Prestamo.id.desc())
    .limit(50000)
)

print("=" * 120)
print("PASO 1: Busqueda exacta")
print("=" * 120)

for p_id, cli_id, p_estado, p_cedula, cli_cedula in db.execute(q_exacto):
    cedula_cli = (cli_cedula or p_cedula or "").strip()
    cedula_cli_norm = cedula_cli.replace("-", "").replace(" ", "").upper()

    cedula_encontrada = None
    for ced_clean in cedulas_clean:
        ced_clean_norm = ced_clean.replace("-", "").replace(" ", "").upper()
        if cedula_cli_norm == ced_clean_norm:
            cedula_encontrada = ced_clean
            break

    if cedula_encontrada:
        cedulas_encontradas.add(cedula_encontrada)
        resultado[cedula_encontrada].append({"id": p_id, "estado": p_estado, "cedula": cedula_cli})
        print(f"  MATCH: {cedula_encontrada} -> prestamo_id={p_id} estado={p_estado} cedula_bd={cedula_cli}")

print(f"\nEncontradas en PASO 1: {len(cedulas_encontradas)}: {cedulas_encontradas}")

# PASO 2: Faltantes
cedulas_faltantes = [c for c in cedulas_clean if c not in cedulas_encontradas]
print(f"\nFaltantes despues PASO 1: {len(cedulas_faltantes)}: {cedulas_faltantes}")

if cedulas_faltantes:
    cedulas_norm_map = {}
    for ced in cedulas_faltantes:
        ced_norm = ced.replace("-", "").replace(" ", "").upper()
        cedulas_norm_map[ced_norm] = ced

    print(f"\nNormalizadas para PASO 2: {cedulas_norm_map}")

    or_conditions = []
    for ced_norm in cedulas_norm_map.keys():
        or_conditions.append(
            func.upper(func.replace(func.replace(Cliente.cedula, "-", ""), " ", "")) == ced_norm
        )
        or_conditions.append(
            func.upper(func.replace(func.replace(Prestamo.cedula, "-", ""), " ", "")) == ced_norm
        )

    q_faltantes = (
        select(Prestamo.id, Prestamo.cliente_id, Prestamo.estado, Prestamo.cedula, Cliente.cedula)
        .select_from(Prestamo)
        .join(Cliente, Prestamo.cliente_id == Cliente.id)
        .where(or_(*or_conditions))
        .order_by(Prestamo.id.desc())
    )

    print(f"\n{'='*120}")
    print("PASO 2: Busqueda normalizada")
    print("=" * 120)

    for p_id, cli_id, p_estado, p_cedula, cli_cedula in db.execute(q_faltantes):
        cedula_cli = (cli_cedula or p_cedula or "").strip()
        cedula_cli_norm = cedula_cli.replace("-", "").replace(" ", "").upper()

        if cedula_cli_norm in cedulas_norm_map:
            ced_original = cedulas_norm_map[cedula_cli_norm]
            cedulas_encontradas.add(ced_original)
            resultado[ced_original].append({"id": p_id, "estado": p_estado, "cedula": cedula_cli})
            print(f"  MATCH: {ced_original} -> prestamo_id={p_id} estado={p_estado} cedula_bd={cedula_cli}")

print(f"\n{'='*120}")
print(f"RESULTADO FINAL")
print(f"{'='*120}")
print(f"Total encontradas: {len(cedulas_encontradas)}: {cedulas_encontradas}")
print(f"\nResultado devuelto al frontend:")
for ced, arr in resultado.items():
    if arr:
        print(f"  {ced}: {arr}")
    else:
        print(f"  {ced}: [] (VACIA)")

db.close()
