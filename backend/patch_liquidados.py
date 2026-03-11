"""Patch notificaciones.py: add liquidados (total_financiamiento = total_abonos) to clientes-retrasados."""
import re

path = "app/api/v1/endpoints/notificaciones.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

old_import = "from sqlalchemy import select"
new_import = "from sqlalchemy import func, select"
if new_import not in content:
    content = content.replace(old_import, new_import)

old_return = """    # Ordenar mora_90 por dias_atraso desc, luego por cliente
    mora_90_cuotas.sort(key=lambda x: (-x["dias_atraso"], x["cedula"], x["numero_cuota"]))

    return {
        "actualizado_en": hoy.isoformat(),
        "dias_5": dias_5,
        "dias_3": dias_3,
        "dias_1": dias_1,
        "hoy": hoy_list,
        "mora_90": {
            "cuotas": mora_90_cuotas,
            "total_cuotas": len(mora_90_cuotas),
        },
    }"""

new_return = """    # Ordenar mora_90 por dias_atraso desc, luego por cliente
    mora_90_cuotas.sort(key=lambda x: (-x["dias_atraso"], x["cedula"], x["numero_cuota"]))

    # Liquidados: préstamos donde Total financiamiento = total abonos (SUM total_pagado por préstamo)
    subq = (
        select(Cuota.prestamo_id, func.coalesce(func.sum(Cuota.total_pagado), 0).label("total_abonos"))
        .group_by(Cuota.prestamo_id)
    ).subquery()
    q_liq = (
        select(Prestamo, Cliente, subq.c.total_abonos)
        .join(Cliente, Prestamo.cliente_id == Cliente.id)
        .join(subq, Prestamo.id == subq.c.prestamo_id)
        .where(Prestamo.total_financiamiento == subq.c.total_abonos)
    )
    rows_liq = db.execute(q_liq).all()
    liquidados: List[dict] = []
    for (prestamo, cliente, total_abonos) in rows_liq:
        liquidados.append({
            "cliente_id": cliente.id,
            "nombre": cliente.nombres or "",
            "cedula": cliente.cedula or "",
            "prestamo_id": prestamo.id,
            "total_financiamiento": float(prestamo.total_financiamiento) if prestamo.total_financiamiento is not None else 0,
            "total_abonos": float(total_abonos) if total_abonos is not None else 0,
        })

    return {
        "actualizado_en": hoy.isoformat(),
        "dias_5": dias_5,
        "dias_3": dias_3,
        "dias_1": dias_1,
        "hoy": hoy_list,
        "mora_90": {
            "cuotas": mora_90_cuotas,
            "total_cuotas": len(mora_90_cuotas),
        },
        "liquidados": liquidados,
    }"""

if old_return not in content:
    print("Block not found (maybe already patched or encoding)")
    exit(1)
content = content.replace(old_return, new_return)
with open(path, "w", encoding="utf-8") as f:
    f.write(content)
print("Patched notificaciones.py")
