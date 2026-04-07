#!/usr/bin/env python3
"""
Marca como conciliados los pagos con conciliado = false y alinea cartera:
- Si el pago ya tiene filas en cuota_pagos: solo sincroniza banderas (conciliado, fecha_conciliacion, verificado_concordancia, estado PAGADO).
- Si no: concilia y ejecuta la misma cascada que POST /pagos/{id}/aplicar-cuotas.

Uso (desde la carpeta backend, con .env y DATABASE_URL):
  python scripts/conciliar_pagos_no_conciliados.py --dry-run
  python scripts/conciliar_pagos_no_conciliados.py --execute

Opcional: limitar a IDs concretos:
  python scripts/conciliar_pagos_no_conciliados.py --execute --ids 61050,61053
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
from datetime import datetime

from zoneinfo import ZoneInfo

# Añadir backend al path para imports de app
BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND not in sys.path:
    sys.path.insert(0, BACKEND)

# Cargar env si existe (raíz del repo)
_REPO_ROOT = os.path.dirname(BACKEND)
env_path = os.path.join(_REPO_ROOT, ".env")
if os.path.isfile(env_path):
    with open(env_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().replace('"', "").replace("'", ""))

from sqlalchemy import or_, select

from app.api.v1.endpoints.pagos import (
    TZ_NEGOCIO,
    _aplicar_pago_a_cuotas_interno,
    _estado_conciliacion_post_cascada,
)
from app.core.database import SessionLocal
from app.models.pago import Pago
from app.services.cuota_pago_integridad import pago_tiene_aplicaciones_cuotas

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

_EXCL_ESTADOS = frozenset(
    {"DUPLICADO", "ANULADO_IMPORT", "CANCELADO", "RECHAZADO", "REVERSADO"}
)


def _estado_upper(pago: Pago) -> str:
    return str(getattr(pago, "estado", "") or "").strip().upper()


def main() -> int:
    ap = argparse.ArgumentParser(description="Conciliar pagos no conciliados y aplicar a cuotas.")
    ap.add_argument("--execute", action="store_true", help="Persistir cambios (sin esto solo lista).")
    ap.add_argument("--dry-run", action="store_true", help="Solo informar (equivale a no --execute).")
    ap.add_argument("--ids", type=str, default="", help="Lista opcional de id separados por coma.")
    args = ap.parse_args()
    execute = bool(args.execute) and not args.dry_run

    id_set: set[int] | None = None
    if (args.ids or "").strip():
        id_set = set()
        for part in args.ids.split(","):
            part = part.strip()
            if part:
                id_set.add(int(part))

    session = SessionLocal()
    try:
        q = select(Pago).where(or_(Pago.conciliado.is_(False), Pago.conciliado.is_(None)))
        if id_set is not None:
            q = q.where(Pago.id.in_(id_set))
        q = q.order_by(Pago.fecha_pago.asc().nulls_last(), Pago.id.asc())
        pagos = session.execute(q).scalars().all()

        if not pagos:
            logger.info("No hay pagos pendientes de conciliación con los filtros dados.")
            return 0

        ahora = datetime.now(ZoneInfo(TZ_NEGOCIO))
        ok = 0
        skipped = 0
        errores: list[tuple[int, str]] = []

        for pago in pagos:
            est = _estado_upper(pago)
            if est in _EXCL_ESTADOS:
                logger.info("Omitido id=%s estado=%s (excluido)", pago.id, est)
                skipped += 1
                continue

            try:
                with session.begin_nested():
                    if pago_tiene_aplicaciones_cuotas(session, pago.id):
                        pago.estado = "PAGADO"
                        pago.conciliado = True
                        pago.verificado_concordancia = "SI"
                        pago.fecha_conciliacion = ahora
                        logger.info(
                            "id=%s: ya tenía cuota_pagos; banderas sincronizadas.",
                            pago.id,
                        )
                    else:
                        # No poner conciliado=true antes de aplicar: el CHECK en BD prohíbe
                        # conciliado con estado PENDIENTE; el flush del savepoint interno fallaría.
                        cc, cp = _aplicar_pago_a_cuotas_interno(pago, session)
                        pago.estado = _estado_conciliacion_post_cascada(pago, cc, cp)
                        if str(pago.estado or "").upper() == "PAGADO":
                            pago.conciliado = True
                            pago.verificado_concordancia = "SI"
                            pago.fecha_conciliacion = ahora
                        logger.info(
                            "id=%s: aplicado cc=%s cp=%s estado=%s conciliado=%s",
                            pago.id,
                            cc,
                            cp,
                            pago.estado,
                            pago.conciliado,
                        )
                ok += 1
            except Exception as e:
                errores.append((pago.id, str(e)))
                logger.exception("Fallo id=%s: %s", pago.id, e)

        if execute:
            session.commit()
            logger.info("Commit: procesados_ok=%s omitidos=%s errores=%s", ok, skipped, len(errores))
        else:
            session.rollback()
            logger.info(
                "Dry-run (sin commit): habría procesado_ok=%s omitidos=%s errores=%s. "
                "Use --execute para guardar.",
                ok,
                skipped,
                len(errores),
            )

        for pid, msg in errores[:50]:
            logger.error("Error pago_id=%s: %s", pid, msg)
        if len(errores) > 50:
            logger.error("... y %s errores más.", len(errores) - 50)

        return 0 if not errores else 1
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
