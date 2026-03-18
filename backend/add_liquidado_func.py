from pathlib import Path

p = Path("app/api/v1/endpoints/pagos.py")
t = p.read_text(encoding="utf-8", errors="replace")

needle = "def _aplicar_pago_a_cuotas_interno(pago: Pago, db: Session) -> tuple[int, int]:\n    \"\"\"\n    Aplica el monto del pago a cuotas del prAcstamo. Reglas de negocio."

insert = """def _marcar_prestamo_liquidado_si_corresponde(prestamo_id: int, db: Session) -> None:
    \"\"\"Si todas las cuotas del prestamo estan pagadas, actualiza prestamo.estado a LIQUIDADO. No hace commit.\"\"\"
    cuotas = db.execute(select(Cuota).where(Cuota.prestamo_id == prestamo_id)).scalars().all()
    if not cuotas:
        return
    pendientes = sum(1 for c in cuotas if (c.total_pagado or 0) < (float(c.monto) if c.monto else 0) - 0.01)
    if pendientes == 0:
        prestamo = db.execute(select(Prestamo).where(Prestamo.id == prestamo_id)).scalars().first()
        if prestamo and (prestamo.estado or "").upper() == "APROBADO":
            prestamo.estado = "LIQUIDADO"
            logger.info("Prestamo id=%s marcado como LIQUIDADO (todas las cuotas pagadas).", prestamo_id)


"""

if "def _marcar_prestamo_liquidado_si_corresponde" in t:
    print("already there")
else:
    t = t.replace(needle, insert + needle, 1)
    p.write_text(t, encoding="utf-8")
    print("inserted")
