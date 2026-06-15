#!/usr/bin/env python3
"""Documenta en observaciones del préstamo 1535 el pago anulado 48408."""
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
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

from app.core.database import SessionLocal
from app.models.prestamo import Prestamo

PRESTAMO_ID = 1535
NOTA = (
    "[REV MANUAL 2026-06-15] Pago id=48408 (600 USD, ago-2025) en ANULADO_IMPORT: "
    "duplicado; no entra en cascada ni en cartera operativa. "
    "Los 11 pagos PAGADO cubren cuotas 1-11; cuota 12 pendiente de abono real."
)


def main() -> int:
    db = SessionLocal()
    try:
        p = db.get(Prestamo, PRESTAMO_ID)
        if p is None:
            print(f"prestamo_id={PRESTAMO_ID} no encontrado")
            return 1
        obs = (p.observaciones or "").strip()
        if NOTA in obs:
            print("Ya documentado.")
            return 0
        p.observaciones = f"{obs} {NOTA}".strip() if obs else NOTA
        db.commit()
        print(f"Observaciones actualizadas en prestamo_id={PRESTAMO_ID}")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
