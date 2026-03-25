"""
Reaplicacion en cascada integral (reset cuota_pagos + totales en cuotas + aplicar pagos) por prestamo(s).

Politica de aplicacion: cascada por numero_cuota. Script historico reaplicar_fifo_prestamo.py delega aqui.

Ejecutar desde la carpeta backend con venv activo:

  python reaplicar_cascada_prestamo.py --ids 983
  python reaplicar_cascada_prestamo.py --dry-run --ids 983,984
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.services.pagos_cuotas_reaplicacion import reset_y_reaplicar_cascada_prestamo


def main() -> None:
    ap = argparse.ArgumentParser(description="Reaplicar cascada integral por prestamo_id")
    ap.add_argument("--ids", type=str, required=True, help="Lista de prestamo_id separados por coma")
    ap.add_argument("--dry-run", action="store_true", help="No escribe en BD (solo valida que exista prestamo/cuotas)")
    args = ap.parse_args()
    ids = [int(x.strip()) for x in args.ids.split(",") if x.strip()]
    if not ids:
        print("Sin ids")
        return

    db: Session = SessionLocal()
    try:
        for pid in ids:
            if args.dry_run:
                from sqlalchemy import func, select

                from app.models.cuota import Cuota
                from app.models.prestamo import Prestamo

                p = db.get(Prestamo, pid)
                n = db.scalar(select(func.count()).select_from(Cuota).where(Cuota.prestamo_id == pid)) or 0
                print(f"prestamo_id={pid} existe={bool(p)} cuotas={n}")
                continue
            r = reset_y_reaplicar_cascada_prestamo(db, pid)
            if r.get("ok"):
                db.commit()
                print("OK", r)
            else:
                db.rollback()
                print("FAIL", r)
    finally:
        db.close()


if __name__ == "__main__":
    main()
