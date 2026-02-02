"""
Endpoints de pagos. Datos reales desde BD (Cuota, Prestamo, Cliente).
GET /pagos/kpis y GET /pagos/stats con consultas a BD; ceros cuando no hay datos.
"""
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.cliente import Cliente
from app.models.cuota import Cuota
from app.models.prestamo import Prestamo

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
    hoy = date.today()
    # Cuotas pendientes (sin fecha_pago)
    cuotas_pendientes = db.scalar(
        select(func.count()).select_from(Cuota).where(Cuota.fecha_pago.is_(None))
    ) or 0
    # Clientes con al menos una cuota vencida no pagada
    subq = (
        select(Cuota.cliente_id)
        .where(Cuota.fecha_pago.is_(None), Cuota.fecha_vencimiento < hoy)
        .distinct()
    )
    clientes_en_mora = db.scalar(select(func.count()).select_from(subq.subquery())) or 0
    # Monto cobrado en el mes actual (cuotas con fecha_pago en este mes)
    inicio_mes = hoy.replace(day=1)
    monto_cobrado_mes = db.scalar(
        select(func.coalesce(func.sum(Cuota.monto), 0)).select_from(Cuota).where(
            Cuota.fecha_pago.isnot(None),
            func.date(Cuota.fecha_pago) >= inicio_mes,
            func.date(Cuota.fecha_pago) <= hoy,
        )
    ) or 0
    # Saldo por cobrar: suma monto de cuotas no pagadas
    saldo_por_cobrar = db.scalar(
        select(func.coalesce(func.sum(Cuota.monto), 0)).select_from(Cuota).where(
            Cuota.fecha_pago.is_(None)
        )
    ) or 0
    # Clientes al día: clientes que tienen préstamos y no tienen cuotas vencidas sin pagar
    clientes_con_prestamo = db.scalar(select(func.count(func.distinct(Prestamo.cliente_id))).select_from(Prestamo)) or 0
    clientes_al_dia = max(0, clientes_con_prestamo - clientes_en_mora)
    return {
        "cuotas_pendientes": cuotas_pendientes,
        "clientes_en_mora": clientes_en_mora,
        "montoCobradoMes": _safe_float(monto_cobrado_mes),
        "saldoPorCobrar": _safe_float(saldo_por_cobrar),
        "clientesAlDia": clientes_al_dia,
    }


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
    def _cuota_base():
        q = select(Cuota)
        if analista or concesionario or modelo:
            q = q.join(Prestamo, Cuota.prestamo_id == Prestamo.id)
            if analista:
                q = q.where(Prestamo.analista == analista)
            if concesionario:
                q = q.where(Prestamo.concesionario == concesionario)
            if modelo:
                q = q.where(Prestamo.modelo == modelo)
        return q
    # Cuotas pagadas / pendientes / atrasadas (con filtros). Usar solo subquery como FROM
    # para evitar SAWarning "cartesian product" (no referenciar Cuota en el select exterior).
    def _count_from_subquery(q):
        subq = q.subquery()
        return db.scalar(select(func.count()).select_from(subq)) or 0

    q_base = _cuota_base()
    cuotas_pagadas = _count_from_subquery(q_base.where(Cuota.fecha_pago.isnot(None)))
    q_base = _cuota_base()
    cuotas_pendientes = _count_from_subquery(q_base.where(Cuota.fecha_pago.is_(None)))
    q_base = _cuota_base()
    cuotas_atrasadas = _count_from_subquery(
        q_base.where(Cuota.fecha_pago.is_(None), Cuota.fecha_vencimiento < hoy)
    )
    q_base = _cuota_base()
    subq_pagado = q_base.where(Cuota.fecha_pago.isnot(None)).subquery()
    total_pagado = db.scalar(
        select(func.coalesce(func.sum(subq_pagado.c.monto), 0)).select_from(subq_pagado)
    ) or 0
    q_base = _cuota_base()
    pagos_hoy = _count_from_subquery(
        q_base.where(
            Cuota.fecha_pago.isnot(None),
            func.date(Cuota.fecha_pago) == hoy,
        )
    )
    # Pagos por estado (mismos filtros)
    q_estado = select(Cuota.estado, func.count()).select_from(Cuota)
    if analista or concesionario or modelo:
        q_estado = q_estado.join(Prestamo, Cuota.prestamo_id == Prestamo.id)
        if analista:
            q_estado = q_estado.where(Prestamo.analista == analista)
        if concesionario:
            q_estado = q_estado.where(Prestamo.concesionario == concesionario)
        if modelo:
            q_estado = q_estado.where(Prestamo.modelo == modelo)
    q_estado = q_estado.group_by(Cuota.estado)
    rows_estado = db.execute(q_estado).all()
    pagos_por_estado = [{"estado": r[0], "count": r[1]} for r in rows_estado]
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
