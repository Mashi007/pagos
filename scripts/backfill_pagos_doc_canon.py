#!/usr/bin/env python3
"""
Rellena doc_canon_numero y doc_canon_referencia en la tabla pagos.

Misma lógica que la app (normalize_documento). Ejecutar tras 041_PAGOS_DOC_CANON_COLUMNAS.sql.

Uso (raíz del repo, con DATABASE_URL / .env del backend):
  python scripts/backfill_pagos_doc_canon.py

Opcional:
  python scripts/backfill_pagos_doc_canon.py --batch 3000
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from sqlalchemy import select, update  # noqa: E402

from app.core.database import SessionLocal  # noqa: E402
from app.core.documento import normalize_documento  # noqa: E402
from app.models.pago import Pago  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--batch", type=int, default=2500, help="Filas por iteración")
    args = p.parse_args()

    db = SessionLocal()
    total = 0
    try:
        last_id = 0
        while True:
            rows = (
                db.execute(
                    select(Pago.id, Pago.numero_documento, Pago.referencia_pago)
                    .where(Pago.id > last_id)
                    .order_by(Pago.id.asc())
                    .limit(args.batch)
                )
                .all()
            )
            if not rows:
                break
            for rid, nd, rp in rows:
                cn = normalize_documento(nd)
                cr = normalize_documento(rp)
                db.execute(
                    update(Pago)
                    .where(Pago.id == rid)
                    .values(doc_canon_numero=cn, doc_canon_referencia=cr)
                )
                total += 1
                last_id = int(rid)
            db.commit()
            print(f"… actualizados hasta id={last_id} (lote +{len(rows)})", flush=True)
            if len(rows) < args.batch:
                break
    finally:
        db.close()

    print(f"Listo. Filas actualizadas: {total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
