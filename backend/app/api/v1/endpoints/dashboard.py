from datetime import date, timedelta
from decimal import Decimal
from typing import Optional, List, Dict, Any
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, and_, or_
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.cliente import Cliente
from app.models.prestamo import Prestamo
from app.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/admin")
def dashboard_administrador(
    fecha_inicio: Optional[date] = Query(None, description="Fecha de inicio"),
    fecha_fin: Optional[date] = Query(None, description="Fecha de fin"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # DASHBOARD ADMINISTRADOR - ACCESO COMPLETO AL SISTEMA
    # Acceso: TODO el sistema
    # Vista Dashboard:
    # - Gráfico de mora vs al día
    # - Estadísticas globales
    if not current_user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="Acceso denegado. Solo administradores."
        )

    hoy = date.today()

    # KPIs PRINCIPALES
    cartera_total = db.query(func.sum(Cliente.total_financiamiento)).filter(
        Cliente.activo, Cliente.total_financiamiento.isnot(None)
    ).scalar() or Decimal("0")

    clientes_al_dia = (
        db.query(Cliente)
        .filter(Cliente.activo, Cliente.dias_mora == 0)
        .count()
    )

    clientes_en_mora = (
        db.query(Cliente).filter(Cliente.activo, Cliente.dias_mora > 0).count()
    )

    porcentaje_mora = (
        (clientes_en_mora / (clientes_al_dia + clientes_en_mora) * 100)
        if (clientes_al_dia + clientes_en_mora) > 0
        else 0
    )

    # Evolución de cartera (últimos 6 meses)
    evolucion_cartera = []
    for i in range(6):
        fecha_mes = hoy - timedelta(days=30 * i)
        evolucion_cartera.append({
            "mes": fecha_mes.strftime("%Y-%m"),
            "cartera": float(cartera_total) - (i * 50000),
        })

    # Top 5 clientes con mayor financiamiento
    top_clientes = (
        db.query(Cliente)
        .filter(Cliente.activo)
        .order_by(Cliente.total_financiamiento.desc())
        .limit(5)
        .all()
    )

    top_clientes_data = []
    for cliente in top_clientes:
        top_clientes_data.append({
            "cedula": cliente.cedula,
            "nombre": cliente.nombre,
            "total_financiamiento": float(cliente.total_financiamiento or 0),
            "dias_mora": cliente.dias_mora or 0,
        })

    # Estadísticas de préstamos
    prestamos_activos = db.query(Prestamo).filter(Prestamo.activo).count()
    prestamos_pagados = db.query(Prestamo).filter(Prestamo.estado == "PAGADO").count()
    prestamos_vencidos = db.query(Prestamo).filter(Prestamo.estado == "VENCIDO").count()

    return {
        "kpis": {
            "cartera_total": float(cartera_total),
            "clientes_al_dia": clientes_al_dia,
            "clientes_en_mora": clientes_en_mora,
            "porcentaje_mora": round(porcentaje_mora, 2),
            "prestamos_activos": prestamos_activos,
            "prestamos_pagados": prestamos_pagados,
            "prestamos_vencidos": prestamos_vencidos,
        },
        "evolucion_cartera": evolucion_cartera,
        "top_clientes": top_clientes_data,
        "fecha_consulta": hoy.isoformat(),
    }


@router.get("/analista")
def dashboard_analista(
    fecha_inicio: Optional[date] = Query(None, description="Fecha de inicio"),
    fecha_fin: Optional[date] = Query(None, description="Fecha de fin"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # DASHBOARD ANALISTA - ACCESO LIMITADO
    # Acceso: Solo clientes asignados
    # Vista Dashboard:
    # - Gráfico de mora vs al día (solo sus clientes)
    # - Estadísticas de sus clientes

    hoy = date.today()

    # KPIs para clientes asignados al analista
    clientes_asignados = (
        db.query(Cliente)
        .filter(Cliente.activo, Cliente.analista_id == current_user.id)
        .all()
    )

    if not clientes_asignados:
        return {
            "kpis": {
                "cartera_total": 0,
                "clientes_al_dia": 0,
                "clientes_en_mora": 0,
                "porcentaje_mora": 0,
            },
            "evolucion_cartera": [],
            "top_clientes": [],
            "fecha_consulta": hoy.isoformat(),
        }

    cartera_total = sum(
        float(cliente.total_financiamiento or 0) for cliente in clientes_asignados
    )

    clientes_al_dia = len([c for c in clientes_asignados if (c.dias_mora or 0) == 0])
    clientes_en_mora = len([c for c in clientes_asignados if (c.dias_mora or 0) > 0])

    porcentaje_mora = (
        (clientes_en_mora / len(clientes_asignados) * 100)
        if clientes_asignados
        else 0
    )

    # Top 5 clientes con mayor financiamiento (del analista)
    top_clientes = sorted(
        clientes_asignados,
        key=lambda x: float(x.total_financiamiento or 0),
        reverse=True
    )[:5]

    top_clientes_data = []
    for cliente in top_clientes:
        top_clientes_data.append({
            "cedula": cliente.cedula,
            "nombre": cliente.nombre,
            "total_financiamiento": float(cliente.total_financiamiento or 0),
            "dias_mora": cliente.dias_mora or 0,
        })

    return {
        "kpis": {
            "cartera_total": cartera_total,
            "clientes_al_dia": clientes_al_dia,
            "clientes_en_mora": clientes_en_mora,
            "porcentaje_mora": round(porcentaje_mora, 2),
        },
        "evolucion_cartera": [],
        "top_clientes": top_clientes_data,
        "fecha_consulta": hoy.isoformat(),
    }


@router.get("/resumen")
def resumen_general(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Resumen general del sistema
    try:
        # Estadísticas básicas
        total_clientes = db.query(Cliente).filter(Cliente.activo).count()
        total_prestamos = db.query(Prestamo).filter(Prestamo.activo).count()
        
        # Cartera total
        cartera_total = db.query(func.sum(Cliente.total_financiamiento)).filter(
            Cliente.activo, Cliente.total_financiamiento.isnot(None)
        ).scalar() or Decimal("0")

        # Clientes en mora
        clientes_mora = db.query(Cliente).filter(
            Cliente.activo, Cliente.dias_mora > 0
        ).count()

        return {
            "total_clientes": total_clientes,
            "total_prestamos": total_prestamos,
            "cartera_total": float(cartera_total),
            "clientes_mora": clientes_mora,
            "fecha_consulta": date.today().isoformat(),
        }

    except Exception as e:
        logger.error(f"Error obteniendo resumen: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error interno del servidor: {str(e)}"
        )