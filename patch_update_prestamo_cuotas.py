# Patch: when update_prestamo sets estado to APROBADO, auto-generate cuotas if none exist
import os
path = os.path.join(os.path.dirname(__file__), "backend", "app", "api", "v1", "endpoints", "prestamos.py")
with open(path, "r", encoding="utf-8") as f:
    s = f.read()

old = """    if payload.estado is not None:
        row.estado = payload.estado
    if payload.concesionario is not None:"""
new = """    if payload.estado is not None:
        row.estado = payload.estado
    if payload.concesionario is not None:"""
# After db.commit() and db.refresh(row), before return: if estado is APROBADO and 0 cuotas, generate
old_return = """    db.commit()
    db.refresh(row)
    return PrestamoResponse.model_validate(row)


@router.delete("/{prestamo_id}", status_code=204)
def delete_prestamo(prestamo_id: int, db: Session = Depends(get_db)):"""
new_return = """    db.commit()
    db.refresh(row)
    # Si quedó en APROBADO y no tiene cuotas, generar tabla de amortización automáticamente
    if row.estado == "APROBADO":
        existentes = db.scalar(select(func.count()).select_from(Cuota).where(Cuota.prestamo_id == prestamo_id)) or 0
        if existentes == 0:
            numero_cuotas = row.numero_cuotas or 12
            total_fin = float(row.total_financiamiento or 0)
            if numero_cuotas > 0 and total_fin > 0:
                monto_cuota = _resolver_monto_cuota(row, total_fin, numero_cuotas)
                fecha_base = row.fecha_aprobacion.date() if getattr(row, "fecha_aprobacion", None) else (row.fecha_registro.date() if getattr(row, "fecha_registro", None) else hoy)
                if hasattr(fecha_base, "date") and callable(getattr(fecha_base, "date", None)):
                    fecha_base = fecha_base.date()
                _generar_cuotas_amortizacion(db, row, fecha_base, numero_cuotas, monto_cuota)
                db.commit()
                db.refresh(row)
    return PrestamoResponse.model_validate(row)


@router.delete("/{prestamo_id}", status_code=204)
def delete_prestamo(prestamo_id: int, db: Session = Depends(get_db)):"""

if "Si quedó en APROBADO y no tiene cuotas" in s:
    print("Already patched")
else:
    s = s.replace(old_return, new_return)
    with open(path, "w", encoding="utf-8") as f:
        f.write(s)
    print("Patched update_prestamo")

# Ensure update_prestamo has access to 'hoy' - it uses date.today() in create_prestamo. We need to add hoy = date.today() at start of update_prestamo or use date.today() in the patch. Let me use date.today() in the patch to avoid adding a variable.
# Actually the patch uses 'hoy' - update_prestamo might not have 'hoy' in scope. Let me fix the patch to use date.today() instead of hoy.
path = os.path.join(os.path.dirname(__file__), "backend", "app", "api", "v1", "endpoints", "prestamos.py")
with open(path, "r", encoding="utf-8") as f:
    s = f.read()
s = s.replace(
    "fecha_base = row.fecha_aprobacion.date() if getattr(row, \"fecha_aprobacion\", None) else (row.fecha_registro.date() if getattr(row, \"fecha_registro\", None) else hoy)",
    "fecha_base = row.fecha_aprobacion.date() if getattr(row, \"fecha_aprobacion\", None) else (row.fecha_registro.date() if getattr(row, \"fecha_registro\", None) else date.today())"
)
with open(path, "w", encoding="utf-8") as f:
    f.write(s)
print("Fixed hoy -> date.today()")
