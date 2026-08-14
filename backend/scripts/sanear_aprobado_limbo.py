#!/usr/bin/env python3
"""
Sanea pagos_reportados en `aprobado` (limbo post-OCR) sin inventar datos.

Reglas:
  - comprobante ya en `pagos` → importado
  - recibo con datos reales cargables → intenta import existente
  - incompleto / umbral / fallo → en_revision

Uso (desde backend/, con DATABASE_URL):
  python scripts/sanear_aprobado_limbo.py --dry-run
  python scripts/sanear_aprobado_limbo.py --execute --limit 500
  python scripts/sanear_aprobado_limbo.py --execute --loops 10 --limit 120
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time

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
from app.services.cobros.saneamiento_aprobado_limbo import (
    sanear_aprobados_en_limbo,
    sanear_importados_sin_cartera_aplicada,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def main() -> int:
    ap = argparse.ArgumentParser(description="Sanear aprobado limbo post-OCR.")
    ap.add_argument("--execute", action="store_true", help="Persistir cambios.")
    ap.add_argument("--dry-run", action="store_true", help="Solo clasificar (default).")
    ap.add_argument("--limit", type=int, default=120, help="Filas por lote (1-500).")
    ap.add_argument(
        "--loops",
        type=int,
        default=1,
        help="Repetir lotes (para drenar backlog completo).",
    )
    ap.add_argument(
        "--newest-first",
        action="store_true",
        help="Procesar primero los más recientes (default: oldest-first).",
    )
    args = ap.parse_args()
    dry_run = not args.execute or args.dry_run
    loops = max(1, min(int(args.loops or 1), 100))
    limit = max(1, min(int(args.limit or 120), 500))

    totals = {
        "scanned": 0,
        "marcado_importado_colision": 0,
        "importado_auto": 0,
        "a_en_revision": 0,
        "sin_cambio": 0,
        "errores": 0,
        "dry_run": dry_run,
        "loops": [],
    }

    for i in range(loops):
        session = SessionLocal()
        try:
            res = sanear_aprobados_en_limbo(
                session,
                max_ids=limit,
                dry_run=dry_run,
                oldest_first=not args.newest_first,
                include_detalle=(loops == 1),
            )
            d = res.as_dict()
            totals["scanned"] += d["scanned"]
            totals["marcado_importado_colision"] += d["marcado_importado_colision"]
            totals["importado_auto"] += d["importado_auto"]
            totals["a_en_revision"] += d["a_en_revision"]
            totals["sin_cambio"] += d["sin_cambio"]
            totals["errores"] += d["errores"]
            totals["loops"].append(
                {
                    "loop": i + 1,
                    "scanned": d["scanned"],
                    "colision": d["marcado_importado_colision"],
                    "import_auto": d["importado_auto"],
                    "revision": d["a_en_revision"],
                    "errores": d["errores"],
                }
            )
            if d.get("detalle") and loops == 1:
                totals["detalle"] = d["detalle"]
            logger.info(
                "loop=%s scanned=%s colision=%s import=%s revision=%s",
                i + 1,
                d["scanned"],
                d["marcado_importado_colision"],
                d["importado_auto"],
                d["a_en_revision"],
            )
            if d["scanned"] == 0:
                break
            if dry_run:
                break
        finally:
            session.close()
        time.sleep(0.2)

    totals_fant = {
        "scanned": 0,
        "a_en_revision": 0,
        "errores": 0,
        "loops": [],
    }
    after_id = 0
    for i in range(loops):
        session = SessionLocal()
        try:
            fant = sanear_importados_sin_cartera_aplicada(
                session,
                max_ids=limit,
                dry_run=dry_run,
                oldest_first=not args.newest_first,
                include_detalle=(loops == 1),
                after_id=after_id,
            )
            fd = fant.as_dict()
            after_id = int(fd.get("last_id") or after_id)
            totals_fant["scanned"] += fd["scanned"]
            totals_fant["a_en_revision"] += fd["a_en_revision"]
            totals_fant["errores"] += fd["errores"]
            totals_fant["loops"].append(
                {
                    "loop": i + 1,
                    "scanned": fd["scanned"],
                    "revision": fd["a_en_revision"],
                    "errores": fd["errores"],
                }
            )
            if fd.get("detalle") and loops == 1:
                totals_fant["detalle"] = fd["detalle"]
            logger.info(
                "importado-fantasma loop=%s scanned=%s revision=%s",
                i + 1,
                fd["scanned"],
                fd["a_en_revision"],
            )
            if fd["scanned"] == 0:
                break
            if dry_run:
                break
        finally:
            session.close()
        time.sleep(0.2)

    totals["importado_fantasma"] = totals_fant
    totals["errores"] += totals_fant["errores"]

    print(json.dumps(totals, indent=2, ensure_ascii=False, default=str))
    return 0 if totals["errores"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
