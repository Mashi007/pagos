"""One-off patch: fix FIFO cuotas filter in pagos.py."""
from pathlib import Path

p = Path(__file__).resolve().parents[1] / "backend" / "app" / "api" / "v1" / "endpoints" / "pagos.py"
text = p.read_text(encoding="utf-8", errors="replace")

old1 = """            .where(

                Cuota.prestamo_id == prestamo_id,

                Cuota.fecha_pago.is_(None),

                or_(Cuota.total_pagado.is_(None), Cuota.total_pagado < Cuota.monto),

            )

            .order_by(Cuota.numero_cuota.asc())  # FIFO: primero las cuotas más antiguas (numero_cuota menor), luego las siguientes"""

new1 = """            .where(
                Cuota.prestamo_id == prestamo_id,
                # Solo saldo pendiente: no exigir fecha_pago NULL. Si hay fecha_pago pero total_pagado < monto
                # (carga manual, migración o bug), excluir la cuota bloqueaba el FIFO y los pagos quedaban sin aplicar.
                or_(Cuota.total_pagado.is_(None), Cuota.total_pagado < Cuota.monto - 0.01),
            )
            .order_by(Cuota.numero_cuota.asc())  # FIFO: primero las cuotas más antiguas (numero_cuota menor), luego las siguientes"""

old2 = """            cuotas_completadas += 1

        else:

            estado_nuevo = _estado_cuota_por_cobertura(nuevo_total, monto_cuota, fecha_venc)"""

new2 = """            cuotas_completadas += 1

        else:
            # Cuota aún abierta: limpiar fecha_pago residual para no bloquear futuras aplicaciones FIFO.
            c.fecha_pago = None

            estado_nuevo = _estado_cuota_por_cobertura(nuevo_total, monto_cuota, fecha_venc)"""

old3 = """    rows = db.execute(

        select(Pago).where(

            Pago.prestamo_id == prestamo_id,

            or_(

                Pago.conciliado.is_(True),

                func.coalesce(func.upper(func.trim(Pago.verificado_concordancia)), "") == "SI",

            ),

            Pago.monto_pagado > 0,

            ~Pago.id.in_(subq),

        )

    ).scalars().all()"""

new3 = """    rows = db.execute(
        select(Pago)
        .where(
            Pago.prestamo_id == prestamo_id,
            or_(
                Pago.conciliado.is_(True),
                func.coalesce(func.upper(func.trim(Pago.verificado_concordancia)), "") == "SI",
            ),
            Pago.monto_pagado > 0,
            ~Pago.id.in_(subq),
        )
        .order_by(Pago.fecha_pago.asc().nulls_last(), Pago.id.asc())
    ).scalars().all()"""

for name, o, n in (("cuotas_pendientes", old1, new1), ("else_partial", old2, new2), ("rows_order", old3, new3)):
    if o not in text:
        raise SystemExit(f"missing block: {name}")
    text = text.replace(o, n, 1)

p.write_text(text, encoding="utf-8", newline="\n")
print("patched", p)
