# -*- coding: utf-8 -*-
"""Temporary script to fix clientes stats nuevos_este_mes."""
path = 'backend/app/api/v1/endpoints/clientes.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

old = """    # Nuevos clientes registrados en el mes actual (usar fecha de la BD para coincidir con fecha_registro)
    primer_dia_mes = db.scalar(text("SELECT date_trunc('month', CURRENT_DATE)::date"))
    ultimo_dia_mes = db.scalar(text("SELECT (date_trunc('month', CURRENT_DATE) + INTERVAL '1 month' - INTERVAL '1 day')::date"))
    if primer_dia_mes is None or ultimo_dia_mes is None:
        nuevos_este_mes = 0
    else:
        nuevos_este_mes = (
            db.scalar(
                select(func.count()).select_from(Cliente).where(
                    func.date(Cliente.fecha_registro) >= primer_dia_mes,
                    func.date(Cliente.fecha_registro) <= ultimo_dia_mes,
                )
            )
            or 0
        )"""

new = """    # Nuevos clientes registrados en el mes actual (zona Venezuela America/Caracas)
    # fecha_registro se guarda sin tz; se asume UTC en servidores cloud
    primer_dia_mes = db.scalar(text(
        "SELECT date_trunc('month', (CURRENT_TIMESTAMP AT TIME ZONE 'America/Caracas'))::date"
    ))
    ultimo_dia_mes = db.scalar(text(
        "SELECT (date_trunc('month', (CURRENT_TIMESTAMP AT TIME ZONE 'America/Caracas') + INTERVAL '1 month') - INTERVAL '1 day')::date"
    ))
    if primer_dia_mes is None or ultimo_dia_mes is None:
        nuevos_este_mes = 0
    else:
        # Comparar fecha_registro en Venezuela: (ts AT TZ UTC) AT TZ America/Caracas
        stmt = text(\"\"\"
            SELECT count(*) FROM clientes
            WHERE fecha_registro IS NOT NULL
            AND ((fecha_registro AT TIME ZONE 'UTC') AT TIME ZONE 'America/Caracas')::date >= :p1
            AND ((fecha_registro AT TIME ZONE 'UTC') AT TIME ZONE 'America/Caracas')::date <= :p2
        \"\"\")
        nuevos_este_mes = db.execute(stmt, {"p1": primer_dia_mes, "p2": ultimo_dia_mes}).scalar() or 0"""

if old in content:
    content = content.replace(old, new)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print('Replaced OK')
else:
    print('Old block not found')
    idx = content.find('primer_dia_mes')
    if idx >= 0:
        print(repr(content[idx:idx+500]))
