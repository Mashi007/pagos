import logging
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.amortizacion import Cuota
from app.models.analista import Analista
from app.models.cliente import Cliente
from app.models.pago import Pago
from app.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/dashboard")
def dashboard_kpis_principales(
    fecha_corte: Optional[str] = Query(
        None, description="Fecha de corte (default: hoy)"
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """KPIs principales del dashboard"""
    from datetime import date

    if not fecha_corte:
        fecha_corte = date.today()

    # Cartera total
    cartera_total = db.query(func.sum(Cliente.total_financiamiento)).filter(
        Cliente.total_financiamiento.isnot(None)
    ).scalar() or Decimal("0")

    # Clientes al día
    clientes_al_dia = (
        db.query(func.count(Cliente.id)).filter(Cliente.estado == "ACTIVO").scalar()
        or 0
    )

    # Pagos del mes
    pagos_mes = db.query(func.sum(Pago.monto)).filter(
        func.date_trunc("month", Pago.fecha_pago)
        == func.date_trunc("month", fecha_corte)
    ).scalar() or Decimal("0")

    # Cuotas vencidas
    cuotas_vencidas = (
        db.query(func.count(Cuota.id))
        .filter(Cuota.fecha_vencimiento < fecha_corte)
        .filter(Cuota.estado == "PENDIENTE")
        .scalar()
        or 0
    )

    return {
        "cartera_total": float(cartera_total),
        "clientes_al_dia": clientes_al_dia,
        "pagos_mes": float(pagos_mes),
        "cuotas_vencidas": cuotas_vencidas,
        "fecha_corte": str(fecha_corte),
    }


@router.get("/analistas")
def kpis_analistas(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """KPIs por analista"""

    # Analistas con más clientes
    analistas_clientes = (
        db.query(Analista.nombre, func.count(Cliente.id).label("total_clientes"))
        .join(Cliente, Analista.id == Cliente.analista_id)
        .group_by(Analista.id, Analista.nombre)
        .order_by(func.count(Cliente.id).desc())
        .limit(10)
        .all()
    )

    return {
        "analistas_clientes": [
            {"nombre": analista.nombre, "total_clientes": analista.total_clientes}
            for analista in analistas_clientes
        ]
    }


@router.get("/cartera")
def kpis_cartera(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """KPIs de cartera"""

    # Cartera por estado
    cartera_estado = (
        db.query(Cliente.estado, func.sum(Cliente.total_financiamiento).label("total"))
        .group_by(Cliente.estado)
        .all()
    )

    return {
        "cartera_por_estado": [
            {"estado": estado, "total": float(total)}
            for estado, total in cartera_estado
        ]
    }
