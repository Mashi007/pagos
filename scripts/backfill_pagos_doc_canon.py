#!/usr/bin/env python3
"""
Rellena doc_canon_numero y doc_canon_referencia en la tabla pagos.

Misma lógica que la app (normalize_documento). Ejecutar tras 041_PAGOS_DOC_CANON_COLUMNAS.sql.

Uso (raíz del repo, con DATABASE_URL / .env del backend):
  python scripts/backfill_pagos_doc_canon.py

Opcional:
  python scripts/backfill_pagos_doc_canon.py --batch 4000
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from sqlalchemy import and_, func, or_, select  # noqa: E402

from app.core.database import SessionLocal  # noqa: E402
from app.core.documento import normalize_documento  # noqa: E402
from app.models.pago import Pago  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--batch", type=int, default=4000, help="Filas por lote (bulk_update)")
    args = p.parse_args()

    db = SessionLocal()
    total = 0
    try:
        while True:
            nd_nonempty = func.trim(func.coalesce(Pago.numero_documento, "")) != ""
            rp_nonempty = func.trim(func.coalesce(Pago.referencia_pago, "")) != ""
            rows = (
                db.execute(
                    select(Pago.id, Pago.numero_documento, Pago.referencia_pago)
                    .where(
                        or_(
                            and_(Pago.doc_canon_numero.is_(None), nd_nonempty),
                            and_(Pago.doc_canon_referencia.is_(None), rp_nonempty),
                        )
                    )
                    .order_by(Pago.id.asc())
                    .limit(args.batch)
                )
                .all()
            )
            if not rows:
                break
            mappings = [
                {
                    "id": int(rid),
                    "doc_canon_numero": normalize_documento(nd),
                    "doc_canon_referencia": normalize_documento(rp),
                }
                for rid, nd, rp in rows
            ]
            db.bulk_update_mappings(Pago, mappings)
            db.commit()
            total += len(mappings)
            mx = max(m["id"] for m in mappings)
            print(f"… +{len(mappings)} filas (último id={mx}), acumulado {total}", flush=True)
    finally:
        db.close()

    print(f"Listo. Filas actualizadas en total: {total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
