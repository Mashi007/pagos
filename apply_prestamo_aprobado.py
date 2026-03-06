# Apply: préstamos de carga masiva con estado APROBADO y fecha_aprobacion = fecha_requerimiento
import os
base = os.path.dirname(os.path.abspath(__file__))

# 1) Schema: add aprobado_por_carga_masiva to PrestamoCreate
schema_path = os.path.join(base, "backend", "app", "schemas", "prestamo.py")
with open(schema_path, "r", encoding="utf-8") as f:
    s = f.read()
if "aprobado_por_carga_masiva" not in s:
    s = s.replace(
        'class PrestamoCreate(PrestamoBase):\n    """Campos para crear préstamo.',
        'class PrestamoCreate(PrestamoBase):\n    """Campos para crear préstamo.'
    )
    # Insert after the docstring line of PrestamoCreate
    old = 'class PrestamoCreate(PrestamoBase):\n    """Campos para crear préstamo. cedula/nombres se rellenan desde Cliente si no se envían."""\n\n\nclass PrestamoUpdate'
    new = 'class PrestamoCreate(PrestamoBase):\n    """Campos para crear préstamo. cedula/nombres se rellenan desde Cliente si no se envían."""\n    aprobado_por_carga_masiva: Optional[bool] = False  # Si True: estado=APROBADO, fecha_aprobacion=fecha_requerimiento\n\n\nclass PrestamoUpdate'
    if old in s:
        s = s.replace(old, new)
        with open(schema_path, "w", encoding="utf-8") as f:
            f.write(s)
        print("Schema: aprobado_por_carga_masiva added")
    else:
        print("Schema: pattern not found", repr(s[:200]))
else:
    print("Schema: already has aprobado_por_carga_masiva")

# 2) Endpoint: create_prestamo - estado APROBADO and fecha_aprobacion when aprobado_por_carga_masiva
ep_path = os.path.join(base, "backend", "app", "api", "v1", "endpoints", "prestamos.py")
with open(ep_path, "r", encoding="utf-8") as f:
    s = f.read()

# Add time to datetime import
if "from datetime import date, datetime, timedelta" in s and ", time" not in s:
    s = s.replace("from datetime import date, datetime, timedelta", "from datetime import date, datetime, timedelta, time")
    print("Endpoint: added time to import")
elif "from datetime import date, datetime, timedelta, time" in s:
    print("Endpoint: time already in import")
else:
    print("Endpoint: datetime import not found as expected")

# Replace the block that builds row = Prestamo(...)
old_block = """    row = Prestamo(
        cliente_id=payload.cliente_id,
        cedula=cliente.cedula or "",
        nombres=cliente.nombres or "",
        total_financiamiento=payload.total_financiamiento,
        fecha_requerimiento=payload.fecha_requerimiento or hoy,
        modalidad_pago=payload.modalidad_pago or "MENSUAL",
        numero_cuotas=payload.numero_cuotas or 12,
        cuota_periodo=payload.cuota_periodo or 0,
        producto=payload.producto or "Financiamiento",
        estado=payload.estado or "DRAFT",
        concesionario=payload.concesionario,
        modelo_vehiculo=payload.modelo,
        analista=payload.analista or "",
        usuario_proponente=usuario_proponente_email,
    )"""

fecha_req_var = "    fecha_req = payload.fecha_requerimiento or hoy\n"
estado_var = "    estado_inicial = \"APROBADO\" if getattr(payload, \"aprobado_por_carga_masiva\", False) else (payload.estado or \"DRAFT\")\n"
fecha_aprob_var = "    fecha_aprob = datetime.combine(fecha_req, time.min) if getattr(payload, \"aprobado_por_carga_masiva\", False) else None\n"
new_block = fecha_req_var + estado_var + fecha_aprob_var + """    row = Prestamo(
        cliente_id=payload.cliente_id,
        cedula=cliente.cedula or "",
        nombres=cliente.nombres or "",
        total_financiamiento=payload.total_financiamiento,
        fecha_requerimiento=payload.fecha_requerimiento or hoy,
        modalidad_pago=payload.modalidad_pago or "MENSUAL",
        numero_cuotas=payload.numero_cuotas or 12,
        cuota_periodo=payload.cuota_periodo or 0,
        producto=payload.producto or "Financiamiento",
        estado=estado_inicial,
        fecha_aprobacion=fecha_aprob,
        concesionario=payload.concesionario,
        modelo_vehiculo=payload.modelo,
        analista=payload.analista or "",
        usuario_proponente=usuario_proponente_email,
    )"""

if old_block in s and "estado_inicial" not in s:
    s = s.replace(old_block, new_block)
    with open(ep_path, "w", encoding="utf-8") as f:
        f.write(s)
    print("Endpoint: create_prestamo updated (estado APROBADO, fecha_aprobacion)")
else:
    if "estado_inicial" in s:
        print("Endpoint: already updated")
    else:
        print("Endpoint: Prestamo(...) block not found")

# 3) Frontend: useExcelUploadPrestamos - add aprobado_por_carga_masiva: true to prestamoData
fe_path = os.path.join(base, "frontend", "src", "hooks", "useExcelUploadPrestamos.ts")
with open(fe_path, "r", encoding="utf-8") as f:
    s = f.read()
old_fe = "          numero_cuotas: numCuotas,\n          cuota_periodo: cuotaPeriodo,\n          tasa_interes: row.tasa_interes != null ? Number(row.tasa_interes) : 0,\n          observaciones: (row.observaciones || '').trim() || undefined,\n          estado: 'DRAFT',\n        }"
new_fe = "          numero_cuotas: numCuotas,\n          cuota_periodo: cuotaPeriodo,\n          tasa_interes: row.tasa_interes != null ? Number(row.tasa_interes) : 0,\n          observaciones: (row.observaciones || '').trim() || undefined,\n          aprobado_por_carga_masiva: true,\n        }"
if old_fe in s:
    s = s.replace(old_fe, new_fe)
    with open(fe_path, "w", encoding="utf-8") as f:
        f.write(s)
    print("Frontend: aprobado_por_carga_masiva: true added")
else:
    if "aprobado_por_carga_masiva" in s:
        print("Frontend: already has aprobado_por_carga_masiva")
    else:
        print("Frontend: pattern not found")

print("Done.")
