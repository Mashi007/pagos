import logging
from calendar import monthrange
from datetime import date
from decimal import Decimal
from typing import Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, distinct, func, or_
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.cache import cache_result
from app.models.amortizacion import Cuota, pago_cuotas
from app.models.analista import Analista
from app.models.cliente import Cliente
from app.models.pago import Pago  # Mantener para operaciones que necesiten tabla pagos
from app.models.pago_staging import PagoStaging  # Usar para consultas principales (donde están los datos)
from app.models.prestamo import Prestamo
from app.models.user import User
from app.utils.filtros_dashboard import FiltrosDashboard

logger = logging.getLogger(__name__)
router = APIRouter()


def _normalizar_fecha_corte(fecha_corte: Optional[str]) -> date:
    """Normaliza la fecha de corte a date"""
    if not fecha_corte:
        return date.today()
    if isinstance(fecha_corte, str):
        return date.fromisoformat(fecha_corte)
    return fecha_corte


def _calcular_kpis_basicos(
    db: Session,
    fecha_corte: date,
    analista: Optional[str],
    concesionario: Optional[str],
    modelo: Optional[str],
    fecha_inicio: Optional[date],
    fecha_fin: Optional[date],
) -> Dict:
    """Calcula KPIs básicos: cartera, clientes al día, pagos del mes, cuotas vencidas"""
    # Cartera total
    cartera_query = db.query(func.sum(Prestamo.total_financiamiento)).filter(Prestamo.estado == "APROBADO")
    cartera_query = FiltrosDashboard.aplicar_filtros_prestamo(
        cartera_query, analista, concesionario, modelo, fecha_inicio, fecha_fin
    )
    cartera_total = cartera_query.scalar() or Decimal("0")

    # Clientes al día
    clientes_con_cuotas_query = (
        db.query(func.count(func.distinct(Prestamo.cedula)))
        .join(Cuota, Cuota.prestamo_id == Prestamo.id)
        .filter(Prestamo.estado == "APROBADO")
    )
    clientes_con_cuotas_query = FiltrosDashboard.aplicar_filtros_prestamo(
        clientes_con_cuotas_query, analista, concesionario, modelo, fecha_inicio, fecha_fin
    )
    clientes_con_cuotas = clientes_con_cuotas_query.scalar() or 0

    clientes_en_mora_query = (
        db.query(func.count(func.distinct(Prestamo.cedula)))
        .join(Cuota, Cuota.prestamo_id == Prestamo.id)
        .filter(
            Prestamo.estado == "APROBADO",
            Cuota.fecha_vencimiento < fecha_corte,
            Cuota.estado.in_(["PENDIENTE", "ATRASADO", "PARCIAL"]),
        )
    )
    clientes_en_mora_query = FiltrosDashboard.aplicar_filtros_cuota(
        clientes_en_mora_query, analista, concesionario, modelo, fecha_inicio, fecha_fin
    )
    clientes_en_mora = clientes_en_mora_query.scalar() or 0
    clientes_al_dia = max(0, clientes_con_cuotas - clientes_en_mora)

    # Pagos del mes (usa PagoStaging donde están los datos)
    pagos_query = db.query(func.sum(PagoStaging.monto_pagado)).filter(
        func.date_trunc("month", PagoStaging.fecha_pago) == func.date_trunc("month", fecha_corte)
    )
    pagos_query = FiltrosDashboard.aplicar_filtros_pago(pagos_query, analista, concesionario, modelo, fecha_inicio, fecha_fin)
    pagos_mes = pagos_query.scalar() or Decimal("0")

    # Cuotas vencidas
    cuotas_query = (
        db.query(func.count(Cuota.id))
        .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
        .filter(Cuota.fecha_vencimiento < fecha_corte, Cuota.estado == "PENDIENTE")
    )
    cuotas_query = FiltrosDashboard.aplicar_filtros_cuota(
        cuotas_query, analista, concesionario, modelo, fecha_inicio, fecha_fin
    )
    cuotas_vencidas = cuotas_query.scalar() or 0

    return {
        "cartera_total": cartera_total,
        "clientes_al_dia": clientes_al_dia,
        "pagos_mes": pagos_mes,
        "cuotas_vencidas": cuotas_vencidas,
    }


