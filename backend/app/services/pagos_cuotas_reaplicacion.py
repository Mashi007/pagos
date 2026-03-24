"""
Reconstruccion en cascada (waterfall) por prestamo.

- integridad_cuotas_prestamo: diagnostico total_pagado vs SUM(cuota_pagos).
- reset_y_reaplicar_cascada_prestamo: borra articulacion, resetea cuotas y vuelve a aplicar pagos conciliados.

Usar cuando la tabla de amortizacion no refleja los pagos (doble cuota_pagos, migraciones,
total_pagado desincronizado, etc.).
"""
from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any

from sqlalchemy import delete, func, or_, select, text
from sqlalchemy.orm import Session

from app.models.cuota import Cuota
from app.models.cuota_pago import CuotaPago
from app.models.pago import Pago
from app.models.prestamo import Prestamo
from app.models.reporte_contable_cache import ReporteContableCache
from app.services.cuota_estado import sincronizar_columna_estado_cuotas

logger = logging.getLogger(__name__)

TOL_INTEGRIDAD = 0.02


def integridad_cuotas_prestamo(db: Session, prestamo_id: int) -> dict[str, Any]:
    """Compara total_pagado con SUM(cuota_pagos) por cuota; no modifica datos."""
    prestamo = db.get(Prestamo, prestamo_id)
    if not prestamo:
        return {"ok": False, "error": "Prestamo no encontrado", "prestamo_id": prestamo_id}

    q = (
        select(
            Cuota.id,
            Cuota.numero_cuota,
            Cuota.monto,
            Cuota.total_pagado,
            func.coalesce(func.sum(CuotaPago.monto_aplicado), 0).label("sum_aplicado"),
        )
        .select_from(Cuota)
        .outerjoin(CuotaPago, CuotaPago.cuota_id == Cuota.id)
        .where(Cuota.prestamo_id == prestamo_id)
        .group_by(Cuota.id, Cuota.numero_cuota, Cuota.monto, Cuota.total_pagado)
        .order_by(Cuota.numero_cuota.asc())
    )
    rows = db.execute(q).all()

    inconsistentes: list[dict[str, Any]] = []
    for r in rows:
        tp = float(r.total_pagado or 0)
        sa = float(r.sum_aplicado or 0)
        diff = round(tp - sa, 2)
        if abs(diff) > TOL_INTEGRIDAD:
            inconsistentes.append(
                {
                    "cuota_id": r.id,
                    "numero_cuota": r.numero_cuota,
                    "monto_cuota": float(r.monto or 0),
                    "total_pagado": tp,
                    "sum_cuota_pagos": sa,
                    "diff_total_vs_cp": diff,
                }
            )

    sum_total_pagado = float(
        db.scalar(select(func.coalesce(func.sum(Cuota.total_pagado), 0)).where(Cuota.prestamo_id == prestamo_id))
        or 0
    )
    sum_cuota_pagos = float(
        db.scalar(
            select(func.coalesce(func.sum(CuotaPago.monto_aplicado), 0))
            .select_from(CuotaPago)
            .join(Cuota, CuotaPago.cuota_id == Cuota.id)
            .where(Cuota.prestamo_id == prestamo_id)
        )
        or 0
    )
    diff_global = round(sum_total_pagado - sum_cuota_pagos, 2)

    n_fp = int(
        db.scalar(
            select(func.count()).select_from(CuotaPago).join(Cuota, CuotaPago.cuota_id == Cuota.id).where(
                Cuota.prestamo_id == prestamo_id
            )
        )
        or 0
    )

    return {
        "ok": True,
        "prestamo_id": prestamo_id,
        "cuotas": len(rows),
        "filas_cuota_pagos": n_fp,
        "sum_total_pagado_cuotas": sum_total_pagado,
        "sum_monto_cuota_pagos": sum_cuota_pagos,
        "diff_global_total_vs_cp": diff_global,
        "cuotas_inconsistentes": len(inconsistentes),
        "integridad_ok": len(inconsistentes) == 0 and abs(diff_global) <= TOL_INTEGRIDAD,
        "detalle_inconsistencias": inconsistentes[:200],
    }


