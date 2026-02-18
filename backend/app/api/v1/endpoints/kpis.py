"""
Endpoints de KPIs. Datos reales desde BD (Prestamo, Cuota).
GET /kpis/dashboard usado por DashboardFinanciamiento y DashboardCuotas.
"""
from datetime import date
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


@router.get("/dashboard")
def get_kpis_dashboard(
    fecha_inicio: Optional[str] = Query(None),
    fecha_fin: Optional[str] = Query(None),
    analista: Optional[str] = Query(None),
    concesionario: Optional[str] = Query(None),
    modelo: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """KPIs del dashboard desde BD: total_prestamos, total_morosidad (solo clientes ACTIVOS)."""
    hoy = date.today()
    q_prestamos = (
        select(Prestamo)
        .join(Cliente, Prestamo.cliente_id == Cliente.id)
        .where(Cliente.estado == "ACTIVO", Prestamo.estado == "APROBADO")
    )
    if analista:
        q_prestamos = q_prestamos.where(Prestamo.analista == analista)
    if concesionario:
        q_prestamos = q_prestamos.where(Prestamo.concesionario == concesionario)
    if modelo:
        q_prestamos = q_prestamos.where(Prestamo.modelo_vehiculo == modelo)
    total_prestamos = db.scalar(select(func.count()).select_from(q_prestamos.subquery())) or 0
    # Morosidad: suma monto de cuotas vencidas no pagadas (solo clientes ACTIVOS)
    total_morosidad = db.scalar(
        select(func.coalesce(func.sum(Cuota.monto), 0))
        .select_from(Cuota)
        .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
        .join(Cliente, Prestamo.cliente_id == Cliente.id)
        .where(
            Cliente.estado == "ACTIVO",
            Prestamo.estado == "APROBADO",
            Cuota.fecha_pago.is_(None),
            Cuota.fecha_vencimiento < hoy,
        )
    ) or 0
    kpis = [
        {"nombre": "Total préstamos", "valor": total_prestamos, "variacion": 0},
        {"nombre": "Morosidad", "valor": _safe_float(total_morosidad), "variacion": 0},
    ]
    return {
        "kpis": kpis,
        "total_prestamos": total_prestamos,
        "total_morosidad": _safe_float(total_morosidad),
    }
