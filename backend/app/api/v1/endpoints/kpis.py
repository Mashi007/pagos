import logging
from datetime import date
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
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
        Prestamo.estado == "APROBADO"
    )
    cartera_query = FiltrosDashboard.aplicar_filtros_prestamo(
        cartera_query, analista, concesionario, modelo, fecha_inicio, fecha_fin
    )
    cartera_total = cartera_query.scalar() or Decimal("0")

    # ✅ Clientes al día - usar filtros automáticos
    clientes_query = db.query(func.count(func.distinct(Prestamo.cedula))).filter(
        Prestamo.estado == "APROBADO"
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
        .filter(Cuota.fecha_vencimiento < fecha_corte, Cuota.estado == "PENDIENTE")
    )
    cuotas_query = FiltrosDashboard.aplicar_filtros_cuota(
        cuotas_query, analista, concesionario, modelo, fecha_inicio, fecha_fin
    )
    cuotas_vencidas = cuotas_query.scalar() or 0

    # ✅ KPIs adicionales de amortizaciones - usar filtros automáticos
    # Total de cuotas
    total_cuotas_query = db.query(func.count(Cuota.id)).join(
        Prestamo, Cuota.prestamo_id == Prestamo.id
    )
    total_cuotas_query = FiltrosDashboard.aplicar_filtros_cuota(
        total_cuotas_query, analista, concesionario, modelo, fecha_inicio, fecha_fin
    )
    total_cuotas = total_cuotas_query.scalar() or 0

    # Cuotas pendientes (total)
    cuotas_pendientes_query = (
        db.query(func.count(Cuota.id))
        .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
        .filter(Cuota.estado.in_(["PENDIENTE", "ATRASADO", "PARCIAL"]))
    )
    cuotas_pendientes_query = FiltrosDashboard.aplicar_filtros_cuota(
        cuotas_pendientes_query,
        analista,
        concesionario,
        modelo,
        fecha_inicio,
        fecha_fin,
    )
    cuotas_pendientes = cuotas_pendientes_query.scalar() or 0

    # Cuotas pagadas
    cuotas_pagadas_query = (
        db.query(func.count(Cuota.id))
        .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
        .filter(Cuota.estado == "PAGADO")
    )
    cuotas_pagadas_query = FiltrosDashboard.aplicar_filtros_cuota(
        cuotas_pagadas_query, analista, concesionario, modelo, fecha_inicio, fecha_fin
    )
    cuotas_pagadas = cuotas_pagadas_query.scalar() or 0

    # Saldo pendiente total (capital + interés + mora)
    saldo_pendiente_query = (
        db.query(
            func.sum(
                Cuota.capital_pendiente + Cuota.interes_pendiente + Cuota.monto_mora
            )
        )
        .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
        .filter(Cuota.estado.in_(["PENDIENTE", "ATRASADO", "PARCIAL"]))
    )
    saldo_pendiente_query = FiltrosDashboard.aplicar_filtros_cuota(
        saldo_pendiente_query, analista, concesionario, modelo, fecha_inicio, fecha_fin
    )
    saldo_pendiente = saldo_pendiente_query.scalar() or Decimal("0")

    # Monto total vencido (solo cuotas vencidas)
    monto_vencido_query = (
        db.query(
            func.sum(
                Cuota.capital_pendiente + Cuota.interes_pendiente + Cuota.monto_mora
            )
        )
        .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
        .filter(
            Cuota.fecha_vencimiento < fecha_corte,
            Cuota.estado.in_(["PENDIENTE", "ATRASADO", "PARCIAL"]),
        )
    )
    monto_vencido_query = FiltrosDashboard.aplicar_filtros_cuota(
        monto_vencido_query, analista, concesionario, modelo, fecha_inicio, fecha_fin
    )
    monto_vencido = monto_vencido_query.scalar() or Decimal("0")

    # Total pagado en cuotas (capital + interés + mora)
    total_pagado_cuotas_query = db.query(
        func.sum(Cuota.capital_pagado + Cuota.interes_pagado + Cuota.mora_pagada)
    ).join(Prestamo, Cuota.prestamo_id == Prestamo.id)
    total_pagado_cuotas_query = FiltrosDashboard.aplicar_filtros_cuota(
        total_pagado_cuotas_query,
        analista,
        concesionario,
        modelo,
        fecha_inicio,
        fecha_fin,
    )
    total_pagado_cuotas = total_pagado_cuotas_query.scalar() or Decimal("0")

    # Porcentaje de recuperación (total pagado / cartera total)
    porcentaje_recuperacion = (
        float((total_pagado_cuotas / cartera_total) * 100) if cartera_total > 0 else 0.0
    )

    # Porcentaje de cuotas pagadas
    porcentaje_cuotas_pagadas = (
        float((cuotas_pagadas / total_cuotas) * 100) if total_cuotas > 0 else 0.0
    )

    return {
        "cartera_total": float(cartera_total),
        "clientes_al_dia": clientes_al_dia,
        "pagos_mes": float(pagos_mes),
        "cuotas_vencidas": cuotas_vencidas,
        "fecha_corte": str(fecha_corte),
        # Nuevos KPIs de amortizaciones
        "total_cuotas": total_cuotas,
        "cuotas_pendientes": cuotas_pendientes,
        "cuotas_pagadas": cuotas_pagadas,
        "saldo_pendiente": float(saldo_pendiente),
        "monto_vencido": float(monto_vencido),
        "total_pagado_cuotas": float(total_pagado_cuotas),
        "porcentaje_recuperacion": porcentaje_recuperacion,
        "porcentaje_cuotas_pagadas": porcentaje_cuotas_pagadas,
    }


