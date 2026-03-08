# -*- coding: utf-8 -*-
"""Fix prestamos stats to use America/Caracas timezone."""
path = 'backend/app/api/v1/endpoints/prestamos.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Fix the "when mes/anio not provided" block - use America/Caracas
old1 = """    else:
        primer_dia_mes = db.scalar(text("SELECT date_trunc('month', CURRENT_DATE)::date"))
        ultimo_dia_mes = db.scalar(text("SELECT (date_trunc('month', CURRENT_DATE) + INTERVAL '1 month' - INTERVAL '1 day')::date"))"""

new1 = """    else:
        # Zona Venezuela para coincidir con negocio
        primer_dia_mes = db.scalar(text(
            "SELECT date_trunc('month', (CURRENT_TIMESTAMP AT TIME ZONE 'America/Caracas'))::date"
        ))
        ultimo_dia_mes = db.scalar(text(
            "SELECT (date_trunc('month', (CURRENT_TIMESTAMP AT TIME ZONE 'America/Caracas') + INTERVAL '1 month') - INTERVAL '1 day')::date"
        ))"""

# 2. Replace fecha_ref with Venezuela-date version (UTC -> America/Caracas)
old2 = """    # Fecha de referencia: aprobaci\u00f3n o registro (para "aprobados en el mes")
    # Solo clientes ACTIVOS (consistente con dashboard, pagos, reportes)
    fecha_ref = func.coalesce(func.date(Prestamo.fecha_aprobacion), func.date(Prestamo.fecha_registro))
    q_base = (
        select(Prestamo)
        .join(Cliente, Prestamo.cliente_id == Cliente.id)
        .where(
            Cliente.estado == "ACTIVO",
            Prestamo.estado == "APROBADO",
            fecha_ref >= inicio_mes,
            fecha_ref <= fin_mes,
        )
    )"""

new2 = """    # Fecha de referencia en Venezuela (fecha_* guardados sin tz, asumimos UTC)
    # Solo clientes ACTIVOS (consistente con dashboard, pagos, reportes)
    _fecha_ref_vez = text(
        "((COALESCE(prestamos.fecha_aprobacion, prestamos.fecha_registro) "
        "AT TIME ZONE 'UTC') AT TIME ZONE 'America/Caracas')::date"
    )
    q_base = (
        select(Prestamo)
        .join(Cliente, Prestamo.cliente_id == Cliente.id)
        .where(
            Cliente.estado == "ACTIVO",
            Prestamo.estado == "APROBADO",
            _fecha_ref_vez >= inicio_mes,
            _fecha_ref_vez <= fin_mes,
        )
    )"""

# For q_estado we also use fecha_ref - need to replace with _fecha_ref_vez
old3 = """    q_estado = (
        select(Prestamo.estado, func.count())
        .select_from(Prestamo)
        .join(Cliente, Prestamo.cliente_id == Cliente.id)
        .where(
            Cliente.estado == "ACTIVO",
            fecha_ref >= inicio_mes,
            fecha_ref <= fin_mes,
        )
    )"""

new3 = """    q_estado = (
        select(Prestamo.estado, func.count())
        .select_from(Prestamo)
        .join(Cliente, Prestamo.cliente_id == Cliente.id)
        .where(
            Cliente.estado == "ACTIVO",
            _fecha_ref_vez >= inicio_mes,
            _fecha_ref_vez <= fin_mes,
        )
    )"""

if old1 in content:
    content = content.replace(old1, new1)
    print("Replaced 1 OK")
else:
    print("Old1 not found")

if old2 in content:
    content = content.replace(old2, new2)
    print("Replaced 2 OK")
else:
    print("Old2 not found")

if old3 in content:
    content = content.replace(old3, new3)
    print("Replaced 3 OK")
else:
    print("Old3 not found")

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
