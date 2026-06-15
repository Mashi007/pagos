#!/usr/bin/env python3
"""
Borra préstamos duplicados solo en cédulas V/E (máximo un APROBADO).

Cédulas J: pueden tener varios créditos; este script no las toca.

Criterios de borrado (V/E, sin pagos):
  - Re-importe: misma huella que un LIQUIDADO existente.
  - Más de un APROBADO en la misma cédula (sobra el de mayor id).

Uso (desde backend/, con DATABASE_URL en .env):
  python scripts/corregir_aprobados_duplicados_liquidados.py --dry-run
  python scripts/corregir_aprobados_duplicados_liquidados.py --execute

Opcional:
  python scripts/corregir_aprobados_duplicados_liquidados.py --execute --ids 9063,9185
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys

BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND not in sys.path:
    sys.path.insert(0, BACKEND)

_REPO_ROOT = os.path.dirname(BACKEND)
env_path = os.path.join(_REPO_ROOT, ".env")
if os.path.isfile(env_path):
    with open(env_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().replace('"', "").replace("'", ""))

from app.core.database import SessionLocal
from app.services.prestamos.prestamo_reimporte_liquidado import (
    corregir_aprobado_duplicado_liquidado,
    corregir_todos_aprobados_duplicados_liquidados_sin_pagos,
    listar_aprobados_duplicados_liquidados_sin_pagos,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Borrar duplicados V/E (re-importe LIQUIDADO o APROBADO extra, sin pagos)."
    )
    ap.add_argument("--execute", action="store_true", help="Persistir cambios.")
    ap.add_argument("--dry-run", action="store_true", help="Solo listar (default).")
    ap.add_argument(
        "--ids",
        type=str,
        default="",
        help="IDs de préstamos APROBADO a corregir (coma-separados). Sin esto: todos los detectados.",
    )
    args = ap.parse_args()
    dry_run = not args.execute or args.dry_run

    session = SessionLocal()
    try:
        if (args.ids or "").strip():
            id_set = {int(x.strip()) for x in args.ids.split(",") if x.strip()}
            ok_n = 0
            errs = []
            for pid in sorted(id_set):
                ok, msg = corregir_aprobado_duplicado_liquidado(
                    session, pid, dry_run=dry_run
                )
                logger.info("%s", msg)
                if ok:
                    ok_n += 1
                else:
                    errs.append({"prestamo_id": pid, "error": msg})
            if not dry_run:
                session.commit()
            print(json.dumps({"borrados_ok": ok_n, "errores": errs}, indent=2))
            return 0 if not errs else 1

        candidatos = listar_aprobados_duplicados_liquidados_sin_pagos(session)
        logger.info("Candidatos detectados: %s", len(candidatos))
        res = corregir_todos_aprobados_duplicados_liquidados_sin_pagos(
            session, dry_run=dry_run
        )
        print(json.dumps(res, indent=2, default=str))
        return 0 if not res.get("errores") else 1
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
