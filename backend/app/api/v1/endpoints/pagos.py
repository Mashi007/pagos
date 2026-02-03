"""
Endpoints de pagos. Datos reales desde BD (Cuota, Prestamo, Cliente).
GET /pagos/kpis y GET /pagos/stats con consultas a BD; ceros cuando no hay datos.
"""
import logging
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.cliente import Cliente
from app.models.cuota import Cuota
from app.models.prestamo import Prestamo

logger = logging.getLogger(__name__)
router = APIRouter(dependencies=[Depends(get_current_user)])


def _safe_float(val) -> float:
    if val is None:
        return 0.0
    try:
        return float(val)
    except (TypeError, ValueError):
        return 0.0


@router.get("/kpis")
def get_pagos_kpis(
    fecha_inicio: Optional[str] = Query(None),
    fecha_fin: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """
    KPIs de pagos desde BD: cuotas_pendientes, clientes_en_mora,
    montoCobradoMes, saldoPorCobrar, clientesAlDia.
    """
    try:
        hoy = date.today()
        cuotas_pendientes = db.scalar(
            select(func.count()).select_from(Cuota).where(Cuota.fecha_pago.is_(None))
        ) or 0
        subq = (
            select(Cuota.cliente_id)
            .where(Cuota.fecha_pago.is_(None), Cuota.fecha_vencimiento < hoy)
            .distinct()
        )
        clientes_en_mora = db.scalar(select(func.count()).select_from(subq.subquery())) or 0
        inicio_mes = hoy.replace(day=1)
        monto_cobrado_mes = db.scalar(
            select(func.coalesce(func.sum(Cuota.monto), 0)).select_from(Cuota).where(
                Cuota.fecha_pago.isnot(None),
                func.date(Cuota.fecha_pago) >= inicio_mes,
                func.date(Cuota.fecha_pago) <= hoy,
            )
        ) or 0
        saldo_por_cobrar = db.scalar(
            select(func.coalesce(func.sum(Cuota.monto), 0)).select_from(Cuota).where(
                Cuota.fecha_pago.is_(None)
            )
        ) or 0
        clientes_con_prestamo = db.scalar(select(func.count(func.distinct(Prestamo.cliente_id))).select_from(Prestamo)) or 0
        clientes_al_dia = max(0, clientes_con_prestamo - clientes_en_mora)
        return {
            "cuotas_pendientes": cuotas_pendientes,
            "clientes_en_mora": clientes_en_mora,
            "montoCobradoMes": _safe_float(monto_cobrado_mes),
            "saldoPorCobrar": _safe_float(saldo_por_cobrar),
            "clientesAlDia": clientes_al_dia,
        }
    except Exception as e:
        logger.exception("Error en GET /pagos/kpis: %s", e)
        try:
            db.rollback()
        except Exception:
            pass
        return {
            "cuotas_pendientes": 0,
            "clientes_en_mora": 0,
            "montoCobradoMes": 0.0,
            "saldoPorCobrar": 0.0,
            "clientesAlDia": 0,
        }


def _stats_conds_cuota(analista: Optional[str], concesionario: Optional[str], modelo: Optional[str]):
    """Condiciones base para filtrar cuotas por préstamo (analista/concesionario/modelo)."""
    conds = []
    if analista:
        conds.append(Prestamo.analista == analista)
    if concesionario:
        conds.append(Prestamo.concesionario == concesionario)
    if modelo:
        conds.append(Prestamo.modelo == modelo)
    return conds


@router.get("/stats")
def get_pagos_stats(
    fecha_inicio: Optional[str] = Query(None),
    fecha_fin: Optional[str] = Query(None),
    analista: Optional[str] = Query(None),
    concesionario: Optional[str] = Query(None),
    modelo: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """
    Estadísticas de pagos desde BD: total_pagos, total_pagado, pagos_por_estado,
    cuotas_pagadas, cuotas_pendientes, cuotas_atrasadas, pagos_hoy.
    """
    hoy = date.today()
    use_filters = bool(analista or concesionario or modelo)

    def _q_cuotas():
        if use_filters:
            return select(Cuota).join(Prestamo, Cuota.prestamo_id == Prestamo.id).where(
                and_(*_stats_conds_cuota(analista, concesionario, modelo))
            )
        return select(Cuota)

    def _count(q):
        subq = q.subquery()
        return int(db.scalar(select(func.count()).select_from(subq)) or 0)

    try:
        # Cuotas pagadas / pendientes / atrasadas
        cuotas_pagadas = _count(_q_cuotas().where(Cuota.fecha_pago.isnot(None)))
        cuotas_pendientes = _count(_q_cuotas().where(Cuota.fecha_pago.is_(None)))
        cuotas_atrasadas = _count(
            _q_cuotas().where(Cuota.fecha_pago.is_(None), Cuota.fecha_vencimiento < hoy)
        )
        # Total pagado: suma directa sobre Cuota (evita errores con subquery.c.monto)
        q_sum = select(func.coalesce(func.sum(Cuota.monto), 0)).select_from(Cuota).where(
            Cuota.fecha_pago.isnot(None)
        )
        if use_filters:
            q_sum = q_sum.join(Prestamo, Cuota.prestamo_id == Prestamo.id).where(
                and_(*_stats_conds_cuota(analista, concesionario, modelo))
            )
        total_pagado = db.scalar(q_sum) or 0
        # Pagos hoy
        pagos_hoy = _count(
            _q_cuotas().where(
                Cuota.fecha_pago.isnot(None),
                func.date(Cuota.fecha_pago) == hoy,
            )
        )
        # Pagos por estado
        q_estado = select(Cuota.estado, func.count()).select_from(Cuota)
        if use_filters:
            q_estado = q_estado.join(Prestamo, Cuota.prestamo_id == Prestamo.id).where(
                and_(*_stats_conds_cuota(analista, concesionario, modelo))
            )
        q_estado = q_estado.group_by(Cuota.estado)
        rows_estado = db.execute(q_estado).all()
        pagos_por_estado = [{"estado": str(r[0]) if r[0] is not None else "N/A", "count": int(r[1])} for r in rows_estado]
        total_pagos = cuotas_pagadas + cuotas_pendientes
        return {
            "total_pagos": total_pagos,
            "total_pagado": _safe_float(total_pagado),
            "pagos_por_estado": pagos_por_estado,
            "cuotas_pagadas": cuotas_pagadas,
            "cuotas_pendientes": cuotas_pendientes,
            "cuotas_atrasadas": cuotas_atrasadas,
            "pagos_hoy": pagos_hoy,
        }
    except Exception as e:
        logger.exception("Error en GET /pagos/stats: %s", e)
        try:
            db.rollback()
        except Exception:
            pass
        return {
            "total_pagos": 0,
            "total_pagado": 0.0,
            "pagos_por_estado": [],
            "cuotas_pagadas": 0,
            "cuotas_pendientes": 0,
            "cuotas_atrasadas": 0,
            "pagos_hoy": 0,
        }
