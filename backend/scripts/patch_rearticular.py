p = "scripts/rearticular_prestamo_fifo.py"
with open(p, "r", encoding="utf-8") as f:
    c = f.read()
c = c.replace(
    "    from sqlalchemy import select",
    "    from sqlalchemy import delete, select",
)
c = c.replace(
    "session.execute(CuotaPago.__table__.delete().where(CuotaPago.cuota_id.in_(cuota_ids)))",
    "session.execute(delete(CuotaPago).where(CuotaPago.cuota_id.in_(cuota_ids)))",
)
with open(p, "w", encoding="utf-8") as f:
    f.write(c)
print("Patched")
