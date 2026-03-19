"""
Backfill de trazabilidad: crea filas en cuota_pagos para cuotas legacy que tienen
total_pagado y pago_id pero ninguna fila en cuota_pagos.

Reglas: ver sql/backfill_cuota_pagos.sql.

Uso (desde backend, con venv activo):
  python scripts/backfill_cuota_pagos.py --dry-run       # solo cuenta y muestra muestra
  python scripts/backfill_cuota_pagos.py                 # ejecuta todo
  python scripts/backfill_cuota_pagos.py --limit 100     # máximo 100 cuotas
"""
import argparse
import os
import sys
from datetime import datetime, time
from decimal import Decimal
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.cuota import Cuota
from app.models.cuota_pago import CuotaPago
from app.models.pago import Pago

TZ = "America/Caracas"


def _fecha_aplicacion(cuota: Cuota, pago: Pago) -> datetime:
    if pago.fecha_pago:
        dt = pago.fecha_pago
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=ZoneInfo(TZ))
        return dt
    if cuota.fecha_pago:
        return datetime.combine(cuota.fecha_pago, time.min, tzinfo=ZoneInfo(TZ))
    return datetime.now(ZoneInfo(TZ))


def cuotas_sin_trazabilidad(db: Session, limit: int | None = None):
    """Cuotas con total_pagado > 0, pago_id NOT NULL y sin filas en cuota_pagos."""
    subq = select(CuotaPago.cuota_id).distinct()
    q = (
        select(Cuota)
        .join(Pago, Pago.id == Cuota.pago_id)
        .where(
            Cuota.total_pagado.isnot(None),
            Cuota.total_pagado > 0,
            Cuota.pago_id.isnot(None),
            ~Cuota.id.in_(subq),
        )
        .order_by(Cuota.id)
    )
    if limit is not None:
        q = q.limit(limit)
    return db.execute(q).scalars().all()


def main():
    ap = argparse.ArgumentParser(description="Backfill cuota_pagos desde cuotas legacy")
    ap.add_argument("--dry-run", action="store_true", help="Solo listar, no insertar")
    ap.add_argument("--limit", type=int, default=None, help="Máximo número de cuotas a procesar")
    args = ap.parse_args()

    db = SessionLocal()
    try:
        cuotas = cuotas_sin_trazabilidad(db, limit=args.limit)
        n = len(cuotas)
        print(f"Cuotas elegibles para backfill: {n}")
        if n == 0:
            return

        if args.dry_run:
            print("(dry-run: no se inserta nada)")
            for c in cuotas[:10]:
                p = db.get(Pago, c.pago_id)
                print(f"  cuota_id={c.id} prestamo_id={c.prestamo_id} numero_cuota={c.numero_cuota} pago_id={c.pago_id} total_pagado={c.total_pagado} monto_cuota={c.monto}")
            if n > 10:
                print(f"  ... y {n - 10} más")
            return

        insertados = 0
        for cuota in cuotas:
            pago = db.get(Pago, cuota.pago_id)
            if not pago:
                print(f"  [skip] cuota_id={cuota.id}: pago_id={cuota.pago_id} no existe")
                continue
            monto_cuota = float(cuota.monto) if cuota.monto is not None else 0
            total_pagado = float(cuota.total_pagado or 0)
            es_completo = total_pagado >= monto_cuota - 0.01
            row = CuotaPago(
                cuota_id=cuota.id,
                pago_id=cuota.pago_id,
                monto_aplicado=Decimal(str(round(total_pagado, 2))),
                fecha_aplicacion=_fecha_aplicacion(cuota, pago),
                orden_aplicacion=0,
                es_pago_completo=es_completo,
            )
            db.add(row)
            insertados += 1
        db.commit()
        print(f"Insertadas {insertados} filas en cuota_pagos.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
