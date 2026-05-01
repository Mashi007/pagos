"""
Reconstruccion en cascada (waterfall) por prestamo.

La aplicacion a cuotas sigue el orden `numero_cuota` ascendente (cuotas mas antiguas primero).
Politica de negocio: **cascada**; en rutas o codigo antiguo el termino «fifo» se usa solo como alias.

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

from app.models.auditoria_conciliacion_manual import AuditoriaConciliacionManual
from app.models.cuota import Cuota
from app.models.cuota_pago import CuotaPago
from app.models.pago import Pago
from app.models.prestamo import Prestamo
from app.models.reporte_contable_cache import ReporteContableCache
from app.models.revisar_pago import RevisarPago
from app.services.cuota_estado import sincronizar_columna_estado_cuotas

logger = logging.getLogger(__name__)

TOL_INTEGRIDAD = 0.02

_SQL_DELETE_CUOTA_PAGOS_POR_PRESTAMO = text(
    "DELETE FROM cuota_pagos WHERE cuota_id IN "
    "(SELECT id FROM cuotas WHERE prestamo_id = :pid)"
)


def _delete_cuota_pagos_por_prestamo_sql(db: Session, prestamo_id: int) -> int:
    """
    Borra toda la articulación cuota_pagos del préstamo en una sentencia SQL.
    Evita filas residuales que en algunos PG/SQLAlchemy dejaban rowcount incompleto con DELETE ORM + IN (subquery).
    """
    r = db.execute(_SQL_DELETE_CUOTA_PAGOS_POR_PRESTAMO, {"pid": prestamo_id})
    return int(getattr(r, "rowcount", -1) or -1)


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
    from app.api.v1.endpoints.pagos import _where_pago_elegible_reaplicacion_cascada

    subq = select(CuotaPago.pago_id).where(CuotaPago.pago_id.isnot(None)).distinct()
    n_orphans = db.scalar(
        select(func.count())
        .select_from(Pago)
        .where(
            Pago.prestamo_id == prestamo_id,
            _where_pago_elegible_reaplicacion_cascada(),
            Pago.monto_pagado > 0,
            ~Pago.id.in_(subq),
        )
    ) or 0
    if int(n_orphans) > 0:
        return True

    # Todos los pagos elegibles ya tienen al menos una fila en cuota_pagos (subconsulta global),
    # pero el dinero puede no estar reflejado en las cuotas de ESTE préstamo (articulación errónea,
    # filas huérfanas, import parcial). En ese caso aplicar_pagos_pendientes no hace nada y hay que resetear.
    sum_pagos_eleg = float(
        db.scalar(
            select(func.coalesce(func.sum(Pago.monto_pagado), 0)).where(
                Pago.prestamo_id == prestamo_id,
                _where_pago_elegible_reaplicacion_cascada(),
                Pago.monto_pagado > 0,
            )
        )
        or 0
    )
    sum_cp_en_cuotas = float(
        db.scalar(
            select(func.coalesce(func.sum(CuotaPago.monto_aplicado), 0))
            .select_from(CuotaPago)
            .join(Cuota, CuotaPago.cuota_id == Cuota.id)
            .where(Cuota.prestamo_id == prestamo_id)
        )
        or 0
    )
    cap_cuotas = float(
        db.scalar(select(func.coalesce(func.sum(Cuota.monto), 0)).where(Cuota.prestamo_id == prestamo_id)) or 0
    )
    objetivo = min(sum_pagos_eleg, cap_cuotas)
    if objetivo > TOL_INTEGRIDAD and sum_cp_en_cuotas + TOL_INTEGRIDAD < objetivo:
        return True

    return False


def eliminar_todos_pagos_prestamo(db: Session, prestamo_id: int) -> dict[str, Any]:
    """
    Borra todos los pagos de un préstamo y deja las cuotas sin aplicación (como tras un reset de cascada
    sin reaplicar). Misma limpieza que eliminar_pago por dependencias, más reinicio de totales en cuotas.

    Solo préstamos en estado APROBADO (alineado con el flujo «reemplazar pagos» en UI).
    """
    from app.api.v1.endpoints.pagos import _marcar_prestamo_liquidado_si_corresponde

    prestamo = db.get(Prestamo, prestamo_id)
    if not prestamo:
        return {"ok": False, "error": "Prestamo no encontrado", "prestamo_id": prestamo_id}

    est = (prestamo.estado or "").strip().upper()
    if est != "APROBADO":
        return {
            "ok": False,
            "error": "Solo se pueden reemplazar pagos en préstamos en estado APROBADO.",
            "prestamo_id": prestamo_id,
            "estado_actual": prestamo.estado,
        }

    n_pagos_antes = int(
        db.scalar(select(func.count()).select_from(Pago).where(Pago.prestamo_id == prestamo_id)) or 0
    )

    if n_pagos_antes == 0:
        _marcar_prestamo_liquidado_si_corresponde(prestamo_id, db)
        return {
            "ok": True,
            "prestamo_id": prestamo_id,
            "pagos_eliminados": 0,
            "cuota_pagos_eliminadas": 0,
        }

    cuotas = db.execute(
        select(Cuota).where(Cuota.prestamo_id == prestamo_id).order_by(Cuota.numero_cuota.asc())
    ).scalars().all()

    cuota_ids = [c.id for c in cuotas if c.id is not None]

    cuota_pagos_eliminadas = 0
    if cuota_ids:
        _cp = _delete_cuota_pagos_por_prestamo_sql(db, prestamo_id)
        cuota_pagos_eliminadas = _cp if _cp >= 0 else 0
        r_cache = db.execute(delete(ReporteContableCache).where(ReporteContableCache.cuota_id.in_(cuota_ids)))
        _ = int(getattr(r_cache, "rowcount", 0) or 0)
        db.flush()

    for c in cuotas:
        c.total_pagado = Decimal("0")
        c.fecha_pago = None
        c.pago_id = None
        c.dias_mora = None
        c.dias_morosidad = None

    if cuotas:
        sincronizar_columna_estado_cuotas(db, list(cuotas), commit=False)
    db.flush()

    pago_ids = list(db.scalars(select(Pago.id).where(Pago.prestamo_id == prestamo_id)).all())
    if pago_ids:
        db.execute(delete(AuditoriaConciliacionManual).where(AuditoriaConciliacionManual.pago_id.in_(pago_ids)))
        db.execute(delete(RevisarPago).where(RevisarPago.pago_id.in_(pago_ids)))
        db.flush()

    r_del = db.execute(delete(Pago).where(Pago.prestamo_id == prestamo_id))
    pagos_eliminados = int(getattr(r_del, "rowcount", -1) or -1)
    if pagos_eliminados < 0:
        pagos_eliminados = n_pagos_antes

    _marcar_prestamo_liquidado_si_corresponde(prestamo_id, db)

    return {
        "ok": True,
        "prestamo_id": prestamo_id,
        "pagos_eliminados": pagos_eliminados,
        "cuota_pagos_eliminadas": cuota_pagos_eliminadas,
    }


def reset_y_reaplicar_cascada_prestamo(db: Session, prestamo_id: int) -> dict[str, Any]:
    from app.services.pagos_aplicacion_prestamo import aplicar_pagos_pendientes_prestamo
    from app.services.pagos_cascada_aplicacion import _marcar_prestamo_liquidado_si_corresponde

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

    if cuota_ids:
        cuota_pagos_eliminadas = _delete_cuota_pagos_por_prestamo_sql(db, prestamo_id)
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
            "reset_cascada: quedan %s filas cuota_pagos tras DELETE SQL; reintento prestamo_id=%s",
            int(restantes),
            prestamo_id,
        )
        db.execute(_SQL_DELETE_CUOTA_PAGOS_POR_PRESTAMO, {"pid": prestamo_id})
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
# Compat: nombre historico (alias «fifo» en identificadores antiguos).
reconstruir_cascada_fifo_prestamo = reset_y_reaplicar_cascada_prestamo

# Compat: nombre historico
reset_y_reaplicar_fifo_prestamo = reset_y_reaplicar_cascada_prestamo
