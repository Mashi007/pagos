"""
Endpoints para el módulo de Cobranzas
"""

import logging
from datetime import date, datetime, timedelta
from io import BytesIO
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy import and_, func, or_, case
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.amortizacion import Cuota
from app.models.cliente import Cliente
from app.models.prestamo import Prestamo
from app.models.user import User

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/clientes-atrasados")
def obtener_clientes_atrasados(
    dias_retraso: int = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Obtener clientes atrasados filtrados por días de retraso

    Args:
        dias_retraso: Filtrar por días específicos de retraso (1, 3, 5, etc.)
                     Si es None, devuelve todos los clientes atrasados
    """
    try:
        # Calcular fecha límite según días de retraso
        hoy = date.today()

        # Cuotas vencidas (fecha_vencimiento < hoy y estado != PAGADO)
        query = (
            db.query(
                Cliente.cedula,
                Cliente.nombres,
                Prestamo.usuario_proponente.label("analista"),
                Prestamo.id.label("prestamo_id"),
                func.count(Cuota.id).label("cuotas_vencidas"),
                func.sum(Cuota.monto_cuota).label("total_adeudado"),
                func.min(Cuota.fecha_vencimiento).label("fecha_primera_vencida"),
            )
            .join(Prestamo, Prestamo.cedula == Cliente.cedula)
            .join(Cuota, Cuota.prestamo_id == Prestamo.id)
            .filter(Cuota.fecha_vencimiento < hoy, Cuota.estado != "PAGADO")
            .group_by(
                Cliente.cedula,
                Cliente.nombres,
                Prestamo.usuario_proponente,
                Prestamo.id,
            )
        )

        # Si se especifica días de retraso, filtrar por rango
        if dias_retraso:
            fecha_limite = hoy - timedelta(days=dias_retraso)
            query = query.filter(Cuota.fecha_vencimiento <= fecha_limite)

        resultados = query.all()

        # Convertir a diccionarios
        clientes_atrasados = []
        for row in resultados:
            clientes_atrasados.append(
                {
                    "cedula": row.cedula,
                    "nombres": row.nombres,
                    "analista": row.analista,
                    "prestamo_id": row.prestamo_id,
                    "cuotas_vencidas": row.cuotas_vencidas,
                    "total_adeudado": (
                        float(row.total_adeudado) if row.total_adeudado else 0.0
                    ),
                    "fecha_primera_vencida": (
                        row.fecha_primera_vencida.isoformat()
                        if row.fecha_primera_vencida
                        else None
                    ),
                }
            )

        return clientes_atrasados

    except Exception as e:
        logger.error(f"Error obteniendo clientes atrasados: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.get("/clientes-por-cantidad-pagos")
def obtener_clientes_por_cantidad_pagos_atrasados(
    cantidad_pagos: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Obtener clientes que tienen exactamente N cantidad de pagos atrasados
    """
    try:
        hoy = date.today()

        query = (
            db.query(
                Cliente.cedula,
                Cliente.nombres,
                Prestamo.usuario_proponente.label("analista"),
                Prestamo.id.label("prestamo_id"),
                func.sum(Cuota.monto_cuota).label("total_adeudado"),
            )
            .join(Prestamo, Prestamo.cedula == Cliente.cedula)
            .join(Cuota, Cuota.prestamo_id == Prestamo.id)
            .filter(Cuota.fecha_vencimiento < hoy, Cuota.estado != "PAGADO")
            .group_by(
                Cliente.cedula,
                Cliente.nombres,
                Prestamo.usuario_proponente,
                Prestamo.id,
            )
            .having(func.count(Cuota.id) == cantidad_pagos)
        )

        resultados = query.all()

        clientes = []
        for row in resultados:
            clientes.append(
                {
                    "cedula": row.cedula,
                    "nombres": row.nombres,
                    "analista": row.analista,
                    "prestamo_id": row.prestamo_id,
                    "total_adeudado": (
                        float(row.total_adeudado) if row.total_adeudado else 0.0
                    ),
                }
            )

        return clientes

    except Exception as e:
        logger.error(f"Error obteniendo clientes por cantidad de pagos: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.get("/por-analista")
def obtener_cobranzas_por_analista(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Obtener estadísticas de cobranza por analista
    - Cantidad de clientes atrasados
    - Monto total sin cobrar
    """
    try:
        hoy = date.today()

        query = (
            db.query(
                Prestamo.usuario_proponente.label("nombre_analista"),
                func.count(func.distinct(Cliente.cedula)).label("cantidad_clientes"),
                func.sum(Cuota.monto_cuota).label("monto_total"),
            )
            .join(Cliente, Cliente.cedula == Prestamo.cedula)
            .join(Cuota, Cuota.prestamo_id == Prestamo.id)
            .filter(
                Cuota.fecha_vencimiento < hoy,
                Cuota.estado != "PAGADO",
                Prestamo.usuario_proponente.isnot(None),
            )
            .group_by(Prestamo.usuario_proponente)
            .having(func.count(func.distinct(Cliente.cedula)) > 0)
        )

        resultados = query.all()

        analistas = []
        for row in resultados:
            analistas.append(
                {
                    "nombre": row.nombre_analista,
                    "cantidad_clientes": row.cantidad_clientes,
                    "monto_total": float(row.monto_total) if row.monto_total else 0.0,
                }
            )

        return analistas

    except Exception as e:
        logger.error(f"Error obteniendo cobranzas por analista: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.get("/por-analista/{analista}/clientes")
def obtener_clientes_por_analista(
    analista: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Obtener detalle de clientes atrasados para un analista específico
    """
    try:
        hoy = date.today()

        query = (
            db.query(
                Cliente.cedula,
                Cliente.nombres,
                Cliente.telefono,
                Prestamo.id.label("prestamo_id"),
                func.count(Cuota.id).label("cuotas_vencidas"),
                func.sum(Cuota.monto_cuota).label("total_adeudado"),
                func.min(Cuota.fecha_vencimiento).label("fecha_primera_vencida"),
            )
            .join(Prestamo, Prestamo.cedula == Cliente.cedula)
            .join(Cuota, Cuota.prestamo_id == Prestamo.id)
            .filter(
                Prestamo.usuario_proponente == analista,
                Cuota.fecha_vencimiento < hoy,
                Cuota.estado != "PAGADO",
            )
            .group_by(Cliente.cedula, Cliente.nombres, Cliente.telefono, Prestamo.id)
        )

        resultados = query.all()

        clientes = []
        for row in resultados:
            clientes.append(
                {
                    "cedula": row.cedula,
                    "nombres": row.nombres,
                    "telefono": row.telefono,
                    "prestamo_id": row.prestamo_id,
                    "cuotas_vencidas": row.cuotas_vencidas,
                    "total_adeudado": (
                        float(row.total_adeudado) if row.total_adeudado else 0.0
                    ),
                    "fecha_primera_vencida": (
                        row.fecha_primera_vencida.isoformat()
                        if row.fecha_primera_vencida
                        else None
                    ),
                }
            )

        return clientes

    except Exception as e:
        logger.error(f"Error obteniendo clientes del analista {analista}: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.get("/montos-por-mes")
def obtener_montos_vencidos_por_mes(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Obtener montos vencidos agrupados por mes de vencimiento
    Solo incluye cuotas vencidas
    """
    try:
        hoy = date.today()

        query = (
            db.query(
                func.date_trunc("month", Cuota.fecha_vencimiento).label("mes"),
                func.count(Cuota.id).label("cantidad_cuotas"),
                func.sum(Cuota.monto_cuota).label("monto_total"),
            )
            .filter(Cuota.fecha_vencimiento < hoy, Cuota.estado != "PAGADO")
            .group_by(func.date_trunc("month", Cuota.fecha_vencimiento))
            .order_by(func.date_trunc("month", Cuota.fecha_vencimiento))
        )

        resultados = query.all()

        montos_por_mes = []
        for row in resultados:
            montos_por_mes.append(
                {
                    "mes": row.mes.strftime("%Y-%m") if row.mes else None,
                    "mes_display": row.mes.strftime("%B %Y") if row.mes else None,
                    "cantidad_cuotas": row.cantidad_cuotas,
                    "monto_total": float(row.monto_total) if row.monto_total else 0.0,
                }
            )

        return montos_por_mes

    except Exception as e:
        logger.error(f"Error obteniendo montos por mes: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.get("/resumen")
def obtener_resumen_cobranzas(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Obtener resumen general de cobranzas
    """
    try:
        hoy = date.today()

        # Total de cuotas vencidas
        total_cuotas_vencidas = (
            db.query(func.count(Cuota.id))
            .filter(Cuota.fecha_vencimiento < hoy, Cuota.estado != "PAGADO")
            .scalar()
            or 0
        )

        # Monto total adeudado
        monto_total_adeudado = (
            db.query(func.sum(Cuota.monto_cuota))
            .filter(Cuota.fecha_vencimiento < hoy, Cuota.estado != "PAGADO")
            .scalar()
            or 0.0
        )

        # Cantidad de clientes únicos atrasados
        clientes_unicos = (
            db.query(func.count(func.distinct(Prestamo.cedula)))
            .join(Cuota, Cuota.prestamo_id == Prestamo.id)
            .filter(Cuota.fecha_vencimiento < hoy, Cuota.estado != "PAGADO")
            .scalar()
            or 0
        )

        return {
            "total_cuotas_vencidas": total_cuotas_vencidas,
            "monto_total_adeudado": float(monto_total_adeudado),
            "clientes_atrasados": clientes_unicos,
        }

    except Exception as e:
        logger.error(f"Error obteniendo resumen de cobranzas: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


# ============================================
# INFORME 1: Clientes Atrasados Completo
# ============================================


@router.get("/informes/clientes-atrasados")
def informe_clientes_atrasados(
    dias_retraso_min: Optional[int] = Query(
        None, description="Días mínimos de retraso"
    ),
    dias_retraso_max: Optional[int] = Query(
        None, description="Días máximos de retraso"
    ),
    analista: Optional[str] = Query(None, description="Filtrar por analista"),
    formato: str = Query("json", description="Formato: json, pdf, excel"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Informe completo de clientes atrasados con opciones de filtrado"""
    try:
        hoy = date.today()

        query = (
            db.query(
                Cliente.cedula,
                Cliente.nombres,
                Cliente.telefono,
                Prestamo.usuario_proponente.label("analista"),
                Prestamo.id.label("prestamo_id"),
                Prestamo.total_financiamiento,
                func.count(Cuota.id).label("cuotas_vencidas"),
                func.sum(Cuota.monto_cuota).label("total_adeudado"),
                func.min(Cuota.fecha_vencimiento).label("fecha_primera_vencida"),
                func.max(Cuota.fecha_vencimiento).label("fecha_ultima_vencida"),
                func.sum(
                    case(
                        (
                            Cuota.fecha_vencimiento < hoy - timedelta(days=30),
                            Cuota.monto_cuota,
                        ),
                        else_=0,
                    )
                ).label("monto_mas_30_dias"),
            )
            .join(Prestamo, Prestamo.cedula == Cliente.cedula)
            .join(Cuota, Cuota.prestamo_id == Prestamo.id)
            .filter(Cuota.fecha_vencimiento < hoy, Cuota.estado != "PAGADO")
        )

        if analista:
            query = query.filter(Prestamo.usuario_proponente == analista)

        query = query.group_by(
            Cliente.cedula,
            Cliente.nombres,
            Cliente.telefono,
            Prestamo.usuario_proponente,
            Prestamo.id,
            Prestamo.total_financiamiento,
        )

        resultados = query.all()

        # Aplicar filtros de días de retraso en Python
        datos_filtrados = []
        for row in resultados:
            if row.fecha_primera_vencida:
                dias_retraso = (hoy - row.fecha_primera_vencida).days
                if dias_retraso_min and dias_retraso < dias_retraso_min:
                    continue
                if dias_retraso_max and dias_retraso > dias_retraso_max:
                    continue
                datos_filtrados.append(
                    {
                        "cedula": row.cedula,
                        "nombres": row.nombres,
                        "telefono": row.telefono or "N/A",
                        "analista": row.analista or "N/A",
                        "prestamo_id": row.prestamo_id,
                        "total_financiamiento": float(row.total_financiamiento),
                        "cuotas_vencidas": row.cuotas_vencidas,
                        "total_adeudado": (
                            float(row.total_adeudado) if row.total_adeudado else 0.0
                        ),
                        "fecha_primera_vencida": (
                            row.fecha_primera_vencida.isoformat()
                            if row.fecha_primera_vencida
                            else None
                        ),
                        "fecha_ultima_vencida": (
                            row.fecha_ultima_vencida.isoformat()
                            if row.fecha_ultima_vencida
                            else None
                        ),
                        "dias_retraso": dias_retraso,
                        "monto_mas_30_dias": (
                            float(row.monto_mas_30_dias)
                            if row.monto_mas_30_dias
                            else 0.0
                        ),
                    }
                )

        if formato.lower() == "json":
            return {
                "titulo": "Informe de Clientes Atrasados",
                "fecha_generacion": datetime.now().isoformat(),
                "total_registros": len(datos_filtrados),
                "total_adeudado": sum(
                    d.get("total_adeudado", 0) for d in datos_filtrados
                ),
                "datos": datos_filtrados,
            }
        elif formato.lower() == "excel":
            return _generar_excel_clientes_atrasados(datos_filtrados)
        elif formato.lower() == "pdf":
            return _generar_pdf_clientes_atrasados(datos_filtrados)
        else:
            raise HTTPException(
                status_code=400, detail="Formato no válido. Use: json, excel o pdf"
            )

    except Exception as e:
        logger.error(f"Error generando informe clientes atrasados: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


# ============================================
# INFORME 2: Rendimiento por Analista
# ============================================


@router.get("/informes/rendimiento-analista")
def informe_rendimiento_analista(
    formato: str = Query("json", description="Formato: json, pdf, excel"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Informe detallado de rendimiento de cobranzas por analista"""
    try:
        hoy = date.today()

        # Estadísticas por analista
        query = (
            db.query(
                Prestamo.usuario_proponente.label("analista"),
                func.count(func.distinct(Cliente.cedula)).label("total_clientes"),
                func.count(func.distinct(Prestamo.id)).label("total_prestamos"),
                func.sum(Cuota.monto_cuota).label("monto_total_adeudado"),
                func.count(Cuota.id).label("total_cuotas_vencidas"),
                func.avg(
                    case(
                        (
                            Cuota.fecha_vencimiento < hoy,
                            func.extract("day", hoy - Cuota.fecha_vencimiento),
                        ),
                        else_=0,
                    )
                ).label("promedio_dias_retraso"),
            )
            .join(Cliente, Cliente.cedula == Prestamo.cedula)
            .join(Cuota, Cuota.prestamo_id == Prestamo.id)
            .filter(
                Cuota.fecha_vencimiento < hoy,
                Cuota.estado != "PAGADO",
                Prestamo.usuario_proponente.isnot(None),
            )
            .group_by(Prestamo.usuario_proponente)
        )

        resultados = query.all()

        datos_analistas = []
        for row in resultados:
            datos_analistas.append(
                {
                    "analista": row.analista,
                    "total_clientes": row.total_clientes,
                    "total_prestamos": row.total_prestamos,
                    "monto_total_adeudado": (
                        float(row.monto_total_adeudado)
                        if row.monto_total_adeudado
                        else 0.0
                    ),
                    "total_cuotas_vencidas": row.total_cuotas_vencidas,
                    "promedio_dias_retraso": (
                        float(row.promedio_dias_retraso)
                        if row.promedio_dias_retraso
                        else 0.0
                    ),
                }
            )

        if formato.lower() == "json":
            return {
                "titulo": "Informe de Rendimiento por Analista",
                "fecha_generacion": datetime.now().isoformat(),
                "total_analistas": len(datos_analistas),
                "datos": datos_analistas,
            }
        elif formato.lower() == "excel":
            return _generar_excel_rendimiento_analista(datos_analistas)
        elif formato.lower() == "pdf":
            return _generar_pdf_rendimiento_analista(datos_analistas)
        else:
            raise HTTPException(status_code=400, detail="Formato no válido")

    except Exception as e:
        logger.error(f"Error generando informe rendimiento analista: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


# ============================================
# INFORME 3: Montos Vencidos por Período
# ============================================


@router.get("/informes/montos-vencidos-periodo")
def informe_montos_vencidos_periodo(
    fecha_inicio: Optional[date] = Query(None, description="Fecha inicio"),
    fecha_fin: Optional[date] = Query(None, description="Fecha fin"),
    formato: str = Query("json", description="Formato: json, pdf, excel"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Informe de montos vencidos agrupados por período"""
    try:
        hoy = date.today()

        query = (
            db.query(
                func.date_trunc("month", Cuota.fecha_vencimiento).label("mes"),
                func.count(Cuota.id).label("cantidad_cuotas"),
                func.sum(Cuota.monto_cuota).label("monto_total"),
                func.count(func.distinct(Cliente.cedula)).label("clientes_unicos"),
            )
            .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
            .join(Cliente, Prestamo.cedula == Cliente.cedula)
            .filter(Cuota.fecha_vencimiento < hoy, Cuota.estado != "PAGADO")
        )

        if fecha_inicio:
            query = query.filter(Cuota.fecha_vencimiento >= fecha_inicio)
        if fecha_fin:
            query = query.filter(Cuota.fecha_vencimiento <= fecha_fin)

        query = query.group_by(func.date_trunc("month", Cuota.fecha_vencimiento))
        query = query.order_by(func.date_trunc("month", Cuota.fecha_vencimiento))

        resultados = query.all()

        datos_periodo = []
        for row in resultados:
            datos_periodo.append(
                {
                    "mes": row.mes.strftime("%Y-%m") if row.mes else None,
                    "mes_display": row.mes.strftime("%B %Y") if row.mes else None,
                    "cantidad_cuotas": row.cantidad_cuotas,
                    "monto_total": float(row.monto_total) if row.monto_total else 0.0,
                    "clientes_unicos": row.clientes_unicos,
                }
            )

        if formato.lower() == "json":
            return {
                "titulo": "Informe de Montos Vencidos por Período",
                "fecha_generacion": datetime.now().isoformat(),
                "fecha_inicio": fecha_inicio.isoformat() if fecha_inicio else None,
                "fecha_fin": fecha_fin.isoformat() if fecha_fin else None,
                "total_meses": len(datos_periodo),
                "monto_total_acumulado": sum(
                    d.get("monto_total", 0) for d in datos_periodo
                ),
                "datos": datos_periodo,
            }
        elif formato.lower() == "excel":
            return _generar_excel_montos_periodo(datos_periodo)
        elif formato.lower() == "pdf":
            return _generar_pdf_montos_periodo(datos_periodo)
        else:
            raise HTTPException(status_code=400, detail="Formato no válido")

    except Exception as e:
        logger.error(f"Error generando informe montos período: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


# ============================================
# INFORME 4: Antigüedad de Saldos
# ============================================


@router.get("/informes/antiguedad-saldos")
def informe_antiguedad_saldos(
    formato: str = Query("json", description="Formato: json, pdf, excel"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Informe de distribución de mora por rangos de antigüedad"""
    try:
        hoy = date.today()

        # Agrupar por rangos de antigüedad
        query = (
            db.query(
                case(
                    (
                        (func.extract("day", hoy - Cuota.fecha_vencimiento) <= 30),
                        "0-30 días",
                    ),
                    (
                        (func.extract("day", hoy - Cuota.fecha_vencimiento) <= 60),
                        "31-60 días",
                    ),
                    (
                        (func.extract("day", hoy - Cuota.fecha_vencimiento) <= 90),
                        "61-90 días",
                    ),
                    (
                        (func.extract("day", hoy - Cuota.fecha_vencimiento) <= 180),
                        "91-180 días",
                    ),
                    else_="Más de 180 días",
                ).label("rango_antiguedad"),
                func.count(Cuota.id).label("cantidad_cuotas"),
                func.sum(Cuota.monto_cuota).label("monto_total"),
                func.count(func.distinct(Cliente.cedula)).label("clientes_unicos"),
            )
            .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
            .join(Cliente, Prestamo.cedula == Cliente.cedula)
            .filter(Cuota.fecha_vencimiento < hoy, Cuota.estado != "PAGADO")
            .group_by("rango_antiguedad")
        )

        resultados = query.all()

        datos_antiguedad = []
        for row in resultados:
            datos_antiguedad.append(
                {
                    "rango_antiguedad": row.rango_antiguedad,
                    "cantidad_cuotas": row.cantidad_cuotas,
                    "monto_total": float(row.monto_total) if row.monto_total else 0.0,
                    "clientes_unicos": row.clientes_unicos,
                }
            )

        # Ordenar por antigüedad
        orden_rangos = {
            "0-30 días": 1,
            "31-60 días": 2,
            "61-90 días": 3,
            "91-180 días": 4,
            "Más de 180 días": 5,
        }
        datos_antiguedad.sort(
            key=lambda x: orden_rangos.get(x["rango_antiguedad"], 999)
        )

        if formato.lower() == "json":
            total_monto = sum(d.get("monto_total", 0) for d in datos_antiguedad)
            return {
                "titulo": "Informe de Antigüedad de Saldos",
                "fecha_generacion": datetime.now().isoformat(),
                "total_rangos": len(datos_antiguedad),
                "monto_total": total_monto,
                "datos": datos_antiguedad,
            }
        elif formato.lower() == "excel":
            return _generar_excel_antiguedad_saldos(datos_antiguedad)
        elif formato.lower() == "pdf":
            return _generar_pdf_antiguedad_saldos(datos_antiguedad)
        else:
            raise HTTPException(status_code=400, detail="Formato no válido")

    except Exception as e:
        logger.error(f"Error generando informe antigüedad saldos: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


# ============================================
# INFORME 5: Resumen Ejecutivo
# ============================================


@router.get("/informes/resumen-ejecutivo")
def informe_resumen_ejecutivo(
    formato: str = Query("json", description="Formato: json, pdf, excel"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Informe ejecutivo consolidado de cobranzas"""
    try:
        hoy = date.today()

        # Resumen general
        total_cuotas_vencidas = (
            db.query(func.count(Cuota.id))
            .filter(Cuota.fecha_vencimiento < hoy, Cuota.estado != "PAGADO")
            .scalar()
            or 0
        )

        monto_total_adeudado = (
            db.query(func.sum(Cuota.monto_cuota))
            .filter(Cuota.fecha_vencimiento < hoy, Cuota.estado != "PAGADO")
            .scalar()
            or 0.0
        )

        clientes_atrasados = (
            db.query(func.count(func.distinct(Prestamo.cedula)))
            .join(Cuota, Cuota.prestamo_id == Prestamo.id)
            .filter(Cuota.fecha_vencimiento < hoy, Cuota.estado != "PAGADO")
            .scalar()
            or 0
        )

        # Top 5 analistas con más mora
        top_analistas = (
            db.query(
                Prestamo.usuario_proponente.label("analista"),
                func.sum(Cuota.monto_cuota).label("monto_total"),
            )
            .join(Cuota, Cuota.prestamo_id == Prestamo.id)
            .filter(
                Cuota.fecha_vencimiento < hoy,
                Cuota.estado != "PAGADO",
                Prestamo.usuario_proponente.isnot(None),
            )
            .group_by(Prestamo.usuario_proponente)
            .order_by(func.sum(Cuota.monto_cuota).desc())
            .limit(5)
            .all()
        )

        # Top 5 clientes con más deuda
        top_clientes = (
            db.query(
                Cliente.cedula,
                Cliente.nombres,
                func.sum(Cuota.monto_cuota).label("total_adeudado"),
                func.count(Cuota.id).label("cuotas_vencidas"),
            )
            .join(Prestamo, Prestamo.cedula == Cliente.cedula)
            .join(Cuota, Cuota.prestamo_id == Prestamo.id)
            .filter(Cuota.fecha_vencimiento < hoy, Cuota.estado != "PAGADO")
            .group_by(Cliente.cedula, Cliente.nombres)
            .order_by(func.sum(Cuota.monto_cuota).desc())
            .limit(5)
            .all()
        )

        datos_resumen = {
            "fecha_generacion": datetime.now().isoformat(),
            "fecha_corte": hoy.isoformat(),
            "resumen_general": {
                "total_cuotas_vencidas": total_cuotas_vencidas,
                "monto_total_adeudado": float(monto_total_adeudado),
                "clientes_atrasados": clientes_atrasados,
                "promedio_deuda_cliente": (
                    float(monto_total_adeudado / clientes_atrasados)
                    if clientes_atrasados > 0
                    else 0.0
                ),
            },
            "top_analistas": [
                {
                    "analista": row.analista,
                    "monto_total": float(row.monto_total) if row.monto_total else 0.0,
                }
                for row in top_analistas
            ],
            "top_clientes": [
                {
                    "cedula": row.cedula,
                    "nombres": row.nombres,
                    "total_adeudado": (
                        float(row.total_adeudado) if row.total_adeudado else 0.0
                    ),
                    "cuotas_vencidas": row.cuotas_vencidas,
                }
                for row in top_clientes
            ],
        }

        if formato.lower() == "json":
            return datos_resumen
        elif formato.lower() == "excel":
            return _generar_excel_resumen_ejecutivo(datos_resumen)
        elif formato.lower() == "pdf":
            return _generar_pdf_resumen_ejecutivo(datos_resumen)
        else:
            raise HTTPException(status_code=400, detail="Formato no válido")

    except Exception as e:
        logger.error(f"Error generando informe resumen ejecutivo: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


# ============================================
# FUNCIONES AUXILIARES PARA GENERACIÓN EXCEL
# ============================================


def _generar_excel_clientes_atrasados(datos: List[Dict]) -> StreamingResponse:
    """Genera archivo Excel para informe de clientes atrasados"""
    wb = Workbook()
    ws = wb.active
    ws.title = "Clientes Atrasados"

    # Estilos
    header_fill = PatternFill(
        start_color="366092", end_color="366092", fill_type="solid"
    )
    header_font = Font(bold=True, color="FFFFFF", size=12)

    # Encabezados
    headers = [
        "Cédula",
        "Nombres",
        "Teléfono",
        "Analista",
        "Préstamo ID",
        "Total Financiamiento",
        "Cuotas Vencidas",
        "Total Adeudado",
        "Fecha Primera Vencida",
        "Días Retraso",
        "Monto >30 días",
    ]

    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col)
        cell.value = header
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")

    # Datos
    for row_idx, registro in enumerate(datos, 2):
        ws.cell(row=row_idx, column=1, value=registro.get("cedula"))
        ws.cell(row=row_idx, column=2, value=registro.get("nombres"))
        ws.cell(row=row_idx, column=3, value=registro.get("telefono"))
        ws.cell(row=row_idx, column=4, value=registro.get("analista"))
        ws.cell(row=row_idx, column=5, value=registro.get("prestamo_id"))
        ws.cell(row=row_idx, column=6, value=registro.get("total_financiamiento"))
        ws.cell(row=row_idx, column=7, value=registro.get("cuotas_vencidas"))
        ws.cell(row=row_idx, column=8, value=registro.get("total_adeudado"))
        ws.cell(row=row_idx, column=9, value=registro.get("fecha_primera_vencida"))
        ws.cell(row=row_idx, column=10, value=registro.get("dias_retraso"))
        ws.cell(row=row_idx, column=11, value=registro.get("monto_mas_30_dias"))

    # Ajustar anchos
    ws.column_dimensions["A"].width = 15
    ws.column_dimensions["B"].width = 30
    ws.column_dimensions["C"].width = 15
    ws.column_dimensions["D"].width = 25
    ws.column_dimensions["E"].width = 12
    ws.column_dimensions["F"].width = 18
    ws.column_dimensions["G"].width = 15
    ws.column_dimensions["H"].width = 15
    ws.column_dimensions["I"].width = 18
    ws.column_dimensions["J"].width = 12
    ws.column_dimensions["K"].width = 15

    # Totales
    total_row = len(datos) + 3
    ws.cell(row=total_row, column=7, value="TOTAL:")
    ws.cell(row=total_row, column=7).font = Font(bold=True)
    ws.cell(
        row=total_row, column=8, value=sum(d.get("total_adeudado", 0) for d in datos)
    )
    ws.cell(row=total_row, column=8).font = Font(bold=True)

    output = BytesIO()
    wb.save(output)
    output.seek(0)

    fecha = datetime.now().strftime("%Y%m%d")
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f"attachment; filename=informe_clientes_atrasados_{fecha}.xlsx"
        },
    )


def _generar_excel_rendimiento_analista(datos: List[Dict]) -> StreamingResponse:
    """Genera archivo Excel para informe de rendimiento por analista"""
    wb = Workbook()
    ws = wb.active
    ws.title = "Rendimiento Analista"

    header_fill = PatternFill(
        start_color="366092", end_color="366092", fill_type="solid"
    )
    header_font = Font(bold=True, color="FFFFFF", size=12)

    headers = [
        "Analista",
        "Total Clientes",
        "Total Préstamos",
        "Monto Total Adeudado",
        "Cuotas Vencidas",
        "Promedio Días Retraso",
    ]

    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col)
        cell.value = header
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center")

    for row_idx, registro in enumerate(datos, 2):
        ws.cell(row=row_idx, column=1, value=registro.get("analista"))
        ws.cell(row=row_idx, column=2, value=registro.get("total_clientes"))
        ws.cell(row=row_idx, column=3, value=registro.get("total_prestamos"))
        ws.cell(row=row_idx, column=4, value=registro.get("monto_total_adeudado"))
        ws.cell(row=row_idx, column=5, value=registro.get("total_cuotas_vencidas"))
        ws.cell(
            row=row_idx,
            column=6,
            value=round(registro.get("promedio_dias_retraso", 0), 2),
        )

    for col in range(1, 7):
        ws.column_dimensions[chr(64 + col)].width = 20

    output = BytesIO()
    wb.save(output)
    output.seek(0)

    fecha = datetime.now().strftime("%Y%m%d")
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f"attachment; filename=informe_rendimiento_analista_{fecha}.xlsx"
        },
    )


def _generar_excel_montos_periodo(datos: List[Dict]) -> StreamingResponse:
    """Genera archivo Excel para informe de montos por período"""
    wb = Workbook()
    ws = wb.active
    ws.title = "Montos por Período"

    header_fill = PatternFill(
        start_color="366092", end_color="366092", fill_type="solid"
    )
    header_font = Font(bold=True, color="FFFFFF", size=12)

    headers = ["Mes", "Cantidad Cuotas", "Monto Total", "Clientes Únicos"]

    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col)
        cell.value = header
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center")

    for row_idx, registro in enumerate(datos, 2):
        ws.cell(
            row=row_idx,
            column=1,
            value=registro.get("mes_display") or registro.get("mes"),
        )
        ws.cell(row=row_idx, column=2, value=registro.get("cantidad_cuotas"))
        ws.cell(row=row_idx, column=3, value=registro.get("monto_total"))
        ws.cell(row=row_idx, column=4, value=registro.get("clientes_unicos"))

    for col in range(1, 5):
        ws.column_dimensions[chr(64 + col)].width = 20

    output = BytesIO()
    wb.save(output)
    output.seek(0)

    fecha = datetime.now().strftime("%Y%m%d")
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f"attachment; filename=informe_montos_periodo_{fecha}.xlsx"
        },
    )


def _generar_excel_antiguedad_saldos(datos: List[Dict]) -> StreamingResponse:
    """Genera archivo Excel para informe de antigüedad de saldos"""
    wb = Workbook()
    ws = wb.active
    ws.title = "Antigüedad Saldos"

    header_fill = PatternFill(
        start_color="366092", end_color="366092", fill_type="solid"
    )
    header_font = Font(bold=True, color="FFFFFF", size=12)

    headers = ["Rango Antigüedad", "Cantidad Cuotas", "Monto Total", "Clientes Únicos"]

    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col)
        cell.value = header
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center")

    for row_idx, registro in enumerate(datos, 2):
        ws.cell(row=row_idx, column=1, value=registro.get("rango_antiguedad"))
        ws.cell(row=row_idx, column=2, value=registro.get("cantidad_cuotas"))
        ws.cell(row=row_idx, column=3, value=registro.get("monto_total"))
        ws.cell(row=row_idx, column=4, value=registro.get("clientes_unicos"))

    for col in range(1, 5):
        ws.column_dimensions[chr(64 + col)].width = 20

    output = BytesIO()
    wb.save(output)
    output.seek(0)

    fecha = datetime.now().strftime("%Y%m%d")
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f"attachment; filename=informe_antiguedad_saldos_{fecha}.xlsx"
        },
    )


def _generar_excel_resumen_ejecutivo(datos: Dict) -> StreamingResponse:
    """Genera archivo Excel para informe resumen ejecutivo"""
    wb = Workbook()

    # Hoja 1: Resumen General
    ws1 = wb.active
    ws1.title = "Resumen General"

    header_fill = PatternFill(
        start_color="366092", end_color="366092", fill_type="solid"
    )
    header_font = Font(bold=True, color="FFFFFF", size=14)

    ws1["A1"] = "RESUMEN EJECUTIVO DE COBRANZAS"
    ws1["A1"].font = header_font
    ws1["A1"].fill = header_fill

    resumen = datos.get("resumen_general", {})
    row = 3
    ws1.cell(row=row, column=1, value="Total Cuotas Vencidas:").font = Font(bold=True)
    ws1.cell(row=row, column=2, value=resumen.get("total_cuotas_vencidas", 0))
    row += 1
    ws1.cell(row=row, column=1, value="Monto Total Adeudado:").font = Font(bold=True)
    ws1.cell(row=row, column=2, value=resumen.get("monto_total_adeudado", 0))
    row += 1
    ws1.cell(row=row, column=1, value="Clientes Atrasados:").font = Font(bold=True)
    ws1.cell(row=row, column=2, value=resumen.get("clientes_atrasados", 0))
    row += 1
    ws1.cell(row=row, column=1, value="Promedio Deuda por Cliente:").font = Font(
        bold=True
    )
    ws1.cell(row=row, column=2, value=resumen.get("promedio_deuda_cliente", 0))

    # Hoja 2: Top Analistas
    ws2 = wb.create_sheet("Top Analistas")
    headers = ["Analista", "Monto Total Adeudado"]
    for col, header in enumerate(headers, 1):
        cell = ws2.cell(row=1, column=col)
        cell.value = header
        cell.fill = header_fill
        cell.font = Font(bold=True, color="FFFFFF")

    for row_idx, analista in enumerate(datos.get("top_analistas", []), 2):
        ws2.cell(row=row_idx, column=1, value=analista.get("analista"))
        ws2.cell(row=row_idx, column=2, value=analista.get("monto_total"))

    # Hoja 3: Top Clientes
    ws3 = wb.create_sheet("Top Clientes")
    headers = ["Cédula", "Nombres", "Total Adeudado", "Cuotas Vencidas"]
    for col, header in enumerate(headers, 1):
        cell = ws3.cell(row=1, column=col)
        cell.value = header
        cell.fill = header_fill
        cell.font = Font(bold=True, color="FFFFFF")

    for row_idx, cliente in enumerate(datos.get("top_clientes", []), 2):
        ws3.cell(row=row_idx, column=1, value=cliente.get("cedula"))
        ws3.cell(row=row_idx, column=2, value=cliente.get("nombres"))
        ws3.cell(row=row_idx, column=3, value=cliente.get("total_adeudado"))
        ws3.cell(row=row_idx, column=4, value=cliente.get("cuotas_vencidas"))

    output = BytesIO()
    wb.save(output)
    output.seek(0)

    fecha = datetime.now().strftime("%Y%m%d")
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f"attachment; filename=informe_resumen_ejecutivo_{fecha}.xlsx"
        },
    )


# ============================================
# FUNCIONES AUXILIARES PARA GENERACIÓN PDF
# ============================================


def _generar_pdf_clientes_atrasados(datos: List[Dict]) -> StreamingResponse:
    """Genera archivo PDF para informe de clientes atrasados"""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=1 * inch)
    story = []
    styles = getSampleStyleSheet()

    # Título
    title = Paragraph("Informe de Clientes Atrasados", styles["Title"])
    story.append(title)
    story.append(Spacer(1, 0.2 * inch))

    # Fecha de generación
    fecha_gen = Paragraph(
        f"Generado el: {datetime.now().strftime('%d/%m/%Y %H:%M')}", styles["Normal"]
    )
    story.append(fecha_gen)
    story.append(Spacer(1, 0.3 * inch))

    # Tabla de datos
    if datos:
        table_data = [
            ["Cédula", "Nombres", "Analista", "Cuotas", "Adeudado", "Días Retraso"]
        ]
        for registro in datos[:100]:  # Limitar a 100 registros por página
            table_data.append(
                [
                    registro.get("cedula", ""),
                    registro.get("nombres", "")[:30],
                    (registro.get("analista", "") or "N/A")[:20],
                    str(registro.get("cuotas_vencidas", 0)),
                    f"${registro.get('total_adeudado', 0):,.2f}",
                    str(registro.get("dias_retraso", 0)),
                ]
            )

        table = Table(table_data)
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#366092")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 10),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                    ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
                    ("GRID", (0, 0), (-1, -1), 1, colors.black),
                ]
            )
        )
        story.append(table)

        # Total
        story.append(Spacer(1, 0.2 * inch))
        total_adeudado = sum(d.get("total_adeudado", 0) for d in datos)
        total = Paragraph(
            f"<b>Total Adeudado: ${total_adeudado:,.2f}</b>", styles["Normal"]
        )
        story.append(total)

    doc.build(story)
    buffer.seek(0)

    fecha = datetime.now().strftime("%Y%m%d")
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=informe_clientes_atrasados_{fecha}.pdf"
        },
    )


def _generar_pdf_rendimiento_analista(datos: List[Dict]) -> StreamingResponse:
    """Genera archivo PDF para informe de rendimiento por analista"""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    story = []
    styles = getSampleStyleSheet()

    title = Paragraph("Informe de Rendimiento por Analista", styles["Title"])
    story.append(title)
    story.append(Spacer(1, 0.2 * inch))

    if datos:
        table_data = [
            ["Analista", "Clientes", "Préstamos", "Monto Adeudado", "Promedio Días"]
        ]
        for registro in datos:
            table_data.append(
                [
                    registro.get("analista", "")[:30],
                    str(registro.get("total_clientes", 0)),
                    str(registro.get("total_prestamos", 0)),
                    f"${registro.get('monto_total_adeudado', 0):,.2f}",
                    f"{registro.get('promedio_dias_retraso', 0):.1f}",
                ]
            )

        table = Table(table_data)
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#366092")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("GRID", (0, 0), (-1, -1), 1, colors.black),
                ]
            )
        )
        story.append(table)

    doc.build(story)
    buffer.seek(0)

    fecha = datetime.now().strftime("%Y%m%d")
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=informe_rendimiento_analista_{fecha}.pdf"
        },
    )


def _generar_pdf_montos_periodo(datos: List[Dict]) -> StreamingResponse:
    """Genera archivo PDF para informe de montos por período"""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    story = []
    styles = getSampleStyleSheet()

    title = Paragraph("Informe de Montos Vencidos por Período", styles["Title"])
    story.append(title)
    story.append(Spacer(1, 0.2 * inch))

    if datos:
        table_data = [["Mes", "Cuotas", "Monto Total", "Clientes"]]
        for registro in datos:
            table_data.append(
                [
                    registro.get("mes_display", ""),
                    str(registro.get("cantidad_cuotas", 0)),
                    f"${registro.get('monto_total', 0):,.2f}",
                    str(registro.get("clientes_unicos", 0)),
                ]
            )

        table = Table(table_data)
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#366092")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("GRID", (0, 0), (-1, -1), 1, colors.black),
                ]
            )
        )
        story.append(table)

    doc.build(story)
    buffer.seek(0)

    fecha = datetime.now().strftime("%Y%m%d")
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=informe_montos_periodo_{fecha}.pdf"
        },
    )


def _generar_pdf_antiguedad_saldos(datos: List[Dict]) -> StreamingResponse:
    """Genera archivo PDF para informe de antigüedad de saldos"""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    story = []
    styles = getSampleStyleSheet()

    title = Paragraph("Informe de Antigüedad de Saldos", styles["Title"])
    story.append(title)
    story.append(Spacer(1, 0.2 * inch))

    if datos:
        table_data = [["Rango Antigüedad", "Cuotas", "Monto Total", "Clientes"]]
        for registro in datos:
            table_data.append(
                [
                    registro.get("rango_antiguedad", ""),
                    str(registro.get("cantidad_cuotas", 0)),
                    f"${registro.get('monto_total', 0):,.2f}",
                    str(registro.get("clientes_unicos", 0)),
                ]
            )

        table = Table(table_data)
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#366092")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("GRID", (0, 0), (-1, -1), 1, colors.black),
                ]
            )
        )
        story.append(table)

    doc.build(story)
    buffer.seek(0)

    fecha = datetime.now().strftime("%Y%m%d")
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=informe_antiguedad_saldos_{fecha}.pdf"
        },
    )


def _generar_pdf_resumen_ejecutivo(datos: Dict) -> StreamingResponse:
    """Genera archivo PDF para informe resumen ejecutivo"""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    story = []
    styles = getSampleStyleSheet()

    title = Paragraph("Informe Ejecutivo de Cobranzas", styles["Title"])
    story.append(title)
    story.append(Spacer(1, 0.2 * inch))

    resumen = datos.get("resumen_general", {})

    # Resumen General
    story.append(Paragraph("<b>Resumen General</b>", styles["Heading2"]))
    resumen_data = [
        ["Indicador", "Valor"],
        ["Total Cuotas Vencidas", str(resumen.get("total_cuotas_vencidas", 0))],
        ["Monto Total Adeudado", f"${resumen.get('monto_total_adeudado', 0):,.2f}"],
        ["Clientes Atrasados", str(resumen.get("clientes_atrasados", 0))],
        [
            "Promedio Deuda por Cliente",
            f"${resumen.get('promedio_deuda_cliente', 0):,.2f}",
        ],
    ]

    resumen_table = Table(resumen_data)
    resumen_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#366092")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 1, colors.black),
            ]
        )
    )
    story.append(resumen_table)
    story.append(Spacer(1, 0.3 * inch))

    # Top Analistas
    if datos.get("top_analistas"):
        story.append(Paragraph("<b>Top 5 Analistas</b>", styles["Heading2"]))
        analistas_data = [["Analista", "Monto Total"]]
        for analista in datos.get("top_analistas", []):
            analistas_data.append(
                [
                    analista.get("analista", ""),
                    f"${analista.get('monto_total', 0):,.2f}",
                ]
            )

        analistas_table = Table(analistas_data)
        analistas_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#366092")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("GRID", (0, 0), (-1, -1), 1, colors.black),
                ]
            )
        )
        story.append(analistas_table)

    doc.build(story)
    buffer.seek(0)

    fecha = datetime.now().strftime("%Y%m%d")
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=informe_resumen_ejecutivo_{fecha}.pdf"
        },
    )
