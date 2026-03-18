from pathlib import Path

p = Path("app/api/v1/endpoints/cobros.py")
t = p.read_text(encoding="utf-8", errors="replace")

old = """        db.add(row)
        db.commit()
        db.refresh(row)
        _aplicar_pago_a_cuotas_interno(row, db)
        row.estado = "PAGADO"
        db.commit()
        logger.info"""

new = """        db.add(row)
        db.flush()
        db.refresh(row)
        _aplicar_pago_a_cuotas_interno(row, db)
        row.estado = "PAGADO"
        db.commit()
        logger.info"""

if old not in t:
    print("block not found")
else:
    t = t.replace(old, new, 1)
    p.write_text(t, encoding="utf-8")
    print("replaced")
