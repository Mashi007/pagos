"""
Corrección idempotente de desfase monto_pagado vs suma(monto_aplicado) en `cuota_pagos`.

Caso detectado por auditoría:
 - pago_id 31440: suma de monto_aplicado = 114, monto_pagado = 57
 - pago_id 31698: suma de monto_aplicado = 200, monto_pagado = 100

Regla aplicada (misma del SQL):
 - Por cada pago_id, se pone `monto_aplicado = 0` únicamente en la fila de `cuota_pagos`
   con mayor `id` (la última inserción por ese pago en el legacy/backfill).
"""

from __future__ import annotations

import argparse
import os
import sys
from decimal import Decimal

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import func, select

from app.core.database import SessionLocal
from app.models.cuota_pago import CuotaPago


def _max_cuota_pago_ids_por_pago(db, pago_ids: list[int]) -> dict[int, int]:
    # Subconsulta: para cada pago_id, obtener max(id)
    subq = (
        select(CuotaPago.pago_id, func.max(CuotaPago.id).label("max_id"))
        .where(CuotaPago.pago_id.in_(pago_ids))
        .group_by(CuotaPago.pago_id)
    )
    rows = db.execute(subq).all()
    return {int(pago_id): int(max_id) for pago_id, max_id in rows}


def main() -> None:
    ap = argparse.ArgumentParser(description="Corregir desfase en cuota_pagos por pago_id")
    ap.add_argument("--dry-run", action="store_true", help="No actualiza BD; solo muestra qué cambiaría")
    ap.add_argument(
        "--pago-ids",
        type=str,
        default="31440,31698",
        help="Lista de pago_id separados por coma (ej: 31440,31698)",
    )
    args = ap.parse_args()

    pago_ids = [int(x.strip()) for x in args.pago_ids.split(",") if x.strip()]
    if not pago_ids:
        print("No se indicaron pago_ids.")
        return

    db = SessionLocal()
    try:
        max_ids = _max_cuota_pago_ids_por_pago(db, pago_ids)
        if not max_ids:
            print("No se encontraron filas de cuota_pagos para los pago_ids indicados.")
            return

        updates = 0
        for pago_id, max_id in max_ids.items():
            row = db.get(CuotaPago, max_id)
            if not row:
                continue
            if Decimal(row.monto_aplicado) == Decimal("0"):
                continue

            if args.dry_run:
                print(f"[dry-run] pago_id={pago_id} cuota_pago_id={max_id} monto_aplicado={row.monto_aplicado} -> 0")
            else:
                row.monto_aplicado = Decimal("0")
                updates += 1
                print(f"[ok] pago_id={pago_id} cuota_pago_id={max_id} monto_aplicado={row.monto_aplicado}")

        if not args.dry_run and updates > 0:
            db.commit()
            print(f"Actualizadas {updates} fila(s) en cuota_pagos.")
        elif args.dry_run:
            print("Dry-run completado (sin cambios).")
        else:
            print("No hubo cambios (ya estaba en 0 o no existían filas).")
    finally:
        db.close()


if __name__ == "__main__":
    main()

