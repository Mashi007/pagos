#!/usr/bin/env python3
"""
Marca como conciliados los pagos con conciliado = false y alinea cartera:
- Si el pago ya tiene filas en cuota_pagos: solo sincroniza banderas (conciliado, fecha_conciliacion, verificado_concordancia, estado PAGADO).
- Si no: concilia y ejecuta la misma cascada que POST /pagos/{id}/aplicar-cuotas.

Uso (desde la carpeta backend, con .env y DATABASE_URL):
  python scripts/conciliar_pagos_no_conciliados.py --dry-run
  python scripts/conciliar_pagos_no_conciliados.py --execute

Opcional: limitar a IDs o a un préstamo:
  python scripts/conciliar_pagos_no_conciliados.py --execute --ids 61050,61053
  python scripts/conciliar_pagos_no_conciliados.py --execute --prestamo-id 201

Qué NO hace el script (huecos conocidos):
- No arregla duplicados ni sobrepagos: si no hay saldo pendiente en cuotas, el pago
  sigue PENDIENTE y conciliado=false (CHECK de BD).
- No escribe usuario_registro / bitácora de negocio (solo banderas y cascada).
- No usa FIFO de replay de todo el préstamo; solo cascada por pago (política producto).
- No concilia por Excel como /pagos/conciliacion/upload.

Pagos que sigan PENDIENTE tras ejecutar: revisión operativa y aplicar-cuotas por pago;
no replay FIFO del préstamo salvo excepción explícita de negocio.
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
from app.services.cuota_pago_integridad import (
    pago_tiene_aplicaciones_cuotas,
    validar_suma_aplicada_vs_monto_pago,
)

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
    ap.add_argument(
        "--prestamo-id",
        type=int,
        default=None,
        metavar="ID",
        help="Solo pagos de este préstamo (además del filtro conciliado=false).",
    )
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
        if args.prestamo_id is not None:
            q = q.where(Pago.prestamo_id == args.prestamo_id)
        q = q.order_by(Pago.fecha_pago.asc().nulls_last(), Pago.id.asc())
        pagos = session.execute(q).scalars().all()

        if not pagos:
            logger.info("No hay pagos pendientes de conciliación con los filtros dados.")
            return 0

        ahora = datetime.now(ZoneInfo(TZ_NEGOCIO))
        ok = 0
        skipped = 0
        errores: list[tuple[int, str]] = []
        stats = {
            "banderas_sincronizadas": 0,
            "conciliado_tras_cascada": 0,
            "sin_cambio_sigue_pendiente": 0,
        }

        for pago in pagos:
            est = _estado_upper(pago)
            if est in _EXCL_ESTADOS:
                logger.info("Omitido id=%s estado=%s (excluido)", pago.id, est)
                skipped += 1
                continue

            try:
                with session.begin_nested():
                    if pago_tiene_aplicaciones_cuotas(session, pago.id):
                        session.flush()
                        validar_suma_aplicada_vs_monto_pago(
                            session, pago.id, pago.monto_pagado
                        )
                        pago.estado = "PAGADO"
                        pago.conciliado = True
                        pago.verificado_concordancia = "SI"
                        pago.fecha_conciliacion = ahora
                        stats["banderas_sincronizadas"] += 1
                        logger.info(
                            "id=%s: ya tenía cuota_pagos; banderas sincronizadas.",
                            pago.id,
                        )
                    else:
                        cc, cp = 0, 0
                        if not pago.prestamo_id:
                            logger.info(
                                "id=%s: sin prestamo_id; no se aplica cascada.",
                                pago.id,
                            )
                            stats["sin_cambio_sigue_pendiente"] += 1
                        else:
                            # No poner conciliado=true antes de aplicar: el CHECK en BD prohíbe
                            # conciliado con estado PENDIENTE; el flush del savepoint interno fallaría.
                            cc, cp = _aplicar_pago_a_cuotas_interno(pago, session)
                            pago.estado = _estado_conciliacion_post_cascada(
                                pago, cc, cp
                            )
                            if str(pago.estado or "").upper() == "PAGADO":
                                pago.conciliado = True
                                pago.verificado_concordancia = "SI"
                                pago.fecha_conciliacion = ahora
                                stats["conciliado_tras_cascada"] += 1
                            else:
                                stats["sin_cambio_sigue_pendiente"] += 1
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

        resumen = (
            "banderas_sync=%s conciliados_cascada=%s sin_cambio_pendiente=%s"
            % (
                stats["banderas_sincronizadas"],
                stats["conciliado_tras_cascada"],
                stats["sin_cambio_sigue_pendiente"],
            )
        )
        if execute:
            session.commit()
            logger.info(
                "Commit: procesados_ok=%s omitidos=%s errores=%s | %s",
                ok,
                skipped,
                len(errores),
                resumen,
            )
        else:
            session.rollback()
            logger.info(
                "Dry-run (sin commit): habría procesado_ok=%s omitidos=%s errores=%s | %s. "
                "Use --execute para guardar.",
                ok,
                skipped,
                len(errores),
                resumen,
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
