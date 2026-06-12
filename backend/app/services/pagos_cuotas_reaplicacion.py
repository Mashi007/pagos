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
from typing import Any, Optional

from sqlalchemy import delete, func, or_, select, text
from sqlalchemy.orm import Session

from app.models.auditoria_conciliacion_manual import AuditoriaConciliacionManual
from app.models.cuota import Cuota
from app.models.cuota_pago import CuotaPago
from app.models.pago import Pago
from app.models.pago_con_error import PagoConError
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


def _rollback_reset_cascada_fallido(db: Session, prestamo_id: int) -> None:
    try:
        db.rollback()
    except Exception:
        logger.warning(
            "reset_y_reaplicar_cascada_prestamo prestamo_id=%s: no se pudo revertir fallo",
            prestamo_id,
            exc_info=True,
        )


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


def prestamo_tiene_hueco_cascada_cuotas(db: Session, prestamo_id: int, tol: float = TOL_INTEGRIDAD) -> bool:
    """
    True si una cuota anterior tiene saldo y hay cuota_pagos en cuotas posteriores.

    Ocurre al borrar un pago intermedio sin reconstruir la cascada: los pagos
    siguientes quedan articulados en cuotas «más adelante» y se salta el hueco.
    """
    cuotas = db.execute(
        select(Cuota.id, Cuota.numero_cuota, Cuota.monto, Cuota.total_pagado)
        .where(Cuota.prestamo_id == prestamo_id)
        .order_by(Cuota.numero_cuota.asc())
    ).all()
    if len(cuotas) < 2:
        return False

    for idx, c_early in enumerate(cuotas):
        saldo = float(c_early.monto or 0) - float(c_early.total_pagado or 0)
        if saldo <= tol:
            continue
        ids_later = [int(c.id) for c in cuotas[idx + 1 :] if c.id is not None]
        if not ids_later:
            return False
        n_cp = int(
            db.scalar(
                select(func.count())
                .select_from(CuotaPago)
                .where(CuotaPago.cuota_id.in_(ids_later))
            )
            or 0
        )
        if n_cp > 0:
            return True
    return False


def prestamo_requiere_correccion_cascada(db: Session, prestamo_id: int) -> bool:
    """True si hace falta reaplicar en cascada: integridad rota u orfano en pagos conciliados sin cuota_pagos."""
    prestamo = db.get(Prestamo, prestamo_id)
    if not prestamo:
        return False
    if prestamo_tiene_hueco_cascada_cuotas(db, prestamo_id):
        return True
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


