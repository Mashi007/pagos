#!/usr/bin/env python3
"""
Diagnostico y recuperacion parcial de casos finiquito por cedula (p. ej. V31460458).

Uso (desde backend/, con DATABASE_URL en .env):
  python scripts/diagnostico_finiquito_cedula.py V31460458
  python scripts/diagnostico_finiquito_cedula.py V31460458 --refrescar
"""
from __future__ import annotations

import argparse
import os
import sys

BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND not in sys.path:
    sys.path.insert(0, BACKEND)

env_path = os.path.join(BACKEND, ".env")
if os.path.isfile(env_path):
    with open(env_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("cedula", help="Cedula del cliente (ej. V31460458)")
    parser.add_argument(
        "--refrescar",
        action="store_true",
        help="Llama refrescar_finiquito_caso_prestamo_si_aplica por cada prestamo de la cedula",
    )
    args = parser.parse_args()
    cedula = args.cedula.strip().upper()

    from decimal import Decimal

    from sqlalchemy import func, select, text

    from app.core.database import SessionLocal
    from app.models.cuota import Cuota
    from app.models.finiquito import FiniquitoCaso
    from app.models.finiquito_conciliacion_reserva import FiniquitoConciliacionReserva
    from app.models.pago import Pago
    from app.models.prestamo import Prestamo
    from app.services.finiquito_refresh import refrescar_finiquito_caso_prestamo_si_aplica

    db = SessionLocal()
    try:
        prestamos = (
            db.execute(
                select(Prestamo)
                .where(func.upper(func.trim(Prestamo.cedula)) == cedula)
                .order_by(Prestamo.id.asc())
            )
            .scalars()
            .all()
        )
        if not prestamos:
            print(f"Sin prestamos para cedula {cedula}")
            return 1

        print(f"Cedula {cedula}: {len(prestamos)} prestamo(s)\n")
        for p in prestamos:
            pid = int(p.id)
            n_pagos = int(
                db.scalar(select(func.count()).select_from(Pago).where(Pago.prestamo_id == pid))
                or 0
            )
            sum_tp = db.scalar(
                select(func.coalesce(func.sum(Cuota.total_pagado), 0)).where(
                    Cuota.prestamo_id == pid
                )
            )
            caso = db.query(FiniquitoCaso).filter(FiniquitoCaso.prestamo_id == pid).first()
            n_reserva = int(
                db.scalar(
                    select(func.count())
                    .select_from(FiniquitoConciliacionReserva)
                    .where(FiniquitoConciliacionReserva.prestamo_id == pid)
                )
                or 0
            )
            hist = []
            if caso:
                hist = db.execute(
                    text(
                        """
                        SELECT estado_anterior, estado_nuevo, creado_en
                        FROM finiquito_estado_historial
                        WHERE caso_id = :cid
                        ORDER BY creado_en DESC
                        LIMIT 5
                        """
                    ),
                    {"cid": caso.id},
                ).fetchall()

            print(f"--- prestamo_id={pid} estado={p.estado} total_fin={p.total_financiamiento}")
            print(f"    pagos={n_pagos} sum(cuotas.total_pagado)={sum_tp} reserva_filas={n_reserva}")
            if caso:
                print(
                    f"    finiquito_caso id={caso.id} estado={caso.estado} "
                    f"sum_tp_caso={caso.sum_total_pagado}"
                )
            else:
                print("    finiquito_caso: (ninguno)")
            if hist:
                print("    historial reciente:")
                for h in hist:
                    print(f"      {h[2]}  {h[0]} -> {h[1]}")
            elif caso is None:
                print(
                    "    Si el prestamo esta LIQUIDADO y cuotas cuadran con total_financiamiento, "
                    "use --refrescar tras desplegar el fix de Visto."
                )
            if n_pagos == 0 and (sum_tp or Decimal("0")) == 0:
                print(
                    "    ALERTA: sin pagos y cuotas en cero — posible efecto del bug Visto "
                    "(restaurar pagos desde backup o recrear manualmente antes del refresh)."
                )
            print()

            if args.refrescar:
                db.flush()
                r = refrescar_finiquito_caso_prestamo_si_aplica(db, pid)
                db.commit()
                print(f"    refrescar: {r}\n")

        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
