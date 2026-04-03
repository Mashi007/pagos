#!/usr/bin/env python3
"""
Reaplica cascada (reset cuota_pagos + aplicar pagos) para cada prestamo_id dado.
Misma logica que POST /api/v1/prestamos/reaplicar-cascada-aplicacion-masiva.

Uso (desde carpeta backend, DATABASE_URL en .env):
  python scripts/reaplicar_cascada_prestamo_ids.py 201 255 274
"""
from __future__ import annotations

import os
import sys

BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND not in sys.path:
    sys.path.insert(0, BACKEND)


def main() -> int:
    if len(sys.argv) < 2:
        print("Uso: python scripts/reaplicar_cascada_prestamo_ids.py <prestamo_id> [prestamo_id ...]", flush=True)
        return 1

    try:
        from dotenv import load_dotenv

        load_dotenv(os.path.join(BACKEND, ".env"))
        if not os.environ.get("DATABASE_URL"):
            load_dotenv(os.path.join(os.path.dirname(BACKEND), ".env"))
    except ImportError:
        pass

    ids: list[int] = []
    for a in sys.argv[1:]:
        try:
            ids.append(int(a))
        except ValueError:
            print(f"prestamo_id invalido: {a}", flush=True)
            return 1

    from app.core.database import SessionLocal
    from app.services.pagos_cuotas_reaplicacion import reset_y_reaplicar_cascada_prestamo

    db = SessionLocal()
    ok_n = 0
    err_n = 0
    try:
        for pid in ids:
            try:
                r = reset_y_reaplicar_cascada_prestamo(db, pid)
                if r.get("ok"):
                    db.commit()
                    ok_n += 1
                    print(
                        f"OK prestamo_id={pid} pagos_reaplicados={r.get('pagos_reaplicados')}",
                        flush=True,
                    )
                else:
                    db.rollback()
                    err_n += 1
                    print(f"FAIL prestamo_id={pid} {r}", flush=True)
            except Exception as e:
                db.rollback()
                err_n += 1
                print(f"ERR prestamo_id={pid} {e}", flush=True)
    finally:
        db.close()

    print(f"Resumen: ok={ok_n} errores={err_n}", flush=True)
    return 0 if err_n == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
