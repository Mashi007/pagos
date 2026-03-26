from pathlib import Path

p = Path(__file__).resolve().parents[1] / "backend" / "app" / "api" / "v1" / "endpoints" / "prestamos.py"
t = p.read_text(encoding="utf-8")
old = """        # Al desvincular pagos, prestamo_id pasa a NULL; chk_pagos_prestamo_id_not_null exige
        # estado = ANULADO_IMPORT cuando no hay prestamo (mismo criterio que FK ON DELETE SET NULL).
        db.execute(
            update(Pago)
            .where(Pago.prestamo_id == prestamo_id)
            .values(prestamo_id=None, estado="ANULADO_IMPORT")
        )"""
new = """        # Al desvincular pagos, prestamo_id pasa a NULL; chk_pagos_prestamo_id_not_null exige
        # estado = ANULADO_IMPORT cuando no hay prestamo (mismo criterio que FK ON DELETE SET NULL).
        # Dos pasos en SQL crudo: evita PAGADO + prestamo_id NULL si el FK SET NULL actua sin estado.
        db.execute(
            text("UPDATE pagos SET estado = :estado WHERE prestamo_id = :pid"),
            {"estado": "ANULADO_IMPORT", "pid": prestamo_id},
        )
        db.execute(
            text("UPDATE pagos SET prestamo_id = NULL WHERE prestamo_id = :pid"),
            {"pid": prestamo_id},
        )"""
if old not in t:
    raise SystemExit("old block not found")
p.write_text(t.replace(old, new), encoding="utf-8")
print("patched", p)