def prestamo_requiere_correccion_cascada(db: Session, prestamo_id: int) -> bool:
    """True si hace falta reaplicar en cascada: integridad rota u orfano en pagos conciliados sin cuota_pagos."""
    prestamo = db.get(Prestamo, prestamo_id)
    if not prestamo:
        return False
    n_cuotas = int(
        db.scalar(select(func.count()).select_from(Cuota).where(Cuota.prestamo_id == prestamo_id)) or 0
    )
    if n_cuotas == 0:
        return False
    integ = integridad_cuotas_prestamo(db, prestamo_id)
    if integ.get("ok") and not integ.get("integridad_ok"):
        return True
    subq = select(CuotaPago.pago_id).where(CuotaPago.pago_id.isnot(None)).distinct()
    n_orphans = db.scalar(
        select(func.count())
        .select_from(Pago)
        .where(
            Pago.prestamo_id == prestamo_id,
            or_(
                Pago.conciliado.is_(True),
                func.coalesce(func.upper(func.trim(Pago.verificado_concordancia)), "") == "SI",
            ),
            Pago.monto_pagado > 0,
            ~Pago.id.in_(subq),
        )
    ) or 0
    return int(n_orphans) > 0


def reset_y_reaplicar_cascada_prestamo(db: Session, prestamo_id: int) -> dict[str, Any]:
    from app.api.v1.endpoints.pagos import (
        _marcar_prestamo_liquidado_si_corresponde,
        aplicar_pagos_pendientes_prestamo,
    )

    prestamo = db.get(Prestamo, prestamo_id)
    if not prestamo:
        return {"ok": False, "error": "Prestamo no encontrado", "prestamo_id": prestamo_id}

    cuotas = db.execute(
        select(Cuota).where(Cuota.prestamo_id == prestamo_id).order_by(Cuota.numero_cuota.asc())
    ).scalars().all()
    if not cuotas:
        return {"ok": False, "error": "El prestamo no tiene cuotas", "prestamo_id": prestamo_id}

    cuota_ids = [c.id for c in cuotas if c.id is not None]

    cuota_pagos_eliminadas = -1
    cache_eliminadas = -1
    subq_cuotas = select(Cuota.id).where(Cuota.prestamo_id == prestamo_id)

    if cuota_ids:
        r1 = db.execute(delete(CuotaPago).where(CuotaPago.cuota_id.in_(subq_cuotas)))
        cuota_pagos_eliminadas = int(getattr(r1, "rowcount", -1) or -1)
        r2 = db.execute(delete(ReporteContableCache).where(ReporteContableCache.cuota_id.in_(cuota_ids)))
        cache_eliminadas = int(getattr(r2, "rowcount", -1) or -1)
        db.flush()

    for c in cuotas:
        c.total_pagado = Decimal("0")
        c.fecha_pago = None
        c.pago_id = None
        c.dias_mora = None

    sincronizar_columna_estado_cuotas(db, list(cuotas), commit=False)
    db.flush()

    restantes = db.scalar(
        select(func.count())
        .select_from(CuotaPago)
        .join(Cuota, CuotaPago.cuota_id == Cuota.id)
        .where(Cuota.prestamo_id == prestamo_id)
    )
    if restantes and int(restantes) > 0:
        logger.warning(
            "reset_cascada: quedan %s filas cuota_pagos tras DELETE ORM; reintento prestamo_id=%s",
            int(restantes),
            prestamo_id,
        )
        db.execute(
            text(
                "DELETE FROM cuota_pagos WHERE cuota_id IN "
                "(SELECT id FROM cuotas WHERE prestamo_id = :pid)"
            ),
            {"pid": prestamo_id},
        )
        db.flush()
        restantes = db.scalar(
            select(func.count())
            .select_from(CuotaPago)
            .join(Cuota, CuotaPago.cuota_id == Cuota.id)
            .where(Cuota.prestamo_id == prestamo_id)
        )
    if restantes and int(restantes) > 0:
        return {
            "ok": False,
            "error": f"Aun quedan {restantes} filas en cuota_pagos tras DELETE; abortar.",
            "prestamo_id": prestamo_id,
        }

    pagos_reaplicados = aplicar_pagos_pendientes_prestamo(prestamo_id, db)

    cuotas_despues = db.execute(
        select(Cuota).where(Cuota.prestamo_id == prestamo_id).order_by(Cuota.numero_cuota.asc())
    ).scalars().all()
    sincronizar_columna_estado_cuotas(db, list(cuotas_despues), commit=False)
    _marcar_prestamo_liquidado_si_corresponde(prestamo_id, db)

    return {
        "ok": True,
        "prestamo_id": prestamo_id,
        "cuotas": len(cuota_ids),
        "cuota_pagos_eliminadas": cuota_pagos_eliminadas,
        "cache_contable_eliminadas": cache_eliminadas,
        "pagos_reaplicados": pagos_reaplicados,
    }


reconstruir_cascada_prestamo = reset_y_reaplicar_cascada_prestamo
# Compat: nombre historico con sufijo fifo.
reconstruir_cascada_fifo_prestamo = reset_y_reaplicar_cascada_prestamo

# Compat: nombre historico
reset_y_reaplicar_fifo_prestamo = reset_y_reaplicar_cascada_prestamo
