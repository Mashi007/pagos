import logging
from datetime import date, datetime, timedelta
from decimal import Decimal
from io import BytesIO
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request  # type: ignore[import-untyped]
from fastapi.responses import StreamingResponse  # type: ignore[import-untyped]

# Imports para Excel
from openpyxl import Workbook  # type: ignore[import-untyped]
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side  # type: ignore[import-untyped]
from pydantic import BaseModel  # type: ignore[import-untyped]
from reportlab.lib import colors  # type: ignore[import-untyped]
from reportlab.lib.pagesizes import A4  # type: ignore[import-untyped]
from reportlab.lib.styles import getSampleStyleSheet  # type: ignore[import-untyped]
from reportlab.lib.units import inch  # type: ignore[import-untyped]

# Imports para reportes PDF
from reportlab.pdfgen import canvas  # type: ignore[import-untyped]
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle  # type: ignore[import-untyped]
from sqlalchemy import case, func, text  # type: ignore[import-untyped]
from sqlalchemy.orm import Session  # type: ignore[import-untyped]

from app.api.deps import get_current_user, get_db
from app.core.cache import cache_result
from app.core.constants import EstadoPrestamo
from app.core.rate_limiter import RATE_LIMITS, get_rate_limiter
from app.models.amortizacion import Cuota
from app.models.auditoria import Auditoria
from app.models.cliente import Cliente
from app.models.pago import Pago  # Tabla oficial de pagos
from app.models.prestamo import Prestamo
from app.models.user import User
from app.utils.error_handling import handle_report_error, validate_date_range

logger = logging.getLogger(__name__)
router = APIRouter()
limiter = get_rate_limiter()