@router.get("/analistas")
def kpis_analistas(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """KPIs por analista"""

    # Analistas con más clientes
    # CORREGIDO: Cliente no tiene analista_id, usar Prestamo.analista
    analistas_clientes = (
        db.query(
            Prestamo.analista.label("nombre_analista"),
            func.count(func.distinct(Cliente.id)).label("total_clientes"),
        )
        .join(Cliente, Prestamo.cedula == Cliente.cedula)
        .filter(Prestamo.analista.isnot(None), Prestamo.analista != "")
        .group_by(Prestamo.analista)
        .order_by(func.count(func.distinct(Cliente.id)).desc())
        .limit(10)
        .all()
    )

    return {
        "analistas_clientes": [
            {
                "nombre": analista.nombre_analista,
                "total_clientes": analista.total_clientes,
            }
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
    # CORREGIDO: Cliente no tiene total_financiamiento, usar Prestamo.total_financiamiento
    cartera_estado = (
        db.query(Cliente.estado, func.sum(Prestamo.total_financiamiento).label("total"))
        .join(Prestamo, Cliente.cedula == Prestamo.cedula)
        .filter(Prestamo.estado == "APROBADO")
        .group_by(Cliente.estado)
        .all()
    )

    return {
        "cartera_por_estado": [
            {"estado": estado, "total": float(total)}
            for estado, total in cartera_estado
        ]
    }


@router.get("/prestamos")
def kpis_prestamos(
    analista: Optional[str] = Query(None, description="Filtrar por analista"),
    concesionario: Optional[str] = Query(None, description="Filtrar por concesionario"),
    modelo: Optional[str] = Query(None, description="Filtrar por modelo"),
    fecha_inicio: Optional[date] = Query(None, description="Fecha inicio"),
    fecha_fin: Optional[date] = Query(None, description="Fecha fin"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    KPIs específicos para el componente PrestamosKPIs

    Devuelve:
    - totalFinanciamiento: Suma de todos los total_financiamiento
    - totalPrestamos: Conteo total de préstamos
    - promedioMonto: Promedio del monto financiado
    - totalCarteraVigente: Suma de total_financiamiento solo de préstamos APROBADOS

    ✅ SOPORTA FILTROS AUTOMÁTICOS mediante FiltrosDashboard
    """
    try:
        # Base query para todos los préstamos
        base_query = db.query(Prestamo)
        base_query = FiltrosDashboard.aplicar_filtros_prestamo(
            base_query, analista, concesionario, modelo, fecha_inicio, fecha_fin
        )

        # Total financiamiento (suma de todos los préstamos)
        total_financiamiento_query = base_query.with_entities(
            func.sum(Prestamo.total_financiamiento)
        )
        total_financiamiento = total_financiamiento_query.scalar() or Decimal("0")

        # Total préstamos (conteo)
        total_prestamos_query = base_query.with_entities(func.count(Prestamo.id))
        total_prestamos = total_prestamos_query.scalar() or 0

        # Promedio monto
        promedio_monto = (
            float(total_financiamiento / total_prestamos)
            if total_prestamos > 0
            else 0.0
        )

        # Cartera vigente (solo préstamos APROBADOS)
        cartera_vigente_query = base_query.filter(Prestamo.estado == "APROBADO")
        cartera_vigente_query = FiltrosDashboard.aplicar_filtros_prestamo(
            cartera_vigente_query,
            analista,
            concesionario,
            modelo,
            fecha_inicio,
            fecha_fin,
        )
        total_cartera_vigente = cartera_vigente_query.with_entities(
            func.sum(Prestamo.total_financiamiento)
        ).scalar() or Decimal("0")

        return {
            "totalFinanciamiento": float(total_financiamiento),
            "totalPrestamos": total_prestamos,
            "promedioMonto": promedio_monto,
            "totalCarteraVigente": float(total_cartera_vigente),
        }
    except Exception as e:
        logger.error(f"Error obteniendo KPIs de préstamos: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error interno al obtener KPIs: {str(e)}"
        )
