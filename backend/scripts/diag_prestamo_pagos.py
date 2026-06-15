#!/usr/bin/env python3
"""Diagnóstico rápido préstamo: pagos, cuotas, cuota_pagos."""
import os
import sys

BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND)
_REPO = os.path.dirname(BACKEND)
env_path = os.path.join(_REPO, ".env")
if os.path.isfile(env_path):
    with open(env_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().replace('"', "").replace("'", ""))

from sqlalchemy import select, func, text
from app.core.database import SessionLocal
from app.models.pago import Pago
from app.models.cuota import Cuota
from app.models.cuota_pago import CuotaPago
from app.models.prestamo import Prestamo

pid = int(sys.argv[1]) if len(sys.argv) > 1 else 1535

db = SessionLocal()
try:
    p = db.get(Prestamo, pid)
    print("PRESTAMO", pid, "estado=", p.estado if p else None, "monto=", p.total_financiamiento if p else None)
    cuotas = db.execute(
        select(Cuota).where(Cuota.prestamo_id == pid).order_by(Cuota.numero_cuota)
    ).scalars().all()
    print("\nCUOTAS:")
    sum_cuotas = 0
    sum_pagado = 0
    for c in cuotas:
        m = float(c.monto or 0)
        tp = float(c.total_pagado or 0)
        sum_cuotas += m
        sum_pagado += tp
        print(f"  #{c.numero_cuota} id={c.id} monto={m} pagado={tp} estado={c.estado} venc={c.fecha_vencimiento}")
    print(f"  SUMA cuotas={sum_cuotas} total_pagado_cuotas={sum_pagado}")

    pagos = db.execute(
        select(Pago).where(Pago.prestamo_id == pid).order_by(Pago.fecha_pago, Pago.id)
    ).scalars().all()
    print("\nPAGOS:")
    sum_pagos = 0
    for pg in pagos:
        m = float(pg.monto_pagado or 0)
        sum_pagos += m
        n_cp = db.scalar(select(func.count()).select_from(CuotaPago).where(CuotaPago.pago_id == pg.id)) or 0
        sum_ap = db.scalar(
            select(func.coalesce(func.sum(CuotaPago.monto_aplicado), 0)).where(CuotaPago.pago_id == pg.id)
        ) or 0
        print(
            f"  id={pg.id} monto={m} estado={pg.estado} conciliado={pg.conciliado} "
            f"fecha={pg.fecha_pago} cp_rows={n_cp} aplicado={float(sum_ap)}"
        )
    print(f"  SUMA pagos={sum_pagos}")

    print("\nCUOTA_PAGOS (detalle):")
    for pg in pagos:
        cps = db.execute(
            select(CuotaPago, Cuota.numero_cuota)
            .join(Cuota, Cuota.id == CuotaPago.cuota_id)
            .where(CuotaPago.pago_id == pg.id)
            .order_by(CuotaPago.orden_aplicacion)
        ).all()
        if cps:
            for cp, nc in cps:
                print(f"  pago={pg.id} cuota#{nc} aplicado={cp.monto_aplicado}")

    pend = [c for c in cuotas if float(c.total_pagado or 0) < float(c.monto or 0) - 0.01]
    sin_aplicar = [pg for pg in pagos if (db.scalar(select(func.count()).select_from(CuotaPago).where(CuotaPago.pago_id == pg.id)) or 0) == 0]
    print(f"\nCuotas pendientes: {len(pend)}")
    print(f"Pagos sin cuota_pagos: {[pg.id for pg in sin_aplicar]}")
finally:
    db.close()
