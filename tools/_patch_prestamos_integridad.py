"""Patch prestamos.py: integridad import, GET endpoint, POST response enrichment."""
from pathlib import Path

p = Path(__file__).resolve().parents[1] / "backend" / "app" / "api" / "v1" / "endpoints" / "prestamos.py"
text = p.read_text(encoding="utf-8", errors="replace")

old_imp = "from app.services.pagos_cuotas_reaplicacion import reset_y_reaplicar_fifo_prestamo\n"
new_imp = (
    "from app.services.pagos_cuotas_reaplicacion import (\n"
    "    integridad_cuotas_prestamo,\n"
    "    reset_y_reaplicar_fifo_prestamo,\n"
    ")\n"
)
if old_imp not in text:
    if new_imp in text:
        print("import already")
    else:
        raise SystemExit("import anchor missing")
else:
    text = text.replace(old_imp, new_imp, 1)

get_block = '''

@router.get("/{prestamo_id}/integridad-cuotas", response_model=dict)
def get_integridad_cuotas_prestamo(
    prestamo_id: int,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
):
    """
    Diagnostico: total_pagado vs SUM(cuota_pagos) por cuota (y diff global).
    Solo administrador. No modifica datos.
    """
    if (getattr(current_user, "rol", None) or "").lower() != "administrador":
        raise HTTPException(
            status_code=403,
            detail="Solo administracion puede consultar integridad de cuotas.",
        )
    r = integridad_cuotas_prestamo(db, prestamo_id)
    if not r.get("ok"):
        raise HTTPException(status_code=404, detail=r.get("error") or "Prestamo no encontrado")
    return r


'''

marker = '@router.post("/{prestamo_id}/reaplicar-fifo-aplicacion", response_model=dict)\n'
if marker in text and "get_integridad_cuotas_prestamo" not in text:
    text = text.replace(marker, get_block + marker, 1)
    print("inserted GET integridad")
else:
    print("skip GET (exists or marker missing)")

old_try = """    try:
        r = reset_y_reaplicar_fifo_prestamo(db, prestamo_id)
        if not r.get("ok"):
            raise HTTPException(status_code=404, detail=r.get("error") or "No se pudo reaplicar")
        db.commit()
        return {
            **r,
            "mensaje": "FIFO reaplicado: cuota_pagos reiniciado y pagos conciliados aplicados de nuevo.",
        }
"""

new_try = """    try:
        integridad_antes = integridad_cuotas_prestamo(db, prestamo_id)
        r = reset_y_reaplicar_fifo_prestamo(db, prestamo_id)
        if not r.get("ok"):
            raise HTTPException(status_code=404, detail=r.get("error") or "No se pudo reaplicar")
        db.commit()
        db.expire_all()
        integridad_despues = integridad_cuotas_prestamo(db, prestamo_id)
        return {
            **r,
            "integridad_antes": integridad_antes,
            "integridad_despues": integridad_despues,
            "mensaje": "FIFO reaplicado: cuota_pagos reiniciado y pagos conciliados aplicados de nuevo.",
        }
"""

if old_try in text:
    text = text.replace(old_try, new_try, 1)
    print("patched POST reaplicar")
else:
    print("POST block not found; manual check")

p.write_text(text, encoding="utf-8", newline="\n")
print("done")
