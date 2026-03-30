#!/usr/bin/env python
"""Verificar por que la busqueda batch no encuentra ciertas cedulas."""
import os
from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import create_engine, text
from app.core.config import settings

engine = create_engine(settings.DATABASE_URL)

cedulas_buscadas = ["V28480006", "V123947215", "V17042162", "V160607306", "V26948420",
                     "V29950324", "V30427075", "V17457231", "V12782609", "V12782669"]

cedulas_encontradas_mapa = ["12782609", "12782669", "14312485", "17042162", "17457231"]

with engine.connect() as conn:
    print("=" * 120)
    print("VERIFICACION: Cedulas buscadas vs encontradas")
    print("=" * 120)

    for ced in cedulas_buscadas:
        ced_sin_v = ced.lstrip("V").lstrip("v")

        # Buscar en clientes
        result = conn.execute(text("""
            SELECT c.id, c.cedula, c.nombres,
                   (SELECT COUNT(*) FROM prestamos p WHERE p.cliente_id = c.id) as num_prestamos,
                   (SELECT string_agg(CAST(p.id AS text), ',') FROM prestamos p WHERE p.cliente_id = c.id AND p.estado = 'APROBADO') as prestamos_aprobados
            FROM clientes c
            WHERE c.cedula = :ced1 OR c.cedula = :ced2 OR c.cedula = :ced3
               OR UPPER(REPLACE(REPLACE(c.cedula, '-', ''), ' ', '')) = :ced_upper
            LIMIT 5
        """), {"ced1": ced, "ced2": ced_sin_v, "ced3": f"V{ced_sin_v}",
               "ced_upper": ced.replace("-", "").replace(" ", "").upper()})

        rows = result.fetchall()
        if rows:
            for r in rows:
                found_in = "ENCONTRADO EN MAPA" if ced_sin_v in cedulas_encontradas_mapa else "NO EN MAPA"
                print(f"  {ced:15} -> Cliente ID={r[0]:6} cedula_bd='{r[1]}' nombres='{r[2]}' prestamos={r[3]} aprobados=[{r[4]}] {found_in}")
        else:
            print(f"  {ced:15} -> NO EXISTE EN CLIENTES")

        # Buscar en prestamos directamente
        result2 = conn.execute(text("""
            SELECT p.id, p.cedula, p.estado
            FROM prestamos p
            WHERE p.cedula = :ced1 OR p.cedula = :ced2 OR p.cedula = :ced3
               OR UPPER(REPLACE(REPLACE(p.cedula, '-', ''), ' ', '')) = :ced_upper
            LIMIT 5
        """), {"ced1": ced, "ced2": ced_sin_v, "ced3": f"V{ced_sin_v}",
               "ced_upper": ced.replace("-", "").replace(" ", "").upper()})

        rows2 = result2.fetchall()
        if rows2:
            for r in rows2:
                print(f"               -> Prestamo ID={r[0]:6} cedula_bd='{r[1]}' estado='{r[2]}'")

    print("\n" + "=" * 120)
    print("VERIFICACION: Cedulas que SI estan en el mapa - que tienen en BD?")
    print("=" * 120)

    for ced_num in cedulas_encontradas_mapa:
        result = conn.execute(text("""
            SELECT c.id, c.cedula, c.nombres,
                   (SELECT COUNT(*) FROM prestamos p WHERE p.cliente_id = c.id) as num_prestamos,
                   (SELECT string_agg(CAST(p.id AS text) || ':' || p.estado, ',')
                    FROM prestamos p WHERE p.cliente_id = c.id AND p.estado = 'APROBADO') as prestamos_aprobados
            FROM clientes c
            WHERE c.cedula LIKE :pattern
            LIMIT 5
        """), {"pattern": f"%{ced_num}%"})

        rows = result.fetchall()
        for r in rows:
            print(f"  {ced_num:15} -> Cliente ID={r[0]:6} cedula_bd='{r[1]}' nombres='{r[2]}' prestamos={r[3]} aprobados=[{r[4]}]")