def _calcular_kpis_amortizaciones(
    db: Session,
    fecha_corte: date,
    analista: Optional[str],
    concesionario: Optional[str],
    modelo: Optional[str],
    fecha_inicio: Optional[date],
    fecha_fin: Optional[date],
) -> Dict:
    """Calcula KPIs relacionados con amortizaciones"""
    # Total de cuotas
    total_cuotas_query = db.query(func.count(Cuota.id)).join(Prestamo, Cuota.prestamo_id == Prestamo.id)
    total_cuotas_query = FiltrosDashboard.aplicar_filtros_cuota(
        total_cuotas_query, analista, concesionario, modelo, fecha_inicio, fecha_fin
    )
    total_cuotas = total_cuotas_query.scalar() or 0

    # Cuotas pendientes
    cuotas_pendientes_query = (
        db.query(func.count(Cuota.id))
        .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
        .filter(Cuota.estado.in_(["PENDIENTE", "ATRASADO", "PARCIAL"]))
    )
    cuotas_pendientes_query = FiltrosDashboard.aplicar_filtros_cuota(
        cuotas_pendientes_query, analista, concesionario, modelo, fecha_inicio, fecha_fin
    )
    cuotas_pendientes = cuotas_pendientes_query.scalar() or 0

    # Cuotas pagadas
    cuotas_pagadas_query = (
        db.query(func.count(Cuota.id)).join(Prestamo, Cuota.prestamo_id == Prestamo.id).filter(Cuota.estado == "PAGADO")
    )
    cuotas_pagadas_query = FiltrosDashboard.aplicar_filtros_cuota(
        cuotas_pagadas_query, analista, concesionario, modelo, fecha_inicio, fecha_fin
    )
    cuotas_pagadas = cuotas_pagadas_query.scalar() or 0

    # Saldo pendiente
    saldo_pendiente_query = (
        db.query(func.sum(Cuota.capital_pendiente + Cuota.interes_pendiente + Cuota.monto_mora))
        .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
        .filter(Cuota.estado.in_(["PENDIENTE", "ATRASADO", "PARCIAL"]))
    )
    saldo_pendiente_query = FiltrosDashboard.aplicar_filtros_cuota(
        saldo_pendiente_query, analista, concesionario, modelo, fecha_inicio, fecha_fin
    )
    saldo_pendiente = saldo_pendiente_query.scalar() or Decimal("0")

    # Monto vencido
    monto_vencido_query = (
        db.query(func.sum(Cuota.capital_pendiente + Cuota.interes_pendiente + Cuota.monto_mora))
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

    # Total pagado en cuotas
    total_pagado_cuotas_query = db.query(func.sum(Cuota.capital_pagado + Cuota.interes_pagado + Cuota.mora_pagada)).join(
        Prestamo, Cuota.prestamo_id == Prestamo.id
    )
    total_pagado_cuotas_query = FiltrosDashboard.aplicar_filtros_cuota(
        total_pagado_cuotas_query, analista, concesionario, modelo, fecha_inicio, fecha_fin
    )
    total_pagado_cuotas = total_pagado_cuotas_query.scalar() or Decimal("0")

    return {
        "total_cuotas": total_cuotas,
        "cuotas_pendientes": cuotas_pendientes,
        "cuotas_pagadas": cuotas_pagadas,
        "saldo_pendiente": saldo_pendiente,
        "monto_vencido": monto_vencido,
        "total_pagado_cuotas": total_pagado_cuotas,
    }


def _calcular_kpis_mes_actual(
    db: Session,
    fecha_corte: date,
    analista: Optional[str],
    concesionario: Optional[str],
    modelo: Optional[str],
) -> Dict:
    """Calcula KPIs del mes actual: cuotas del mes, conciliadas, atrasadas, impagas"""
    hoy = fecha_corte if isinstance(fecha_corte, date) else date.today()
    año_actual = hoy.year
    mes_actual = hoy.month
    primer_dia_mes = date(año_actual, mes_actual, 1)
    ultimo_dia_mes = date(año_actual, mes_actual, monthrange(año_actual, mes_actual)[1])

    # Total de cuotas del mes
    cuotas_mes_query = (
        db.query(func.count(Cuota.id))
        .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
        .filter(
            func.date(Cuota.fecha_vencimiento) >= primer_dia_mes,
            func.date(Cuota.fecha_vencimiento) <= ultimo_dia_mes,
        )
    )
    cuotas_mes_query = FiltrosDashboard.aplicar_filtros_cuota(cuotas_mes_query, analista, concesionario, modelo, None, None)
    total_cuotas_mes = cuotas_mes_query.scalar() or 0

    # Cuotas conciliadas
    cuotas_conciliadas_query = (
        db.query(func.count(func.distinct(Cuota.id)))
        .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
        .join(pago_cuotas, pago_cuotas.c.cuota_id == Cuota.id)
        .join(Pago, pago_cuotas.c.pago_id == Pago.id)
        .filter(Pago.conciliado.is_(True))
    )
    if analista or concesionario or modelo:
        if analista:
            cuotas_conciliadas_query = cuotas_conciliadas_query.filter(
                or_(Prestamo.analista == analista, Prestamo.producto_financiero == analista)
            )
        if concesionario:
            cuotas_conciliadas_query = cuotas_conciliadas_query.filter(Prestamo.concesionario == concesionario)
        if modelo:
            cuotas_conciliadas_query = cuotas_conciliadas_query.filter(
                or_(Prestamo.producto == modelo, Prestamo.modelo_vehiculo == modelo)
            )
    total_cuotas_conciliadas = cuotas_conciliadas_query.scalar() or 0

    # Cuotas atrasadas del mes
    cuotas_atrasadas_mes_query = (
        db.query(func.count(Cuota.id))
        .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
        .filter(
            func.date(Cuota.fecha_vencimiento) >= primer_dia_mes,
            func.date(Cuota.fecha_vencimiento) <= ultimo_dia_mes,
            Cuota.estado != "PAGADO",
        )
        .filter(
            ~Cuota.id.in_(
                db.query(pago_cuotas.c.cuota_id).join(PagoStaging, pago_cuotas.c.pago_id == PagoStaging.id).filter(PagoStaging.conciliado.is_(True))
            )
        )
    )
    cuotas_atrasadas_mes_query = FiltrosDashboard.aplicar_filtros_cuota(
        cuotas_atrasadas_mes_query, analista, concesionario, modelo, None, None
    )
    cuotas_atrasadas_mes = cuotas_atrasadas_mes_query.scalar() or 0

    # Cuotas impagas 2 o más por cliente
    clientes_cuotas_impagas_query = (
        db.query(Prestamo.cedula, func.count(Cuota.id).label("cantidad_impagas"))
        .join(Cuota, Cuota.prestamo_id == Prestamo.id)
        .filter(Cuota.estado != "PAGADO")
        .group_by(Prestamo.cedula)
        .having(func.count(Cuota.id) >= 2)
    )
    if analista:
        clientes_cuotas_impagas_query = clientes_cuotas_impagas_query.filter(
            or_(Prestamo.analista == analista, Prestamo.producto_financiero == analista)
        )
    if concesionario:
        clientes_cuotas_impagas_query = clientes_cuotas_impagas_query.filter(Prestamo.concesionario == concesionario)
    if modelo:
        clientes_cuotas_impagas_query = clientes_cuotas_impagas_query.filter(
            or_(Prestamo.producto == modelo, Prestamo.modelo_vehiculo == modelo)
        )
    clientes_con_impagas = clientes_cuotas_impagas_query.all()
    total_cuotas_impagas_2mas = sum(cantidad for cedula, cantidad in clientes_con_impagas)

    return {
        "total_cuotas_mes": total_cuotas_mes,
        "total_cuotas_conciliadas": total_cuotas_conciliadas,
        "cuotas_atrasadas_mes": cuotas_atrasadas_mes,
        "total_cuotas_impagas_2mas": total_cuotas_impagas_2mas,
    }


def _calcular_kpis_financiamiento_por_estado(
    db: Session,
    analista: Optional[str],
    concesionario: Optional[str],
    modelo: Optional[str],
    fecha_inicio: Optional[date],
    fecha_fin: Optional[date],
) -> Dict:
    """Calcula KPIs de financiamiento por estado de cliente"""

    def crear_query_prestamo_base():
        query = db.query(Prestamo)
        return FiltrosDashboard.aplicar_filtros_prestamo(query, analista, concesionario, modelo, fecha_inicio, fecha_fin)

    total_financiamiento_query = crear_query_prestamo_base().with_entities(func.sum(Prestamo.total_financiamiento))
    total_financiamiento = total_financiamiento_query.scalar() or Decimal("0")

    total_financiamiento_activo_query = (
        crear_query_prestamo_base()
        .join(Cliente, Prestamo.cedula == Cliente.cedula)
        .filter(Cliente.estado == "ACTIVO")
        .with_entities(func.sum(Prestamo.total_financiamiento))
    )
    total_financiamiento_activo = total_financiamiento_activo_query.scalar() or Decimal("0")

    total_financiamiento_inactivo_query = (
        crear_query_prestamo_base()
        .join(Cliente, Prestamo.cedula == Cliente.cedula)
        .filter(Cliente.estado == "INACTIVO")
        .with_entities(func.sum(Prestamo.total_financiamiento))
    )
    total_financiamiento_inactivo = total_financiamiento_inactivo_query.scalar() or Decimal("0")

    total_financiamiento_finalizado_query = (
        crear_query_prestamo_base()
        .join(Cliente, Prestamo.cedula == Cliente.cedula)
        .filter(Cliente.estado == "FINALIZADO")
        .with_entities(func.sum(Prestamo.total_financiamiento))
    )
    total_financiamiento_finalizado = total_financiamiento_finalizado_query.scalar() or Decimal("0")

    return {
        "total_financiamiento": total_financiamiento,
        "total_financiamiento_activo": total_financiamiento_activo,
        "total_financiamiento_inactivo": total_financiamiento_inactivo,
        "total_financiamiento_finalizado": total_financiamiento_finalizado,
    }


@router.get("/dashboard")
@cache_result(ttl=300, key_prefix="kpis")  # Cache por 5 minutos
def dashboard_kpis_principales(
    fecha_corte: Optional[str] = Query(None, description="Fecha de corte (default: hoy)"),
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
    fecha_corte = _normalizar_fecha_corte(fecha_corte)

    kpis_basicos = _calcular_kpis_basicos(db, fecha_corte, analista, concesionario, modelo, fecha_inicio, fecha_fin)
    kpis_amortizaciones = _calcular_kpis_amortizaciones(
        db, fecha_corte, analista, concesionario, modelo, fecha_inicio, fecha_fin
    )
    kpis_mes = _calcular_kpis_mes_actual(db, fecha_corte, analista, concesionario, modelo)
    kpis_financiamiento = _calcular_kpis_financiamiento_por_estado(
        db, analista, concesionario, modelo, fecha_inicio, fecha_fin
    )

    # Calcular porcentajes
    porcentaje_recuperacion = (
        float((kpis_amortizaciones["total_pagado_cuotas"] / kpis_basicos["cartera_total"]) * 100)
        if kpis_basicos["cartera_total"] > 0
        else 0.0
    )
    porcentaje_cuotas_pagadas = (
        float((kpis_amortizaciones["cuotas_pagadas"] / kpis_amortizaciones["total_cuotas"]) * 100)
        if kpis_amortizaciones["total_cuotas"] > 0
        else 0.0
    )

    return {
        "cartera_total": float(kpis_basicos["cartera_total"]),
        "clientes_al_dia": kpis_basicos["clientes_al_dia"],
        "pagos_mes": float(kpis_basicos["pagos_mes"]),
        "cuotas_vencidas": kpis_basicos["cuotas_vencidas"],
        "fecha_corte": str(fecha_corte),
        "total_cuotas": kpis_amortizaciones["total_cuotas"],
        "cuotas_pendientes": kpis_amortizaciones["cuotas_pendientes"],
        "cuotas_pagadas": kpis_amortizaciones["cuotas_pagadas"],
        "saldo_pendiente": float(kpis_amortizaciones["saldo_pendiente"]),
        "monto_vencido": float(kpis_amortizaciones["monto_vencido"]),
        "total_pagado_cuotas": float(kpis_amortizaciones["total_pagado_cuotas"]),
        "porcentaje_recuperacion": porcentaje_recuperacion,
        "porcentaje_cuotas_pagadas": porcentaje_cuotas_pagadas,
        "total_financiamiento": float(kpis_financiamiento["total_financiamiento"]),
        "total_financiamiento_activo": float(kpis_financiamiento["total_financiamiento_activo"]),
        "total_financiamiento_inactivo": float(kpis_financiamiento["total_financiamiento_inactivo"]),
        "total_financiamiento_finalizado": float(kpis_financiamiento["total_financiamiento_finalizado"]),
        "total_cuotas_mes": kpis_mes["total_cuotas_mes"],
        "total_cuotas_conciliadas": kpis_mes["total_cuotas_conciliadas"],
        "cuotas_atrasadas_mes": kpis_mes["cuotas_atrasadas_mes"],
        "total_cuotas_impagas_2mas": kpis_mes["total_cuotas_impagas_2mas"],
    }


@router.get("/analistas")
@cache_result(ttl=300, key_prefix="kpis")  # Cache por 5 minutos
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
@cache_result(ttl=300, key_prefix="kpis")  # Cache por 5 minutos
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

    return {"cartera_por_estado": [{"estado": estado, "total": float(total)} for estado, total in cartera_estado]}


@router.get("/prestamos")
@cache_result(ttl=300, key_prefix="kpis")  # Cache por 5 minutos
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
        total_financiamiento_query = base_query.with_entities(func.sum(Prestamo.total_financiamiento))
        total_financiamiento = total_financiamiento_query.scalar() or Decimal("0")

        # Total préstamos (conteo)
        total_prestamos_query = base_query.with_entities(func.count(Prestamo.id))
        total_prestamos = total_prestamos_query.scalar() or 0

        # Promedio monto
        promedio_monto = float(total_financiamiento / total_prestamos) if total_prestamos > 0 else 0.0

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
        raise HTTPException(status_code=500, detail=f"Error interno al obtener KPIs: {str(e)}")