def eliminar_todos_pagos_prestamo(
    db: Session,
    prestamo_id: int,
    *,
    contexto_revision_conciliar: bool = False,
) -> dict[str, Any]:
    """
    Borra todos los pagos de un préstamo y deja las cuotas sin aplicación (como tras un reset de cascada
    sin reaplicar). Misma limpieza que eliminar_pago por dependencias, más reinicio de totales en cuotas.

    Por defecto solo préstamos APROBADO (alineado con el flujo «reemplazar pagos» en UI).
    Con contexto_revision_conciliar=True (admin, botón Conciliar) también permite LIQUIDADO.
    """
    prestamo = db.get(Prestamo, prestamo_id)
    if not prestamo:
        return {"ok": False, "error": "Prestamo no encontrado", "prestamo_id": prestamo_id}

    est = (prestamo.estado or "").strip().upper()
    estados_ok_conciliar = frozenset({"APROBADO", "LIQUIDADO"})
    if contexto_revision_conciliar:
        if est not in estados_ok_conciliar:
            return {
                "ok": False,
                "error": (
                    f"Conciliar cartera solo en préstamos APROBADO o LIQUIDADO "
                    f"(estado actual: {prestamo.estado or 'sin estado'})."
                ),
                "prestamo_id": prestamo_id,
                "estado_actual": prestamo.estado,
            }
    elif est != "APROBADO":
        from app.services.finiquito_conciliacion_visto_service import (
            prestamo_tiene_reserva_finiquito_activa,
        )

        if not prestamo_tiene_reserva_finiquito_activa(db, prestamo_id):
            return {
                "ok": False,
                "error": (
                    "Solo se pueden reemplazar pagos en préstamos APROBADO, "
                    "o en finiquito con reserva Visto activa (area de revision)."
                ),
                "prestamo_id": prestamo_id,
                "estado_actual": prestamo.estado,
            }

    n_pagos_antes = int(
        db.scalar(select(func.count()).select_from(Pago).where(Pago.prestamo_id == prestamo_id)) or 0
    )

    if n_pagos_antes == 0:
        pagos_con_errores_eliminados = _eliminar_pagos_con_errores_reemplazo_prestamo(
            db, prestamo_id, prestamo.cedula
        )
        _marcar_liquidado_tras_eliminar_pagos(db, prestamo_id)
        return {
            "ok": True,
            "prestamo_id": prestamo_id,
            "pagos_eliminados": 0,
            "cuota_pagos_eliminadas": 0,
            "pagos_con_errores_eliminados": pagos_con_errores_eliminados,
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

    pagos_con_errores_eliminados = _eliminar_pagos_con_errores_reemplazo_prestamo(
        db, prestamo_id, prestamo.cedula
    )

    _marcar_liquidado_tras_eliminar_pagos(db, prestamo_id)

    return {
        "ok": True,
        "prestamo_id": prestamo_id,
        "pagos_eliminados": pagos_eliminados,
        "cuota_pagos_eliminadas": cuota_pagos_eliminadas,
        "pagos_con_errores_eliminados": pagos_con_errores_eliminados,
    }


def _marcar_liquidado_tras_eliminar_pagos(db: Session, prestamo_id: int) -> None:
    """
    Tras borrar pagos, recalcula LIQUIDADO/APROBADO.
    Si hay conciliacion Visto activa (reserva temporal), no tocar: evita borrar finiquito_casos.
    """
    from app.services.finiquito_conciliacion_visto_service import (
        prestamo_tiene_reserva_finiquito_activa,
    )

    if prestamo_tiene_reserva_finiquito_activa(db, prestamo_id):
        logger.info(
            "eliminar_todos_pagos: omitido recalculo liquidado/finiquito prestamo_id=%s "
            "(conciliacion Visto activa)",
            prestamo_id,
        )
        return
    from app.api.v1.endpoints.pagos import _marcar_prestamo_liquidado_si_corresponde

    _marcar_prestamo_liquidado_si_corresponde(prestamo_id, db)


def _eliminar_pagos_con_errores_reemplazo_prestamo(
    db: Session,
    prestamo_id: int,
    cedula_prestamo: Optional[str],
) -> int:
    """
    Quita filas de `pagos_con_errores` que bloquean re-cargar el mismo comprobante+código
    tras «Reemplazar pagos» (numero_documento_ya_registrado consulta pagos y pagos_con_errores).
    """
    from app.utils.cedula_almacenamiento import normalizar_cedula_almacenamiento

    condiciones = [PagoConError.prestamo_id == prestamo_id]
    ced_norm = normalizar_cedula_almacenamiento(cedula_prestamo or "")
    if ced_norm:
        pc = func.upper(func.replace(func.coalesce(PagoConError.cedula_cliente, ""), "-", ""))
        condiciones.append(
            (PagoConError.prestamo_id.is_(None)) & (pc == ced_norm.replace("-", "").upper())
        )
    r = db.execute(delete(PagoConError).where(or_(*condiciones)))
    n = int(getattr(r, "rowcount", 0) or 0)
    if n:
        logger.info(
            "[REEMPLAZAR_PAGOS] pagos_con_errores eliminados=%s prestamo_id=%s cedula=%s",
            n,
            prestamo_id,
            (ced_norm or "")[:20],
        )
    return n


def realinear_cuotas_prestamo_desde_cuota_pagos(db: Session, prestamo_id: int) -> dict[str, Any]:
    """
    Recalcula total_pagado y metadatos de cuotas desde cuota_pagos existentes.

    Camino liviano tras eliminar un solo pago: no borra ni reaplica todos los pagos del crédito.
    """
    from app.services.cuota_estado import (
        dias_retraso_desde_vencimiento,
        hoy_negocio,
        sincronizar_columna_estado_cuotas,
    )
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
    if cuota_ids:
        db.execute(delete(ReporteContableCache).where(ReporteContableCache.cuota_id.in_(cuota_ids)))

    hoy = hoy_negocio()
    for c in cuotas:
        sum_aplicado = float(
            db.scalar(
                select(func.coalesce(func.sum(CuotaPago.monto_aplicado), 0)).where(
                    CuotaPago.cuota_id == c.id
                )
            )
            or 0
        )
        c.total_pagado = Decimal(str(round(sum_aplicado, 2)))

        ultimo_cp = db.execute(
            select(CuotaPago.pago_id, CuotaPago.es_pago_completo, CuotaPago.fecha_aplicacion)
            .where(CuotaPago.cuota_id == c.id)
            .order_by(CuotaPago.orden_aplicacion.desc(), CuotaPago.id.desc())
            .limit(1)
        ).first()
        c.pago_id = int(ultimo_cp[0]) if ultimo_cp and ultimo_cp[0] is not None else None

        monto_cuota = float(c.monto or 0)
        nuevo_total = float(c.total_pagado or 0)
        fecha_venc = c.fecha_vencimiento
        if fecha_venc is not None and hasattr(fecha_venc, "date"):
            fecha_venc = fecha_venc.date()
        fecha_venc = fecha_venc or hoy

        if nuevo_total >= monto_cuota - 0.01 and monto_cuota > 0:
            fecha_pago_row = None
            if c.pago_id is not None:
                fecha_pago_row = db.scalar(
                    select(Pago.fecha_pago).where(Pago.id == c.pago_id)
                )
            if fecha_pago_row is not None and hasattr(fecha_pago_row, "date"):
                c.fecha_pago = fecha_pago_row.date()
            elif fecha_pago_row is not None:
                c.fecha_pago = fecha_pago_row
            else:
                c.fecha_pago = None
            c.dias_mora = 0
            c.dias_morosidad = 0
        else:
            c.fecha_pago = None
            c.dias_mora = dias_retraso_desde_vencimiento(fecha_venc, hoy) if nuevo_total > 0 else None
            c.dias_morosidad = c.dias_mora

    sincronizar_columna_estado_cuotas(db, list(cuotas), commit=False)
    db.flush()
    _marcar_prestamo_liquidado_si_corresponde(prestamo_id, db)

    integ = integridad_cuotas_prestamo(db, prestamo_id)
    return {
        "ok": True,
        "prestamo_id": prestamo_id,
        "cuotas": len(cuotas),
        "integridad_ok": bool(integ.get("integridad_ok")),
        "requiere_reset_cascada": prestamo_requiere_correccion_cascada(db, prestamo_id),
    }


def reset_y_reaplicar_cascada_prestamo(db: Session, prestamo_id: int) -> dict[str, Any]:
    from app.services.pagos_aplicacion_prestamo import (
        aplicar_pagos_pendientes_prestamo,
        detalle_excepcion_db,
    )
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

    try:
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
            _rollback_reset_cascada_fallido(db, prestamo_id)
            return {
                "ok": False,
                "error": f"Aun quedan {restantes} filas en cuota_pagos tras DELETE; abortar.",
                "prestamo_id": prestamo_id,
            }

        pagos_reaplicados = aplicar_pagos_pendientes_prestamo(
            prestamo_id,
            db,
            fail_fast=True,
            marcar_liquidado=False,
        )

        cuotas_despues = db.execute(
            select(Cuota).where(Cuota.prestamo_id == prestamo_id).order_by(Cuota.numero_cuota.asc())
        ).scalars().all()
        sincronizar_columna_estado_cuotas(db, list(cuotas_despues), commit=False)
        _marcar_prestamo_liquidado_si_corresponde(prestamo_id, db)
    except Exception as exc:
        logger.exception("reset_y_reaplicar_cascada_prestamo prestamo_id=%s", prestamo_id)
        _rollback_reset_cascada_fallido(db, prestamo_id)
        return {
            "ok": False,
            "error": detalle_excepcion_db(exc),
            "prestamo_id": prestamo_id,
        }

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
