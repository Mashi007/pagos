# -*- coding: utf-8 -*-
"""
Clona un préstamo (mismas condiciones) + cuotas + pagos + cuota_pagos.

Uso (desde backend/):
  set DATABASE_URL=postgresql://...
  python tools/_clone_prestamo_completo.py 155

Opcional: --dry-run solo muestra conteos sin insertar.
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional

# backend/ en path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import inspect, select, text
from sqlalchemy.orm import Session


def _cols(table: str, db: Session) -> List[str]:
    insp = inspect(db.bind)
    return [c["name"] for c in insp.get_columns(table)]


def _row_as_dict(db: Session, table: str, pk_col: str, pk_val: Any) -> Optional[Dict[str, Any]]:
    cols = _cols(table, db)
    col_sql = ", ".join(f'"{c}"' for c in cols)
    r = db.execute(
        text(f'SELECT {col_sql} FROM "{table}" WHERE "{pk_col}" = :id'),
        {"id": pk_val},
    ).mappings().first()
    return dict(r) if r else None


def _insert_returning_id(
    db: Session, table: str, data: Dict[str, Any], *, id_col: str = "id"
) -> int:
    cols = [c for c in data.keys() if c != id_col]
    col_sql = ", ".join(f'"{c}"' for c in cols)
    bind_sql = ", ".join(f":{c}" for c in cols)
    params = {c: data[c] for c in cols}
    row = db.execute(
        text(
            f'INSERT INTO "{table}" ({col_sql}) VALUES ({bind_sql}) RETURNING "{id_col}"'
        ),
        params,
    ).first()
    return int(row[0])


def clone_prestamo(db: Session, prestamo_id: int, *, dry_run: bool = False) -> Dict[str, Any]:
    src = _row_as_dict(db, "prestamos", "id", prestamo_id)
    if not src:
        raise SystemExit(f"No existe prestamo id={prestamo_id}")

    cedula = (src.get("cedula") or "").strip()
    n_aprob = db.execute(
        text(
            "SELECT COUNT(*) FROM prestamos "
            "WHERE UPPER(TRIM(cedula)) = UPPER(TRIM(:c)) AND UPPER(TRIM(estado)) = 'APROBADO'"
        ),
        {"c": cedula},
    ).scalar()
    n_aprob = int(n_aprob or 0)

    cuotas = list(
        db.execute(
            text('SELECT * FROM cuotas WHERE prestamo_id = :p ORDER BY id'),
            {"p": prestamo_id},
        ).mappings()
    )
    pagos = list(
        db.execute(
            text('SELECT * FROM pagos WHERE prestamo_id = :p ORDER BY id'),
            {"p": prestamo_id},
        ).mappings()
    )
    cuota_ids = [int(c["id"]) for c in cuotas]
    pago_ids = [int(p["id"]) for p in pagos]
    cps: List[Dict[str, Any]] = []
    if cuota_ids and pago_ids:
        cps = list(
            db.execute(
                text(
                    "SELECT * FROM cuota_pagos "
                    "WHERE cuota_id = ANY(:cids) AND pago_id = ANY(:pids) "
                    "ORDER BY id"
                ),
                {"cids": cuota_ids, "pids": pago_ids},
            ).mappings()
        )

    resumen = {
        "origen_id": prestamo_id,
        "cedula": cedula,
        "estado": src.get("estado"),
        "aprobados_misma_cedula_antes": n_aprob,
        "cuotas": len(cuotas),
        "pagos": len(pagos),
        "cuota_pagos": len(cps),
        "dry_run": dry_run,
    }
    if dry_run:
        return resumen

    # --- prestamo ---
    nuevo = dict(src)
    nuevo.pop("id", None)
    nota = f"[CLONE_DE_PRESTAMO_{prestamo_id} {datetime.utcnow().date().isoformat()}]"
    obs = (nuevo.get("observaciones") or "").strip()
    nuevo["observaciones"] = (f"{obs} {nota}".strip() if obs else nota)[:2000]
    # Evitar chocar con campos de gestión de finiquito del original
    for k in (
        "estado_gestion_finiquito",
        "finiquito_tramite_fecha_limite",
        "fecha_liquidado",
    ):
        if k in nuevo:
            nuevo[k] = None

    new_pid = _insert_returning_id(db, "prestamos", nuevo)

    # --- cuotas ---
    map_cuota: Dict[int, int] = {}
    for c in cuotas:
        old_id = int(c["id"])
        row = dict(c)
        row.pop("id", None)
        row["prestamo_id"] = new_pid
        # pago_id se reasigna después
        row["pago_id"] = None
        new_cid = _insert_returning_id(db, "cuotas", row)
        map_cuota[old_id] = new_cid

    # --- pagos ---
    map_pago: Dict[int, int] = {}
    for p in pagos:
        old_id = int(p["id"])
        row = dict(p)
        row.pop("id", None)
        row["prestamo_id"] = new_pid
        # notas de trazabilidad
        prev = (row.get("notas") or "").strip()
        tag = f"[CLONE_DE_PAGO_{old_id} PRESTAMO_{prestamo_id}]"
        row["notas"] = (f"{prev} {tag}".strip() if prev else tag)[:2000]
        new_pago_id = _insert_returning_id(db, "pagos", row)
        map_pago[old_id] = new_pago_id

    # --- cuota.pago_id ---
    for c in cuotas:
        old_cid = int(c["id"])
        old_pago = c.get("pago_id")
        if old_pago is None:
            continue
        new_cid = map_cuota[old_cid]
        new_pago = map_pago.get(int(old_pago))
        if new_pago is None:
            continue
        db.execute(
            text('UPDATE cuotas SET pago_id = :pid WHERE id = :cid'),
            {"pid": new_pago, "cid": new_cid},
        )

    # --- cuota_pagos ---
    for cp in cps:
        row = dict(cp)
        row.pop("id", None)
        old_c = int(row["cuota_id"])
        old_p = int(row["pago_id"])
        if old_c not in map_cuota or old_p not in map_pago:
            continue
        row["cuota_id"] = map_cuota[old_c]
        row["pago_id"] = map_pago[old_p]
        _insert_returning_id(db, "cuota_pagos", row)

    db.commit()
    resumen["nuevo_prestamo_id"] = new_pid
    resumen["aprobados_misma_cedula_despues"] = n_aprob + (
        1 if str(src.get("estado") or "").upper() == "APROBADO" else 0
    )
    return resumen


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("prestamo_id", type=int)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not os.environ.get("DATABASE_URL"):
        raise SystemExit("Falta DATABASE_URL en el entorno.")

    from app.core.database import SessionLocal

    db = SessionLocal()
    try:
        out = clone_prestamo(db, args.prestamo_id, dry_run=args.dry_run)
        print(out)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