@router.get("/health")
def healthcheck_reportes(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Verificación rápida del módulo de Reportes y conexión a BD.

    Ejecuta consultas mínimas para confirmar conectividad y disponibilidad de datos
    necesarios para la generación de reportes de cartera y pagos.
    """
    try:
        logger.info("[reportes.health] Verificando conexión a BD y métricas básicas")

        total_prestamos = db.query(func.count(Prestamo.id)).scalar() or 0
        total_pagos = db.query(func.count(Pago.id)).filter(Pago.activo.is_(True)).scalar() or 0

        return {
            "status": "ok",
            "database": True,
            "metrics": {
                "total_prestamos": int(total_prestamos),
                "total_pagos": int(total_pagos),
            },
            "timestamp": datetime.now(),
        }
    except Exception as e:
        logger.error(f"[reportes.health] Error: {e}")
        raise HTTPException(status_code=500, detail="Error de conexión o consulta a la base de datos")


class ReporteCartera(BaseModel):
    """Schema para reporte de cartera"""

    fecha_corte: date
    cartera_total: Decimal
    capital_pendiente: Decimal
    intereses_pendientes: Decimal
    mora_total: Decimal
    cantidad_prestamos_activos: int
    cantidad_prestamos_mora: int
    distribucion_por_monto: list[dict]
    distribucion_por_mora: list[dict]


class ReportePagos(BaseModel):
    """Schema para reporte de pagos"""

    fecha_inicio: date
    fecha_fin: date
    total_pagos: Decimal
    cantidad_pagos: int
    pagos_por_metodo: list[dict]
    pagos_por_dia: list[dict]


class ReporteMorosidad(BaseModel):
    """Schema para reporte de morosidad"""

    fecha_corte: date
    total_prestamos_mora: int
    total_clientes_mora: int
    monto_total_mora: Decimal
    promedio_dias_mora: float
    distribucion_por_rango: list[dict]
    morosidad_por_analista: list[dict]
    detalle_prestamos: list[dict]


class ReporteFinanciero(BaseModel):
    """Schema para reporte financiero"""

    fecha_corte: date
    total_ingresos: Decimal
    cantidad_pagos: int
    cartera_total: Decimal
    cartera_pendiente: Decimal
    morosidad_total: Decimal
    saldo_pendiente: Decimal
    porcentaje_cobrado: float
    ingresos_por_mes: list[dict]
    egresos_programados: list[dict]
    flujo_caja: list[dict]


class ReporteAsesores(BaseModel):
    """Schema para reporte de asesores"""

    fecha_corte: date
    resumen_por_analista: list[dict]
    desempeno_mensual: list[dict]
    clientes_por_analista: list[dict]


class ReporteProductos(BaseModel):
    """Schema para reporte de productos"""

    fecha_corte: date
    resumen_por_producto: list[dict]
    productos_por_concesionario: list[dict]
    tendencia_mensual: list[dict]


@router.get("/cartera", response_model=ReporteCartera)
@cache_result(ttl=300, key_prefix="reportes")  # Cache por 5 minutos
def reporte_cartera(
    fecha_corte: Optional[date] = Query(None, description="Fecha de corte"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Genera reporte de cartera al día de corte."""
    try:
        logger.info("[reportes.cartera] Iniciando generación de reporte")
        if not fecha_corte:
            fecha_corte = date.today()

        # Cartera total: suma de total_financiamiento de préstamos APROBADOS
        cartera_total = db.query(func.sum(Prestamo.total_financiamiento)).filter(
            Prestamo.estado == "APROBADO"
        ).scalar() or Decimal("0")

        logger.info(f"[reportes.cartera] Cartera total: {cartera_total}")

        # Capital pendiente: suma de capital_pendiente de todas las cuotas no pagadas
        capital_pendiente = (
            db.query(func.sum(func.coalesce(Cuota.capital_pendiente, Decimal("0.00"))))
            .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
            .filter(
                Prestamo.estado == "APROBADO",
                Cuota.estado != "PAGADO",
            )
            .scalar()
        ) or Decimal("0")

        logger.info(f"[reportes.cartera] Capital pendiente: {capital_pendiente}")

        # Intereses pendientes: suma de interes_pendiente de todas las cuotas no pagadas
        intereses_pendientes = (
            db.query(func.sum(func.coalesce(Cuota.interes_pendiente, Decimal("0.00"))))
            .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
            .filter(
                Prestamo.estado == "APROBADO",
                Cuota.estado != "PAGADO",
            )
            .scalar()
        ) or Decimal("0")

        logger.info(f"[reportes.cartera] Intereses pendientes: {intereses_pendientes}")

        # Mora total: suma de monto_mora de todas las cuotas con mora
        mora_total = (
            db.query(func.sum(func.coalesce(Cuota.monto_mora, Decimal("0.00"))))
            .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
            .filter(
                Prestamo.estado == "APROBADO",
                Cuota.monto_mora > Decimal("0.00"),
            )
            .scalar()
        ) or Decimal("0")

        logger.info(f"[reportes.cartera] Mora total: {mora_total}")

        # Cantidad de préstamos APROBADOS
        cantidad_prestamos_activos = db.query(Prestamo).filter(Prestamo.estado == "APROBADO").count()

        logger.info(f"[reportes.cartera] Préstamos activos: {cantidad_prestamos_activos}")

        # Préstamos con cuotas en mora
        cantidad_prestamos_mora = (
            db.query(func.count(func.distinct(Prestamo.id)))
            .join(Cuota, Cuota.prestamo_id == Prestamo.id)
            .filter(
                Prestamo.estado == "APROBADO",
                Cuota.monto_mora > Decimal("0.00"),
            )
            .scalar()
        ) or 0

        logger.info(f"[reportes.cartera] Préstamos en mora: {cantidad_prestamos_mora}")

        # Distribución por monto: usar total_financiamiento
        distribucion_por_monto_query = (
            db.query(
                case(
                    (Prestamo.total_financiamiento <= 1000, "Hasta $1,000"),
                    (Prestamo.total_financiamiento <= 5000, "$1,001 - $5,000"),
                    (Prestamo.total_financiamiento <= 10000, "$5,001 - $10,000"),
                    else_="Más de $10,000",
                ).label("rango"),
                func.count(Prestamo.id).label("cantidad"),
                func.sum(Prestamo.total_financiamiento).label("monto"),
            )
            .filter(Prestamo.estado == "APROBADO")
            .group_by("rango")
            .all()
        )

        distribucion_por_monto = [
            {
                "rango": item.rango,
                "cantidad": item.cantidad,
                "monto": float(item.monto) if item.monto else 0.0,
            }
            for item in distribucion_por_monto_query
        ]

        # Distribución por mora
        rangos_mora = [
            {"min": 1, "max": 30, "label": "1-30 días"},
            {"min": 31, "max": 60, "label": "31-60 días"},
            {"min": 61, "max": 90, "label": "61-90 días"},
            {"min": 91, "max": 999999, "label": "Más de 90 días"},
        ]

        distribucion_por_mora = []
        hoy = date.today()
        for rango in rangos_mora:
            # CORREGIDO: Los préstamos en mora se identifican por tener cuotas vencidas no pagadas
            # No existe EstadoPrestamo.EN_MORA, usar filtros de cuotas vencidas
            cantidad = (
                db.query(func.count(func.distinct(Prestamo.id)))
                .join(Cuota, Prestamo.id == Cuota.prestamo_id)
                .filter(
                    Prestamo.estado == EstadoPrestamo.APROBADO,  # Solo préstamos aprobados
                    Cuota.fecha_vencimiento < hoy,  # Cuotas vencidas
                    Cuota.estado != "PAGADO",  # Cuotas no pagadas
                    Cuota.dias_mora >= rango["min"],
                    Cuota.dias_mora <= rango["max"],
                )
                .scalar()
            ) or 0

            monto_mora = (
                db.query(func.sum(Cuota.monto_mora))
                .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
                .filter(
                    Prestamo.estado == EstadoPrestamo.APROBADO,  # Solo préstamos aprobados
                    Cuota.fecha_vencimiento < hoy,  # Cuotas vencidas
                    Cuota.estado != "PAGADO",  # Cuotas no pagadas
                    Cuota.dias_mora >= rango["min"],
                    Cuota.dias_mora <= rango["max"],
                )
                .scalar()
            ) or Decimal("0")

            distribucion_por_mora.append(
                {
                    "rango": rango["label"],
                    "cantidad": cantidad,
                    "monto_total": monto_mora,
                }
            )

        resultado = ReporteCartera(
            fecha_corte=fecha_corte,
            cartera_total=cartera_total,
            capital_pendiente=capital_pendiente,
            intereses_pendientes=intereses_pendientes,
            mora_total=mora_total,
            cantidad_prestamos_activos=cantidad_prestamos_activos,
            cantidad_prestamos_mora=cantidad_prestamos_mora,
            distribucion_por_monto=distribucion_por_monto,
            distribucion_por_mora=distribucion_por_mora,
        )
        logger.info("[reportes.cartera] Reporte generado correctamente")
        return resultado

    except HTTPException:
        raise
    except Exception as e:
        raise handle_report_error(e, "generar reporte de cartera")


@router.get("/pagos", response_model=ReportePagos)
@cache_result(ttl=300, key_prefix="reportes")  # Cache por 5 minutos
def reporte_pagos(
    fecha_inicio: date = Query(..., description="Fecha de inicio"),
    fecha_fin: date = Query(..., description="Fecha de fin"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Genera reporte de pagos en un rango de fechas."""
    try:
        # Validar rango de fechas
        validate_date_range(fecha_inicio, fecha_fin, max_days=365)

        logger.info(f"[reportes.pagos] Generando reporte pagos desde {fecha_inicio} hasta {fecha_fin}")
        # Total de pagos: usar tabla pagos (tipos nativos)
        fecha_inicio_dt = datetime.combine(fecha_inicio, datetime.min.time())
        fecha_fin_dt = datetime.combine(fecha_fin, datetime.max.time())

        total_pagos_query = db.execute(
            text(
                """
                SELECT COALESCE(SUM(monto_pagado), 0)
                FROM pagos
                WHERE fecha_pago >= :fecha_inicio
                  AND fecha_pago <= :fecha_fin
                  AND monto_pagado IS NOT NULL
                  AND monto_pagado > 0
                  AND activo = TRUE
            """
            ).bindparams(fecha_inicio=fecha_inicio_dt, fecha_fin=fecha_fin_dt)
        )
        total_pagos = Decimal(str(total_pagos_query.scalar() or 0))

        logger.info(f"[reportes.pagos] Total pagos: {total_pagos}")

        cantidad_pagos = (
            db.query(Pago)
            .filter(
                Pago.fecha_pago >= fecha_inicio_dt,
                Pago.fecha_pago <= fecha_fin_dt,
                Pago.activo.is_(True),
            )
            .count()
        )

        # Pagos por método: usar institucion_bancaria de la tabla pagos
        pagos_por_metodo_raw = db.execute(
            text(
                """
                SELECT
                    COALESCE(institucion_bancaria, 'Sin especificar') AS metodo,
                    COUNT(*) AS cantidad,
                    COALESCE(SUM(monto_pagado), 0) AS monto
                FROM pagos
                WHERE fecha_pago >= :fecha_inicio
                  AND fecha_pago <= :fecha_fin
                  AND monto_pagado IS NOT NULL
                  AND monto_pagado > 0
                  AND activo = TRUE
                GROUP BY institucion_bancaria
            """
            ).bindparams(fecha_inicio=fecha_inicio_dt, fecha_fin=fecha_fin_dt)
        ).fetchall()

        pagos_por_metodo = [
            {
                "metodo": row[0] if row[0] is not None else "",
                "cantidad": row[1] if row[1] is not None else 0,
                "monto": float(row[2]) if row[2] is not None else 0.0,
            }
            for row in pagos_por_metodo_raw
        ]

        # ✅ Usar tabla pagos con institucion_bancaria

        logger.info(f"[reportes.pagos] Pagos por método: {len(pagos_por_metodo)} métodos")

        # Pagos por día: usar tabla pagos (tipos nativos)
        pagos_por_dia_raw = db.execute(
            text(
                """
                SELECT
                    DATE(fecha_pago) AS fecha,
                    COUNT(*) AS cantidad,
                    COALESCE(SUM(monto_pagado), 0) AS monto
                FROM pagos
                WHERE fecha_pago >= :fecha_inicio
                  AND fecha_pago <= :fecha_fin
                  AND monto_pagado IS NOT NULL
                  AND monto_pagado > 0
                  AND activo = TRUE
                GROUP BY DATE(fecha_pago)
                ORDER BY fecha
            """
            ).bindparams(fecha_inicio=fecha_inicio_dt, fecha_fin=fecha_fin_dt)
        ).fetchall()

        pagos_por_dia = [
            {
                "fecha": row[0].isoformat() if row[0] is not None else None,
                "cantidad": row[1] if row[1] is not None else 0,
                "monto": float(row[2]) if row[2] is not None else 0.0,
            }
            for row in pagos_por_dia_raw
        ]

        logger.info(f"[reportes.pagos] Pagos por día: {len(pagos_por_dia)} días")

        resultado = ReportePagos(
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            total_pagos=total_pagos,
            cantidad_pagos=cantidad_pagos,
            pagos_por_metodo=pagos_por_metodo,
            pagos_por_dia=pagos_por_dia,
        )
        logger.info("[reportes.pagos] Reporte generado correctamente")
        return resultado

    except HTTPException:
        raise
    except Exception as e:
        raise handle_report_error(e, "generar reporte de pagos")


@router.get("/morosidad", response_model=ReporteMorosidad)
@cache_result(ttl=300, key_prefix="reportes")  # Cache por 5 minutos
def reporte_morosidad(
    fecha_corte: Optional[date] = Query(None, description="Fecha de corte"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Genera reporte detallado de morosidad."""
    try:
        logger.info("[reportes.morosidad] Iniciando generación de reporte")
        if not fecha_corte:
            fecha_corte = date.today()

        # 1. Resumen General de Morosidad
        resumen_query = db.execute(
            text(
                """
                SELECT
                    COUNT(DISTINCT p.id) as total_prestamos_mora,
                    COUNT(DISTINCT p.cedula) as total_clientes_mora,
                    COALESCE(SUM(c.monto_morosidad), 0) as monto_total_mora,
                    COALESCE(SUM(c.dias_morosidad), 0) as dias_totales_mora,
                    AVG(c.dias_morosidad) as promedio_dias_mora
                FROM prestamos p
                INNER JOIN cuotas c ON c.prestamo_id = p.id
                INNER JOIN clientes cl ON cl.id = p.cliente_id
                WHERE p.estado = 'APROBADO'
                  AND c.dias_morosidad > 0
                  AND c.monto_morosidad > 0
                  AND cl.estado != 'INACTIVO'
            """
            )
        )
        resumen = resumen_query.first()
        if resumen is None:
            total_prestamos_mora = 0
            total_clientes_mora = 0
            monto_total_mora = Decimal("0")
            promedio_dias_mora = 0.0
        else:
            total_prestamos_mora = resumen[0] or 0
            total_clientes_mora = resumen[1] or 0
            monto_total_mora = Decimal(str(resumen[2] or 0))
            promedio_dias_mora = float(resumen[4] or 0)

        # 2. Distribución por Rango de Días
        distribucion_query = db.execute(
            text(
                """
                SELECT
                    CASE
                        WHEN c.dias_morosidad BETWEEN 1 AND 30 THEN '1-30 días'
                        WHEN c.dias_morosidad BETWEEN 31 AND 60 THEN '31-60 días'
                        WHEN c.dias_morosidad BETWEEN 61 AND 90 THEN '61-90 días'
                        WHEN c.dias_morosidad BETWEEN 91 AND 180 THEN '91-180 días'
                        ELSE 'Más de 180 días'
                    END as rango_dias,
                    COUNT(DISTINCT p.id) as cantidad_prestamos,
                    COUNT(DISTINCT p.cedula) as cantidad_clientes,
                    COUNT(c.id) as cantidad_cuotas,
                    COALESCE(SUM(c.monto_morosidad), 0) as monto_total
                FROM prestamos p
                INNER JOIN cuotas c ON c.prestamo_id = p.id
                INNER JOIN clientes cl ON cl.id = p.cliente_id
                WHERE p.estado = 'APROBADO'
                  AND c.dias_morosidad > 0
                  AND c.monto_morosidad > 0
                  AND cl.estado != 'INACTIVO'
                GROUP BY rango_dias
                ORDER BY
                    CASE rango_dias
                        WHEN '1-30 días' THEN 1
                        WHEN '31-60 días' THEN 2
                        WHEN '61-90 días' THEN 3
                        WHEN '91-180 días' THEN 4
                        ELSE 5
                    END
            """
            )
        )
        distribucion_por_rango = [
            {
                "rango": row[0] if row[0] is not None else "",
                "cantidad_prestamos": row[1] if row[1] is not None else 0,
                "cantidad_clientes": row[2] if row[2] is not None else 0,
                "cantidad_cuotas": row[3] if row[3] is not None else 0,
                "monto_total": float(row[4]) if row[4] is not None else 0.0,
            }
            for row in distribucion_query.fetchall()
        ]

        # 3. Morosidad por Analista
        analistas_query = db.execute(
            text(
                """
                SELECT
                    COALESCE(p.analista, p.producto_financiero, 'Sin Analista') as analista,
                    COUNT(DISTINCT p.id) as cantidad_prestamos,
                    COUNT(DISTINCT p.cedula) as cantidad_clientes,
                    COALESCE(SUM(c.monto_morosidad), 0) as monto_total_mora,
                    AVG(c.dias_morosidad) as promedio_dias_mora
                FROM prestamos p
                INNER JOIN cuotas c ON c.prestamo_id = p.id
                INNER JOIN clientes cl ON cl.id = p.cliente_id
                WHERE p.estado = 'APROBADO'
                  AND c.dias_morosidad > 0
                  AND c.monto_morosidad > 0
                  AND cl.estado != 'INACTIVO'
                GROUP BY COALESCE(p.analista, p.producto_financiero, 'Sin Analista')
                ORDER BY monto_total_mora DESC
            """
            )
        )
        morosidad_por_analista = [
            {
                "analista": row[0] if row[0] is not None else "",
                "cantidad_prestamos": row[1] if row[1] is not None else 0,
                "cantidad_clientes": row[2] if row[2] is not None else 0,
                "monto_total_mora": float(row[3]) if row[3] is not None else 0.0,
                "promedio_dias_mora": float(row[4] or 0) if row[4] is not None else 0.0,
            }
            for row in analistas_query.fetchall()
        ]

        # 4. Detalle de Préstamos en Mora (con límite de paginación)
        detalle_query = db.execute(
            text(
                """
                SELECT
                    p.id as prestamo_id,
                    p.cedula,
                    p.nombres,
                    p.total_financiamiento,
                    COALESCE(p.analista, p.producto_financiero, 'Sin Analista') as analista,
                    p.concesionario,
                    COUNT(c.id) as cuotas_en_mora,
                    COALESCE(SUM(c.monto_morosidad), 0) as monto_total_mora,
                    MAX(c.dias_morosidad) as max_dias_mora,
                    MIN(c.fecha_vencimiento) as primera_cuota_vencida
                FROM prestamos p
                INNER JOIN cuotas c ON c.prestamo_id = p.id
                INNER JOIN clientes cl ON cl.id = p.cliente_id
                WHERE p.estado = 'APROBADO'
                  AND c.dias_morosidad > 0
                  AND c.monto_morosidad > 0
                  AND cl.estado != 'INACTIVO'
                GROUP BY p.id, p.cedula, p.nombres, p.total_financiamiento, p.analista, p.producto_financiero, p.concesionario
                ORDER BY monto_total_mora DESC
                LIMIT 1000
            """
            )
        )
        detalle_prestamos = [
            {
                "prestamo_id": row[0] if row[0] is not None else 0,
                "cedula": row[1] if row[1] is not None else "",
                "nombres": row[2] if row[2] is not None else "",
                "total_financiamiento": float(row[3]) if row[3] is not None else 0.0,
                "analista": row[4] if row[4] is not None else "",
                "concesionario": row[5] if row[5] is not None else "",
                "cuotas_en_mora": row[6] if row[6] is not None else 0,
                "monto_total_mora": float(row[7]) if row[7] is not None else 0.0,
                "max_dias_mora": row[8] if row[8] is not None else 0,
                "primera_cuota_vencida": row[9].isoformat() if row[9] is not None else None,
            }
            for row in detalle_query.fetchall()
        ]

        resultado = ReporteMorosidad(
            fecha_corte=fecha_corte,
            total_prestamos_mora=total_prestamos_mora,
            total_clientes_mora=total_clientes_mora,
            monto_total_mora=monto_total_mora,
            promedio_dias_mora=promedio_dias_mora,
            distribucion_por_rango=distribucion_por_rango,
            morosidad_por_analista=morosidad_por_analista,
            detalle_prestamos=detalle_prestamos,
        )
        logger.info("[reportes.morosidad] Reporte generado correctamente")
        return resultado

    except HTTPException:
        raise
    except Exception as e:
        raise handle_report_error(e, "generar reporte de morosidad")


@router.get("/financiero", response_model=ReporteFinanciero)
@cache_result(ttl=300, key_prefix="reportes")  # Cache por 5 minutos
def reporte_financiero(
    fecha_corte: Optional[date] = Query(None, description="Fecha de corte"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Genera reporte financiero consolidado."""
    try:
        logger.info("[reportes.financiero] Iniciando generación de reporte")
        if not fecha_corte:
            fecha_corte = date.today()

        # 1. Resumen Financiero General
        resumen_query = db.execute(
            text(
                """
                SELECT
                    COALESCE(SUM(pa.monto_pagado), 0) as total_ingresos,
                    COUNT(pa.id) as cantidad_pagos,
                    COALESCE(SUM(p.total_financiamiento), 0) as cartera_total,
                    COALESCE(SUM(c.capital_pendiente + c.interes_pendiente + COALESCE(c.monto_mora, 0)), 0) as cartera_pendiente,
                    COALESCE(SUM(CASE WHEN c.dias_morosidad > 0 THEN c.monto_morosidad ELSE 0 END), 0) as morosidad_total
                FROM prestamos p
                LEFT JOIN cuotas c ON c.prestamo_id = p.id AND c.estado != 'PAGADO'
                LEFT JOIN pagos pa ON pa.prestamo_id = p.id AND pa.activo = true
                INNER JOIN clientes cl ON cl.id = p.cliente_id
                WHERE p.estado = 'APROBADO'
                  AND cl.estado != 'INACTIVO'
            """
            )
        )
        resumen = resumen_query.first()
        if resumen is None:
            total_ingresos = Decimal("0")
            cantidad_pagos = 0
            cartera_total = Decimal("0")
            cartera_pendiente = Decimal("0")
            morosidad_total = Decimal("0")
        else:
            total_ingresos = Decimal(str(resumen[0] or 0))
            cantidad_pagos = resumen[1] or 0
            cartera_total = Decimal(str(resumen[2] or 0))
            cartera_pendiente = Decimal(str(resumen[3] or 0))
            morosidad_total = Decimal(str(resumen[4] or 0))
        saldo_pendiente = cartera_total - total_ingresos
        porcentaje_cobrado = float((total_ingresos / cartera_total * 100) if cartera_total > 0 else 0)

        # 2. Ingresos por Mes (Últimos 12 meses)
        ingresos_query = db.execute(
            text(
                """
                SELECT
                    DATE_TRUNC('month', pa.fecha_pago)::date as mes,
                    COUNT(pa.id) as cantidad_pagos,
                    COALESCE(SUM(pa.monto_pagado), 0) as monto_total
                FROM pagos pa
                INNER JOIN prestamos p ON p.id = pa.prestamo_id
                INNER JOIN clientes cl ON cl.id = p.cliente_id
                WHERE pa.activo = true
                  AND p.estado = 'APROBADO'
                  AND cl.estado != 'INACTIVO'
                  AND pa.fecha_pago >= DATE_TRUNC('month', CURRENT_DATE) - INTERVAL '12 months'
                GROUP BY DATE_TRUNC('month', pa.fecha_pago)
                ORDER BY mes DESC
            """
            )
        )
        ingresos_por_mes = [
            {
                "mes": row[0].isoformat() if row[0] else None,
                "cantidad_pagos": row[1],
                "monto_total": float(row[2]),
            }
            for row in ingresos_query.fetchall()
        ]

        # 3. Egresos Programados (Cuotas por Vencer)
        egresos_query = db.execute(
            text(
                """
                SELECT
                    DATE_TRUNC('month', c.fecha_vencimiento)::date as mes,
                    COUNT(c.id) as cantidad_cuotas,
                    COALESCE(SUM(c.monto_cuota), 0) as monto_programado
                FROM cuotas c
                INNER JOIN prestamos p ON p.id = c.prestamo_id
                INNER JOIN clientes cl ON cl.id = p.cliente_id
                WHERE p.estado = 'APROBADO'
                  AND c.estado != 'PAGADO'
                  AND cl.estado != 'INACTIVO'
                  AND c.fecha_vencimiento >= DATE_TRUNC('month', CURRENT_DATE)
                  AND c.fecha_vencimiento < DATE_TRUNC('month', CURRENT_DATE) + INTERVAL '12 months'
                GROUP BY DATE_TRUNC('month', c.fecha_vencimiento)
                ORDER BY mes
            """
            )
        )
        egresos_programados = [
            {
                "mes": row[0].isoformat() if row[0] else None,
                "cantidad_cuotas": row[1],
                "monto_programado": float(row[2]),
            }
            for row in egresos_query.fetchall()
        ]

        # 4. Flujo de Caja (combinar ingresos y egresos)
        flujo_caja = []
        ingresos_dict = {item["mes"]: item["monto_total"] for item in ingresos_por_mes}
        egresos_dict = {item["mes"]: item["monto_programado"] for item in egresos_programados}
        todos_meses = set(list(ingresos_dict.keys()) + list(egresos_dict.keys()))

        for mes in sorted(todos_meses):
            ingresos = ingresos_dict.get(mes, 0)
            egresos = egresos_dict.get(mes, 0)
            flujo_caja.append(
                {
                    "mes": mes,
                    "ingresos": ingresos,
                    "egresos_programados": egresos,
                    "flujo_neto": ingresos - egresos,
                }
            )

        resultado = ReporteFinanciero(
            fecha_corte=fecha_corte,
            total_ingresos=total_ingresos,
            cantidad_pagos=cantidad_pagos,
            cartera_total=cartera_total,
            cartera_pendiente=cartera_pendiente,
            morosidad_total=morosidad_total,
            saldo_pendiente=saldo_pendiente,
            porcentaje_cobrado=porcentaje_cobrado,
            ingresos_por_mes=ingresos_por_mes,
            egresos_programados=egresos_programados,
            flujo_caja=flujo_caja,
        )
        logger.info("[reportes.financiero] Reporte generado correctamente")
        return resultado

    except HTTPException:
        raise
    except Exception as e:
        raise handle_report_error(e, "generar reporte financiero")


@router.get("/asesores", response_model=ReporteAsesores)
@cache_result(ttl=300, key_prefix="reportes")  # Cache por 5 minutos
def reporte_asesores(
    fecha_corte: Optional[date] = Query(None, description="Fecha de corte"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Genera reporte de desempeño de asesores/analistas."""
    try:
        logger.info("[reportes.asesores] Iniciando generación de reporte")
        if not fecha_corte:
            fecha_corte = date.today()

        # 1. Resumen por Analista
        resumen_query = db.execute(
            text(
                """
                SELECT
                    COALESCE(p.analista, p.producto_financiero, 'Sin Analista') as analista,
                    COUNT(DISTINCT p.id) as total_prestamos,
                    COUNT(DISTINCT p.cedula) as total_clientes,
                    COALESCE(SUM(p.total_financiamiento), 0) as cartera_total,
                    COALESCE(SUM(CASE WHEN c.dias_morosidad > 0 THEN c.monto_morosidad ELSE 0 END), 0) as morosidad_total,
                    COALESCE(SUM(pa.monto_pagado), 0) as total_cobrado
                FROM prestamos p
                LEFT JOIN cuotas c ON c.prestamo_id = p.id
                LEFT JOIN pagos pa ON pa.prestamo_id = p.id AND pa.activo = true
                INNER JOIN clientes cl ON cl.id = p.cliente_id
                WHERE p.estado = 'APROBADO'
                  AND cl.estado != 'INACTIVO'
                GROUP BY COALESCE(p.analista, p.producto_financiero, 'Sin Analista')
                ORDER BY cartera_total DESC
            """
            )
        )
        resumen_por_analista = []
        for row in resumen_query.fetchall():
            cartera_total = float(row[3])
            total_cobrado = float(row[5])
            morosidad_total = float(row[4])
            porcentaje_cobrado = (total_cobrado / cartera_total * 100) if cartera_total > 0 else 0
            porcentaje_morosidad = (morosidad_total / cartera_total * 100) if cartera_total > 0 else 0

            resumen_por_analista.append(
                {
                    "analista": row[0],
                    "total_prestamos": row[1],
                    "total_clientes": row[2],
                    "cartera_total": cartera_total,
                    "morosidad_total": morosidad_total,
                    "total_cobrado": total_cobrado,
                    "porcentaje_cobrado": porcentaje_cobrado,
                    "porcentaje_morosidad": porcentaje_morosidad,
                }
            )

        # 2. Desempeño Mensual (Últimos 6 meses)
        desempeno_query = db.execute(
            text(
                """
                SELECT
                    COALESCE(p.analista, p.producto_financiero, 'Sin Analista') as analista,
                    DATE_TRUNC('month', p.fecha_aprobacion)::date as mes,
                    COUNT(DISTINCT p.id) as prestamos_aprobados,
                    COALESCE(SUM(p.total_financiamiento), 0) as monto_aprobado,
                    COALESCE(SUM(pa.monto_pagado), 0) as monto_cobrado
                FROM prestamos p
                LEFT JOIN pagos pa ON pa.prestamo_id = p.id
                    AND pa.activo = true
                    AND DATE_TRUNC('month', pa.fecha_pago) = DATE_TRUNC('month', p.fecha_aprobacion)
                INNER JOIN clientes cl ON cl.id = p.cliente_id
                WHERE p.estado = 'APROBADO'
                  AND cl.estado != 'INACTIVO'
                  AND p.fecha_aprobacion >= DATE_TRUNC('month', CURRENT_DATE) - INTERVAL '6 months'
                GROUP BY COALESCE(p.analista, p.producto_financiero, 'Sin Analista'), DATE_TRUNC('month', p.fecha_aprobacion)
                ORDER BY analista, mes DESC
            """
            )
        )
        desempeno_mensual = [
            {
                "analista": row[0],
                "mes": row[1].isoformat() if row[1] else None,
                "prestamos_aprobados": row[2],
                "monto_aprobado": float(row[3]),
                "monto_cobrado": float(row[4]),
            }
            for row in desempeno_query.fetchall()
        ]

        # 3. Clientes por Analista
        clientes_query = db.execute(
            text(
                """
                SELECT
                    COALESCE(p.analista, p.producto_financiero, 'Sin Analista') as analista,
                    p.cedula,
                    p.nombres,
                    COUNT(DISTINCT p.id) as cantidad_prestamos,
                    COALESCE(SUM(p.total_financiamiento), 0) as monto_total_prestamos,
                    COALESCE(SUM(pa.monto_pagado), 0) as monto_total_pagado,
                    COALESCE(SUM(CASE WHEN c.dias_morosidad > 0 THEN c.monto_morosidad ELSE 0 END), 0) as monto_mora
                FROM prestamos p
                LEFT JOIN cuotas c ON c.prestamo_id = p.id
                LEFT JOIN pagos pa ON pa.prestamo_id = p.id AND pa.activo = true
                INNER JOIN clientes cl ON cl.id = p.cliente_id
                WHERE p.estado = 'APROBADO'
                  AND cl.estado != 'INACTIVO'
                GROUP BY COALESCE(p.analista, p.producto_financiero, 'Sin Analista'), p.cedula, p.nombres
                ORDER BY analista, monto_total_prestamos DESC
            """
            )
        )
        clientes_por_analista = [
            {
                "analista": row[0],
                "cedula": row[1],
                "nombres": row[2],
                "cantidad_prestamos": row[3],
                "monto_total_prestamos": float(row[4]),
                "monto_total_pagado": float(row[5]),
                "monto_mora": float(row[6]),
            }
            for row in clientes_query.fetchall()
        ]

        resultado = ReporteAsesores(
            fecha_corte=fecha_corte,
            resumen_por_analista=resumen_por_analista,
            desempeno_mensual=desempeno_mensual,
            clientes_por_analista=clientes_por_analista,
        )
        logger.info("[reportes.asesores] Reporte generado correctamente")
        return resultado

    except HTTPException:
        raise
    except Exception as e:
        raise handle_report_error(e, "generar reporte de asesores")


@router.get("/productos", response_model=ReporteProductos)
@cache_result(ttl=300, key_prefix="reportes")  # Cache por 5 minutos
def reporte_productos(
    fecha_corte: Optional[date] = Query(None, description="Fecha de corte"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Genera reporte de productos/modelos de vehículos."""
    try:
        logger.info("[reportes.productos] Iniciando generación de reporte")
        if not fecha_corte:
            fecha_corte = date.today()

        # 1. Resumen por Producto/Modelo
        resumen_query = db.execute(
            text(
                """
                SELECT
                    COALESCE(p.modelo_vehiculo, p.producto, 'Sin Modelo') as producto,
                    COUNT(DISTINCT p.id) as total_prestamos,
                    COUNT(DISTINCT p.cedula) as total_clientes,
                    COALESCE(SUM(p.total_financiamiento), 0) as cartera_total,
                    COALESCE(AVG(p.total_financiamiento), 0) as promedio_prestamo,
                    COALESCE(SUM(pa.monto_pagado), 0) as total_cobrado,
                    COALESCE(SUM(CASE WHEN c.dias_morosidad > 0 THEN c.monto_morosidad ELSE 0 END), 0) as morosidad_total
                FROM prestamos p
                LEFT JOIN cuotas c ON c.prestamo_id = p.id
                LEFT JOIN pagos pa ON pa.prestamo_id = p.id AND pa.activo = true
                INNER JOIN clientes cl ON cl.id = p.cliente_id
                WHERE p.estado = 'APROBADO'
                  AND cl.estado != 'INACTIVO'
                GROUP BY COALESCE(p.modelo_vehiculo, p.producto, 'Sin Modelo')
                ORDER BY cartera_total DESC
            """
            )
        )
        resumen_por_producto = []
        for row in resumen_query.fetchall():
            cartera_total = float(row[3])
            total_cobrado = float(row[5])
            porcentaje_cobrado = (total_cobrado / cartera_total * 100) if cartera_total > 0 else 0

            resumen_por_producto.append(
                {
                    "producto": row[0],
                    "total_prestamos": row[1],
                    "total_clientes": row[2],
                    "cartera_total": cartera_total,
                    "promedio_prestamo": float(row[4]),
                    "total_cobrado": total_cobrado,
                    "morosidad_total": float(row[6]),
                    "porcentaje_cobrado": porcentaje_cobrado,
                }
            )

        # 2. Productos por Concesionario
        concesionario_query = db.execute(
            text(
                """
                SELECT
                    p.concesionario,
                    COALESCE(p.modelo_vehiculo, p.producto, 'Sin Modelo') as producto,
                    COUNT(DISTINCT p.id) as cantidad_prestamos,
                    COALESCE(SUM(p.total_financiamiento), 0) as monto_total
                FROM prestamos p
                INNER JOIN clientes cl ON cl.id = p.cliente_id
                WHERE p.estado = 'APROBADO'
                  AND cl.estado != 'INACTIVO'
                  AND p.concesionario IS NOT NULL
                GROUP BY p.concesionario, COALESCE(p.modelo_vehiculo, p.producto, 'Sin Modelo')
                ORDER BY p.concesionario, monto_total DESC
            """
            )
        )
        productos_por_concesionario = [
            {
                "concesionario": row[0],
                "producto": row[1],
                "cantidad_prestamos": row[2],
                "monto_total": float(row[3]),
            }
            for row in concesionario_query.fetchall()
        ]

        # 3. Tendencia de Productos (Últimos 12 meses)
        tendencia_query = db.execute(
            text(
                """
                SELECT
                    COALESCE(p.modelo_vehiculo, p.producto, 'Sin Modelo') as producto,
                    DATE_TRUNC('month', p.fecha_aprobacion)::date as mes,
                    COUNT(DISTINCT p.id) as prestamos_aprobados,
                    COALESCE(SUM(p.total_financiamiento), 0) as monto_aprobado
                FROM prestamos p
                INNER JOIN clientes cl ON cl.id = p.cliente_id
                WHERE p.estado = 'APROBADO'
                  AND cl.estado != 'INACTIVO'
                  AND p.fecha_aprobacion >= DATE_TRUNC('month', CURRENT_DATE) - INTERVAL '12 months'
                GROUP BY COALESCE(p.modelo_vehiculo, p.producto, 'Sin Modelo'), DATE_TRUNC('month', p.fecha_aprobacion)
                ORDER BY producto, mes DESC
            """
            )
        )
        tendencia_mensual = [
            {
                "producto": row[0],
                "mes": row[1].isoformat() if row[1] else None,
                "prestamos_aprobados": row[2],
                "monto_aprobado": float(row[3]),
            }
            for row in tendencia_query.fetchall()
        ]

        resultado = ReporteProductos(
            fecha_corte=fecha_corte,
            resumen_por_producto=resumen_por_producto,
            productos_por_concesionario=productos_por_concesionario,
            tendencia_mensual=tendencia_mensual,
        )
        logger.info("[reportes.productos] Reporte generado correctamente")
        return resultado

    except HTTPException:
        raise
    except Exception as e:
        raise handle_report_error(e, "generar reporte de productos")


def _obtener_distribucion_por_monto(db: Session) -> list:
    """Obtiene distribución de préstamos por rango de monto"""
    distribucion_por_monto_query = (
        db.query(
            case(
                (Prestamo.total_financiamiento <= 1000, "Hasta $1,000"),
                (Prestamo.total_financiamiento <= 5000, "$1,001 - $5,000"),
                (Prestamo.total_financiamiento <= 10000, "$5,001 - $10,000"),
                else_="Más de $10,000",
            ).label("rango"),
            func.count(Prestamo.id).label("cantidad"),
            func.sum(Prestamo.total_financiamiento).label("monto"),
        )
        .filter(Prestamo.estado == "APROBADO")
        .group_by("rango")
        .all()
    )

    return [
        {
            "rango": item.rango,
            "cantidad": item.cantidad,
            "monto": float(item.monto) if item.monto else 0.0,
        }
        for item in distribucion_por_monto_query
    ]


def _obtener_distribucion_por_mora(db: Session) -> list:
    """Obtiene distribución de préstamos por rango de días de mora"""
    rangos_mora = [
        {"min": 1, "max": 30, "label": "1-30 días"},
        {"min": 31, "max": 60, "label": "31-60 días"},
        {"min": 61, "max": 90, "label": "61-90 días"},
        {"min": 91, "max": 999999, "label": "Más de 90 días"},
    ]

    distribucion_por_mora = []
    for rango in rangos_mora:
        cantidad = (
            db.query(func.count(func.distinct(Prestamo.id)))
            .join(Cuota, Cuota.prestamo_id == Prestamo.id)
            .filter(
                Prestamo.estado == "APROBADO",
                Cuota.monto_mora > Decimal("0.00"),
                Cuota.dias_mora >= rango["min"],
                Cuota.dias_mora <= rango["max"],
            )
            .scalar()
        ) or 0

        monto_mora = (
            db.query(func.sum(Cuota.monto_mora))
            .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
            .filter(
                Prestamo.estado == "APROBADO",
                Cuota.monto_mora > Decimal("0.00"),
                Cuota.dias_mora >= rango["min"],
                Cuota.dias_mora <= rango["max"],
            )
            .scalar()
        ) or Decimal("0")

        distribucion_por_mora.append(
            {
                "rango": rango["label"],
                "cantidad": cantidad,
                "monto_total": float(monto_mora),
            }
        )

    return distribucion_por_mora


def _obtener_estilos_excel():
    """Obtiene estilos reutilizables para Excel"""
    return {
        "header_fill": PatternFill(start_color="366092", end_color="366092", fill_type="solid"),
        "header_font": Font(bold=True, color="FFFFFF", size=14),
        "title_font": Font(bold=True, size=16),
        "label_font": Font(bold=True),
        "border": Border(
            left=Side(style="thin"),
            right=Side(style="thin"),
            top=Side(style="thin"),
            bottom=Side(style="thin"),
        ),
    }


def _crear_hoja_resumen_excel(ws, reporte, cantidad_prestamos_activos, cantidad_prestamos_mora, estilos):
    """Crea la hoja de resumen ejecutivo en Excel"""
    ws.title = "Resumen Ejecutivo"

    ws.merge_cells("A1:B1")
    ws["A1"] = "REPORTE DE CARTERA"
    ws["A1"].font = estilos["title_font"]
    ws["A1"].alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 30

    ws["A2"] = f"Fecha de Corte: {reporte.fecha_corte}"
    ws["A2"].font = Font(size=12)
    ws["A3"] = f"Generado el: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"
    ws["A3"].font = Font(size=10, italic=True)

    row = 5
    datos_resumen = [
        ("Cartera Total:", reporte.cartera_total),
        ("Capital Pendiente:", reporte.capital_pendiente),
        ("Intereses Pendientes:", reporte.intereses_pendientes),
        ("Mora Total:", reporte.mora_total),
        ("Préstamos Activos:", cantidad_prestamos_activos),
        ("Préstamos en Mora:", cantidad_prestamos_mora),
    ]

    for label, value in datos_resumen:
        ws[f"A{row}"] = label
        ws[f"A{row}"].font = estilos["label_font"]
        if isinstance(value, Decimal):
            ws[f"B{row}"] = float(value)
            ws[f"B{row}"].number_format = '"$"#,##0.00'
        else:
            ws[f"B{row}"] = value
        ws[f"B{row}"].font = Font(bold=True)
        row += 1

    ws.column_dimensions["A"].width = 25
    ws.column_dimensions["B"].width = 20


def _crear_hoja_distribucion_monto_excel(ws, distribucion_por_monto, estilos):
    """Crea la hoja de distribución por monto en Excel"""
    ws.title = "Distribución por Monto"

    headers = ["Rango de Monto", "Cantidad Préstamos", "Monto Total"]
    for col_idx, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col_idx, value=header)
        cell.font = estilos["header_font"]
        cell.fill = estilos["header_fill"]
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = estilos["border"]

    for row_idx, item in enumerate(distribucion_por_monto, 2):
        ws.cell(row=row_idx, column=1, value=item["rango"]).border = estilos["border"]
        ws.cell(row=row_idx, column=2, value=item["cantidad"]).border = estilos["border"]
        cell_monto = ws.cell(row=row_idx, column=3, value=float(item["monto"]))
        cell_monto.number_format = '"$"#,##0.00'
        cell_monto.border = estilos["border"]

    total_row = len(distribucion_por_monto) + 3
    ws.cell(row=total_row, column=1, value="TOTAL:").font = Font(bold=True)
    ws.cell(row=total_row, column=2, value=sum(item["cantidad"] for item in distribucion_por_monto)).font = Font(bold=True)
    total_cell = ws.cell(row=total_row, column=3, value=sum(item["monto"] for item in distribucion_por_monto))
    total_cell.number_format = '"$"#,##0.00'
    total_cell.font = Font(bold=True)

    ws.column_dimensions["A"].width = 20
    ws.column_dimensions["B"].width = 20
    ws.column_dimensions["C"].width = 20


def _crear_hoja_distribucion_mora_excel(ws, distribucion_por_mora, estilos):
    """Crea la hoja de distribución por mora en Excel"""
    ws.title = "Distribución por Mora"

    headers_mora = ["Rango de Días", "Cantidad Préstamos", "Monto Total Mora"]
    for col_idx, header in enumerate(headers_mora, 1):
        cell = ws.cell(row=1, column=col_idx, value=header)
        cell.font = estilos["header_font"]
        cell.fill = estilos["header_fill"]
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = estilos["border"]

    for row_idx, item in enumerate(distribucion_por_mora, 2):
        ws.cell(row=row_idx, column=1, value=item["rango"]).border = estilos["border"]
        ws.cell(row=row_idx, column=2, value=item["cantidad"]).border = estilos["border"]
        cell_mora = ws.cell(row=row_idx, column=3, value=float(item["monto_total"]))
        cell_mora.number_format = '"$"#,##0.00'
        cell_mora.border = estilos["border"]

    total_row_mora = len(distribucion_por_mora) + 3
    ws.cell(row=total_row_mora, column=1, value="TOTAL:").font = Font(bold=True)
    ws.cell(row=total_row_mora, column=2, value=sum(item["cantidad"] for item in distribucion_por_mora)).font = Font(bold=True)
    total_cell_mora = ws.cell(
        row=total_row_mora, column=3, value=float(sum(item["monto_total"] for item in distribucion_por_mora))
    )
    total_cell_mora.number_format = '"$"#,##0.00'
    total_cell_mora.font = Font(bold=True)

    ws.column_dimensions["A"].width = 20
    ws.column_dimensions["B"].width = 20
    ws.column_dimensions["C"].width = 20


def _crear_hoja_prestamos_detallados_excel(ws, db: Session, estilos):
    """Crea la hoja de préstamos detallados en Excel"""
    ws.title = "Préstamos Detallados"

    prestamos_detalle = (
        db.query(
            Prestamo.id,
            Prestamo.cedula,
            Prestamo.nombres,
            Prestamo.total_financiamiento,
            Prestamo.estado,
            Prestamo.modalidad_pago,
            Prestamo.numero_cuotas,
            Prestamo.usuario_proponente.label("analista"),
            func.sum(
                func.coalesce(Cuota.capital_pendiente, Decimal("0.00"))
                + func.coalesce(Cuota.interes_pendiente, Decimal("0.00"))
                + func.coalesce(Cuota.monto_mora, Decimal("0.00"))
            ).label("saldo_pendiente"),
            func.count(Cuota.id).label("cuotas_pendientes"),
        )
        .join(Cuota, Cuota.prestamo_id == Prestamo.id, isouter=True)
        .filter(Prestamo.estado == "APROBADO")
        .group_by(Prestamo.id)
        .order_by(Prestamo.id)
        .all()
    )

    headers_detalle = [
        "ID Préstamo",
        "Cédula",
        "Cliente",
        "Total Financiamiento",
        "Saldo Pendiente",
        "Cuotas Pendientes",
        "Modalidad",
        "Analista",
        "Estado",
    ]
    for col_idx, header in enumerate(headers_detalle, 1):
        cell = ws.cell(row=1, column=col_idx, value=header)
        cell.font = estilos["header_font"]
        cell.fill = estilos["header_fill"]
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = estilos["border"]

    for row_idx, prestamo in enumerate(prestamos_detalle, 2):
        ws.cell(row=row_idx, column=1, value=prestamo.id).border = estilos["border"]
        ws.cell(row=row_idx, column=2, value=prestamo.cedula).border = estilos["border"]
        ws.cell(row=row_idx, column=3, value=prestamo.nombres or "").border = estilos["border"]
        cell_total = ws.cell(row=row_idx, column=4, value=float(prestamo.total_financiamiento))
        cell_total.number_format = '"$"#,##0.00'
        cell_total.border = estilos["border"]
        cell_saldo = ws.cell(row=row_idx, column=5, value=float(prestamo.saldo_pendiente or Decimal("0")))
        cell_saldo.number_format = '"$"#,##0.00'
        cell_saldo.border = estilos["border"]
        ws.cell(row=row_idx, column=6, value=prestamo.cuotas_pendientes or 0).border = estilos["border"]
        ws.cell(row=row_idx, column=7, value=prestamo.modalidad_pago or "").border = estilos["border"]
        ws.cell(row=row_idx, column=8, value=prestamo.analista or "").border = estilos["border"]
        ws.cell(row=row_idx, column=9, value=prestamo.estado or "").border = estilos["border"]

    column_widths = [12, 15, 30, 18, 18, 15, 15, 25, 12]
    for idx, width in enumerate(column_widths, 1):
        ws.column_dimensions[chr(64 + idx)].width = width


def _generar_excel_completo(reporte, db: Session, cantidad_prestamos_activos, cantidad_prestamos_mora):
    """Genera el archivo Excel completo con todas las hojas"""
    wb = Workbook()
    estilos = _obtener_estilos_excel()

    _crear_hoja_resumen_excel(wb.active, reporte, cantidad_prestamos_activos, cantidad_prestamos_mora, estilos)
    _crear_hoja_distribucion_monto_excel(
        wb.create_sheet("Distribución por Monto"), _obtener_distribucion_por_monto(db), estilos
    )
    _crear_hoja_distribucion_mora_excel(wb.create_sheet("Distribución por Mora"), _obtener_distribucion_por_mora(db), estilos)
    _crear_hoja_prestamos_detallados_excel(wb.create_sheet("Préstamos Detallados"), db, estilos)

    output = BytesIO()
    wb.save(output)
    output.seek(0)
    return output


def _generar_pdf_completo(reporte):
    """Genera el archivo PDF completo"""
    try:
        output = BytesIO()
        c = canvas.Canvas(output, pagesize=A4)

        c.setFont("Helvetica-Bold", 16)
        c.drawString(100, 750, "REPORTE DE CARTERA")

        c.setFont("Helvetica", 12)
        c.drawString(100, 720, f"Fecha de Corte: {reporte.fecha_corte}")
        c.drawString(100, 700, f"Generado el: {datetime.now().strftime('%d/%m/%Y %H:%M')}")

        y = 680
        c.drawString(100, y, f"Cartera Total: ${float(reporte.cartera_total):,.2f}")
        y -= 20
        c.drawString(100, y, f"Capital Pendiente: ${float(reporte.capital_pendiente):,.2f}")
        y -= 20
        c.drawString(100, y, f"Intereses Pendientes: ${float(reporte.intereses_pendientes):,.2f}")
        y -= 20
        c.drawString(100, y, f"Mora Total: ${float(reporte.mora_total):,.2f}")
        y -= 20
        c.drawString(100, y, f"Préstamos Activos: {reporte.cantidad_prestamos_activos}")
        y -= 20
        c.drawString(100, y, f"Préstamos en Mora: {reporte.cantidad_prestamos_mora}")

        c.save()
        output.seek(0)
        return output
    except Exception as e:
        logger.error(f"Error generando PDF completo: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error generando PDF: {str(e)}")


def _registrar_auditoria_exportacion(db: Session, current_user: User, formato: str, fecha_corte: date):
    """Registra la auditoría de la exportación"""
    try:
        audit = Auditoria(
            usuario_id=current_user.id,
            accion="EXPORT",
            entidad="REPORTES",
            entidad_id=None,
            detalles=f"Exportó cartera en {formato.upper()} (fecha_corte={fecha_corte})",
            exito=True,
        )
        db.add(audit)
        db.commit()
    except Exception as e:
        logger.warning(f"No se pudo registrar auditoría de exportación ({formato}): {e}")


@router.get("/exportar/cartera")
@limiter.limit(RATE_LIMITS["strict"])  # Rate limiting estricto: 10/minuto
def exportar_reporte_cartera(
    request: Request,
    formato: str = Query("excel", description="Formato: excel o pdf"),
    fecha_corte: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Exporta reporte de cartera en Excel o PDF."""
    try:
        logger.info(f"[reportes.exportar] Exportando reporte cartera en formato {formato}")
        reporte = reporte_cartera(fecha_corte, db, current_user)

        cantidad_prestamos_activos = db.query(Prestamo).filter(Prestamo.estado == "APROBADO").count()
        cantidad_prestamos_mora = (
            db.query(func.count(func.distinct(Prestamo.id)))
            .join(Cuota, Cuota.prestamo_id == Prestamo.id)
            .filter(Prestamo.estado == "APROBADO", Cuota.monto_mora > Decimal("0.00"))
            .scalar()
        ) or 0

        if formato.lower() == "excel":
            output = _generar_excel_completo(reporte, db, cantidad_prestamos_activos, cantidad_prestamos_mora)
            response = StreamingResponse(
                output,
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                headers={"Content-Disposition": f"attachment; filename=reporte_cartera_{reporte.fecha_corte}.xlsx"},
            )
            logger.info("[reportes.exportar] Excel generado correctamente")
            try:
                _registrar_auditoria_exportacion(db, current_user, "excel", reporte.fecha_corte)
            except Exception as audit_error:
                logger.warning(f"No se pudo registrar auditoría: {audit_error}")
            return response

        elif formato.lower() == "pdf":
            output = _generar_pdf_completo(reporte)
            response = StreamingResponse(
                output,
                media_type="application/pdf",
                headers={"Content-Disposition": f"attachment; filename=reporte_cartera_{reporte.fecha_corte}.pdf"},
            )
            logger.info("[reportes.exportar] PDF generado correctamente")
            try:
                _registrar_auditoria_exportacion(db, current_user, "pdf", reporte.fecha_corte)
            except Exception as audit_error:
                logger.warning(f"No se pudo registrar auditoría: {audit_error}")
            return response

        else:
            raise HTTPException(status_code=400, detail="Formato no soportado. Use 'excel' o 'pdf'")

    except HTTPException:
        raise
    except Exception as e:
        raise handle_report_error(e, "exportar reporte de cartera")


@router.get("/dashboard/resumen")
@cache_result(ttl=300, key_prefix="reportes")  # Cache por 5 minutos
def resumen_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Obtiene resumen para dashboard."""
    try:
        # ✅ ROLLBACK PREVENTIVO: Restaurar transacción si está abortada
        try:
            db.execute(text("SELECT 1"))
        except Exception as test_error:
            error_str = str(test_error)
            if "aborted" in error_str.lower() or "InFailedSqlTransaction" in error_str:
                logger.warning("⚠️ [reportes.resumen] Transacción abortada detectada, haciendo rollback preventivo")
                try:
                    db.rollback()
                except Exception:
                    pass

        hoy = date.today()

        # Estadísticas básicas - Solo préstamos aprobados
        try:
            total_clientes = db.query(Cliente).filter(Cliente.activo).count()
        except Exception as e:
            logger.error(f"❌ [reportes.resumen] Error obteniendo total_clientes: {e}", exc_info=True)
            try:
                db.rollback()
            except Exception:
                pass
            total_clientes = 0

        try:
            # Total préstamos: usar query más robusta con func.count
            total_prestamos_query = db.query(func.count(Prestamo.id)).filter(Prestamo.estado == "APROBADO")
            total_prestamos = total_prestamos_query.scalar() or 0
            logger.info(f"[reportes.resumen] Total préstamos aprobados: {total_prestamos}")

            # Validación adicional: verificar que hay préstamos en la BD
            if total_prestamos == 0:
                total_todos_prestamos = db.query(func.count(Prestamo.id)).scalar() or 0
                logger.warning(
                    f"⚠️ [reportes.resumen] No hay préstamos APROBADOS. Total préstamos en BD: {total_todos_prestamos}"
                )
        except Exception as e:
            logger.error(f"❌ [reportes.resumen] Error obteniendo total_prestamos: {e}", exc_info=True)
            try:
                db.rollback()
            except Exception:
                pass
            total_prestamos = 0

        try:
            total_pagos = db.query(Pago).count()
        except Exception as e:
            logger.error(f"❌ [reportes.resumen] Error obteniendo total_pagos: {e}", exc_info=True)
            try:
                db.rollback()
            except Exception:
                pass
            total_pagos = 0

        # Cartera activa: calcular desde cuotas pendientes
        # Suma de capital_pendiente + interes_pendiente + monto_mora
        # Solo para préstamos aprobados y cuotas no pagadas
        try:
            cartera_activa_query = db.execute(
                text(
                    """
                    SELECT COALESCE(SUM(
                        COALESCE(c.capital_pendiente, 0) +
                        COALESCE(c.interes_pendiente, 0) +
                        COALESCE(c.monto_mora, 0)
                    ), 0) as cartera_activa
                    FROM cuotas c
                    INNER JOIN prestamos p ON c.prestamo_id = p.id
                    WHERE p.estado = 'APROBADO'
                      AND c.estado != 'PAGADO'
                """
                )
            )
            resultado_cartera = cartera_activa_query.scalar()
            if resultado_cartera is None:
                cartera_activa = 0.0
            elif isinstance(resultado_cartera, Decimal):
                cartera_activa = float(resultado_cartera)
            else:
                cartera_activa = float(resultado_cartera) if resultado_cartera else 0.0
            logger.info(f"[reportes.resumen] Cartera activa: {cartera_activa:,.2f}")
        except Exception as e:
            logger.error(f"❌ [reportes.resumen] Error obteniendo cartera_activa: {e}", exc_info=True)
            try:
                db.rollback()
            except Exception:
                pass
            cartera_activa = 0.0

        # Mora: préstamos con cuotas vencidas no pagadas
        try:
            prestamos_mora_query = db.execute(
                text(
                    """
                    SELECT COUNT(DISTINCT p.id) as prestamos_mora
                    FROM prestamos p
                    INNER JOIN cuotas c ON c.prestamo_id = p.id
                    WHERE p.estado = 'APROBADO'
                      AND c.fecha_vencimiento < :hoy
                      AND c.estado != 'PAGADO'
                """
                ).bindparams(hoy=hoy)
            )
            prestamos_mora = prestamos_mora_query.scalar() or 0
            logger.info(f"[reportes.resumen] Préstamos en mora: {prestamos_mora}")
        except Exception as e:
            logger.error(f"❌ [reportes.resumen] Error obteniendo prestamos_mora: {e}", exc_info=True)
            try:
                db.rollback()
            except Exception:
                pass
            prestamos_mora = 0

        # Pagos del mes: usar tabla pagos (tipos nativos)
        fecha_inicio_mes = hoy.replace(day=1)
        fecha_inicio_mes_dt = datetime.combine(fecha_inicio_mes, datetime.min.time())
        fecha_fin_mes_dt = datetime.combine(hoy, datetime.max.time())

        try:
            pagos_mes_query = db.execute(
                text(
                    """
                    SELECT COALESCE(SUM(monto_pagado), 0)
                    FROM pagos
                    WHERE fecha_pago >= :fecha_inicio
                      AND fecha_pago <= :fecha_fin
                      AND monto_pagado IS NOT NULL
                      AND monto_pagado > 0
                      AND activo = TRUE
                """
                ).bindparams(fecha_inicio=fecha_inicio_mes_dt, fecha_fin=fecha_fin_mes_dt)
            )
            resultado_pagos = pagos_mes_query.scalar()
            # Manejar diferentes tipos de retorno (Decimal, float, int, None)
            if resultado_pagos is None:
                pagos_mes = 0.0
            elif isinstance(resultado_pagos, Decimal):
                pagos_mes = float(resultado_pagos)
            else:
                pagos_mes = float(resultado_pagos) if resultado_pagos else 0.0
            logger.info(f"[reportes.resumen] Pagos del mes: {pagos_mes:,.2f} (desde {fecha_inicio_mes} hasta {hoy})")
        except Exception as e:
            logger.error(f"❌ [reportes.resumen] Error obteniendo pagos_mes: {e}", exc_info=True)
            try:
                db.rollback()
            except Exception:
                pass
            pagos_mes = 0.0

        # Asegurar que todos los valores sean del tipo correcto
        resultado = {
            "total_clientes": int(total_clientes),
            "total_prestamos": int(total_prestamos),
            "total_pagos": int(total_pagos),
            "cartera_activa": float(cartera_activa),
            "prestamos_mora": int(prestamos_mora),
            "pagos_mes": float(pagos_mes),
            "fecha_actualizacion": datetime.now().isoformat(),
        }

        logger.info(f"[reportes.resumen] Resumen generado: {resultado}")
        return resultado

    except HTTPException:
        raise
    except Exception as e:
        try:
            db.rollback()
        except Exception:
            pass
        raise handle_report_error(e, "obtener resumen del dashboard")


# ============================================
# REPORTE PDF: Pendientes por Cliente
# ============================================
def _obtener_cliente_validado(cedula: str, db: Session) -> Cliente:
    """Obtiene y valida que el cliente exista"""
    cliente = db.query(Cliente).filter(Cliente.cedula == cedula).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    return cliente


def _obtener_prestamos_cliente(cedula: str, db: Session) -> List[Prestamo]:
    """Obtiene todos los préstamos del cliente"""
    prestamos = db.query(Prestamo).filter(Prestamo.cedula == cedula).all()
    if not prestamos:
        raise HTTPException(status_code=404, detail="Cliente no tiene préstamos registrados")
    return prestamos


def _obtener_cuotas_pendientes(prestamo_id: int, hoy: date, db: Session) -> List[dict]:
    """Obtiene cuotas pendientes/vencidas de un préstamo"""
    cuotas = db.query(Cuota).filter(Cuota.prestamo_id == prestamo_id).order_by(Cuota.numero_cuota).all()
    return [
        {
            "numero": c.numero_cuota,
            "fecha_vencimiento": (c.fecha_vencimiento.strftime("%d/%m/%Y") if c.fecha_vencimiento else "N/A"),
            "monto_cuota": float(c.monto_cuota),
            "total_pagado": float(c.total_pagado or Decimal("0.00")),
            "capital_pendiente": float(c.capital_pendiente or Decimal("0.00")),
            "interes_pendiente": float(c.interes_pendiente or Decimal("0.00")),
            "monto_mora": float(c.monto_mora or Decimal("0.00")),
            "estado": c.estado,
            "vencida": (c.fecha_vencimiento < hoy if c.fecha_vencimiento else False),
        }
        for c in cuotas
        if c.estado != "PAGADO"
    ]


def _obtener_modelo_vehiculo(prestamo: Prestamo, db: Session) -> str:
    """Obtiene el modelo de vehículo de un préstamo"""
    if not hasattr(prestamo, "modelo_vehiculo_id") or not prestamo.modelo_vehiculo_id:
        return "N/A"

    from app.models.modelo_vehiculo import ModeloVehiculo

    modelo = db.query(ModeloVehiculo).filter(ModeloVehiculo.id == prestamo.modelo_vehiculo_id).first()
    if modelo:
        return f"{modelo.marca} {modelo.modelo} {modelo.ano or ''}".strip()
    return "N/A"


def _preparar_datos_prestamos(prestamos: List[Prestamo], hoy: date, db: Session) -> List[dict]:
    """Prepara datos de préstamos para el PDF"""
    datos_prestamos = []
    for prestamo in prestamos:
        cuotas_pendientes = _obtener_cuotas_pendientes(prestamo.id, hoy, db)
        modelo_vehiculo = _obtener_modelo_vehiculo(prestamo, db)
        datos_prestamos.append(
            {
                "prestamo_id": prestamo.id,
                "total_financiamiento": float(prestamo.total_financiamiento or Decimal("0.00")),
                "numero_cuotas": prestamo.numero_cuotas or 0,
                "modalidad": prestamo.modalidad_pago or "N/A",
                "estado": prestamo.estado or "N/A",
                "modelo_vehiculo": modelo_vehiculo,
                "cuotas_pendientes": cuotas_pendientes,
            }
        )
    return datos_prestamos


def _crear_tabla_cuotas_pendientes(cuotas_pendientes: List[dict], styles) -> Table:
    """Crea tabla de cuotas pendientes para el PDF"""
    table_data = [
        [
            "Cuota",
            "Fecha Venc.",
            "Monto Cuota",
            "Pagado",
            "Capital Pend.",
            "Interés Pend.",
            "Mora",
            "Estado",
        ]
    ]

    for cuota in cuotas_pendientes:
        fecha_venc = cuota["fecha_vencimiento"]
        if cuota["vencida"]:
            fecha_venc = f"<b><font color='red'>{fecha_venc} (VENCIDA)</font></b>"

        table_data.append(
            [
                str(cuota["numero"]),
                fecha_venc,
                f"${cuota['monto_cuota']:,.2f}",
                f"${cuota['total_pagado']:,.2f}",
                f"${cuota['capital_pendiente']:,.2f}",
                f"${cuota['interes_pendiente']:,.2f}",
                f"${cuota['monto_mora']:,.2f}",
                cuota["estado"],
            ]
        )

    table = Table(
        table_data,
        colWidths=[0.5 * inch, 1 * inch, 1 * inch, 1 * inch, 1 * inch, 1 * inch, 0.8 * inch, 1 * inch],
    )
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#366092")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 8),
                ("FONTSIZE", (0, 1), (-1, -1), 7),
                ("GRID", (0, 0), (-1, -1), 1, colors.black),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
            ]
        )
    )
    return table


def _construir_contenido_pdf(cliente: Cliente, datos_prestamos: List[dict], styles) -> List:
    """Construye el contenido completo del PDF"""
    story = []

    title = Paragraph(f"<b>REPORTE DE PENDIENTES - {cliente.nombres or 'Cliente'}</b>", styles["Title"])
    story.append(title)

    info_cliente = Paragraph(
        f"<b>Cédula:</b> {cliente.cedula}<br/>"
        f"<b>Nombre:</b> {cliente.nombres or 'N/A'}<br/>"
        f"<b>Fecha de Generación:</b> {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        styles["Normal"],
    )
    story.append(info_cliente)
    story.append(Spacer(1, 0.3 * inch))

    for datos_prestamo in datos_prestamos:
        header_prestamo = Paragraph(
            f"<b>PRÉSTAMO ID #{datos_prestamo['prestamo_id']}</b> - "
            f"Total: ${datos_prestamo['total_financiamiento']:,.2f} - "
            f"Modelo: {datos_prestamo['modelo_vehiculo']}",
            styles["Heading2"],
        )
        story.append(header_prestamo)

        info_prestamo = Paragraph(
            f"Modalidad: {datos_prestamo['modalidad']} | "
            f"Cuotas Totales: {datos_prestamo['numero_cuotas']} | "
            f"Estado: {datos_prestamo['estado']}",
            styles["Normal"],
        )
        story.append(info_prestamo)
        story.append(Spacer(1, 0.2 * inch))

        if datos_prestamo["cuotas_pendientes"]:
            table = _crear_tabla_cuotas_pendientes(datos_prestamo["cuotas_pendientes"], styles)
            story.append(table)
        else:
            story.append(Paragraph("<i>No hay cuotas pendientes para este préstamo</i>", styles["Normal"]))

        story.append(Spacer(1, 0.3 * inch))

    return story


@router.get("/cliente/{cedula}/pendientes.pdf")
def generar_pdf_pendientes_cliente(
    cedula: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Genera PDF con préstamos pendientes, cuotas, modelos y fechas vencidas para un cliente.
    Contiene: Préstamos, Cuotas, Modelo, Fechas Vencidas (Amortización completa)
    """
    try:
        hoy = date.today()

        cliente = _obtener_cliente_validado(cedula, db)
        prestamos = _obtener_prestamos_cliente(cedula, db)
        datos_prestamos = _preparar_datos_prestamos(prestamos, hoy, db)

        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=0.5 * inch)
        styles = getSampleStyleSheet()

        story = _construir_contenido_pdf(cliente, datos_prestamos, styles)

        doc.build(story)
        buffer.seek(0)

        filename = f"pendientes_{cedula}_{hoy.strftime('%Y%m%d')}.pdf"
        return StreamingResponse(
            buffer,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generando PDF pendientes para cliente {cedula}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error al generar PDF: {str(e)}")
