"""
Endpoints de reportes. GET /reportes/dashboard/resumen con datos reales desde BD.
"""
from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends
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


@router.get("/dashboard/resumen")
def get_resumen_dashboard(db: Session = Depends(get_db)):
    """
    Resumen para el dashboard de reportes: total_clientes, total_prestamos, total_pagos,
    cartera_activa, prestamos_mora, pagos_mes, fecha_actualizacion. Datos reales desde BD.
    """
    hoy = date.today()
    now_utc = datetime.now(timezone.utc)
    inicio_mes = hoy.replace(day=1)

    total_clientes = db.scalar(select(func.count()).select_from(Cliente)) or 0
    total_prestamos = db.scalar(
        select(func.count()).select_from(Prestamo).where(Prestamo.estado == "APROBADO")
    ) or 0
    total_pagos = db.scalar(
        select(func.count()).select_from(Cuota).where(Cuota.fecha_pago.isnot(None))
    ) or 0
    cartera_activa = db.scalar(
        select(func.coalesce(func.sum(Cuota.monto), 0)).select_from(Cuota).where(
            Cuota.fecha_pago.is_(None)
        )
    ) or 0
    # Préstamos con al menos una cuota vencida sin pagar
    subq_mora = (
        select(Cuota.prestamo_id)
        .where(
            Cuota.fecha_pago.is_(None),
            Cuota.fecha_vencimiento < hoy,
        )
        .distinct()
    )
    prestamos_mora = db.scalar(select(func.count()).select_from(subq_mora.subquery())) or 0
    pagos_mes = db.scalar(
        select(func.count()).select_from(Cuota).where(
            Cuota.fecha_pago.isnot(None),
            func.date(Cuota.fecha_pago) >= inicio_mes,
            func.date(Cuota.fecha_pago) <= hoy,
        )
    ) or 0

    return {
        "total_clientes": total_clientes,
        "total_prestamos": total_prestamos,
        "total_pagos": total_pagos,
        "cartera_activa": _safe_float(cartera_activa),
        "prestamos_mora": prestamos_mora,
        "pagos_mes": pagos_mes,
        "fecha_actualizacion": now_utc.isoformat(),
    }
