#!/usr/bin/env python3
"""Script para remover filtro Cliente.estado == ACTIVO de las 9 funciones especificadas"""

import re

# Leer el archivo
filepath = 'backend/app/api/v1/endpoints/dashboard.py'
with open(filepath, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Convertir a string para búsquedas más fáciles
content = ''.join(lines)

# 1. get_opciones_filtros (lineas 92-123)
# Remover Cliente.estado == "ACTIVO" de la consulta de analistas
content = content.replace(
    '.where(Cliente.estado == "ACTIVO", Prestamo.estado == "APROBADO", Prestamo.analista.isnot(None))',
    '.where(Prestamo.estado == "APROBADO", Prestamo.analista.isnot(None))'
)

# Remover de la consulta de concesionarios
content = content.replace(
    '.where(Cliente.estado == "ACTIVO", Prestamo.estado == "APROBADO", Prestamo.concesionario.isnot(None))',
    '.where(Prestamo.estado == "APROBADO", Prestamo.concesionario.isnot(None))'
)

# Remover de la consulta de modelos
content = content.replace(
    '.where(Cliente.estado == "ACTIVO", Prestamo.estado == "APROBADO", modelo_nombre.isnot(None))',
    '.where(Prestamo.estado == "APROBADO", modelo_nombre.isnot(None))'
)

# Actualizar docstring
content = content.replace(
    '"""Opciones para filtros desde BD: analistas, concesionarios, modelos (solo clientes ACTIVOS)."""',
    '"""Opciones para filtros desde BD: analistas, concesionarios, modelos."""'
)

# 2. _compute_kpis_principales - remover TODOS los Cliente.estado == "ACTIVO"
# Hay múltiples líneas que contienen este filtro
content = content.replace(
    '        conds = [\n            Prestamo.cliente_id == Cliente.id,\n            Cliente.estado == "ACTIVO",\n            Prestamo.estado == "APROBADO",',
    '        conds = [\n            Prestamo.cliente_id == Cliente.id,\n            Prestamo.estado == "APROBADO",'
)

content = content.replace(
    '            Cliente.estado == "ACTIVO",\n            Prestamo.estado == "APROBADO",\n            Prestamo.fecha_registro >= inicio_dt,',
    '            Prestamo.estado == "APROBADO",\n            Prestamo.fecha_registro >= inicio_dt,'
)

# Para la consulta de total_mes_actual
content = content.replace(
    '            .where(and_(\n                Cliente.estado == "ACTIVO",\n                Prestamo.estado == "APROBADO",',
    '            .where(and_(\n                Prestamo.estado == "APROBADO",'
)

# Para conds_ant
content = content.replace(
    '        conds_ant = [\n            Prestamo.cliente_id == Cliente.id,\n            Cliente.estado == "ACTIVO",\n            Prestamo.estado == "APROBADO",',
    '        conds_ant = [\n            Prestamo.cliente_id == Cliente.id,\n            Prestamo.estado == "APROBADO",'
)

# Para conds_moro
content = content.replace(
    '        conds_moro = [\n            Cuota.prestamo_id == Prestamo.id,\n            Prestamo.cliente_id == Cliente.id,\n            Cliente.estado == "ACTIVO",\n            Prestamo.estado == "APROBADO",',
    '        conds_moro = [\n            Cuota.prestamo_id == Prestamo.id,\n            Prestamo.cliente_id == Cliente.id,\n            Prestamo.estado == "APROBADO",'
)

# Para conds_moro_ant
content = content.replace(
    '        conds_moro_ant = [\n            Cuota.prestamo_id == Prestamo.id,\n            Prestamo.cliente_id == Cliente.id,\n            Cliente.estado == "ACTIVO",\n            Prestamo.estado == "APROBADO",',
    '        conds_moro_ant = [\n            Cuota.prestamo_id == Prestamo.id,\n            Prestamo.cliente_id == Cliente.id,\n            Prestamo.estado == "APROBADO",'
)

# Para conds_cuota
content = content.replace(
    '        conds_cuota = [\n            Cuota.prestamo_id == Prestamo.id,\n            Prestamo.cliente_id == Cliente.id,\n            Cliente.estado == "ACTIVO",\n            Prestamo.estado == "APROBADO",',
    '        conds_cuota = [\n            Cuota.prestamo_id == Prestamo.id,\n            Prestamo.cliente_id == Cliente.id,\n            Prestamo.estado == "APROBADO",'
)

# Actualizar docstring de kpis
content = content.replace(
    '    """Calcula KPIs principales (usado por endpoint y por refresh de cach\u00e9)."""\n    try:\n        # KPIs solo incluyen clientes ACTIVOS',
    '    """Calcula KPIs principales (usado por endpoint y por refresh de cach\u00e9)."""\n    try:'
)

# 3. get_financiamiento_tendencia_mensual (linea 702)
content = content.replace(
    '                .where(\n                    Cliente.estado == "ACTIVO",\n                    Prestamo.fecha_registro <= ultimo_dia,\n                    Prestamo.estado == "APROBADO",\n                )',
    '                .where(\n                    Prestamo.fecha_registro <= ultimo_dia,\n                    Prestamo.estado == "APROBADO",\n                )'
)

# 4. _compute_morosidad_por_dia (linea 747)
content = content.replace(
    '                .where(\n                    Cliente.estado == "ACTIVO",\n                    Prestamo.estado == "APROBADO",\n                    Cuota.fecha_vencimiento == d,\n                    Cuota.fecha_pago.is_(None),\n                )',
    '                .where(\n                    Prestamo.estado == "APROBADO",\n                    Cuota.fecha_vencimiento == d,\n                    Cuota.fecha_pago.is_(None),\n                )'
)

# 5. get_prestamos_por_concesionario
# Remover de conds_base
content = content.replace(
    '        conds_base = [\n            Cliente.estado == "ACTIVO",\n            Prestamo.estado == "APROBADO",\n            func.date(Prestamo.fecha_registro) >= inicio,\n            func.date(Prestamo.fecha_registro) <= fin,\n        ]',
    '        conds_base = [\n            Prestamo.estado == "APROBADO",\n            func.date(Prestamo.fecha_registro) >= inicio,\n            func.date(Prestamo.fecha_registro) <= fin,\n        ]'
)

# Remover de conds_acum
content = content.replace(
    '        conds_acum = [Cliente.estado == "ACTIVO", Prestamo.estado == "APROBADO"]',
    '        conds_acum = [Prestamo.estado == "APROBADO"]'
)

# 6. get_prestamos_por_modelo
# Remover de conds_base (hay uno específico para este modelo)
content = content.replace(
    '        conds_base = [\n            Cliente.estado == "ACTIVO",\n            Prestamo.estado == "APROBADO",\n            func.date(Prestamo.fecha_registro) >= inicio,\n            func.date(Prestamo.fecha_registro) <= fin,\n        ]',
    '        conds_base = [\n            Prestamo.estado == "APROBADO",\n            func.date(Prestamo.fecha_registro) >= inicio,\n            func.date(Prestamo.fecha_registro) <= fin,\n        ]'
)

# 7. _compute_financiamiento_por_rangos
content = content.replace(
    '        conds_base = [\n            Prestamo.cliente_id == Cliente.id,\n            Cliente.estado == "ACTIVO",\n            Prestamo.estado == "APROBADO",\n            Prestamo.total_financiamiento.isnot(None),\n        ]',
    '        conds_base = [\n            Prestamo.cliente_id == Cliente.id,\n            Prestamo.estado == "APROBADO",\n            Prestamo.total_financiamiento.isnot(None),\n        ]'
)

# 8. get_proyeccion_cobro_30_dias - hay dos consultas
# Primera consulta (programado)
content = content.replace(
    '            programado = db.scalar(\n                select(func.coalesce(func.sum(Cuota.monto), 0))\n                .select_from(Cuota)\n                .join(Prestamo, Cuota.prestamo_id == Prestamo.id)\n                .join(Cliente, Prestamo.cliente_id == Cliente.id)\n                .where(\n                    Cliente.estado == "ACTIVO",\n                    Prestamo.estado == "APROBADO",\n                    Cuota.fecha_vencimiento == d,\n                )\n            ) or 0',
    '            programado = db.scalar(\n                select(func.coalesce(func.sum(Cuota.monto), 0))\n                .select_from(Cuota)\n                .join(Prestamo, Cuota.prestamo_id == Prestamo.id)\n                .join(Cliente, Prestamo.cliente_id == Cliente.id)\n                .where(\n                    Prestamo.estado == "APROBADO",\n                    Cuota.fecha_vencimiento == d,\n                )\n            ) or 0'
)

# Segunda consulta (pendiente)
content = content.replace(
    '            pendiente = db.scalar(\n                select(func.coalesce(func.sum(Cuota.monto), 0))\n                .select_from(Cuota)\n                .join(Prestamo, Cuota.prestamo_id == Prestamo.id)\n                .join(Cliente, Prestamo.cliente_id == Cliente.id)\n                .where(\n                    Cliente.estado == "ACTIVO",\n                    Prestamo.estado == "APROBADO",\n                    Cuota.fecha_vencimiento == d,\n                    Cuota.fecha_pago.is_(None),\n                )\n            ) or 0',
    '            pendiente = db.scalar(\n                select(func.coalesce(func.sum(Cuota.monto), 0))\n                .select_from(Cuota)\n                .join(Prestamo, Cuota.prestamo_id == Prestamo.id)\n                .join(Cliente, Prestamo.cliente_id == Cliente.id)\n                .where(\n                    Prestamo.estado == "APROBADO",\n                    Cuota.fecha_vencimiento == d,\n                    Cuota.fecha_pago.is_(None),\n                )\n            ) or 0'
)

# 9. get_monto_programado_proxima_semana
content = content.replace(
    '            programado = db.scalar(\n                select(func.coalesce(func.sum(Cuota.monto), 0))\n                .select_from(Cuota)\n                .join(Prestamo, Cuota.prestamo_id == Prestamo.id)\n                .join(Cliente, Prestamo.cliente_id == Cliente.id)\n                .where(\n                    Cliente.estado == "ACTIVO",\n                    Prestamo.estado == "APROBADO",\n                    Cuota.fecha_vencimiento == d,\n                )\n            ) or 0\n            resultado.append({\n                "fecha": d.isoformat(),\n                "dia": f"{d.day} {nombres_mes[d.month - 1]}",\n                "monto_programado": round(_safe_float(programado), 2),\n            })',
    '            programado = db.scalar(\n                select(func.coalesce(func.sum(Cuota.monto), 0))\n                .select_from(Cuota)\n                .join(Prestamo, Cuota.prestamo_id == Prestamo.id)\n                .join(Cliente, Prestamo.cliente_id == Cliente.id)\n                .where(\n                    Prestamo.estado == "APROBADO",\n                    Cuota.fecha_vencimiento == d,\n                )\n            ) or 0\n            resultado.append({\n                "fecha": d.isoformat(),\n                "dia": f"{d.day} {nombres_mes[d.month - 1]}",\n                "monto_programado": round(_safe_float(programado), 2),\n            })'
)

# Escribir el archivo
with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print("Cambios aplicados correctamente al archivo dashboard.py")
