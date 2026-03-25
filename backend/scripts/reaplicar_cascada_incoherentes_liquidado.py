#!/usr/bin/env python3
"""
Reaplica en cascada una lista fija de prestamo_id (incoherentes LIQUIDADO vs suma cuota_pagos).
Misma logica que POST /prestamos/reaplicar-cascada-aplicacion-masiva (un commit por prestamo ok).

Uso (desde carpeta backend, con DATABASE_URL en .env):
  python scripts/reaplicar_cascada_incoherentes_liquidado.py
  python scripts/reaplicar_cascada_incoherentes_liquidado.py --dry-run
  python scripts/reaplicar_cascada_incoherentes_liquidado.py --yes   # sin pedir 'fin' (solo automatizacion/CI)

No escribe en la BD hasta que escribas la palabra fin (igual que run_verificar_cascada.py), salvo --dry-run o --yes.
"""
from __future__ import annotations

import argparse
import os
import sys

BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND not in sys.path:
    sys.path.insert(0, BACKEND)

# Lista generada desde consulta: LIQUIDADO con |total_financiamiento - sum(cuota_pagos)| > 0.01
PRESTAMO_IDS_INCOHERENTES = [
    966, 4612, 4636, 4521, 4551, 973, 4649, 12, 4634, 4638, 4650, 4430, 4503, 4629, 4645, 4640,
    4616, 4547, 4623, 4635, 4625, 4463, 4590, 4459, 4628, 2138, 4432, 4462, 4483, 4510, 4613,
    4440, 435, 4652, 4626, 4611, 4610, 62, 4525, 4487, 4478, 1779, 1975, 4411, 1, 4499, 4536,
    4533, 4466, 4606, 4615, 4425, 4, 4458, 4509, 4429, 1068, 4597, 4574, 4511, 4537, 4538, 4540,
    281, 9, 4423, 4442, 336, 1944, 1143, 4527, 4589, 4416, 4534, 4447, 4415, 4419, 4420, 4516,
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Solo listar ids, no tocar BD")
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Ejecutar sin pedir confirmacion 'fin' (usar solo si sabe lo que hace)",
    )
    args = parser.parse_args()

    try:
        from dotenv import load_dotenv

        load_dotenv(os.path.join(BACKEND, ".env"))
    except ImportError:
        pass

    if not os.environ.get("DATABASE_URL"):
        print("ERROR: DATABASE_URL no definida. Configure .env en backend o variable de entorno.", flush=True)
        return 1

    ids = sorted(set(PRESTAMO_IDS_INCOHERENTES))
    print(f"Prestamos a procesar: {len(ids)}", flush=True)

    if args.dry_run:
        print(ids, flush=True)
        return 0

    if not args.yes:
        palabra = input("Escriba fin para ejecutar la reaplicacion en cascada en la BD: ").strip().lower()
        if palabra != "fin":
            print("Cancelado: no se escribio fin.", flush=True)
            return 0

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
                    print(f"OK prestamo_id={pid} pagos_reaplicados={r.get('pagos_reaplicados')}", flush=True)
                else:
                    db.rollback()
                    err_n += 1
                    print(f"FAIL prestamo_id={pid} error={r.get('error')}", flush=True)
            except Exception as e:
                db.rollback()
                err_n += 1
                print(f"FAIL prestamo_id={pid} exception={e}", flush=True)
    finally:
        db.close()

    print(f"Resumen: ok={ok_n} errores={err_n} total={len(ids)}", flush=True)
    return 0 if err_n == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
