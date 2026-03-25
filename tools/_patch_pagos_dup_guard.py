"""Insert duplicate guard in _aplicar_pago_a_cuotas_interno before a_aplicar = min(...)."""
from pathlib import Path

p = Path(__file__).resolve().parents[1] / "backend" / "app" / "api" / "v1" / "endpoints" / "pagos.py"
text = p.read_text(encoding="utf-8", errors="replace")

old = """        monto_necesario = monto_cuota - total_pagado_actual

        if monto_restante <= 0 or monto_cuota <= 0:

            break

        a_aplicar = min(monto_restante, monto_necesario)"""

new = """        monto_necesario = monto_cuota - total_pagado_actual

        if monto_restante <= 0 or monto_cuota <= 0:

            break

        dup = db.scalar(
            select(func.count())
            .select_from(CuotaPago)
            .where(CuotaPago.cuota_id == c.id, CuotaPago.pago_id == pago.id)
        )
        if dup and int(dup) > 0:
            logger.warning(
                "Aplicacion en cascada detenida: ya existe cuota_pagos para cuota_id=%s pago_id=%s. "
                "Use POST /prestamos/{id}/reaplicar-cascada-aplicacion (compat: .../reaplicar-fifo-aplicacion) para reconstruir.",
                c.id,
                pago.id,
            )
            break

        a_aplicar = min(monto_restante, monto_necesario)"""

if "Aplicacion en cascada detenida" in text:
    print("guard already present")
elif old not in text:
    raise SystemExit("anchor not found")
else:
    text = text.replace(old, new, 1)
    p.write_text(text, encoding="utf-8", newline="\n")
    print("patched pagos.py")
