# -*- coding: utf-8 -*-
"""Fix prestamos stats - use BETWEEN with bindparams (text>=date fails)."""
path = 'backend/app/api/v1/endpoints/prestamos.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

old = """    # Fecha de referencia en Venezuela (fecha_* guardados sin tz, asumimos UTC)
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

new = """    # Fecha de referencia en Venezuela (fecha_* sin tz, asumimos UTC)
    # Solo clientes ACTIVOS (consistente con dashboard, pagos, reportes)
    _cond_fecha = text(
        "((COALESCE(prestamos.fecha_aprobacion, prestamos.fecha_registro) "
        "AT TIME ZONE 'UTC') AT TIME ZONE 'America/Caracas')::date BETWEEN :inicio AND :fin"
    ).bindparams(inicio=inicio_mes, fin=fin_mes)
    q_base = (
        select(Prestamo)
        .join(Cliente, Prestamo.cliente_id == Cliente.id)
        .where(
            Cliente.estado == "ACTIVO",
            Prestamo.estado == "APROBADO",
            _cond_fecha,
        )
    )"""

old2 = """    q_estado = (
        select(Prestamo.estado, func.count())
        .select_from(Prestamo)
        .join(Cliente, Prestamo.cliente_id == Cliente.id)
        .where(
            Cliente.estado == "ACTIVO",
            _fecha_ref_vez >= inicio_mes,
            _fecha_ref_vez <= fin_mes,
        )
    )"""

new2 = """    _cond_fecha2 = text(
        "((COALESCE(prestamos.fecha_aprobacion, prestamos.fecha_registro) "
        "AT TIME ZONE 'UTC') AT TIME ZONE 'America/Caracas')::date BETWEEN :inicio AND :fin"
    ).bindparams(inicio=inicio_mes, fin=fin_mes)
    q_estado = (
        select(Prestamo.estado, func.count())
        .select_from(Prestamo)
        .join(Cliente, Prestamo.cliente_id == Cliente.id)
        .where(
            Cliente.estado == "ACTIVO",
            _cond_fecha2,
        )
    )"""

content = content.replace(old, new)
content = content.replace(old2, new2)
with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
print("Done")
