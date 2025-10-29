import logging
from decimal import Decimal
from typing import Optional
from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.amortizacion import Cuota
from app.models.analista import Analista
from app.models.cliente import Cliente
from app.models.pago import Pago
from app.models.prestamo import Prestamo
from app.models.user import User
from app.utils.filtros_dashboard import FiltrosDashboard

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/dashboard")
def dashboard_kpis_principales(
    fecha_corte: Optional[str] = Query(
        None, description="Fecha de corte (default: hoy)"
    ),
    analista: Optional[str] = Query(None, description="Filtrar por analista"),
    concesionario: Optional[str] = Query(None, description="Filtrar por concesionario"),
    modelo: Optional[str] = Query(None, description="Filtrar por modelo"),
    fecha_inicio: Optional[date] = Query(None, description="Fecha inicio"),
    fecha_fin: Optional[date] = Query(None, description="Fecha fin"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    KPIs principales del dashboard
    
    ✅ SOPORTA FILTROS AUTOMÁTICOS:
    - analista: Filtrar por analista
    - concesionario: Filtrar por concesionario
    - modelo: Filtrar por modelo
    - fecha_inicio/fecha_fin: Rango de fechas
    
    Cualquier KPI nuevo agregado aquí debe usar FiltrosDashboard para aplicar filtros automáticamente.
    """
    if not fecha_corte:
        fecha_corte = date.today()
    elif isinstance(fecha_corte, str):
        fecha_corte = date.fromisoformat(fecha_corte)

    # ✅ Cartera total - usar filtros automáticos
    cartera_query = db.query(func.sum(Prestamo.total_financiamiento)).filter(
        Prestamo.activo.is_(True)
    )
    cartera_query = FiltrosDashboard.aplicar_filtros_prestamo(
        cartera_query, analista, concesionario, modelo, fecha_inicio, fecha_fin
    )
    cartera_total = cartera_query.scalar() or Decimal("0")

    # ✅ Clientes al día - usar filtros automáticos
    clientes_query = db.query(func.count(func.distinct(Prestamo.cedula))).filter(
        Prestamo.activo.is_(True)
    )
    clientes_query = FiltrosDashboard.aplicar_filtros_prestamo(
        clientes_query, analista, concesionario, modelo, fecha_inicio, fecha_fin
    )
    clientes_al_dia = clientes_query.scalar() or 0

    # ✅ Pagos del mes - usar filtros automáticos
    pagos_query = db.query(func.sum(Pago.monto_pagado)).filter(
        func.date_trunc("month", Pago.fecha_pago)
        == func.date_trunc("month", fecha_corte)
    )
    if analista or concesionario or modelo:
        pagos_query = pagos_query.join(Prestamo, Pago.prestamo_id == Prestamo.id)
    pagos_query = FiltrosDashboard.aplicar_filtros_pago(
        pagos_query, analista, concesionario, modelo, fecha_inicio, fecha_fin
    )
    pagos_mes = pagos_query.scalar() or Decimal("0")

    # ✅ Cuotas vencidas - usar filtros automáticos
    cuotas_query = (
        db.query(func.count(Cuota.id))
        .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
        .filter(
            Cuota.fecha_vencimiento < fecha_corte,
            Cuota.estado == "PENDIENTE"
        )
    )
    cuotas_query = FiltrosDashboard.aplicar_filtros_cuota(
        cuotas_query, analista, concesionario, modelo, fecha_inicio, fecha_fin
    )
    cuotas_vencidas = cuotas_query.scalar() or 0

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
