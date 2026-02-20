"""
Reportes dashboard - resumen general.
"""
from datetime import date, datetime, timezone, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.cliente import Cliente
from app.models.cuota import Cuota
from app.models.prestamo import Prestamo

from app.api.v1.endpoints.reportes_utils import _safe_float

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get("/dashboard/resumen")
def get_resumen_dashboard(db: Session = Depends(get_db)):
    """
    Resumen para el dashboard de reportes: total_clientes, total_prestamos, total_pagos,
    cartera_activa, prestamos_mora, pagos_mes, fecha_actualizacion. Datos reales desde BD.
    """
    hoy = date.today()
    now_utc = datetime.now(timezone.utc)
    inicio_mes = hoy.replace(day=1)

    # KPIs solo incluyen clientes ACTIVOS
    total_clientes = db.scalar(
        select(func.count()).select_from(Cliente).where(Cliente.estado == "ACTIVO")
    ) or 0
    total_prestamos = db.scalar(
        select(func.count())
        .select_from(Prestamo)
        .join(Cliente, Prestamo.cliente_id == Cliente.id)
        .where(Cliente.estado == "ACTIVO", Prestamo.estado == "APROBADO")
    ) or 0
    total_pagos = db.scalar(
        select(func.count())
        .select_from(Cuota)
        .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
        .join(Cliente, Prestamo.cliente_id == Cliente.id)
        .where(
            Cliente.estado == "ACTIVO",
            Prestamo.estado == "APROBADO",
            Cuota.fecha_pago.isnot(None),
        )
    ) or 0
    cartera_activa = db.scalar(
        select(func.coalesce(func.sum(Cuota.monto), 0))
        .select_from(Cuota)
        .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
        .join(Cliente, Prestamo.cliente_id == Cliente.id)
        .where(
            Cliente.estado == "ACTIVO",
            Prestamo.estado == "APROBADO",
            Cuota.fecha_pago.is_(None),
        )
    ) or 0
    subq_mora = (
        select(Cuota.prestamo_id)
        .select_from(Cuota)
        .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
        .join(Cliente, Prestamo.cliente_id == Cliente.id)
        .where(
            Cliente.estado == "ACTIVO",
            Prestamo.estado == "APROBADO",
            Cuota.fecha_pago.is_(None),
            Cuota.fecha_vencimiento < (hoy - timedelta(days=89)),  # MOROSO: vencido hace 90+ días
        )
        .distinct()
    )
    prestamos_mora = db.scalar(select(func.count()).select_from(subq_mora.subquery())) or 0
    # Monto total cobrado este mes (cuotas con fecha_pago en el mes actual)
    pagos_mes = _safe_float(
        db.scalar(
            select(func.coalesce(func.sum(Cuota.monto), 0))
            .select_from(Cuota)
            .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
            .join(Cliente, Prestamo.cliente_id == Cliente.id)
            .where(
                Cliente.estado == "ACTIVO",
                Prestamo.estado == "APROBADO",
                Cuota.fecha_pago.isnot(None),
                func.date(Cuota.fecha_pago) >= inicio_mes,
                func.date(Cuota.fecha_pago) <= hoy,
            )
        )
        or 0
    )

    return {
        "total_clientes": total_clientes,
        "total_prestamos": total_prestamos,
        "total_pagos": total_pagos,
        "cartera_activa": _safe_float(cartera_activa),
        "pagos_vencidos": prestamos_mora,
        "pagos_mes": pagos_mes,
        "fecha_actualizacion": now_utc.isoformat(),
    }
