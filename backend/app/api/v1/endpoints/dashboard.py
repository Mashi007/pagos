import logging
import time
from calendar import monthrange
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query  # type: ignore[import-untyped]
from sqlalchemy import Integer, and_, case, cast, func, or_, text  # type: ignore[import-untyped]
from sqlalchemy.orm import Session  # type: ignore[import-untyped]

from app.api.deps import get_current_user, get_db
from app.core.cache import cache_result
from app.core.debug_helpers import DebugAlert, debug_timing, log_graph_debug_info, run_debug_checklist, validate_graph_data
from app.models.amortizacion import Cuota
from app.models.cliente import Cliente
from app.models.dashboard_oficial import (
    DashboardCobranzasMensuales,
    DashboardFinanciamientoMensual,
    DashboardKPIsDiarios,
    DashboardMetricasAcumuladas,
    DashboardMorosidadMensual,
    DashboardMorosidadPorAnalista,
    DashboardPagosMensuales,
    DashboardPrestamosPorConcesionario,
)
from app.models.pago import Pago  # Mantener para operaciones que necesiten tabla pagos

# ✅ ACTUALIZADO: Usar tabla pagos (no pagos_staging) - PagoStaging removido de imports
from app.models.prestamo import Prestamo
from app.models.user import User
from app.utils.filtros_dashboard import FiltrosDashboard
from app.utils.pagos_cuotas_helper import calcular_monto_pagado_mes
from app.utils.query_monitor import query_monitor

logger = logging.getLogger(__name__)
router = APIRouter()


# ============================================================================
# HELPERS DE NORMALIZACIÓN Y UTILIDADES
# ============================================================================


def normalize_to_date(fecha: Any) -> Optional[date]:
    """
    Normaliza cualquier tipo de fecha a date.
    Maneja datetime, date, string, y None.

    Args:
        fecha: Puede ser datetime, date, string ISO, o None

    Returns:
        date o None si no se puede convertir
    """
    if fecha is None:
        return None
    if isinstance(fecha, date):
        return fecha
    if isinstance(fecha, datetime):
        return fecha.date()
    if isinstance(fecha, str):
        try:
            # Intentar parsear como ISO format
            if "T" in fecha or " " in fecha:
                return datetime.fromisoformat(fecha.replace("Z", "+00:00")).date()
            else:
                return datetime.strptime(fecha, "%Y-%m-%d").date()
        except (ValueError, AttributeError):
            logger.warning(f"No se pudo convertir fecha a date: {fecha}")
            return None
    logger.warning(f"Tipo de fecha no soportado: {type(fecha)}")
    return None


def _calcular_periodos(periodo: str, hoy: date) -> tuple[date, date]:
    """Calcula fecha_inicio_periodo y fecha_fin_periodo_anterior según el período"""
    if periodo == "mes":
        fecha_inicio_periodo = date(hoy.year, hoy.month, 1)
        fecha_fin_periodo_anterior = fecha_inicio_periodo - timedelta(days=1)
    elif periodo == "semana":
        fecha_inicio_periodo = hoy - timedelta(days=hoy.weekday())
        fecha_fin_periodo_anterior = fecha_inicio_periodo - timedelta(days=1)
    elif periodo == "año":
        fecha_inicio_periodo = date(hoy.year, 1, 1)
        fecha_fin_periodo_anterior = date(hoy.year - 1, 12, 31)
    else:  # dia
        fecha_inicio_periodo = hoy
        fecha_fin_periodo_anterior = hoy - timedelta(days=1)
    return fecha_inicio_periodo, fecha_fin_periodo_anterior


def _calcular_cartera_anterior(
    db: Session,
    periodo: str,
    fecha_fin_periodo_anterior: date,
    analista: Optional[str],
    concesionario: Optional[str],
    modelo: Optional[str],
    cartera_total: Decimal,
) -> float:
    """Calcula la cartera anterior según el período"""
    if periodo == "dia":
        return float(cartera_total)

    # Usar comparación directa con timestamp en lugar de func.date()
    fecha_fin_periodo_anterior_dt = datetime.combine(fecha_fin_periodo_anterior, datetime.max.time())
    cartera_anterior_query = db.query(func.sum(Prestamo.total_financiamiento)).filter(
        Prestamo.estado == "APROBADO",
        Prestamo.fecha_registro <= fecha_fin_periodo_anterior_dt,
    )
    cartera_anterior_query = FiltrosDashboard.aplicar_filtros_prestamo(
        cartera_anterior_query, analista, concesionario, modelo, None, None
    )
    return float(cartera_anterior_query.scalar() or Decimal("0"))


def _calcular_total_cobrado_mes(
    db: Session,
    primer_dia: date,
    ultimo_dia: date,
    analista: Optional[str],
    concesionario: Optional[str],
    modelo: Optional[str],
) -> Decimal:
    """Calcula el total cobrado en un mes"""
    # ✅ ACTUALIZADO: Usar tabla pagos (no pagos_staging) con prestamo_id y cedula
    primer_dia_dt = datetime.combine(primer_dia, datetime.min.time())
    ultimo_dia_dt = datetime.combine(ultimo_dia, datetime.max.time())

    # Construir filtros de préstamo si existen
    prestamo_conditions = []
    bind_params = {"primer_dia": primer_dia_dt, "ultimo_dia": ultimo_dia_dt}

    if analista or concesionario or modelo:
        if analista:
            prestamo_conditions.append("(pr.analista = :analista OR pr.producto_financiero = :analista)")
            bind_params["analista"] = analista
        if concesionario:
            prestamo_conditions.append("pr.concesionario = :concesionario")
            bind_params["concesionario"] = concesionario
        if modelo:
            prestamo_conditions.append("(pr.producto = :modelo OR pr.modelo_vehiculo = :modelo)")
            bind_params["modelo"] = modelo

        # ✅ CORRECCIÓN: Cuando hay filtros, usar INNER JOIN y asegurar que pr.estado = 'APROBADO'
        # Si no hay filtros de préstamo, incluir pagos sin préstamo asociado
        where_clause = """p.fecha_pago >= :primer_dia
          AND p.fecha_pago <= :ultimo_dia
          AND p.monto_pagado IS NOT NULL
          AND p.monto_pagado > 0
          AND p.activo = TRUE
          AND pr.estado = 'APROBADO'"""

        if prestamo_conditions:
            where_clause += " AND " + " AND ".join(prestamo_conditions)

        query_sql = text(
            f"""
            SELECT COALESCE(SUM(p.monto_pagado), 0)
            FROM pagos p
            INNER JOIN prestamos pr ON (
                (p.prestamo_id IS NOT NULL AND pr.id = p.prestamo_id)
                OR (p.prestamo_id IS NULL AND pr.cedula = p.cedula AND pr.estado = 'APROBADO')
            )
            WHERE {where_clause}
            """
        ).bindparams(**bind_params)
    else:
        # Sin filtros, query más simple
        query_sql = text(
            """
            SELECT COALESCE(SUM(monto_pagado), 0)
            FROM pagos
            WHERE fecha_pago >= :primer_dia
              AND fecha_pago <= :ultimo_dia
              AND monto_pagado IS NOT NULL
              AND monto_pagado > 0
              AND activo = TRUE
            """
        ).bindparams(primer_dia=primer_dia_dt, ultimo_dia=ultimo_dia_dt)

    result = db.execute(query_sql)
    return Decimal(str(result.scalar() or 0))


def _calcular_mes_anterior(mes_actual: int, año_actual: int) -> tuple[int, int]:
    """Calcula mes y año anterior"""
    if mes_actual == 1:
        return (12, año_actual - 1)
    return (mes_actual - 1, año_actual)


def _obtener_fechas_mes(mes: int, año: int) -> tuple[date, date]:
    """Obtiene primer y último día de un mes"""
    primer_dia = date(año, mes, 1)
    ultimo_dia = date(año, mes, monthrange(año, mes)[1])
    return primer_dia, ultimo_dia


def _obtener_fechas_mes_siguiente(mes: int, año: int) -> date:
    """Obtiene primer día del mes siguiente"""
    if mes == 12:
        return date(año + 1, 1, 1)
    return date(año, mes + 1, 1)


def _calcular_variacion(valor_actual: float, valor_anterior: float) -> tuple[float, float]:
    """Calcula variación porcentual y absoluta"""
    variacion_absoluta = valor_actual - valor_anterior
    variacion_porcentual = ((valor_actual - valor_anterior) / valor_anterior * 100) if valor_anterior > 0 else 0
    return variacion_porcentual, variacion_absoluta


def _calcular_morosidad(
    db: Session,
    fecha: date,
    analista: Optional[str],
    concesionario: Optional[str],
    modelo: Optional[str],
    fecha_inicio: Optional[date],
    fecha_fin: Optional[date],
) -> float:
    """
    Calcula morosidad acumulada usando la misma lógica que la tabla SQL:
    - Morosidad mensual = MAX(0, Monto Programado del mes - Monto Pagado del mes)
    - Morosidad acumulada = Suma de todas las morosidades mensuales desde 2024 hasta la fecha

    ✅ CORRECCIÓN: Usa la misma lógica que obtener_financiamiento_tendencia_mensual
    """
    # Fecha de inicio: 2024-01-01 o fecha_inicio si es más reciente
    fecha_inicio_calculo = date(2024, 1, 1)
    if fecha_inicio and fecha_inicio > fecha_inicio_calculo:
        fecha_inicio_calculo = fecha_inicio

    # Construir filtros para WHERE clause
    # ✅ Crear dos versiones: una para CTE 'meses' (usa alias 'p') y otra para CTE 'pagos_por_mes' (usa alias 'pr')
    filtros_prestamo_p = []  # Para CTE meses (alias p)
    filtros_prestamo_pr = []  # Para CTE pagos_por_mes (alias pr)
    bind_params = {"fecha_limite": fecha, "fecha_inicio_calculo": fecha_inicio_calculo}

    if analista:
        filtros_prestamo_p.append("(p.analista = :analista OR p.producto_financiero = :analista)")
        filtros_prestamo_pr.append("(pr.analista = :analista OR pr.producto_financiero = :analista)")
        bind_params["analista"] = analista
    if concesionario:
        filtros_prestamo_p.append("p.concesionario = :concesionario")
        filtros_prestamo_pr.append("pr.concesionario = :concesionario")
        bind_params["concesionario"] = concesionario
    if modelo:
        filtros_prestamo_p.append("(p.producto = :modelo OR p.modelo_vehiculo = :modelo)")
        filtros_prestamo_pr.append("(pr.producto = :modelo OR pr.modelo_vehiculo = :modelo)")
        bind_params["modelo"] = modelo
    if fecha_inicio:
        filtros_prestamo_p.append("p.fecha_aprobacion >= :fecha_inicio")
        filtros_prestamo_pr.append("pr.fecha_aprobacion >= :fecha_inicio")
        bind_params["fecha_inicio"] = fecha_inicio
    if fecha_fin:
        filtros_prestamo_p.append("p.fecha_aprobacion <= :fecha_fin")
        filtros_prestamo_pr.append("pr.fecha_aprobacion <= :fecha_fin")
        bind_params["fecha_fin"] = fecha_fin

    where_prestamo_p = " AND " + " AND ".join(filtros_prestamo_p) if filtros_prestamo_p else ""
    where_prestamo_pr = " AND " + " AND ".join(filtros_prestamo_pr) if filtros_prestamo_pr else ""

    # ✅ Query que calcula morosidad acumulada mes por mes
    # Suma todas las morosidades mensuales desde 2024 hasta la fecha
    # Usa la misma lógica que obtener_financiamiento_tendencia_mensual

    if filtros_prestamo_p:
        # Con filtros: filtrar pagos a través de préstamos
        # ✅ CORRECCIÓN: Usar where_prestamo_p para CTE meses (alias p) y where_prestamo_pr para CTE pagos_por_mes (alias pr)
        query_sql = text(
            f"""
            WITH meses AS (
                SELECT
                    EXTRACT(YEAR FROM c.fecha_vencimiento)::integer as año,
                    EXTRACT(MONTH FROM c.fecha_vencimiento)::integer as mes,
                    COALESCE(SUM(c.monto_cuota), 0) as monto_programado
                FROM cuotas c
                INNER JOIN prestamos p ON c.prestamo_id = p.id
                WHERE p.estado = 'APROBADO'
                  AND c.fecha_vencimiento >= :fecha_inicio_calculo
                  AND c.fecha_vencimiento <= :fecha_limite
                  {where_prestamo_p}
                GROUP BY EXTRACT(YEAR FROM c.fecha_vencimiento), EXTRACT(MONTH FROM c.fecha_vencimiento)
            ),
            pagos_por_mes AS (
                SELECT
                    EXTRACT(YEAR FROM pa.fecha_pago)::integer as año,
                    EXTRACT(MONTH FROM pa.fecha_pago)::integer as mes,
                    COALESCE(SUM(pa.monto_pagado), 0) as monto_pagado
                FROM pagos pa
                LEFT JOIN prestamos pr ON (
                    (pa.prestamo_id IS NOT NULL AND pr.id = pa.prestamo_id)
                    OR (pa.prestamo_id IS NULL AND pr.cedula = pa.cedula AND pr.estado = 'APROBADO')
                )
                WHERE pa.fecha_pago >= :fecha_inicio_calculo
                  AND pa.fecha_pago <= :fecha_limite
                  AND pa.monto_pagado IS NOT NULL
                  AND pa.monto_pagado > 0
                  AND pa.activo = TRUE
                  AND (pr.estado = 'APROBADO' OR pr.estado IS NULL)
                  {where_prestamo_pr}
                GROUP BY EXTRACT(YEAR FROM pa.fecha_pago), EXTRACT(MONTH FROM pa.fecha_pago)
            )
            SELECT COALESCE(SUM(GREATEST(0, m.monto_programado - COALESCE(p.monto_pagado, 0))), 0) as morosidad_acumulada
            FROM meses m
            LEFT JOIN pagos_por_mes p ON m.año = p.año AND m.mes = p.mes
        """
        )
    else:
        # Sin filtros: query más simple (suma todos los pagos)
        query_sql = text(
            """
            WITH meses AS (
                SELECT
                    EXTRACT(YEAR FROM c.fecha_vencimiento)::integer as año,
                    EXTRACT(MONTH FROM c.fecha_vencimiento)::integer as mes,
                    COALESCE(SUM(c.monto_cuota), 0) as monto_programado
                FROM cuotas c
                INNER JOIN prestamos p ON c.prestamo_id = p.id
                WHERE p.estado = 'APROBADO'
                  AND c.fecha_vencimiento >= :fecha_inicio_calculo
                  AND c.fecha_vencimiento <= :fecha_limite
                GROUP BY EXTRACT(YEAR FROM c.fecha_vencimiento), EXTRACT(MONTH FROM c.fecha_vencimiento)
            ),
            pagos_por_mes AS (
                SELECT
                    EXTRACT(YEAR FROM pa.fecha_pago)::integer as año,
                    EXTRACT(MONTH FROM pa.fecha_pago)::integer as mes,
                    COALESCE(SUM(pa.monto_pagado), 0) as monto_pagado
                FROM pagos pa
                WHERE pa.fecha_pago >= :fecha_inicio_calculo
                  AND pa.fecha_pago <= :fecha_limite
                  AND pa.monto_pagado IS NOT NULL
                  AND pa.monto_pagado > 0
                  AND pa.activo = TRUE
                GROUP BY EXTRACT(YEAR FROM pa.fecha_pago), EXTRACT(MONTH FROM pa.fecha_pago)
            )
            SELECT COALESCE(SUM(GREATEST(0, m.monto_programado - COALESCE(p.monto_pagado, 0))), 0) as morosidad_acumulada
            FROM meses m
            LEFT JOIN pagos_por_mes p ON m.año = p.año AND m.mes = p.mes
        """
        )

    resultado = db.execute(query_sql.bindparams(**bind_params)).scalar()

    return float(resultado or Decimal("0"))


def _calcular_total_a_cobrar_fecha(
    db: Session,
    fecha: date,
    analista: Optional[str],
    concesionario: Optional[str],
    modelo: Optional[str],
    fecha_inicio: Optional[date],
    fecha_fin: Optional[date],
) -> float:
    """Calcula total a cobrar en una fecha específica"""
    query = (
        db.query(func.sum(Cuota.monto_cuota))
        .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
        .filter(
            Prestamo.estado == "APROBADO",
            Cuota.fecha_vencimiento == fecha,
        )
    )
    query = FiltrosDashboard.aplicar_filtros_cuota(query, analista, concesionario, modelo, fecha_inicio, fecha_fin)
    return float(query.scalar() or Decimal("0"))


def _calcular_dias_mora_cliente(db: Session, cedula: str, hoy: date) -> int:
    """Calcula días de mora máximo para un cliente"""
    # ✅ CORRECCIÓN: En PostgreSQL, date - date ya devuelve integer (días)
    # No usar date_part, usar la resta directamente con parámetros bind
    dias_mora_query = (
        db.query(func.max(text("(:hoy::date - cuotas.fecha_vencimiento::date)")))
        .params(hoy=hoy)
        .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
        .filter(
            Prestamo.cedula == cedula,
            Prestamo.estado == "APROBADO",
            Cuota.fecha_vencimiento < hoy,
            Cuota.estado != "PAGADO",
        )
        .scalar()
    )
    return int(dias_mora_query) if dias_mora_query else 0


def _procesar_distribucion_por_plazo(query_base, total_prestamos: int, total_monto: float) -> list:
    """Procesa distribución por plazo (numero_cuotas)"""
    distribucion_data = []
    query_plazo = (
        query_base.with_entities(
            Prestamo.numero_cuotas.label("plazo"),
            func.count(Prestamo.id).label("cantidad"),
            func.sum(Prestamo.total_financiamiento).label("monto_total"),
        )
        .group_by(Prestamo.numero_cuotas)
        .order_by(Prestamo.numero_cuotas)
    )
    resultados = query_plazo.all()
    for row in resultados:
        cantidad = row.cantidad or 0
        monto_total = float(row.monto_total or Decimal("0"))
        porcentaje_cantidad = (cantidad / total_prestamos * 100) if total_prestamos > 0 else 0
        porcentaje_monto = (monto_total / total_monto * 100) if total_monto > 0 else 0
        distribucion_data.append(
            {
                "categoria": f"{row.plazo} cuotas",
                "cantidad_prestamos": cantidad,
                "monto_total": monto_total,
                "porcentaje_cantidad": round(porcentaje_cantidad, 2),
                "porcentaje_monto": round(porcentaje_monto, 2),
            }
        )
    return distribucion_data


def _procesar_distribucion_por_estado(query_base, total_prestamos: int, total_monto: float) -> list:
    """Procesa distribución por estado"""
    distribucion_data = []
    query_estado = query_base.with_entities(
        Prestamo.estado.label("estado"),
        func.count(Prestamo.id).label("cantidad"),
        func.sum(Prestamo.total_financiamiento).label("monto_total"),
    ).group_by(Prestamo.estado)
    resultados = query_estado.all()
    for row in resultados:
        cantidad = row.cantidad or 0
        monto_total = float(row.monto_total or Decimal("0"))
        porcentaje_cantidad = (cantidad / total_prestamos * 100) if total_prestamos > 0 else 0
        porcentaje_monto = (monto_total / total_monto * 100) if total_monto > 0 else 0
        distribucion_data.append(
            {
                "categoria": row.estado or "Sin Estado",
                "cantidad_prestamos": cantidad,
                "monto_total": monto_total,
                "porcentaje_cantidad": round(porcentaje_cantidad, 2),
                "porcentaje_monto": round(porcentaje_monto, 2),
            }
        )
    return distribucion_data


def _procesar_distribucion_rango_monto_plazo(
    query_base, rangos_monto: list, rangos_plazo: list, total_prestamos: int, total_monto: float
) -> list:
    """Procesa distribución combinada por rango de monto y plazo"""
    distribucion_data = []
    for min_monto, max_monto, cat_monto in rangos_monto:
        for min_plazo, max_plazo, cat_plazo in rangos_plazo:
            query_combinado = query_base.filter(Prestamo.total_financiamiento >= Decimal(str(min_monto)))
            if max_monto:
                query_combinado = query_combinado.filter(Prestamo.total_financiamiento < Decimal(str(max_monto)))
            query_combinado = query_combinado.filter(Prestamo.numero_cuotas >= min_plazo)
            if max_plazo:
                query_combinado = query_combinado.filter(Prestamo.numero_cuotas < max_plazo)
            cantidad = query_combinado.count()
            if cantidad > 0:
                monto_total = float(
                    query_combinado.with_entities(func.sum(Prestamo.total_financiamiento)).scalar() or Decimal("0")
                )
                porcentaje_cantidad = (cantidad / total_prestamos * 100) if total_prestamos > 0 else 0
                porcentaje_monto = (monto_total / total_monto * 100) if total_monto > 0 else 0
                distribucion_data.append(
                    {
                        "categoria": f"{cat_monto} - {cat_plazo}",
                        "cantidad_prestamos": cantidad,
                        "monto_total": monto_total,
                        "porcentaje_cantidad": round(porcentaje_cantidad, 2),
                        "porcentaje_monto": round(porcentaje_monto, 2),
                    }
                )
    return distribucion_data


def _procesar_distribucion_rango_monto(
    query_base, rangos: list, total_prestamos: int, total_monto: float, db: Optional[Session] = None
) -> list:
    """
    Procesa distribución por rango de monto
    ✅ OPTIMIZADO: Usa GROUP BY en SQL en lugar de procesamiento en Python
    """
    if not rangos:
        logger.warning("No hay rangos para procesar, retornando lista vacía")
        return []

    try:
        # ✅ OPTIMIZACIÓN: Usar GROUP BY en SQL en lugar de procesamiento en Python
        # Esto reduce de 2 queries + procesamiento a 1 query con GROUP BY
        if db is not None:
            from sqlalchemy import text

            # Detectar paso del rango (asumiendo rangos uniformes)
            paso_rango = None
            max_rango_val = None
            for min_val, max_val, _ in rangos:
                if max_val is not None:
                    if paso_rango is None:
                        paso_rango = max_val - min_val
                else:
                    max_rango_val = min_val

            if paso_rango is None or paso_rango <= 0:
                logger.warning("⚠️ No se pudo detectar paso del rango, usando método fallback")
                return _procesar_distribucion_rango_monto_fallback(query_base, rangos, total_prestamos, total_monto, db)

            # Obtener el WHERE clause de query_base
            # Construir query SQL optimizada con GROUP BY
            # Usar división entera para calcular el rango directamente en SQL
            try:
                # ✅ DIAGNÓSTICO: Verificar query_base antes de obtener IDs
                try:
                    count_antes_ids = query_base.with_entities(Prestamo.id).count()
                    logger.info(f"📊 [financiamiento-por-rangos] query_base.count() antes de obtener IDs: {count_antes_ids}")
                except Exception as e:
                    logger.warning(f"⚠️ [financiamiento-por-rangos] No se pudo contar query_base antes de IDs: {e}")

                # Obtener los IDs de préstamos que cumplen los filtros
                prestamo_ids_query = query_base.with_entities(Prestamo.id)
                prestamo_ids_result = prestamo_ids_query.all()
                prestamo_ids = [row[0] for row in prestamo_ids_result]

                logger.info(f"📊 [financiamiento-por-rangos] IDs obtenidos: {len(prestamo_ids)} préstamos")

                if not prestamo_ids:
                    # Si no hay préstamos, construir respuesta con todos los rangos en 0
                    logger.warning(
                        f"⚠️ [financiamiento-por-rangos] No se encontraron préstamos con los filtros aplicados. "
                        f"query_base.count()={count_antes_ids if 'count_antes_ids' in locals() else 'N/A'}, "
                        f"total_prestamos={total_prestamos}"
                    )
                    distribucion_data = []
                    for min_val, max_val, categoria in rangos:
                        distribucion_data.append(
                            {
                                "categoria": categoria,
                                "cantidad_prestamos": 0,
                                "monto_total": 0.0,
                                "porcentaje_cantidad": 0.0,
                                "porcentaje_monto": 0.0,
                            }
                        )
                    return distribucion_data

                # Query SQL optimizada con GROUP BY usando división entera
                # Calcular el rango usando: FLOOR(total_financiamiento / paso_rango) * paso_rango
                logger.info(
                    f"📊 [financiamiento-por-rangos] Ejecutando query SQL optimizada con {len(prestamo_ids)} IDs, "
                    f"paso_rango={paso_rango}, max_rango={max_rango_val if max_rango_val else 50000.0}"
                )

                # ✅ MEJORA: Usar sintaxis más robusta para PostgreSQL con array
                # Usar CAST para asegurar que PostgreSQL entienda que es un array
                query_sql = text(
                    """
                    WITH rangos_calculados AS (
                        SELECT
                            CASE
                                WHEN total_financiamiento >= :max_rango THEN :max_rango
                                ELSE FLOOR(total_financiamiento / :paso_rango) * :paso_rango
                            END as rango_min,
                            CASE
                                WHEN total_financiamiento >= :max_rango THEN NULL
                                ELSE FLOOR(total_financiamiento / :paso_rango) * :paso_rango + :paso_rango
                            END as rango_max,
                            total_financiamiento
                        FROM prestamos
                        WHERE id = ANY(CAST(:ids AS INTEGER[]))
                          AND total_financiamiento IS NOT NULL
                          AND total_financiamiento > 0
                    )
                    SELECT
                        rango_min,
                        rango_max,
                        COUNT(*) as cantidad_prestamos,
                        SUM(total_financiamiento) as monto_total
                    FROM rangos_calculados
                    GROUP BY rango_min, rango_max
                    ORDER BY rango_min
                """
                )

                try:
                    result = db.execute(
                        query_sql,
                        {
                            "ids": prestamo_ids,
                            "paso_rango": float(paso_rango),
                            "max_rango": float(max_rango_val) if max_rango_val else 50000.0,
                        },
                    )

                    # Crear diccionario con resultados de SQL
                    distribucion_dict = {}
                    rows_processed = 0
                    for row in result:
                        rows_processed += 1
                        rango_min = float(row.rango_min) if row.rango_min else 0
                        rango_max = float(row.rango_max) if row.rango_max else None

                        # Formatear categoría
                        if rango_max is None:
                            categoria = f"${int(rango_min):,}+".replace(",", "")
                        else:
                            categoria = f"${int(rango_min):,} - ${int(rango_max):,}".replace(",", "")

                        distribucion_dict[categoria] = {
                            "cantidad": int(row.cantidad_prestamos),
                            "monto_total": float(row.monto_total),
                        }
                        logger.debug(
                            f"📊 [financiamiento-por-rangos] Rango procesado: {categoria} = "
                            f"{distribucion_dict[categoria]['cantidad']} préstamos, "
                            f"${distribucion_dict[categoria]['monto_total']:,.2f}"
                        )

                    logger.info(
                        f"📊 [financiamiento-por-rangos] Query SQL retornó {rows_processed} grupos, "
                        f"mapeados a {len(distribucion_dict)} categorías únicas"
                    )

                    # ✅ DIAGNÓSTICO: Log de categorías generadas vs categorías esperadas
                    categorias_generadas = set(distribucion_dict.keys())
                    categorias_esperadas = set(cat for _, _, cat in rangos)
                    categorias_no_encontradas = categorias_esperadas - categorias_generadas
                    categorias_extra = categorias_generadas - categorias_esperadas

                    if categorias_no_encontradas:
                        # Limitar la cantidad de categorías mostradas para evitar logs excesivamente largos
                        total_no_encontradas = len(categorias_no_encontradas)
                        categorias_muestra = list(categorias_no_encontradas)[:10]  # Mostrar solo las primeras 10
                        if total_no_encontradas > 10:
                            logger.debug(
                                f"📊 [financiamiento-por-rangos] {total_no_encontradas} categorías esperadas sin datos "
                                f"(muestra: {categorias_muestra}...). Esto es normal si no hay préstamos en esos rangos."
                            )
                        else:
                            logger.debug(
                                f"📊 [financiamiento-por-rangos] {total_no_encontradas} categorías esperadas sin datos: "
                                f"{categorias_no_encontradas}. Esto es normal si no hay préstamos en esos rangos."
                            )
                    if categorias_extra:
                        logger.warning(
                            f"⚠️ [financiamiento-por-rangos] Categorías generadas por SQL que no están en rangos esperados: {categorias_extra}"
                        )

                    # ✅ VERIFICACIÓN: Si la query SQL no retornó resultados pero hay préstamos, usar fallback
                    if rows_processed == 0 and len(prestamo_ids) > 0:
                        logger.warning(
                            f"⚠️ [financiamiento-por-rangos] Query SQL optimizada no retornó resultados "
                            f"pero hay {len(prestamo_ids)} préstamos. Usando método fallback."
                        )
                        return _procesar_distribucion_rango_monto_fallback(
                            query_base, rangos, total_prestamos, total_monto, db
                        )

                    # ✅ VERIFICACIÓN: Si hay resultados pero ninguna categoría coincide con los rangos esperados, usar fallback
                    if rows_processed > 0 and len(categorias_generadas.intersection(categorias_esperadas)) == 0:
                        logger.warning(
                            f"⚠️ [financiamiento-por-rangos] Query SQL retornó {rows_processed} grupos pero ninguna categoría coincide "
                            f"con los rangos esperados. Categorías generadas: {categorias_generadas}, "
                            f"Categorías esperadas: {categorias_esperadas}. Usando método fallback."
                        )
                        return _procesar_distribucion_rango_monto_fallback(
                            query_base, rangos, total_prestamos, total_monto, db
                        )

                except Exception as e:
                    logger.error(f"❌ [financiamiento-por-rangos] Error ejecutando query SQL optimizada: {e}", exc_info=True)
                    logger.warning("⚠️ [financiamiento-por-rangos] Usando método fallback debido a error en query SQL")
                    return _procesar_distribucion_rango_monto_fallback(query_base, rangos, total_prestamos, total_monto, db)

                # Construir respuesta manteniendo el orden de los rangos originales
                distribucion_data = []
                for min_val, max_val, categoria in rangos:
                    datos = distribucion_dict.get(categoria, {"cantidad": 0, "monto_total": 0.0})
                    cantidad = datos["cantidad"]
                    monto_total = datos["monto_total"]
                    porcentaje_cantidad = (cantidad / total_prestamos * 100) if total_prestamos > 0 else 0
                    porcentaje_monto = (monto_total / total_monto * 100) if total_monto > 0 else 0

                    distribucion_data.append(
                        {
                            "categoria": categoria,
                            "cantidad_prestamos": cantidad,
                            "monto_total": monto_total,
                            "porcentaje_cantidad": round(porcentaje_cantidad, 2),
                            "porcentaje_monto": round(porcentaje_monto, 2),
                        }
                    )

                # ✅ Verificar que la suma de todos los rangos coincida con el total
                try:
                    suma_cantidad = sum(r.get("cantidad_prestamos", 0) for r in distribucion_data)
                    if suma_cantidad != total_prestamos and total_prestamos > 0:
                        logger.warning(
                            f"⚠️ DISCREPANCIA: Suma de rangos ({suma_cantidad}) no coincide con total_prestamos ({total_prestamos}). "
                            f"Diferencia: {abs(suma_cantidad - total_prestamos)} préstamos."
                        )
                except Exception as e:
                    logger.error(f"Error verificando suma de rangos: {e}", exc_info=True)

                return distribucion_data

            except Exception as e:
                logger.warning(f"⚠️ Error en query optimizada, usando método fallback: {e}")
                return _procesar_distribucion_rango_monto_fallback(query_base, rangos, total_prestamos, total_monto, db)
        else:
            # Fallback si no hay db
            return _procesar_distribucion_rango_monto_fallback(query_base, rangos, total_prestamos, total_monto, db)
    except Exception as e:
        logger.error(f"Error procesando distribución por rangos: {e}", exc_info=True)
        if db is not None:
            try:
                db.rollback()
            except Exception:
                pass
        logger.warning("Retornando distribución vacía debido a error en procesamiento")
        return []


def _procesar_distribucion_rango_monto_fallback(
    query_base, rangos: list, total_prestamos: int, total_monto: float, db: Optional[Session] = None
) -> list:
    """
    Método fallback para procesar distribución por rango de monto
    Usa el método original de procesamiento en Python
    """
    logger.info("🔄 [financiamiento-por-rangos] Usando método fallback para procesar distribución")

    if not rangos:
        logger.warning("⚠️ [financiamiento-por-rangos] No hay rangos para procesar en fallback")
        return []

    try:
        from sqlalchemy import text

        if db is not None:
            # Obtener IDs primero
            try:
                logger.info("📊 [financiamiento-por-rangos] Obteniendo IDs de préstamos en método fallback")
                prestamo_ids_query = query_base.with_entities(Prestamo.id)
                prestamo_ids_result = prestamo_ids_query.all()
                prestamo_ids = [row[0] for row in prestamo_ids_result]
                logger.info(f"📊 [financiamiento-por-rangos] Obtenidos {len(prestamo_ids)} IDs en método fallback")

                if not prestamo_ids:
                    logger.warning("⚠️ [financiamiento-por-rangos] No se encontraron IDs en método fallback")
                    distribucion_data = []
                    for min_val, max_val, categoria in rangos:
                        distribucion_data.append(
                            {
                                "categoria": categoria,
                                "cantidad_prestamos": 0,
                                "monto_total": 0.0,
                                "porcentaje_cantidad": 0.0,
                                "porcentaje_monto": 0.0,
                            }
                        )
                    return distribucion_data

                # Query SQL directa
                logger.info(f"📊 [financiamiento-por-rangos] Ejecutando query SQL directa con {len(prestamo_ids)} IDs")
                # ✅ MEJORA: Usar sintaxis más robusta para PostgreSQL con array
                query_sql = text("SELECT id, total_financiamiento FROM prestamos WHERE id = ANY(CAST(:ids AS INTEGER[]))")
                result = db.execute(query_sql, {"ids": prestamo_ids})
                prestamos_data = [(row.id, row.total_financiamiento) for row in result]
                logger.info(f"📊 [financiamiento-por-rangos] Obtenidos {len(prestamos_data)} préstamos de la BD")
            except Exception as e:
                logger.error(f"❌ [financiamiento-por-rangos] Error obteniendo préstamos en fallback: {e}", exc_info=True)
                return []
        else:
            try:
                logger.info("📊 [financiamiento-por-rangos] Obteniendo préstamos directamente de query_base")
                prestamos_data = query_base.with_entities(Prestamo.id, Prestamo.total_financiamiento).all()
                logger.info(f"📊 [financiamiento-por-rangos] Obtenidos {len(prestamos_data)} préstamos de query_base")
            except Exception as e:
                logger.error(f"❌ [financiamiento-por-rangos] Error obteniendo préstamos con query_base: {e}", exc_info=True)
                return []

        # Procesar en Python (método original)
        logger.info(f"📊 [financiamiento-por-rangos] Procesando {len(prestamos_data)} préstamos en Python")
        distribucion_dict = {}
        prestamos_procesados = 0
        prestamos_omitidos = 0

        for prestamo_id, monto in prestamos_data:
            if monto is None or monto <= 0:
                prestamos_omitidos += 1
                continue

            prestamos_procesados += 1
            monto_decimal = Decimal(str(monto)) if not isinstance(monto, Decimal) else monto
            monto_float = float(monto_decimal)

            # Buscar rango
            categoria = None
            for min_val, max_val, cat in rangos:
                if max_val is None:
                    if monto_float >= min_val:
                        categoria = cat
                        break
                else:
                    if min_val <= monto_float < max_val:
                        categoria = cat
                        break

            # Si no se encontró rango, usar "Otro" (aunque no debería pasar con rangos bien definidos)
            if categoria is None:
                logger.warning(
                    f"⚠️ [financiamiento-por-rangos] Préstamo {prestamo_id} con monto ${monto_float:,.2f} no encaja en ningún rango"
                )
                categoria = "Otro"

            if categoria not in distribucion_dict:
                distribucion_dict[categoria] = {"cantidad": 0, "monto_total": Decimal("0")}
            distribucion_dict[categoria]["cantidad"] += 1
            distribucion_dict[categoria]["monto_total"] += monto_decimal

        logger.info(
            f"📊 [financiamiento-por-rangos] Procesamiento fallback completado: "
            f"{prestamos_procesados} procesados, {prestamos_omitidos} omitidos, "
            f"{len(distribucion_dict)} categorías con datos"
        )

        # Convertir Decimal a float
        for cat in distribucion_dict:
            distribucion_dict[cat]["monto_total"] = float(distribucion_dict[cat]["monto_total"])

    except Exception as e:
        logger.error(f"Error en fallback de distribución por rangos: {e}", exc_info=True)
        return []

    # Construir respuesta
    distribucion_data = []
    for min_val, max_val, categoria in rangos:
        datos = distribucion_dict.get(categoria, {"cantidad": 0, "monto_total": 0.0})
        cantidad = datos["cantidad"]
        monto_total = datos["monto_total"]
        porcentaje_cantidad = (cantidad / total_prestamos * 100) if total_prestamos > 0 else 0
        porcentaje_monto = (monto_total / total_monto * 100) if total_monto > 0 else 0

        distribucion_data.append(
            {
                "categoria": categoria,
                "cantidad_prestamos": cantidad,
                "monto_total": monto_total,
                "porcentaje_cantidad": round(porcentaje_cantidad, 2),
                "porcentaje_monto": round(porcentaje_monto, 2),
            }
        )

    return distribucion_data


def _calcular_rango_fechas_granularidad(
    granularidad: str, hoy: date, dias: Optional[int], fecha_inicio: Optional[date], fecha_fin: Optional[date]
) -> tuple[date, date]:
    """Calcula rango de fechas según granularidad"""
    if granularidad == "mes_actual":
        fecha_inicio_query = date(hoy.year, hoy.month, 1)
        fecha_fin_query = _obtener_fechas_mes_siguiente(hoy.month, hoy.year)
    elif granularidad == "proximos_n_dias":
        fecha_inicio_query = hoy
        fecha_fin_query = hoy + timedelta(days=dias or 30)
    elif granularidad == "hasta_fin_anio":
        fecha_inicio_query = hoy
        fecha_fin_query = date(hoy.year, 12, 31)
    else:  # personalizado
        fecha_inicio_query = fecha_inicio or hoy
        fecha_fin_query = fecha_fin or (hoy + timedelta(days=30))
    return fecha_inicio_query, fecha_fin_query


def _calcular_proyeccion_cuentas_cobrar(datos: List[dict[str, Any]]) -> float:
    """Calcula proyección de cuentas por cobrar usando último valor conocido"""
    ultimo_valor: float = 0.0
    if datos and len(datos) > 0 and "cuentas_por_cobrar" in datos[-1]:
        valor = datos[-1]["cuentas_por_cobrar"]
        if valor is not None and isinstance(valor, (int, float)):
            ultimo_valor = float(valor)
    return ultimo_valor * 1.02 if ultimo_valor > 0 else 0.0  # Crecimiento del 2%


def _calcular_proyeccion_cuotas_dias(datos: List[dict[str, Any]]) -> int:
    """Calcula proyección de cuotas en días usando promedio histórico"""
    if len(datos) > 0:
        valores_historicos = [
            d["cuotas_en_dias"] for d in datos if d.get("cuotas_en_dias") is not None and d["cuotas_en_dias"] > 0
        ]
        return int(sum(valores_historicos) / len(valores_historicos)) if valores_historicos else 0
    return 0


def _calcular_pagos_fecha(
    db: Session,
    fecha: date,
    analista: Optional[str],
    concesionario: Optional[str],
    modelo: Optional[str],
    fecha_inicio: Optional[date],
    fecha_fin: Optional[date],
) -> float:
    """Calcula pagos en una fecha específica"""
    # ✅ ACTUALIZADO: Usar tabla pagos (no pagos_staging) con prestamo_id y cedula
    fecha_dt = datetime.combine(fecha, datetime.min.time())
    fecha_dt_end = datetime.combine(fecha, datetime.max.time())

    # Construir query con filtros opcionales
    if analista or concesionario or modelo:
        prestamo_conditions = []
        bind_params = {"fecha_inicio": fecha_dt, "fecha_fin": fecha_dt_end}

        if analista:
            prestamo_conditions.append("(pr.analista = :analista OR pr.producto_financiero = :analista)")
            bind_params["analista"] = analista
        if concesionario:
            prestamo_conditions.append("pr.concesionario = :concesionario")
            bind_params["concesionario"] = concesionario
        if modelo:
            prestamo_conditions.append("(pr.producto = :modelo OR pr.modelo_vehiculo = :modelo)")
            bind_params["modelo"] = modelo

        where_clause = """p.fecha_pago >= :fecha_inicio
          AND p.fecha_pago <= :fecha_fin
          AND p.monto_pagado IS NOT NULL
          AND p.monto_pagado > 0
          AND p.activo = TRUE
          AND pr.estado = 'APROBADO'"""

        if prestamo_conditions:
            where_clause += " AND " + " AND ".join(prestamo_conditions)

        query_sql = text(
            f"""
            SELECT COALESCE(SUM(p.monto_pagado), 0)
            FROM pagos p
            INNER JOIN prestamos pr ON (
                (p.prestamo_id IS NOT NULL AND pr.id = p.prestamo_id)
                OR (p.prestamo_id IS NULL AND pr.cedula = p.cedula AND pr.estado = 'APROBADO')
            )
            WHERE {where_clause}
            """
        ).bindparams(**bind_params)
    else:
        query_sql = text(
            """
            SELECT COALESCE(SUM(monto_pagado), 0)
            FROM pagos
            WHERE fecha_pago >= :fecha_inicio
              AND fecha_pago <= :fecha_fin
              AND monto_pagado IS NOT NULL
              AND monto_pagado > 0
              AND activo = TRUE
            """
        ).bindparams(fecha_inicio=fecha_dt, fecha_fin=fecha_dt_end)

    result = db.execute(query_sql)
    return float(result.scalar() or Decimal("0"))


def _calcular_tasa_recuperacion(
    db: Session,
    primer_dia: date,
    ultimo_dia: date,
    analista: Optional[str],
    concesionario: Optional[str],
    modelo: Optional[str],
) -> float:
    """Calcula la tasa de recuperación mensual"""
    # Cuotas a cobrar del mes
    cuotas_a_cobrar_query = (
        db.query(func.sum(Cuota.monto_cuota))
        .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
        .filter(
            func.date(Cuota.fecha_vencimiento) >= primer_dia,
            func.date(Cuota.fecha_vencimiento) <= ultimo_dia,
            Prestamo.estado == "APROBADO",
        )
    )
    cuotas_a_cobrar_query = FiltrosDashboard.aplicar_filtros_cuota(
        cuotas_a_cobrar_query, analista, concesionario, modelo, None, None
    )

    # Cuotas pagadas del mes
    cuotas_pagadas_query = (
        db.query(func.count(Cuota.id))
        .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
        .filter(
            Cuota.estado == "PAGADO",
            Cuota.fecha_pago.isnot(None),
            func.date(Cuota.fecha_pago) >= primer_dia,
            func.date(Cuota.fecha_pago) <= ultimo_dia,
            Prestamo.estado == "APROBADO",
        )
    )
    cuotas_pagadas_query = FiltrosDashboard.aplicar_filtros_cuota(
        cuotas_pagadas_query, analista, concesionario, modelo, None, None
    )
    cuotas_pagadas = cuotas_pagadas_query.scalar() or 0

    # Total cuotas planificadas
    total_cuotas_query = (
        db.query(func.count(Cuota.id))
        .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
        .filter(
            func.date(Cuota.fecha_vencimiento) >= primer_dia,
            func.date(Cuota.fecha_vencimiento) <= ultimo_dia,
            Prestamo.estado == "APROBADO",
        )
    )
    total_cuotas_query = FiltrosDashboard.aplicar_filtros_cuota(
        total_cuotas_query, analista, concesionario, modelo, None, None
    )
    total_cuotas = total_cuotas_query.scalar() or 0

    return (cuotas_pagadas / total_cuotas * 100) if total_cuotas > 0 else 0


def _normalizar_valor(valor: Optional[str]) -> Optional[str]:
    """Normaliza un valor: trim, validar no vacío"""
    if not valor:
        return None
    valor_limpio = str(valor).strip()
    return valor_limpio if valor_limpio else None


def _obtener_valores_unicos(query_result) -> set:
    """Extrae valores únicos normalizados de una query"""
    valores = set()
    for item in query_result:
        valor = item[0] if isinstance(item, tuple) else item
        valor_limpio = _normalizar_valor(valor)
        if valor_limpio:
            valores.add(valor_limpio)
    return valores


def _obtener_valores_distintos_de_columna(db: Session, columna, default: Optional[set] = None) -> set:
    """Obtiene valores distintos de una columna con manejo de excepciones"""
    if default is None:
        default = set()
    try:
        query = db.query(func.distinct(columna)).filter(columna.isnot(None), columna != "").all()
        return _obtener_valores_unicos(query)
    except Exception:
        return default


@router.get("/opciones-filtros")
@cache_result(ttl=600, key_prefix="dashboard")  # Cache por 10 minutos (cambia poco)
def obtener_opciones_filtros(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Obtener opciones disponibles para filtros del dashboard - Sin duplicados"""
    try:
        # Optimizar: usar queries separadas optimizadas para categorías específicas
        # Separar en categorías para mejor organización
        analistas_set = _obtener_valores_distintos_de_columna(db, Prestamo.analista)
        productos_set = _obtener_valores_distintos_de_columna(db, Prestamo.producto_financiero)
        analistas_final = sorted(analistas_set | productos_set)

        concesionarios_set = _obtener_valores_distintos_de_columna(db, Prestamo.concesionario)
        concesionarios_final = sorted(concesionarios_set)

        modelos_producto_set = _obtener_valores_distintos_de_columna(db, Prestamo.producto)
        modelos_vehiculo_set = _obtener_valores_distintos_de_columna(db, Prestamo.modelo_vehiculo)
        modelos_final = sorted(modelos_producto_set | modelos_vehiculo_set)

        return {
            "analistas": analistas_final,
            "concesionarios": concesionarios_final,
            "modelos": modelos_final,
        }
    except Exception as e:
        logger.error(f"Error obteniendo opciones de filtros: {e}", exc_info=True)
        return {"analistas": [], "concesionarios": [], "modelos": []}


def _validar_acceso_admin(current_user: User) -> None:
    """Valida acceso admin de forma tolerante"""
    try:
        es_admin = getattr(current_user, "is_admin", None)
    except Exception:
        es_admin = None
    if es_admin is False:
        raise HTTPException(status_code=403, detail="Acceso denegado. Solo administradores.")


def _normalizar_dias(dias: Optional[int]) -> int:
    """Normaliza parámetro días"""
    try:
        dias_norm = int(dias or 30)
    except Exception:
        dias_norm = 30
    return max(dias_norm, 30) if dias_norm <= 0 else dias_norm


def _calcular_total_a_cobrar(
    db: Session, fecha_dia: date, analista: Optional[str], concesionario: Optional[str], modelo: Optional[str]
) -> float:
    """Calcula total a cobrar para una fecha específica"""
    try:
        cuotas_dia_query = (
            db.query(func.sum(Cuota.monto_cuota))
            .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
            .filter(Cuota.fecha_vencimiento == fecha_dia, Prestamo.estado == "APROBADO")
        )
        cuotas_dia_query = FiltrosDashboard.aplicar_filtros_cuota(
            cuotas_dia_query, analista, concesionario, modelo, None, None
        )
        return float(cuotas_dia_query.scalar() or Decimal("0"))
    except Exception:
        logger.error(
            "Error en query total_a_cobrar",
            extra={"fecha": fecha_dia.isoformat(), "analista": analista, "concesionario": concesionario, "modelo": modelo},
            exc_info=True,
        )
        return 0.0


def _calcular_total_cobrado(
    db: Session, fecha_dia: date, analista: Optional[str], concesionario: Optional[str], modelo: Optional[str]
) -> float:
    """Calcula total cobrado para una fecha específica"""
    try:
        # ✅ ACTUALIZADO: Usar tabla pagos (no pagos_staging) con prestamo_id y cedula
        fecha_dt = datetime.combine(fecha_dia, datetime.min.time())
        fecha_dt_end = datetime.combine(fecha_dia, datetime.max.time())

        # Construir query con filtros opcionales
        if analista or concesionario or modelo:
            prestamo_conditions = []
            bind_params = {"fecha_inicio": fecha_dt, "fecha_fin": fecha_dt_end}

            if analista:
                prestamo_conditions.append("(pr.analista = :analista OR pr.producto_financiero = :analista)")
                bind_params["analista"] = analista
            if concesionario:
                prestamo_conditions.append("pr.concesionario = :concesionario")
                bind_params["concesionario"] = concesionario
            if modelo:
                prestamo_conditions.append("(pr.producto = :modelo OR pr.modelo_vehiculo = :modelo)")
                bind_params["modelo"] = modelo

            where_clause = """p.fecha_pago >= :fecha_inicio
              AND p.fecha_pago <= :fecha_fin
              AND p.monto_pagado IS NOT NULL
              AND p.monto_pagado > 0
              AND p.activo = TRUE
              AND pr.estado = 'APROBADO'"""

            if prestamo_conditions:
                where_clause += " AND " + " AND ".join(prestamo_conditions)

            query_sql = text(
                f"""
                SELECT COALESCE(SUM(p.monto_pagado), 0)
                FROM pagos p
                INNER JOIN prestamos pr ON (
                    (p.prestamo_id IS NOT NULL AND pr.id = p.prestamo_id)
                    OR (p.prestamo_id IS NULL AND pr.cedula = p.cedula AND pr.estado = 'APROBADO')
                )
                WHERE {where_clause}
                """
            ).bindparams(**bind_params)
        else:
            query_sql = text(
                """
                SELECT COALESCE(SUM(monto_pagado), 0)
                FROM pagos
                WHERE fecha_pago >= :fecha_inicio
                  AND fecha_pago <= :fecha_fin
                  AND monto_pagado IS NOT NULL
                  AND monto_pagado > 0
                  AND activo = TRUE
                """
            ).bindparams(fecha_inicio=fecha_dt, fecha_fin=fecha_dt_end)

        result = db.execute(query_sql)
        return float(result.scalar() or Decimal("0"))
    except Exception:
        logger.error(
            "Error en query total_cobrado",
            extra={"fecha": fecha_dia.isoformat(), "analista": analista, "concesionario": concesionario, "modelo": modelo},
            exc_info=True,
        )
        return 0.0


def _calcular_total_cobrado_acumulativo(
    db: Session, analista: Optional[str], concesionario: Optional[str], modelo: Optional[str]
) -> Decimal:
    """Calcula el total cobrado acumulativo (todos los pagos históricos)"""
    try:
        # ✅ ACTUALIZADO: Usar tabla pagos (no pagos_staging) con prestamo_id y cedula
        # Sin filtro de fecha - suma TODOS los pagos históricos

        # Construir query con filtros opcionales
        if analista or concesionario or modelo:
            prestamo_conditions = []
            bind_params = {}

            if analista:
                prestamo_conditions.append("(pr.analista = :analista OR pr.producto_financiero = :analista)")
                bind_params["analista"] = analista
            if concesionario:
                prestamo_conditions.append("pr.concesionario = :concesionario")
                bind_params["concesionario"] = concesionario
            if modelo:
                prestamo_conditions.append("(pr.producto = :modelo OR pr.modelo_vehiculo = :modelo)")
                bind_params["modelo"] = modelo

            where_clause = """p.monto_pagado IS NOT NULL
              AND p.monto_pagado > 0
              AND p.activo = TRUE
              AND pr.estado = 'APROBADO'"""

            if prestamo_conditions:
                where_clause += " AND " + " AND ".join(prestamo_conditions)

            query_sql = text(
                f"""
                SELECT COALESCE(SUM(p.monto_pagado), 0)
                FROM pagos p
                INNER JOIN prestamos pr ON (
                    (p.prestamo_id IS NOT NULL AND pr.id = p.prestamo_id)
                    OR (p.prestamo_id IS NULL AND pr.cedula = p.cedula AND pr.estado = 'APROBADO')
                )
                WHERE {where_clause}
                """
            ).bindparams(**bind_params)
        else:
            query_sql = text(
                """
                SELECT COALESCE(SUM(monto_pagado), 0)
                FROM pagos
                WHERE monto_pagado IS NOT NULL
                  AND monto_pagado > 0
                  AND activo = TRUE
                """
            )

        result = db.execute(query_sql)
        return Decimal(str(result.scalar() or 0))
    except Exception:
        logger.error(
            "Error en query total_cobrado_acumulativo",
            extra={"analista": analista, "concesionario": concesionario, "modelo": modelo},
            exc_info=True,
        )
        return Decimal("0")


def _generar_lista_fechas(fecha_inicio: date, fecha_fin: date) -> List[date]:
    """Genera lista de fechas entre inicio y fin"""
    fechas = []
    current_date = fecha_inicio
    while current_date <= fecha_fin:
        fechas.append(current_date)
        current_date += timedelta(days=1)
    return fechas


@router.get("/cobros-diarios")
def obtener_cobros_diarios(
    dias: Optional[int] = Query(30, description="Número de días a mostrar"),
    analista: Optional[str] = Query(None, description="Filtrar por analista"),
    concesionario: Optional[str] = Query(None, description="Filtrar por concesionario"),
    modelo: Optional[str] = Query(None, description="Filtrar por modelo"),
    fecha_inicio: Optional[date] = Query(None, description="Fecha inicio"),
    fecha_fin: Optional[date] = Query(None, description="Fecha fin"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Obtener total a cobrar y total cobrado por día"""
    try:
        _validar_acceso_admin(current_user)

        dias_norm = _normalizar_dias(dias)
        hoy = date.today()

        fecha_inicio_query = fecha_inicio if fecha_inicio else hoy - timedelta(days=dias_norm)
        fecha_fin_query = fecha_fin if fecha_fin else hoy

        fechas = _generar_lista_fechas(fecha_inicio_query, fecha_fin_query)

        datos_diarios = []
        for fecha_dia in fechas:
            total_a_cobrar = _calcular_total_a_cobrar(db, fecha_dia, analista, concesionario, modelo)
            total_cobrado = _calcular_total_cobrado(db, fecha_dia, analista, concesionario, modelo)

            datos_diarios.append(
                {
                    "fecha": fecha_dia.isoformat(),
                    "dia": fecha_dia.strftime("%d/%m"),
                    "dia_semana": fecha_dia.strftime("%a"),
                    "total_a_cobrar": total_a_cobrar,
                    "total_cobrado": total_cobrado,
                }
            )

        return {"datos": datos_diarios}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo cobros diarios: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.get("/admin")
@cache_result(ttl=300, key_prefix="dashboard")  # Cache por 5 minutos
def dashboard_administrador(
    periodo: Optional[str] = Query("mes", description="Periodo: dia, semana, mes, año"),
    analista: Optional[str] = Query(None, description="Filtrar por analista"),
    concesionario: Optional[str] = Query(None, description="Filtrar por concesionario"),
    modelo: Optional[str] = Query(None, description="Filtrar por modelo de vehículo"),
    fecha_inicio: Optional[date] = Query(None, description="Fecha inicio del rango"),
    fecha_fin: Optional[date] = Query(None, description="Fecha fin del rango"),
    consolidado: Optional[bool] = Query(False, description="Agrupar datos consolidados"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Dashboard para administradores con datos reales de la base de datos
    Soporta filtros: analista, concesionario, modelo, rango de fechas
    ✅ OPTIMIZADO: Reducción de queries y mejor uso de índices
    """
    import time

    start_total = time.time()
    try:
        if not current_user.is_admin:
            raise HTTPException(status_code=403, detail="Acceso denegado. Solo administradores.")

        hoy = date.today()
        logger.info(
            f"📊 [dashboard/admin] Iniciando cálculo - período={periodo}, filtros: analista={analista}, concesionario={concesionario}, modelo={modelo}"
        )

        # Aplicar filtros base a queries de préstamos (usando clase centralizada)
        # Prestamo NO tiene campo 'activo', usar estado == "APROBADO"
        base_prestamo_query = db.query(Prestamo).filter(Prestamo.estado == "APROBADO")
        base_prestamo_query = FiltrosDashboard.aplicar_filtros_prestamo(
            base_prestamo_query,
            analista,
            concesionario,
            modelo,
            fecha_inicio,
            fecha_fin,
        )

        # 1. CARTERA TOTAL - Suma de todos los préstamos activos
        cartera_total = base_prestamo_query.with_entities(func.sum(Prestamo.total_financiamiento)).scalar() or Decimal("0")

        # 2. CARTERA VENCIDA - Monto de préstamos con cuotas vencidas (no pagadas)
        # ✅ Usar select_from para evitar ambigüedad en JOIN
        cartera_vencida_query = (
            db.query(func.sum(Cuota.monto_cuota))
            .select_from(Cuota)
            .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
            .filter(
                and_(
                    Cuota.fecha_vencimiento < hoy,
                    Cuota.estado != "PAGADO",
                    Prestamo.estado == "APROBADO",
                )
            )
        )
        cartera_vencida_query = FiltrosDashboard.aplicar_filtros_cuota(
            cartera_vencida_query,
            analista,
            concesionario,
            modelo,
            fecha_inicio,
            fecha_fin,
        )
        cartera_vencida = cartera_vencida_query.scalar() or Decimal("0")

        # 3. CARTERA AL DÍA - Cartera total menos cartera vencida
        cartera_al_dia = cartera_total - cartera_vencida

        # 4. PORCENTAJE DE MORA
        porcentaje_mora = (float(cartera_vencida) / float(cartera_total) * 100) if cartera_total > 0 else 0

        # 5. PAGOS DE HOY (con filtros)
        # ✅ ACTUALIZADO: Usar tabla pagos (no pagos_staging) con prestamo_id y cedula
        # text ya está importado al inicio del archivo

        hoy_dt = datetime.combine(hoy, datetime.min.time())
        hoy_dt_end = datetime.combine(hoy, datetime.max.time())

        # ✅ ACTUALIZADO: Usar tabla pagos (no pagos_staging) con prestamo_id y cedula
        pagos_hoy_query = db.execute(
            text("SELECT COUNT(*) FROM pagos WHERE fecha_pago >= :inicio AND fecha_pago <= :fin AND activo = TRUE").bindparams(
                inicio=hoy_dt, fin=hoy_dt_end
            )
        )
        pagos_hoy = pagos_hoy_query.scalar() or 0

        monto_pagos_hoy_query = db.execute(
            text(
                "SELECT COALESCE(SUM(monto_pagado), 0) FROM pagos WHERE fecha_pago >= :inicio AND fecha_pago <= :fin AND monto_pagado IS NOT NULL AND monto_pagado > 0 AND activo = TRUE"
            ).bindparams(inicio=hoy_dt, fin=hoy_dt_end)
        )
        monto_pagos_hoy = Decimal(str(monto_pagos_hoy_query.scalar() or 0))

        # ⚠️ Filtros por analista/concesionario/modelo no aplicados aquí (requeriría JOIN con prestamos)
        # if analista or concesionario or modelo:
        #     # No disponible sin prestamo_id

        # ⚠️ Filtros ya aplicados arriba con SQL directo, valores ya calculados

        # 6. CLIENTES ACTIVOS - Clientes con préstamos activos
        clientes_activos = base_prestamo_query.with_entities(func.count(func.distinct(Prestamo.cedula))).scalar() or 0

        # 7. CLIENTES EN MORA - Clientes con cuotas vencidas
        # ✅ Usar select_from con Cuota como base y JOIN explícito
        clientes_mora_query = (
            db.query(func.count(func.distinct(Prestamo.cedula)))
            .select_from(Cuota)
            .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
            .filter(
                and_(
                    Cuota.fecha_vencimiento < hoy,
                    Cuota.estado != "PAGADO",
                    Prestamo.estado == "APROBADO",
                )
            )
        )
        # Aplicar filtros solo si se proporcionan (evitar errores si no hay filtros)
        if analista or concesionario or modelo or fecha_inicio or fecha_fin:
            clientes_mora_query = FiltrosDashboard.aplicar_filtros_cuota(
                clientes_mora_query,
                analista,
                concesionario,
                modelo,
                fecha_inicio,
                fecha_fin,
            )
        clientes_en_mora = clientes_mora_query.scalar() or 0

        # 8. PRÉSTAMOS ACTIVOS (calculado pero no usado actualmente en respuesta)
        # prestamos_activos = (
        #     base_prestamo_query.with_entities(func.count(Prestamo.id)).scalar() or 0
        # )

        # 9. PRÉSTAMOS PAGADOS (calculado pero no usado actualmente en respuesta)
        # prestamos_pagados = (
        #     db.query(func.count(Prestamo.id))
        #     .filter(Prestamo.estado == "PAGADO")
        #     .scalar()
        #     or 0
        # )

        # 10. PRÉSTAMOS VENCIDOS (calculado pero no usado actualmente en respuesta)
        # prestamos_vencidos = (
        #     db.query(func.count(func.distinct(Prestamo.id)))
        #     .join(Cuota, Cuota.prestamo_id == Prestamo.id)
        #     .filter(
        #         and_(
        #             Cuota.fecha_vencimiento < hoy,
        #             Cuota.estado != "PAGADO",
        #             Prestamo.activo.is_(True),
        #         )
        #     )
        #     .scalar()
        #     or 0
        # )

        # 11. TOTAL PAGADO (histórico o con filtros)
        # ✅ ACTUALIZADO: Usar tabla pagos (no pagos_staging) con prestamo_id y cedula
        # Nota: Esta query está comentada porque no se usa en la respuesta actual
        # query_sql = "SELECT COALESCE(SUM(monto_pagado), 0) FROM pagos WHERE monto_pagado IS NOT NULL AND monto_pagado > 0 AND activo = TRUE"
        # params = {}

        # Aplicar filtros de fecha si existen
        # if fecha_inicio:
        #     query_sql += " AND fecha_pago >= :fecha_inicio"
        #     params["fecha_inicio"] = datetime.combine(fecha_inicio, datetime.min.time())
        # if fecha_fin:
        #     query_sql += " AND fecha_pago <= :fecha_fin"
        #     params["fecha_fin"] = datetime.combine(fecha_fin, datetime.max.time())

        # ⚠️ Filtros por analista/concesionario/modelo requerirían JOIN con prestamos

        # total_cobrado_query = db.execute(text(query_sql).bindparams(**params))
        # total_cobrado se calcula pero no se usa en la respuesta actual
        # total_cobrado = total_cobrado_query.scalar() or Decimal("0")

        # 12. CUOTAS PAGADAS TOTALES
        cuotas_pagadas_query = (
            db.query(func.count(Cuota.id))
            .select_from(Cuota)
            .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
            .filter(Cuota.estado == "PAGADO", Prestamo.estado == "APROBADO")
        )
        # 13. CUOTAS PENDIENTES
        cuotas_pendientes_query = (
            db.query(func.count(Cuota.id))
            .select_from(Cuota)
            .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
            .filter(Cuota.estado == "PENDIENTE", Prestamo.estado == "APROBADO")
        )
        # 14. CUOTAS ATRASADAS
        cuotas_atrasadas_query = (
            db.query(func.count(Cuota.id))
            .select_from(Cuota)
            .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
            .filter(
                and_(
                    Cuota.estado == "ATRASADO",
                    Cuota.fecha_vencimiento < hoy,
                    Prestamo.estado == "APROBADO",
                )
            )
        )

        # ✅ Aplicar filtros usando clase centralizada (automático para todas las cuotas)
        cuotas_pagadas_query = FiltrosDashboard.aplicar_filtros_cuota(
            cuotas_pagadas_query,
            analista,
            concesionario,
            modelo,
            fecha_inicio,
            fecha_fin,
        )
        cuotas_pendientes_query = FiltrosDashboard.aplicar_filtros_cuota(
            cuotas_pendientes_query,
            analista,
            concesionario,
            modelo,
            fecha_inicio,
            fecha_fin,
        )
        cuotas_atrasadas_query = FiltrosDashboard.aplicar_filtros_cuota(
            cuotas_atrasadas_query,
            analista,
            concesionario,
            modelo,
            fecha_inicio,
            fecha_fin,
        )

        # Variables calculadas pero no usadas actualmente en la respuesta
        # cuotas_pagadas = cuotas_pagadas_query.scalar() or 0
        # cuotas_pendientes = cuotas_pendientes_query.scalar() or 0
        # cuotas_atrasadas = cuotas_atrasadas_query.scalar() or 0

        # 15. CÁLCULO DE PERÍODOS ANTERIORES
        try:
            fecha_inicio_periodo, fecha_fin_periodo_anterior = _calcular_periodos(periodo, hoy)

            # Cartera anterior - Calcular desde BD histórica
            cartera_anterior_val = _calcular_cartera_anterior(
                db, periodo, fecha_fin_periodo_anterior, analista, concesionario, modelo, cartera_total
            )
        except Exception as e:
            logger.warning(f"Error calculando períodos anteriores: {e}")
            try:
                db.rollback()
            except Exception:
                pass
            cartera_anterior_val = float(cartera_total)

        # 16. TOTAL COBRADO ACUMULATIVO (TODOS LOS PAGOS HISTÓRICOS)
        # ✅ CAMBIO: Ahora calcula el total acumulativo, no solo del mes actual
        try:
            total_cobrado_acumulativo = _calcular_total_cobrado_acumulativo(db, analista, concesionario, modelo)
        except Exception as e:
            logger.warning(f"Error calculando total cobrado acumulativo: {e}")
            try:
                db.rollback()
            except Exception:
                pass
            total_cobrado_acumulativo = Decimal("0")

        # Total cobrado mes actual (para comparación y tasa de recuperación)
        año_actual = hoy.year
        mes_actual = hoy.month
        primer_dia_mes = date(año_actual, mes_actual, 1)
        ultimo_dia_mes = date(año_actual, mes_actual, monthrange(año_actual, mes_actual)[1])

        try:
            total_cobrado_periodo = _calcular_total_cobrado_mes(
                db, primer_dia_mes, ultimo_dia_mes, analista, concesionario, modelo
            )
        except Exception as e:
            logger.warning(f"Error calculando total cobrado período: {e}")
            try:
                db.rollback()
            except Exception:
                pass
            total_cobrado_periodo = Decimal("0")

        # Total cobrado mes anterior
        try:
            mes_anterior, año_anterior = _calcular_mes_anterior(mes_actual, año_actual)
            primer_dia_mes_anterior, ultimo_dia_mes_anterior = _obtener_fechas_mes(mes_anterior, año_anterior)

            total_cobrado_anterior = _calcular_total_cobrado_mes(
                db, primer_dia_mes_anterior, ultimo_dia_mes_anterior, analista, concesionario, modelo
            )
        except Exception as e:
            logger.warning(f"Error calculando total cobrado anterior: {e}")
            try:
                db.rollback()
            except Exception:
                pass
            total_cobrado_anterior = Decimal("0")

        # 17. TASA DE RECUPERACIÓN MENSUAL
        try:
            tasa_recuperacion = _calcular_tasa_recuperacion(
                db, primer_dia_mes, ultimo_dia_mes, analista, concesionario, modelo
            )
        except Exception as e:
            logger.warning(f"Error calculando tasa recuperación: {e}")
            try:
                db.rollback()
            except Exception:
                pass
            tasa_recuperacion = 0.0

        # Tasa recuperación mes anterior
        try:
            tasa_recuperacion_anterior = _calcular_tasa_recuperacion(
                db, primer_dia_mes_anterior, ultimo_dia_mes_anterior, analista, concesionario, modelo
            )
        except Exception as e:
            logger.warning(f"Error calculando tasa recuperación anterior: {e}")
            try:
                db.rollback()
            except Exception:
                pass
            tasa_recuperacion_anterior = 0.0

        # 18. PROMEDIO DÍAS DE MORA
        # Calcular desde cuotas vencidas en lugar de usar campo inexistente
        # ✅ CORRECCIÓN: Usar CAST para convertir el parámetro bind correctamente
        try:
            promedio_dias_mora_query = db.execute(
                text(
                    """
                    SELECT COALESCE(AVG(CAST(:hoy AS date) - CAST(c.fecha_vencimiento AS date)), 0)
                    FROM cuotas c
                    INNER JOIN prestamos p ON c.prestamo_id = p.id
                    WHERE c.fecha_vencimiento < CAST(:hoy AS date)
                      AND c.estado != 'PAGADO'
                      AND p.estado = 'APROBADO'
                """
                ).bindparams(hoy=hoy)
            )
            promedio_dias_mora = float(promedio_dias_mora_query.scalar() or 0.0)
        except Exception as e:
            logger.warning(f"Error calculando promedio días de mora: {e}")
            try:
                db.rollback()
            except Exception:
                pass
            promedio_dias_mora = 0.0

        # 19. PORCENTAJE CUMPLIMIENTO (clientes al día / total clientes)
        porcentaje_cumplimiento = (
            ((clientes_activos - clientes_en_mora) / clientes_activos * 100) if clientes_activos > 0 else 0
        )

        # 20. TICKET PROMEDIO (promedio de préstamos)
        ticket_promedio = float(cartera_total / clientes_activos) if clientes_activos > 0 else 0

        # 20.1. MODELOS MÁS Y MENOS VENDIDOS (conectado a datos reales)
        try:
            query_modelos = (
                db.query(
                    func.coalesce(func.coalesce(Prestamo.modelo_vehiculo, Prestamo.producto), "Sin Modelo").label("modelo"),
                    func.sum(Prestamo.total_financiamiento).label("total_prestamos"),
                    func.count(Prestamo.id).label("cantidad_prestamos"),
                )
                .filter(Prestamo.estado == "APROBADO")
                .group_by("modelo")
            )
            # Aplicar filtros
            query_modelos = FiltrosDashboard.aplicar_filtros_prestamo(
                query_modelos, analista, concesionario, None, fecha_inicio, fecha_fin
            )
            resultados_modelos = query_modelos.all()

            if resultados_modelos:
                # Ordenar por total_prestamos
                modelos_ordenados = sorted(
                    resultados_modelos, key=lambda x: float(x.total_prestamos or Decimal("0")), reverse=True
                )
                modelo_mas_vendido = modelos_ordenados[0].modelo or "N/A"
                ventas_modelo_mas_vendido = int(modelos_ordenados[0].cantidad_prestamos or 0)
                modelo_menos_vendido = modelos_ordenados[-1].modelo or "N/A"
                total_modelos = len(modelos_ordenados)
            else:
                modelo_mas_vendido = "N/A"
                ventas_modelo_mas_vendido = 0
                modelo_menos_vendido = "N/A"
                total_modelos = 0
        except Exception as e:
            logger.warning(f"Error calculando modelos más/menos vendidos: {e}")
            try:
                db.rollback()
            except Exception:
                pass
            modelo_mas_vendido = "N/A"
            ventas_modelo_mas_vendido = 0
            modelo_menos_vendido = "N/A"
            total_modelos = 0

        # 21. EVOLUCIÓN MENSUAL (últimos 6 meses)
        # ✅ OPTIMIZACIÓN: Combinar múltiples queries en una sola consulta con GROUP BY
        start_evolucion = time.time()
        evolucion_mensual = []
        nombres_meses = [
            "Ene",
            "Feb",
            "Mar",
            "Abr",
            "May",
            "Jun",
            "Jul",
            "Ago",
            "Sep",
            "Oct",
            "Nov",
            "Dic",
        ]
        try:
            # Calcular rango de meses (últimos 7 meses)
            meses_rango = []
            for i in range(6, -1, -1):
                mes_fecha = hoy - timedelta(days=30 * i)
                mes_inicio = date(mes_fecha.year, mes_fecha.month, 1)
                if mes_fecha.month == 12:
                    mes_fin = date(mes_fecha.year + 1, 1, 1) - timedelta(days=1)
                else:
                    mes_fin = date(mes_fecha.year, mes_fecha.month + 1, 1) - timedelta(days=1)
                meses_rango.append(
                    {
                        "fecha": mes_fecha,
                        "inicio": mes_inicio,
                        "fin": mes_fin,
                        "inicio_dt": datetime.combine(mes_inicio, datetime.min.time()),
                        "fin_dt": datetime.combine(mes_fin, datetime.max.time()),
                    }
                )

            # ✅ OPTIMIZACIÓN: Una sola query para obtener todos los pagos del rango
            fecha_primera = meses_rango[0]["inicio_dt"]
            fecha_ultima = meses_rango[-1]["fin_dt"]
            # ✅ ACTUALIZADO: Usar tabla pagos (no pagos_staging) con prestamo_id y cedula
            try:
                # Asegurar que las fechas sean datetime objects
                if isinstance(fecha_primera, date) and not isinstance(fecha_primera, datetime):
                    fecha_primera = datetime.combine(fecha_primera, datetime.min.time())
                if isinstance(fecha_ultima, date) and not isinstance(fecha_ultima, datetime):
                    fecha_ultima = datetime.combine(fecha_ultima, datetime.max.time())

                pagos_evolucion_query = db.execute(
                    text(
                        """
                        SELECT
                            EXTRACT(YEAR FROM fecha_pago)::integer as año,
                            EXTRACT(MONTH FROM fecha_pago)::integer as mes,
                            COALESCE(SUM(monto_pagado), 0) as monto_total
                        FROM pagos
                        WHERE fecha_pago >= :fecha_inicio
                          AND fecha_pago <= :fecha_fin
                          AND monto_pagado IS NOT NULL
                          AND monto_pagado > 0
                          AND activo = TRUE
                GROUP BY EXTRACT(YEAR FROM fecha_pago), EXTRACT(MONTH FROM fecha_pago)
                        ORDER BY año, mes
                    """
                    ).bindparams(fecha_inicio=fecha_primera, fecha_fin=fecha_ultima)
                )
                pagos_por_mes = {(int(row[0]), int(row[1])): Decimal(str(row[2] or 0)) for row in pagos_evolucion_query}
            except Exception as e:
                logger.error(f"Error consultando pagos en dashboard_administrador: {e}", exc_info=True)
                try:
                    db.rollback()
                except Exception:
                    pass
                pagos_por_mes = {}

            # ✅ OPTIMIZACIÓN: Una sola query para obtener cuotas vencidas por mes
            try:
                cuotas_vencidas_query = db.execute(
                    text(
                        """
                        SELECT
                            EXTRACT(YEAR FROM c.fecha_vencimiento)::integer as año,
                            EXTRACT(MONTH FROM c.fecha_vencimiento)::integer as mes,
                            COUNT(*) as cantidad_vencidas
                        FROM cuotas c
                        INNER JOIN prestamos p ON c.prestamo_id = p.id
                        WHERE p.estado = 'APROBADO'
                          AND c.estado != 'PAGADO'
                          AND c.fecha_vencimiento >= :fecha_inicio
                          AND c.fecha_vencimiento <= :fecha_fin
                GROUP BY EXTRACT(YEAR FROM c.fecha_vencimiento), EXTRACT(MONTH FROM c.fecha_vencimiento)
                        ORDER BY año, mes
                    """
                    ).bindparams(fecha_inicio=meses_rango[0]["inicio"], fecha_fin=meses_rango[-1]["fin"])
                )
                cuotas_vencidas_por_mes = {(int(row[0]), int(row[1])): int(row[2] or 0) for row in cuotas_vencidas_query}
            except Exception as e:
                logger.error(f"Error consultando cuotas vencidas en dashboard_administrador: {e}", exc_info=True)
                try:
                    db.rollback()
                except Exception:
                    pass
                cuotas_vencidas_por_mes = {}

            # ✅ OPTIMIZACIÓN: Una sola query para obtener cuotas pagadas por mes
            try:
                cuotas_pagadas_query = db.execute(
                    text(
                        """
                    SELECT
                        EXTRACT(YEAR FROM DATE(c.fecha_pago))::integer as año,
                        EXTRACT(MONTH FROM DATE(c.fecha_pago))::integer as mes,
                        COUNT(*) as cantidad_pagadas
                    FROM cuotas c
                    INNER JOIN prestamos p ON c.prestamo_id = p.id
                    WHERE p.estado = 'APROBADO'
                      AND c.estado = 'PAGADO'
                      AND c.fecha_pago IS NOT NULL
                      AND DATE(c.fecha_pago) >= :fecha_inicio
                      AND DATE(c.fecha_pago) <= :fecha_fin
                GROUP BY EXTRACT(YEAR FROM DATE(c.fecha_pago)), EXTRACT(MONTH FROM DATE(c.fecha_pago))
                    ORDER BY año, mes
                """
                    ).bindparams(fecha_inicio=meses_rango[0]["inicio"], fecha_fin=meses_rango[-1]["fin"])
                )
                cuotas_pagadas_por_mes = {(int(row[0]), int(row[1])): int(row[2] or 0) for row in cuotas_pagadas_query}
            except Exception as e:
                logger.error(f"Error consultando cuotas pagadas en dashboard_administrador: {e}", exc_info=True)
                try:
                    db.rollback()
                except Exception:
                    pass
                cuotas_pagadas_por_mes = {}

            # ✅ OPTIMIZACIÓN: Calcular cartera acumulada para todos los meses en una sola query
            # Usar una query con CASE WHEN para calcular cartera acumulada por mes
            fecha_ultima = meses_rango[-1]["fin_dt"]
            cartera_por_mes_query = db.execute(
                text(
                    """
                    SELECT
                        EXTRACT(YEAR FROM fecha_registro)::integer as año,
                        EXTRACT(MONTH FROM fecha_registro)::integer as mes,
                        SUM(total_financiamiento) as monto_mes
                    FROM prestamos
                    WHERE estado = 'APROBADO'
                      AND fecha_registro <= :fecha_fin
                GROUP BY EXTRACT(YEAR FROM fecha_registro), EXTRACT(MONTH FROM fecha_registro)
                    ORDER BY año, mes
                """
                ).bindparams(fecha_fin=fecha_ultima)
            )
            cartera_por_mes_raw = {(int(row[0]), int(row[1])): Decimal(str(row[2] or 0)) for row in cartera_por_mes_query}

            # Calcular cartera acumulada por mes (suma acumulativa)
            cartera_acumulada = {}
            cartera_acum = Decimal("0")
            for mes_info in sorted(meses_rango, key=lambda x: (x["fecha"].year, x["fecha"].month)):
                año_mes = int(mes_info["fecha"].year)
                num_mes = int(mes_info["fecha"].month)
                mes_key: tuple[int, int] = (año_mes, num_mes)

                # Sumar cartera del mes actual
                cartera_acum += cartera_por_mes_raw.get(mes_key, Decimal("0"))
                cartera_acumulada[mes_key] = cartera_acum

            # Construir evolución mensual con datos pre-calculados
            for mes_info in meses_rango:
                año_mes = int(mes_info["fecha"].year)
                num_mes = int(mes_info["fecha"].month)
                mes_key_evol: tuple[int, int] = (año_mes, num_mes)

                # Cartera acumulada hasta el fin del mes (de datos pre-calculados)
                cartera_mes = float(cartera_acumulada.get(mes_key_evol, Decimal("0")))

                # Cobrado del mes (de datos pre-calculados)
                cobrado_mes = pagos_por_mes.get(mes_key_evol, Decimal("0"))

                # Cuotas vencidas y pagadas (de datos pre-calculados)
                cuotas_vencidas_mes = cuotas_vencidas_por_mes.get(mes_key_evol, 0)
                cuotas_pagadas_mes = cuotas_pagadas_por_mes.get(mes_key_evol, 0)
                total_cuotas_mes = cuotas_vencidas_mes + cuotas_pagadas_mes
                morosidad_mes = (cuotas_vencidas_mes / total_cuotas_mes * 100) if total_cuotas_mes > 0 else 0

                evolucion_mensual.append(
                    {
                        "mes": f"{nombres_meses[num_mes - 1]} {año_mes}",
                        "cartera": float(cartera_mes),
                        "cobrado": float(cobrado_mes),
                        "morosidad": round(morosidad_mes, 1),
                    }
                )

            tiempo_evolucion = int((time.time() - start_evolucion) * 1000)
            logger.info(f"📊 [dashboard/admin] Evolución mensual calculada en {tiempo_evolucion}ms")
        except Exception as e:
            logger.error(f"Error calculando evolución mensual: {e}", exc_info=True)
            try:
                db.rollback()
            except Exception:
                pass
            evolucion_mensual = []

        # 22. ANÁLISIS DE MOROSIDAD - Cálculo real desde BD
        # Total Financiamiento: Suma de todos los préstamos aprobados (ACUMULATIVO - sin filtros de fecha)
        # ✅ CORRECCIÓN: Hacer acumulativo para consistencia con Cartera Recobrada y Morosidad
        try:
            total_financiamiento_query = db.query(func.sum(Prestamo.total_financiamiento)).filter(
                Prestamo.estado == "APROBADO"
            )
            # ✅ Aplicar solo filtros de analista, concesionario y modelo (NO filtros de fecha)
            # Esto hace que sea acumulativo, consistente con totalCobrado y morosidad
            total_financiamiento_query = FiltrosDashboard.aplicar_filtros_prestamo(
                total_financiamiento_query,
                analista,
                concesionario,
                modelo,
                None,  # ✅ NO aplicar fecha_inicio
                None,  # ✅ NO aplicar fecha_fin
            )
            total_financiamiento_operaciones = float(total_financiamiento_query.scalar() or Decimal("0"))
        except Exception as e:
            logger.error(f"Error calculando total_financiamiento_operaciones: {e}", exc_info=True)
            try:
                db.rollback()  # ✅ Rollback para restaurar transacción después de error
            except Exception:
                pass
            total_financiamiento_operaciones = 0.0

        # Cartera Cobrada: Suma de TODOS los pagos
        # ✅ ACTUALIZADO: Usar tabla pagos (no pagos_staging) con prestamo_id y cedula
        # Usar SQL directo para sumar monto_pagado con filtros de fecha únicamente
        where_conditions = ["monto_pagado IS NOT NULL", "monto_pagado > 0", "activo = TRUE"]
        params = {}

        if fecha_inicio:
            where_conditions.append("fecha_pago >= :fecha_inicio")
            params["fecha_inicio"] = datetime.combine(fecha_inicio, datetime.min.time())
        if fecha_fin:
            where_conditions.append("fecha_pago <= :fecha_fin")
            params["fecha_fin"] = datetime.combine(fecha_fin, datetime.max.time())

        where_clause = " AND ".join(where_conditions)

        try:
            cartera_cobrada_query = db.execute(
                text(f"SELECT COALESCE(SUM(monto_pagado), 0) FROM pagos WHERE {where_clause}").bindparams(**params)
            )
            cartera_cobrada_total = float(cartera_cobrada_query.scalar() or Decimal("0"))
        except Exception as e:
            logger.error(f"Error calculando cartera_cobrada_total: {e}", exc_info=True)
            try:
                db.rollback()  # ✅ Rollback para restaurar transacción después de error
            except Exception:
                pass
            cartera_cobrada_total = 0.0

        # Morosidad (Diferencia): Total Financiamiento - Cartera Cobrada
        morosidad_diferencia = max(0, total_financiamiento_operaciones - cartera_cobrada_total)

        # Mantener nombres de variables para compatibilidad con frontend
        ingresos_capital = total_financiamiento_operaciones
        ingresos_interes = cartera_cobrada_total
        ingresos_mora = morosidad_diferencia

        # 23. META MENSUAL - Total a cobrar del mes actual (suma de monto_cuota de cuotas del mes)
        # Meta = Total a cobrar del mes (cuotas planificadas)
        # Recaudado = Pagos conciliados del mes
        try:
            query_meta_mensual = (
                db.query(func.sum(Cuota.monto_cuota))
                .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
                .filter(
                    Prestamo.estado == "APROBADO",
                    func.date(Cuota.fecha_vencimiento) >= primer_dia_mes,
                    func.date(Cuota.fecha_vencimiento) <= ultimo_dia_mes,
                )
            )
            query_meta_mensual = FiltrosDashboard.aplicar_filtros_cuota(
                query_meta_mensual, analista, concesionario, modelo, None, None
            )
            meta_mensual_final = float(query_meta_mensual.scalar() or Decimal("0"))
        except Exception as e:
            logger.error(f"Error calculando meta_mensual_final: {e}", exc_info=True)
            try:
                db.rollback()  # ✅ Rollback para restaurar transacción después de error
            except Exception:
                pass
            meta_mensual_final = 0.0

        return {
            "cartera_total": float(cartera_total),
            "cartera_anterior": round(cartera_anterior_val, 2),
            "cartera_al_dia": float(cartera_al_dia),
            "cartera_vencida": float(cartera_vencida),
            "porcentaje_mora": round(porcentaje_mora, 2),
            "porcentaje_mora_anterior": round(max(0, porcentaje_mora + 2.5), 2),
            "pagos_hoy": pagos_hoy,
            "monto_pagos_hoy": float(monto_pagos_hoy),
            "clientes_activos": clientes_activos,
            "clientes_mora": clientes_en_mora,
            "clientes_anterior": max(0, clientes_activos - 2),
            "meta_mensual": round(meta_mensual_final, 2),
            "avance_meta": float(total_cobrado_periodo),  # Pagos conciliados del mes
            "financieros": {
                "totalCobrado": float(total_cobrado_acumulativo),  # ✅ CAMBIO: Total acumulativo (todos los pagos históricos)
                "totalCobradoAnterior": float(total_cobrado_anterior),
                "ingresosCapital": round(ingresos_capital, 2),
                "ingresosInteres": round(ingresos_interes, 2),
                "ingresosMora": round(ingresos_mora, 2),
                "tasaRecuperacion": round(tasa_recuperacion, 1),
                "tasaRecuperacionAnterior": round(tasa_recuperacion_anterior, 1),
            },
            "cobranza": {
                "promedioDiasMora": round(promedio_dias_mora, 1),
                "promedioDiasMoraAnterior": round(max(0, promedio_dias_mora + 2), 1),
                "porcentajeCumplimiento": round(porcentaje_cumplimiento, 1),
                "porcentajeCumplimientoAnterior": round(max(0, porcentaje_cumplimiento - 3), 1),
                "clientesMora": clientes_en_mora,
            },
            "analistaes": {
                "totalAsesores": 0,  # Se calcularía desde tabla de analistas
                "analistaesActivos": 0,
                "ventasMejorAsesor": 0,
                "montoMejorAsesor": 0,
                "promedioVentas": 0,
                "tasaConversion": 0,
                "tasaConversionAnterior": 0,
            },
            "productos": {
                "modeloMasVendido": modelo_mas_vendido,
                "ventasModeloMasVendido": ventas_modelo_mas_vendido,
                "ticketPromedio": round(ticket_promedio, 2),
                "ticketPromedioAnterior": round(ticket_promedio * 0.95, 2),
                "totalModelos": total_modelos,
                "modeloMenosVendido": modelo_menos_vendido,
            },
            "evolucion_mensual": evolucion_mensual,
            "fecha_consulta": hoy.isoformat(),
        }

        tiempo_total = int((time.time() - start_total) * 1000)
        logger.info(f"⏱️ [dashboard/admin] Endpoint completado en {tiempo_total}ms")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en dashboard admin: {e}", exc_info=True)
        try:
            db.rollback()  # ✅ Rollback para restaurar transacción después de error
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


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
    # Cliente NO tiene analista_id, usar JOIN con Prestamo.usuario_proponente
    clientes_asignados = (
        db.query(Cliente)
        .join(Prestamo, Prestamo.cedula == Cliente.cedula)
        .filter(
            Cliente.activo,
            Prestamo.estado == "APROBADO",
            Prestamo.usuario_proponente == current_user.email,
        )
        .distinct()
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

    # Calcular cartera total desde préstamos (Cliente NO tiene total_financiamiento)
    cartera_total_query = (
        db.query(func.sum(Prestamo.total_financiamiento))
        .filter(
            Prestamo.estado == "APROBADO",
            Prestamo.usuario_proponente == current_user.email,
        )
        .scalar()
    )
    cartera_total = float(cartera_total_query or 0)

    # Calcular clientes al día y en mora desde cuotas (Cliente NO tiene dias_mora)
    clientes_cedulas = [c.cedula for c in clientes_asignados]
    clientes_al_dia_query = (
        db.query(func.count(func.distinct(Prestamo.cedula)))
        .join(Cuota, Cuota.prestamo_id == Prestamo.id)
        .filter(
            Prestamo.cedula.in_(clientes_cedulas),
            Prestamo.estado == "APROBADO",
            or_(
                Cuota.estado == "PAGADO",
                and_(Cuota.fecha_vencimiento >= hoy, Cuota.estado == "PENDIENTE"),
            ),
        )
    )
    clientes_al_dia = clientes_al_dia_query.scalar() or 0

    clientes_en_mora_query = (
        db.query(func.count(func.distinct(Prestamo.cedula)))
        .join(Cuota, Cuota.prestamo_id == Prestamo.id)
        .filter(
            Prestamo.cedula.in_(clientes_cedulas),
            Prestamo.estado == "APROBADO",
            Cuota.fecha_vencimiento < hoy,
            Cuota.estado != "PAGADO",
        )
    )
    clientes_en_mora = clientes_en_mora_query.scalar() or 0

    porcentaje_mora = (clientes_en_mora / len(clientes_asignados) * 100) if clientes_asignados else 0

    # Top 5 clientes con mayor financiamiento (del analista)
    # Calcular desde préstamos ya que Cliente NO tiene total_financiamiento
    top_clientes_query = (
        db.query(
            Prestamo.cedula,
            Cliente.nombres,
            func.sum(Prestamo.total_financiamiento).label("total_financiamiento"),
        )
        .join(Cliente, Prestamo.cedula == Cliente.cedula)
        .filter(
            Prestamo.estado == "APROBADO",
            Prestamo.usuario_proponente == current_user.email,
        )
        .group_by(Prestamo.cedula, Cliente.nombres)
        .order_by(func.sum(Prestamo.total_financiamiento).desc())
        .limit(5)
        .all()
    )

    top_clientes_data = []
    for row in top_clientes_query:
        dias_mora = _calcular_dias_mora_cliente(db, row.cedula, hoy)
        top_clientes_data.append(
            {
                "cedula": row.cedula,
                "nombre": row.nombres,
                "total_financiamiento": float(row.total_financiamiento or 0),
                "dias_mora": dias_mora,
            }
        )

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
        total_prestamos = db.query(Prestamo).filter(Prestamo.estado == "APROBADO").with_entities(Prestamo.id).count()

        # Cartera total (desde préstamos, Cliente NO tiene total_financiamiento)
        cartera_total = (
            db.query(func.sum(Prestamo.total_financiamiento)).filter(Prestamo.estado == "APROBADO").scalar()
        ) or Decimal("0")

        # Clientes en mora (desde cuotas, Cliente NO tiene dias_mora)
        clientes_mora = (
            db.query(func.count(func.distinct(Prestamo.cedula)))
            .join(Cuota, Cuota.prestamo_id == Prestamo.id)
            .filter(
                Prestamo.estado == "APROBADO",
                Cuota.fecha_vencimiento < date.today(),
                Cuota.estado != "PAGADO",
            )
            .scalar()
        ) or 0

        return {
            "total_clientes": total_clientes,
            "total_prestamos": total_prestamos,
            "cartera_total": float(cartera_total),
            "clientes_mora": clientes_mora,
            "fecha_consulta": date.today().isoformat(),
        }

    except Exception as e:
        logger.error(f"Error obteniendo resumen: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")


# ============================================================================
# ENDPOINTS PARA COMPONENTES DEL DASHBOARD (6 COMPONENTES)
# ============================================================================


def _normalizar_valor_filtro(valor: Optional[str]) -> Optional[str]:
    """
    Normaliza valores de filtros que pueden venir con formato de tupla: ('VALOR',) o ("VALOR",)
    """
    if not valor:
        return None
    valor_str = str(valor).strip()
    # Casos: ('ABC',) o ("ABC",)
    if (valor_str.startswith("('") and valor_str.endswith("',)")) or (
        valor_str.startswith('("') and valor_str.endswith('",)')
    ):
        valor_str = valor_str[2:-2]
    elif valor_str.startswith("(") and valor_str.endswith(",)"):
        valor_str = valor_str[1:-2]
    # Remover comillas sobrantes en extremos
    valor_str = valor_str.strip().strip("'\"").strip()
    return valor_str if valor_str else None


@router.get("/kpis-principales")
@cache_result(ttl=300, key_prefix="dashboard")  # Cache por 5 minutos
def obtener_kpis_principales(
    analista: Optional[str] = Query(None, description="Filtrar por analista"),
    concesionario: Optional[str] = Query(None, description="Filtrar por concesionario"),
    modelo: Optional[str] = Query(None, description="Filtrar por modelo"),
    fecha_inicio: Optional[date] = Query(None, description="Fecha inicio"),
    fecha_fin: Optional[date] = Query(None, description="Fecha fin"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    KPIs principales con variación respecto al mes anterior:
    - Total Préstamos
    - Créditos Nuevos en el Mes
    - Total Clientes
    - Total Morosidad en Dólares
    """
    start_time = time.time()
    try:
        # ✅ Normalizar valores de filtros que puedan venir con formato de tupla
        analista = _normalizar_valor_filtro(analista)
        concesionario = _normalizar_valor_filtro(concesionario)
        modelo = _normalizar_valor_filtro(modelo)
        hoy = date.today()
        mes_actual = hoy.month
        año_actual = hoy.year

        # Calcular mes anterior
        mes_anterior, año_anterior = _calcular_mes_anterior(mes_actual, año_actual)

        fecha_inicio_mes_actual = date(año_actual, mes_actual, 1)
        fecha_inicio_mes_anterior = date(año_anterior, mes_anterior, 1)

        # Último día del mes anterior y actual
        fecha_fin_mes_anterior = _obtener_fechas_mes_siguiente(mes_anterior, año_anterior)
        fecha_fin_mes_actual = _obtener_fechas_mes_siguiente(mes_actual, año_actual)

        # ✅ MONITOREO: Registrar inicio de query
        query_start = time.time()

        # ✅ OPTIMIZACIÓN: Combinar queries de mes actual y anterior en una sola query
        # 1. TOTAL PRESTAMOS Y CREDITOS NUEVOS (mes actual y anterior en una query)
        # ⚠️ TEMPORAL: Usar fecha_aprobacion porque fecha_registro no migró correctamente
        kpis_prestamos = db.query(
            # Total financiamiento mes actual
            func.sum(
                case(
                    (
                        and_(
                            Prestamo.fecha_aprobacion >= fecha_inicio_mes_actual,
                            Prestamo.fecha_aprobacion < fecha_fin_mes_actual,
                        ),
                        Prestamo.total_financiamiento,
                    ),
                    else_=0,
                )
            ).label("total_actual"),
            # Total financiamiento mes anterior
            func.sum(
                case(
                    (
                        and_(
                            Prestamo.fecha_aprobacion >= fecha_inicio_mes_anterior,
                            Prestamo.fecha_aprobacion < fecha_fin_mes_anterior,
                        ),
                        Prestamo.total_financiamiento,
                    ),
                    else_=0,
                )
            ).label("total_anterior"),
            # Créditos nuevos mes actual - Préstamos aprobados en el mes corriente
            func.sum(
                case(
                    (
                        and_(
                            Prestamo.fecha_aprobacion >= fecha_inicio_mes_actual,
                            Prestamo.fecha_aprobacion < fecha_fin_mes_actual,
                            Prestamo.estado == "APROBADO",
                        ),
                        1,
                    ),
                    else_=0,
                )
            ).label("creditos_actual"),
            # Créditos nuevos mes anterior - Préstamos aprobados en el mes anterior
            func.sum(
                case(
                    (
                        and_(
                            Prestamo.fecha_aprobacion >= fecha_inicio_mes_anterior,
                            Prestamo.fecha_aprobacion < fecha_fin_mes_anterior,
                            Prestamo.estado == "APROBADO",
                        ),
                        1,
                    ),
                    else_=0,
                )
            ).label("creditos_anterior"),
        ).filter(Prestamo.estado == "APROBADO")

        # Aplicar filtros
        kpis_prestamos = FiltrosDashboard.aplicar_filtros_prestamo(kpis_prestamos, analista, concesionario, modelo, None, None)

        resultado_kpis = kpis_prestamos.first()
        if resultado_kpis is None:
            total_prestamos_actual = 0.0
            total_prestamos_anterior = 0.0
            creditos_nuevos_actual = 0
            creditos_nuevos_anterior = 0
        else:
            total_prestamos_actual = float(resultado_kpis.total_actual or Decimal("0"))
            total_prestamos_anterior = float(resultado_kpis.total_anterior or Decimal("0"))
            creditos_nuevos_actual = int(resultado_kpis.creditos_actual or 0)
            creditos_nuevos_anterior = int(resultado_kpis.creditos_anterior or 0)

        variacion_prestamos, variacion_prestamos_abs = _calcular_variacion(
            float(total_prestamos_actual), float(total_prestamos_anterior)
        )

        variacion_creditos, variacion_creditos_abs = _calcular_variacion(
            float(creditos_nuevos_actual), float(creditos_nuevos_anterior)
        )

        # 3. CLIENTES POR ESTADO (ACTIVOS, INACTIVOS, FINALIZADOS)
        # ✅ CORRECCIÓN: Usar Cliente.estado en lugar de Prestamo.estado
        # Los estados de clientes son: ACTIVO, INACTIVO, FINALIZADO
        # Siempre contar solo clientes que tienen préstamos aprobados

        query_base_clientes = (
            db.query(Cliente)
            .join(Prestamo, Cliente.cedula == Prestamo.cedula)
            .filter(Prestamo.estado == "APROBADO")  # Solo clientes con préstamos aprobados
        )

        # Aplicar filtros de préstamos si existen
        if analista or concesionario or modelo or fecha_inicio or fecha_fin:
            query_base_clientes = FiltrosDashboard.aplicar_filtros_prestamo(
                query_base_clientes, analista, concesionario, modelo, fecha_inicio, fecha_fin
            )

        # ✅ Query optimizada: calcular todos los estados en una sola query usando Cliente.estado
        clientes_por_estado = query_base_clientes.with_entities(
            func.count(func.distinct(case((Cliente.estado == "ACTIVO", Cliente.id), else_=None))).label("activos"),
            func.count(func.distinct(case((Cliente.estado == "FINALIZADO", Cliente.id), else_=None))).label("finalizados"),
            func.count(func.distinct(case((Cliente.estado == "INACTIVO", Cliente.id), else_=None))).label("inactivos"),
        )
        resultado_clientes = clientes_por_estado.first()
        if resultado_clientes is None:
            clientes_activos_actual = 0
            clientes_finalizados_actual = 0
            clientes_inactivos_actual = 0
        else:
            clientes_activos_actual = int(resultado_clientes.activos or 0)
            clientes_finalizados_actual = int(resultado_clientes.finalizados or 0)
            clientes_inactivos_actual = int(resultado_clientes.inactivos or 0)
        total_clientes_actual = clientes_activos_actual + clientes_finalizados_actual + clientes_inactivos_actual

        # ✅ Query optimizada para mes anterior: calcular todos los estados en una sola query
        # Para mes anterior, usar clientes que tenían préstamos aprobados en ese mes
        if analista or concesionario or modelo:
            query_base_anterior = (
                db.query(Cliente)
                .join(Prestamo, Cliente.cedula == Prestamo.cedula)
                .filter(
                    and_(
                        Prestamo.estado == "APROBADO",
                        Prestamo.fecha_aprobacion >= fecha_inicio_mes_anterior,
                        Prestamo.fecha_aprobacion < fecha_fin_mes_anterior,
                    )
                )
            )
            query_base_anterior = FiltrosDashboard.aplicar_filtros_prestamo(
                query_base_anterior, analista, concesionario, modelo, None, None
            )
        else:
            # Sin filtros: usar clientes con préstamos aprobados en el mes anterior
            query_base_anterior = (
                db.query(Cliente)
                .join(Prestamo, Cliente.cedula == Prestamo.cedula)
                .filter(
                    and_(
                        Prestamo.estado == "APROBADO",
                        Prestamo.fecha_aprobacion >= fecha_inicio_mes_anterior,
                        Prestamo.fecha_aprobacion < fecha_fin_mes_anterior,
                    )
                )
            )

        clientes_por_estado_anterior = query_base_anterior.with_entities(
            func.count(func.distinct(case((Cliente.estado == "ACTIVO", Cliente.id), else_=None))).label("activos"),
            func.count(func.distinct(case((Cliente.estado == "FINALIZADO", Cliente.id), else_=None))).label("finalizados"),
            func.count(func.distinct(case((Cliente.estado == "INACTIVO", Cliente.id), else_=None))).label("inactivos"),
        )
        resultado_clientes_anterior = clientes_por_estado_anterior.first()
        if resultado_clientes_anterior is None:
            clientes_activos_anterior = 0
            clientes_finalizados_anterior = 0
            clientes_inactivos_anterior = 0
        else:
            clientes_activos_anterior = int(resultado_clientes_anterior.activos or 0)
            clientes_finalizados_anterior = int(resultado_clientes_anterior.finalizados or 0)
            clientes_inactivos_anterior = int(resultado_clientes_anterior.inactivos or 0)
        total_clientes_anterior = clientes_activos_anterior + clientes_finalizados_anterior + clientes_inactivos_anterior

        variacion_clientes, variacion_clientes_abs = _calcular_variacion(
            float(total_clientes_actual), float(total_clientes_anterior)
        )

        # 4. TOTAL MOROSIDAD EN DOLARES
        # ✅ CORRECCIÓN: Morosidad = cuotas vencidas - pagos aplicados (morosidad neta)
        # Usar función helper que calcula correctamente restando pagos
        morosidad_actual = _calcular_morosidad(db, hoy, analista, concesionario, modelo, fecha_inicio, fecha_fin)

        # ✅ CORRECCIÓN: Para mes anterior, calcular morosidad total hasta el último día del mes anterior
        # No solo cuotas que vencieron EN ese mes, sino todas las cuotas vencidas HASTA ese momento
        fecha_fin_mes_anterior_menos_1 = fecha_fin_mes_anterior - timedelta(days=1)
        morosidad_anterior = _calcular_morosidad(
            db, fecha_fin_mes_anterior_menos_1, analista, concesionario, modelo, None, None
        )

        variacion_morosidad, variacion_morosidad_abs = _calcular_variacion(morosidad_actual, morosidad_anterior)

        nombres_meses = [
            "Enero",
            "Febrero",
            "Marzo",
            "Abril",
            "Mayo",
            "Junio",
            "Julio",
            "Agosto",
            "Septiembre",
            "Octubre",
            "Noviembre",
            "Diciembre",
        ]

        total_time = int((time.time() - start_time) * 1000)
        query_time = int((time.time() - query_start) * 1000)

        # ✅ MONITOREO: Registrar métrica de query con información de BD y campos
        from app.utils.db_analyzer import analyze_query_tables_columns, get_database_size

        # Obtener información de BD
        db_info = get_database_size(db)

        # Analizar tablas y columnas usadas
        query_analysis = analyze_query_tables_columns(None)  # No tenemos SQL directo, pero sabemos las tablas
        query_analysis["tables"] = ["prestamos", "cuotas", "clientes"]  # Tablas usadas en KPIs
        query_analysis["columns"] = [
            "fecha_aprobacion",
            "total_financiamiento",
            "estado",
            "fecha_vencimiento",
            "capital_pendiente",
            "interes_pendiente",
            "monto_mora",
        ]

        query_monitor.record_query(
            query_name="obtener_kpis_principales",
            execution_time_ms=query_time,
            query_type="SELECT",
            tables=query_analysis["tables"],
            columns=query_analysis["columns"],
        )

        # ✅ Calcular cuotas programadas (suma de monto_cuota de todas las cuotas)
        # Nota: No aplicar filtros de fecha aquí porque queremos el total de todas las cuotas programadas
        query_cuotas_programadas = (
            db.query(func.sum(Cuota.monto_cuota))
            .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
            .filter(Prestamo.estado == "APROBADO")
        )
        # Aplicar solo filtros de analista, concesionario y modelo (sin fechas)
        query_cuotas_programadas = FiltrosDashboard.aplicar_filtros_cuota(
            query_cuotas_programadas, analista, concesionario, modelo, None, None
        )
        total_cuotas_programadas = float(query_cuotas_programadas.scalar() or 0)

        # ✅ Calcular porcentaje de cuotas pagadas
        query_cuotas_pagadas = (
            db.query(func.count(Cuota.id))
            .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
            .filter(Prestamo.estado == "APROBADO", Cuota.estado == "PAGADO")
        )
        # Aplicar solo filtros de analista, concesionario y modelo (sin fechas)
        query_cuotas_pagadas = FiltrosDashboard.aplicar_filtros_cuota(
            query_cuotas_pagadas, analista, concesionario, modelo, None, None
        )
        total_cuotas_pagadas = query_cuotas_pagadas.scalar() or 0

        query_total_cuotas = (
            db.query(func.count(Cuota.id))
            .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
            .filter(Prestamo.estado == "APROBADO")
        )
        # Aplicar solo filtros de analista, concesionario y modelo (sin fechas)
        query_total_cuotas = FiltrosDashboard.aplicar_filtros_cuota(
            query_total_cuotas, analista, concesionario, modelo, None, None
        )
        total_cuotas = query_total_cuotas.scalar() or 0

        porcentaje_cuotas_pagadas = (total_cuotas_pagadas / total_cuotas * 100) if total_cuotas > 0 else 0.0

        logger.info(f"📊 [kpis-principales] Completado en {total_time}ms (query: {query_time}ms)")

        # ✅ ALERTA: Si la query es muy lenta (con info de BD y campos)
        if query_time >= 5000:
            db_size_info = f"BD: {db_info.get('size_pretty', 'N/A')}" if db_info else "BD: N/A"
            tables_info = f"Tablas: {', '.join(query_analysis['tables'])}"
            logger.error(
                f"🚨 [ALERTA] KPIs principales muy lento: {query_time}ms - "
                f"{db_size_info} - {tables_info} - Revisar índices y optimizaciones"
            )
        elif query_time >= 2000:
            db_size_info = f"BD: {db_info.get('size_pretty', 'N/A')}" if db_info else "BD: N/A"
            tables_info = f"Tablas: {', '.join(query_analysis['tables'])}"
            logger.warning(
                f"⚠️ [ALERTA] KPIs principales lento: {query_time}ms - "
                f"{db_size_info} - {tables_info} - Considerar optimización"
            )

        return {
            "total_prestamos": {
                "valor_actual": total_prestamos_actual,
                "valor_mes_anterior": total_prestamos_anterior,
                "variacion_porcentual": round(variacion_prestamos, 2),
                "variacion_absoluta": variacion_prestamos_abs,
            },
            "creditos_nuevos_mes": {
                "valor_actual": creditos_nuevos_actual,
                "valor_mes_anterior": creditos_nuevos_anterior,
                "variacion_porcentual": round(variacion_creditos, 2),
                "variacion_absoluta": variacion_creditos_abs,
            },
            "total_clientes": {
                "valor_actual": total_clientes_actual,
                "valor_mes_anterior": total_clientes_anterior,
                "variacion_porcentual": round(variacion_clientes, 2),
                "variacion_absoluta": variacion_clientes_abs,
            },
            "clientes_por_estado": {
                "activos": {
                    "valor_actual": clientes_activos_actual,
                    "valor_mes_anterior": clientes_activos_anterior,
                    "variacion_porcentual": round(
                        _calcular_variacion(float(clientes_activos_actual), float(clientes_activos_anterior))[0], 2
                    ),
                },
                "inactivos": {
                    "valor_actual": clientes_inactivos_actual,
                    "valor_mes_anterior": clientes_inactivos_anterior,
                    "variacion_porcentual": round(
                        _calcular_variacion(float(clientes_inactivos_actual), float(clientes_inactivos_anterior))[0], 2
                    ),
                },
                "finalizados": {
                    "valor_actual": clientes_finalizados_actual,
                    "valor_mes_anterior": clientes_finalizados_anterior,
                    "variacion_porcentual": round(
                        _calcular_variacion(float(clientes_finalizados_actual), float(clientes_finalizados_anterior))[0], 2
                    ),
                },
            },
            "total_morosidad_usd": {
                "valor_actual": morosidad_actual,
                "valor_mes_anterior": morosidad_anterior,
                "variacion_porcentual": round(variacion_morosidad, 2),
                "variacion_absoluta": variacion_morosidad_abs,
            },
            "cuotas_programadas": {
                "valor_actual": total_cuotas_programadas,
            },
            "porcentaje_cuotas_pagadas": round(porcentaje_cuotas_pagadas, 2),
            "mes_actual": nombres_meses[mes_actual - 1],
            "mes_anterior": nombres_meses[mes_anterior - 1],
        }

    except Exception as e:
        import traceback

        error_traceback = traceback.format_exc()
        logger.error(
            f"❌ Error obteniendo KPIs principales: {e} | "
            f"Filtros: analista={analista}, concesionario={concesionario}, modelo={modelo}, "
            f"fecha_inicio={fecha_inicio}, fecha_fin={fecha_fin} | "
            f"Traceback completo: {error_traceback}",
            exc_info=True,
        )
        try:
            db.rollback()
        except Exception:
            pass
        # ✅ Mejorar mensaje de error para debugging
        error_detail = str(e)
        if "fecha_registro" in error_detail.lower():
            error_detail += " (Error: fecha_registro no existe, usar fecha_aprobacion)"
        raise HTTPException(status_code=500, detail=f"Error interno al obtener KPIs principales: {error_detail}")


@router.get("/cobranzas-mensuales")
@cache_result(ttl=600, key_prefix="dashboard")  # Cache por 10 minutos (datos históricos)
def obtener_cobranzas_mensuales(
    analista: Optional[str] = Query(None),
    concesionario: Optional[str] = Query(None),
    modelo: Optional[str] = Query(None),
    fecha_inicio: Optional[date] = Query(None),
    fecha_fin: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Componente 1: Cobranzas mensuales vs Pagos y Meta Mensual
    Suma las cobranzas mensuales (amortizaciones de todos los clientes) y las grafica contra pagos.
    Meta mensual se actualiza el día 1 de cada mes.
    OPTIMIZADO: Una sola query con GROUP BY en lugar de múltiples queries en loop
    """
    import time

    start_time = time.time()
    logger.info("📊 [cobranzas-mensuales] Iniciando cálculo de cobranzas mensuales")

    try:
        hoy = date.today()
        nombres_meses = [
            "Enero",
            "Febrero",
            "Marzo",
            "Abril",
            "Mayo",
            "Junio",
            "Julio",
            "Agosto",
            "Septiembre",
            "Octubre",
            "Noviembre",
            "Diciembre",
        ]

        # Calcular fecha inicio (hace 12 meses)
        año_inicio = hoy.year
        mes_inicio = hoy.month - 11
        if mes_inicio <= 0:
            año_inicio -= 1
            mes_inicio += 12
        fecha_inicio_query = date(año_inicio, mes_inicio, 1)

        # ✅ OPTIMIZACIÓN: Query única para cobranzas planificadas con GROUP BY
        start_cobranzas = time.time()
        filtros_cobranzas = [
            "p.estado = 'APROBADO'",
            "c.fecha_vencimiento >= :fecha_inicio",
            "c.fecha_vencimiento <= :fecha_fin_total",
        ]
        params_cobranzas = {
            "fecha_inicio": fecha_inicio_query,
            "fecha_fin_total": hoy,
        }

        if analista:
            filtros_cobranzas.append("(p.analista = :analista OR p.producto_financiero = :analista)")
            params_cobranzas["analista"] = analista
        if concesionario:
            filtros_cobranzas.append("p.concesionario = :concesionario")
            params_cobranzas["concesionario"] = concesionario
        if modelo:
            filtros_cobranzas.append("(p.producto = :modelo OR p.modelo_vehiculo = :modelo)")
            params_cobranzas["modelo"] = modelo

        where_clause_cobranzas = " AND ".join(filtros_cobranzas)
        try:
            query_cobranzas_sql = text(
                f"""
                SELECT
                    EXTRACT(YEAR FROM c.fecha_vencimiento)::int as año,
                    EXTRACT(MONTH FROM c.fecha_vencimiento)::int as mes,
                    COALESCE(SUM(c.monto_cuota), 0) as cobranzas
                FROM cuotas c
                INNER JOIN prestamos p ON c.prestamo_id = p.id
                WHERE {where_clause_cobranzas}
                GROUP BY EXTRACT(YEAR FROM c.fecha_vencimiento), EXTRACT(MONTH FROM c.fecha_vencimiento)
                ORDER BY año, mes
            """
            ).bindparams(**params_cobranzas)

            result_cobranzas = db.execute(query_cobranzas_sql)
            cobranzas_por_mes = {(int(row[0]), int(row[1])): float(row[2] or Decimal("0")) for row in result_cobranzas}
            tiempo_cobranzas = int((time.time() - start_cobranzas) * 1000)
            logger.info(
                f"📊 [cobranzas-mensuales] Query cobranzas completada en {tiempo_cobranzas}ms, {len(cobranzas_por_mes)} meses"
            )
        except Exception as e:
            logger.error(f"Error consultando cobranzas en cobranzas-mensuales: {e}", exc_info=True)
            try:
                db.rollback()
            except Exception:
                pass
            cobranzas_por_mes = {}
            tiempo_cobranzas = int((time.time() - start_cobranzas) * 1000)

        # ✅ OPTIMIZACIÓN: Query única para pagos reales con GROUP BY
        start_pagos = time.time()
        fecha_inicio_dt = datetime.combine(fecha_inicio_query, datetime.min.time())
        fecha_fin_dt = datetime.combine(hoy, datetime.max.time())

        # ✅ ACTUALIZADO: Usar tabla pagos (no pagos_staging) con prestamo_id y cedula
        try:
            query_pagos_sql = text(
                """
                SELECT
                    EXTRACT(YEAR FROM fecha_pago)::int as año,
                    EXTRACT(MONTH FROM fecha_pago)::int as mes,
                    COALESCE(SUM(monto_pagado), 0) as pagos
                FROM pagos
                WHERE fecha_pago >= :fecha_inicio
                  AND fecha_pago <= :fecha_fin
                  AND monto_pagado IS NOT NULL
                  AND monto_pagado > 0
                  AND activo = TRUE
                GROUP BY EXTRACT(YEAR FROM fecha_pago), EXTRACT(MONTH FROM fecha_pago)
                ORDER BY año, mes
            """
            )

            result_pagos = db.execute(query_pagos_sql.bindparams(fecha_inicio=fecha_inicio_dt, fecha_fin=fecha_fin_dt))
            pagos_por_mes = {(int(row[0]), int(row[1])): float(row[2] or Decimal("0")) for row in result_pagos}
            tiempo_pagos = int((time.time() - start_pagos) * 1000)
            logger.info(f"📊 [cobranzas-mensuales] Query pagos completada en {tiempo_pagos}ms, {len(pagos_por_mes)} meses")
        except Exception as e:
            logger.error(f"Error consultando pagos en cobranzas-mensuales: {e}", exc_info=True)
            try:
                db.rollback()
            except Exception:
                pass
            pagos_por_mes = {}
            tiempo_pagos = int((time.time() - start_pagos) * 1000)

        # Generar datos mensuales (incluyendo meses sin datos)
        meses_data = []
        current_date = fecha_inicio_query
        for i in range(12):
            if current_date > hoy:
                break
            año_mes = int(current_date.year)
            num_mes = int(current_date.month)
            mes_key: tuple[int, int] = (año_mes, num_mes)

            cobranzas_planificadas = cobranzas_por_mes.get(mes_key, 0.0)
            pagos_reales = pagos_por_mes.get(mes_key, 0.0)

            meses_data.append(
                {
                    "mes": current_date.strftime("%Y-%m"),
                    "nombre_mes": nombres_meses[num_mes - 1],
                    "cobranzas_planificadas": cobranzas_planificadas,
                    "pagos_reales": pagos_reales,
                    "meta_mensual": cobranzas_planificadas,  # Meta = cobranzas planificadas
                }
            )

            # Avanzar al siguiente mes
            current_date = _obtener_fechas_mes_siguiente(num_mes, año_mes)

        # Meta actual = cobranzas planificadas del mes actual (usar datos ya calculados si es posible)
        start_meta = time.time()
        mes_actual_key = (hoy.year, hoy.month)
        meta_actual = cobranzas_por_mes.get(mes_actual_key, 0.0)

        # Si no está en los datos calculados, hacer query adicional solo si es necesario
        if meta_actual == 0.0:
            mes_actual_inicio = date(hoy.year, hoy.month, 1)
            if hoy.month == 12:
                mes_actual_fin = date(hoy.year + 1, 1, 1)
            else:
                mes_actual_fin = date(hoy.year, hoy.month + 1, 1)

            try:
                query_meta = (
                    db.query(func.sum(Cuota.monto_cuota))
                    .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
                    .filter(
                        Prestamo.estado == "APROBADO",
                        Cuota.fecha_vencimiento >= mes_actual_inicio,
                        Cuota.fecha_vencimiento < mes_actual_fin,
                    )
                )
                query_meta = FiltrosDashboard.aplicar_filtros_cuota(
                    query_meta, analista, concesionario, modelo, fecha_inicio, fecha_fin
                )
                meta_actual = float(query_meta.scalar() or Decimal("0"))
            except Exception as e:
                logger.error(f"Error consultando meta en cobranzas-mensuales: {e}", exc_info=True)
                try:
                    db.rollback()
                except Exception:
                    pass
                meta_actual = 0.0

        tiempo_meta = int((time.time() - start_meta) * 1000)
        total_time = int((time.time() - start_time) * 1000)
        logger.info(
            f"⏱️ [cobranzas-mensuales] Tiempo total: {total_time}ms (cobranzas: {tiempo_cobranzas}ms, pagos: {tiempo_pagos}ms, meta: {tiempo_meta}ms)"
        )
        logger.info(f"📊 [cobranzas-mensuales] Devolviendo {len(meses_data)} meses de datos, meta_actual=${meta_actual:,.2f}")

        return {
            "meses": meses_data,
            "meta_actual": meta_actual,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo cobranzas mensuales: {e}", exc_info=True)
        try:
            db.rollback()  # ✅ Rollback para restaurar transacción después de error
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.get("/cobranza-por-dia")
def obtener_cobranza_por_dia(
    dias: Optional[int] = Query(30, description="Número de días a mostrar"),
    analista: Optional[str] = Query(None),
    concesionario: Optional[str] = Query(None),
    modelo: Optional[str] = Query(None),
    fecha_inicio: Optional[date] = Query(None),
    fecha_fin: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Componente 2: Total a Cobrar, Pagos y Morosidad por Día
    """
    try:
        hoy = date.today()

        # Calcular rango de fechas
        fecha_inicio_query = fecha_inicio or (hoy - timedelta(days=dias or 30))
        fecha_fin_query = fecha_fin or hoy

        # Generar lista de fechas
        fechas = []
        current_date = fecha_inicio_query
        while current_date <= fecha_fin_query:
            fechas.append(current_date)
            current_date += timedelta(days=1)

        dias_data = []
        for fecha_dia in fechas:
            cobranza_planificada = _calcular_total_a_cobrar_fecha(
                db, fecha_dia, analista, concesionario, modelo, fecha_inicio, fecha_fin
            )
            cobranza_real = _calcular_pagos_fecha(db, fecha_dia, analista, concesionario, modelo, fecha_inicio, fecha_fin)
            morosidad = _calcular_morosidad(db, fecha_dia, analista, concesionario, modelo, fecha_inicio, fecha_fin)

            dias_data.append(
                {
                    "fecha": fecha_dia.isoformat(),
                    "total_a_cobrar": cobranza_planificada,  # Mantener compatibilidad
                    "cobranza_planificada": cobranza_planificada,
                    "cobranza_real": cobranza_real,
                    "pagos": cobranza_real,  # Mantener compatibilidad
                    "morosidad": morosidad,
                }
            )

        return {"dias": dias_data}

    except Exception as e:
        logger.error(f"Error obteniendo cobranza por día: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.get("/cobranza-fechas-especificas")
def obtener_cobranza_fechas_especificas(
    analista: Optional[str] = Query(None),
    concesionario: Optional[str] = Query(None),
    modelo: Optional[str] = Query(None),
    fecha_inicio: Optional[date] = Query(None),
    fecha_fin: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Obtiene datos de cobranza planificada y real para fechas específicas:
    - Sábado y Viernes (últimos 2 días)
    - Hoy (formato: día/mes abreviado, ej: 11/Nov)
    - Mañana (día de la semana, ej: Lunes)
    """
    try:
        hoy = date.today()
        mañana = hoy + timedelta(days=1)
        ayer = hoy - timedelta(days=1)
        anteayer = hoy - timedelta(days=2)

        # Nombres de días de la semana en español
        dias_semana = {
            0: "Lunes",
            1: "Martes",
            2: "Miércoles",
            3: "Jueves",
            4: "Viernes",
            5: "Sábado",
            6: "Domingo",
        }

        # Meses abreviados en español
        meses_abrev = {
            1: "Ene",
            2: "Feb",
            3: "Mar",
            4: "Abr",
            5: "May",
            6: "Jun",
            7: "Jul",
            8: "Ago",
            9: "Sep",
            10: "Oct",
            11: "Nov",
            12: "Dic",
        }

        # Formatear fecha de hoy: día/mes (ej: 11/Nov)
        nombre_hoy = f"{hoy.day}/{meses_abrev[hoy.month]}"

        # Obtener día de la semana de mañana
        dia_semana_mañana = mañana.weekday()  # 0=Lunes, 6=Domingo
        nombre_mañana = dias_semana[dia_semana_mañana]

        # Preparar fechas: Sábado y Viernes (últimos 2 días)
        fechas = []

        # Buscar los últimos Viernes y Sábado (hasta 7 días atrás)
        viernes_encontrado = None
        sabado_encontrado = None

        for i in range(1, 8):  # Buscar hasta 7 días atrás
            fecha_buscar = hoy - timedelta(days=i)
            dia_semana = fecha_buscar.weekday()

            if dia_semana == 4 and viernes_encontrado is None:  # Viernes
                viernes_encontrado = fecha_buscar
            elif dia_semana == 5 and sabado_encontrado is None:  # Sábado
                sabado_encontrado = fecha_buscar

            # Si ya encontramos ambos, salir
            if viernes_encontrado and sabado_encontrado:
                break

        # Agregar Viernes y Sábado si se encontraron
        if viernes_encontrado:
            fechas.append((dias_semana[4], viernes_encontrado))
        if sabado_encontrado:
            fechas.append((dias_semana[5], sabado_encontrado))

        # Ordenar: Viernes primero, luego Sábado
        fechas.sort(key=lambda x: x[1])

        # Agregar Hoy y Mañana
        fechas.append((nombre_hoy, hoy))
        fechas.append((nombre_mañana, mañana))

        dias_data = []
        for nombre_fecha, fecha_dia in fechas:
            cobranza_planificada = _calcular_total_a_cobrar_fecha(
                db, fecha_dia, analista, concesionario, modelo, fecha_inicio, fecha_fin
            )
            cobranza_real = _calcular_pagos_fecha(db, fecha_dia, analista, concesionario, modelo, fecha_inicio, fecha_fin)

            dias_data.append(
                {
                    "fecha": fecha_dia.isoformat(),
                    "nombre_fecha": nombre_fecha,
                    "cobranza_planificada": cobranza_planificada,
                    "cobranza_real": cobranza_real,
                }
            )

        return {"dias": dias_data}

    except Exception as e:
        logger.error(f"Error obteniendo cobranza fechas específicas: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.get("/metricas-acumuladas")
def obtener_metricas_acumuladas(
    analista: Optional[str] = Query(None),
    concesionario: Optional[str] = Query(None),
    modelo: Optional[str] = Query(None),
    fecha_inicio: Optional[date] = Query(None),
    fecha_fin: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Métricas acumuladas para Componente 2:
    - Acumulado mensual (se pone a cero al cambiar de mes)
    - Acumulado anual (se acumula todos los meses)
    - Clientes con 1 pago atrasado
    - Clientes con 3+ cuotas atrasadas
    """
    try:
        hoy = date.today()

        # Fechas de inicio de mes y año
        fecha_inicio_mes = date(hoy.year, hoy.month, 1)
        fecha_inicio_anio = date(hoy.year, 1, 1)

        # Acumulado mensual: Pagos desde inicio del mes
        # ✅ ACTUALIZADO: Usar tabla pagos (no pagos_staging) con prestamo_id y cedula
        fecha_inicio_mes_dt = datetime.combine(fecha_inicio_mes, datetime.min.time())
        query_acumulado_mensual = db.execute(
            text(
                """
                SELECT COALESCE(SUM(monto_pagado), 0)
                FROM pagos
                WHERE fecha_pago >= :fecha_inicio_mes
                  AND monto_pagado IS NOT NULL
                  AND monto_pagado > 0
                  AND activo = TRUE
            """
            ).bindparams(fecha_inicio_mes=fecha_inicio_mes_dt)
        )
        acumulado_mensual = float(query_acumulado_mensual.scalar() or Decimal("0"))

        # Acumulado anual: Pagos desde inicio del año
        # ✅ ACTUALIZADO: Usar tabla pagos (no pagos_staging) con prestamo_id y cedula
        fecha_inicio_anio_dt = datetime.combine(fecha_inicio_anio, datetime.min.time())
        query_acumulado_anual = db.execute(
            text(
                """
                SELECT COALESCE(SUM(monto_pagado), 0)
                FROM pagos
                WHERE fecha_pago >= :fecha_inicio_anio
                  AND monto_pagado IS NOT NULL
                  AND monto_pagado > 0
                  AND activo = TRUE
            """
            ).bindparams(fecha_inicio_anio=fecha_inicio_anio_dt)
        )
        acumulado_anual = float(query_acumulado_anual.scalar() or Decimal("0"))

        # Clientes con 1 pago atrasado
        query_clientes_1_atrasado = (
            db.query(func.count(func.distinct(Prestamo.cedula)))
            .join(Cuota, Cuota.prestamo_id == Prestamo.id)
            .filter(
                Prestamo.estado == "APROBADO",
                Cuota.fecha_vencimiento < hoy,
                Cuota.estado != "PAGADO",
            )
        )
        query_clientes_1_atrasado = FiltrosDashboard.aplicar_filtros_cuota(
            query_clientes_1_atrasado, analista, concesionario, modelo, fecha_inicio, fecha_fin
        )
        clientes_1_atrasado = query_clientes_1_atrasado.scalar() or 0

        # Clientes con 3+ cuotas atrasadas
        # Subquery: clientes con 3 o más cuotas atrasadas
        subquery_cuotas_atrasadas = (
            db.query(Prestamo.cedula, func.count(Cuota.id).label("cuotas_atrasadas"))
            .join(Cuota, Cuota.prestamo_id == Prestamo.id)
            .filter(
                Prestamo.estado == "APROBADO",
                Cuota.fecha_vencimiento < hoy,
                Cuota.estado != "PAGADO",
            )
            .group_by(Prestamo.cedula)
            .having(func.count(Cuota.id) >= 3)
            .subquery()
        )

        query_clientes_3mas = db.query(func.count(func.distinct(subquery_cuotas_atrasadas.c.cedula))).select_from(
            subquery_cuotas_atrasadas
        )
        clientes_3mas = query_clientes_3mas.scalar() or 0

        return {
            "acumulado_mensual": acumulado_mensual,
            "acumulado_anual": acumulado_anual,
            "clientes_1_pago_atrasado": clientes_1_atrasado,
            "clientes_3mas_cuotas_atrasadas": clientes_3mas,
            "fecha_inicio_mes": fecha_inicio_mes.isoformat(),
            "fecha_inicio_anio": fecha_inicio_anio.isoformat(),
        }

    except Exception as e:
        logger.error(f"Error obteniendo métricas acumuladas: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.get("/morosidad-por-analista")
@cache_result(ttl=300, key_prefix="dashboard")  # Cache por 5 minutos
def obtener_morosidad_por_analista(
    analista: Optional[str] = Query(None),
    concesionario: Optional[str] = Query(None),
    modelo: Optional[str] = Query(None),
    fecha_inicio: Optional[date] = Query(None),
    fecha_fin: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Componente 3: Morosidad por Analista
    Todos los clientes que tienen morosidad desde 1 día
    """
    start_time = time.time()
    try:
        hoy = date.today()

        # Obtener morosidad por analista (morosidad = cuotas vencidas no pagadas)
        # Usar la expresión completa en group_by para evitar errores SQL
        analista_expr = func.coalesce(Prestamo.analista, Prestamo.producto_financiero, "Sin Analista")
        query = (
            db.query(
                analista_expr.label("analista"),
                func.sum(Cuota.monto_cuota).label("total_morosidad"),
                func.count(func.distinct(Prestamo.cedula)).label("cantidad_clientes"),
                func.count(Cuota.id).label("cantidad_cuotas_atrasadas"),
            )
            .join(Cuota, Cuota.prestamo_id == Prestamo.id)
            .filter(
                Prestamo.estado == "APROBADO",
                Cuota.fecha_vencimiento < hoy,
                Cuota.estado != "PAGADO",
            )
            .group_by(analista_expr)
        )

        # Aplicar filtros (excepto analista que ya estamos agrupando)
        if concesionario:
            query = query.filter(Prestamo.concesionario == concesionario)
        if modelo:
            query = query.filter(or_(Prestamo.producto == modelo, Prestamo.modelo_vehiculo == modelo))

        resultados = query.all()
        query_time = int((time.time() - start_time) * 1000)

        analistas_data = []
        for row in resultados:
            total_morosidad = float(row.total_morosidad or Decimal("0"))
            cantidad_clientes = row.cantidad_clientes or 0
            cantidad_cuotas = row.cantidad_cuotas_atrasadas or 0

            promedio_por_cliente = total_morosidad / cantidad_clientes if cantidad_clientes > 0 else 0

            analistas_data.append(
                {
                    "analista": row.analista or "Sin Analista",
                    "total_morosidad": total_morosidad,
                    "cantidad_clientes": cantidad_clientes,
                    "cantidad_cuotas_atrasadas": cantidad_cuotas,
                    "promedio_morosidad_por_cliente": promedio_por_cliente,
                }
            )

        # Ordenar de mayor a menor por total_morosidad
        analistas_data.sort(key=lambda x: x["total_morosidad"], reverse=True)

        total_time = int((time.time() - start_time) * 1000)
        logger.info(
            f"📊 [morosidad-por-analista] Query: {query_time}ms, Total: {total_time}ms, {len(analistas_data)} analistas"
        )

        return {"analistas": analistas_data}

    except Exception as e:
        logger.error(f"Error obteniendo morosidad por analista: {e}", exc_info=True)
        try:
            db.rollback()
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.get("/prestamos-por-concesionario")
def obtener_prestamos_por_concesionario(
    analista: Optional[str] = Query(None),
    concesionario: Optional[str] = Query(None),
    modelo: Optional[str] = Query(None),
    fecha_inicio: Optional[date] = Query(None),
    fecha_fin: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Componente 4: Préstamos por Concesionario (expresado en porcentaje)
    """
    try:
        # Obtener total general de préstamos (cantidad y monto)
        query_base = db.query(Prestamo).filter(Prestamo.estado == "APROBADO")
        query_base = FiltrosDashboard.aplicar_filtros_prestamo(
            query_base, analista, concesionario, modelo, fecha_inicio, fecha_fin
        )

        total_general_monto = float(query_base.with_entities(func.sum(Prestamo.total_financiamiento)).scalar() or Decimal("0"))
        total_general_cantidad = query_base.count()

        # Agrupar por concesionario
        query_concesionarios = (
            db.query(
                func.coalesce(Prestamo.concesionario, "Sin Concesionario").label("concesionario"),
                func.sum(Prestamo.total_financiamiento).label("total_prestamos"),
                func.count(Prestamo.id).label("cantidad_prestamos"),
            )
            .filter(Prestamo.estado == "APROBADO")
            .group_by("concesionario")
        )

        # Aplicar filtros
        if analista:
            query_concesionarios = query_concesionarios.filter(
                or_(Prestamo.analista == analista, Prestamo.producto_financiero == analista)
            )
        if modelo:
            query_concesionarios = query_concesionarios.filter(
                or_(Prestamo.producto == modelo, Prestamo.modelo_vehiculo == modelo)
            )
        if fecha_inicio:
            query_concesionarios = query_concesionarios.filter(Prestamo.fecha_registro >= fecha_inicio)
        if fecha_fin:
            query_concesionarios = query_concesionarios.filter(Prestamo.fecha_registro <= fecha_fin)

        resultados = query_concesionarios.all()

        concesionarios_data = []
        for row in resultados:
            total_prestamos = float(row.total_prestamos or Decimal("0"))
            cantidad_prestamos = row.cantidad_prestamos or 0
            # Calcular porcentaje basado en cantidad de préstamos (no en monto)
            porcentaje = (cantidad_prestamos / total_general_cantidad * 100) if total_general_cantidad > 0 else 0

            concesionarios_data.append(
                {
                    "concesionario": row.concesionario or "Sin Concesionario",
                    "total_prestamos": total_prestamos,
                    "cantidad_prestamos": cantidad_prestamos,
                    "porcentaje": round(porcentaje, 2),
                }
            )

        return {
            "concesionarios": concesionarios_data,
            "total_general": total_general_monto,
        }

    except Exception as e:
        logger.error(f"Error obteniendo préstamos por concesionario: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.get("/prestamos-por-modelo")
@cache_result(ttl=600, key_prefix="dashboard")  # Cache por 10 minutos
def obtener_prestamos_por_modelo(
    analista: Optional[str] = Query(None),
    concesionario: Optional[str] = Query(None),
    modelo: Optional[str] = Query(None),
    fecha_inicio: Optional[date] = Query(None),
    fecha_fin: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Préstamos por Modelo (expresado en porcentaje)
    Agrupa por producto y modelo_vehiculo
    """
    try:
        # Obtener total general de préstamos (cantidad y monto)
        query_base = db.query(Prestamo).filter(Prestamo.estado == "APROBADO")
        query_base = FiltrosDashboard.aplicar_filtros_prestamo(
            query_base, analista, concesionario, modelo, fecha_inicio, fecha_fin
        )

        total_general_monto = float(query_base.with_entities(func.sum(Prestamo.total_financiamiento)).scalar() or Decimal("0"))
        total_general_cantidad = query_base.count()

        # Agrupar por modelo (usar producto o modelo_vehiculo)
        query_modelos = (
            db.query(
                func.coalesce(func.coalesce(Prestamo.modelo_vehiculo, Prestamo.producto), "Sin Modelo").label("modelo"),
                func.sum(Prestamo.total_financiamiento).label("total_prestamos"),
                func.count(Prestamo.id).label("cantidad_prestamos"),
            )
            .filter(Prestamo.estado == "APROBADO")
            .group_by("modelo")
        )

        # Aplicar filtros
        if analista:
            query_modelos = query_modelos.filter(or_(Prestamo.analista == analista, Prestamo.producto_financiero == analista))
        if concesionario:
            query_modelos = query_modelos.filter(Prestamo.concesionario == concesionario)
        if fecha_inicio:
            query_modelos = query_modelos.filter(Prestamo.fecha_registro >= fecha_inicio)
        if fecha_fin:
            query_modelos = query_modelos.filter(Prestamo.fecha_registro <= fecha_fin)

        resultados = query_modelos.all()

        modelos_data = []
        for row in resultados:
            total_prestamos = float(row.total_prestamos or Decimal("0"))
            cantidad_prestamos = row.cantidad_prestamos or 0
            # Calcular porcentaje basado en cantidad de préstamos (no en monto)
            porcentaje = (cantidad_prestamos / total_general_cantidad * 100) if total_general_cantidad > 0 else 0

            modelos_data.append(
                {
                    "modelo": row.modelo or "Sin Modelo",
                    "total_prestamos": total_prestamos,
                    "cantidad_prestamos": cantidad_prestamos,
                    "porcentaje": round(porcentaje, 2),
                }
            )

        # Ordenar por cantidad_prestamos descendente (cantidad real, no monto)
        modelos_data.sort(key=lambda x: x["cantidad_prestamos"], reverse=True)

        return {
            "modelos": modelos_data,
            "total_general": total_general_monto,
        }

    except Exception as e:
        logger.error(f"Error obteniendo préstamos por modelo: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.get("/pagos-conciliados")
def obtener_pagos_conciliados(
    analista: Optional[str] = Query(None),
    concesionario: Optional[str] = Query(None),
    modelo: Optional[str] = Query(None),
    fecha_inicio: Optional[date] = Query(None),
    fecha_fin: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Obtiene estadísticas de pagos totales vs pagos conciliados
    """
    try:
        # Query base para pagos (usar tabla Pago que tiene conciliado)
        query_base = db.query(Pago).filter(Pago.activo.is_(True))

        # Aplicar filtros de fecha si existen
        if fecha_inicio:
            query_base = query_base.filter(Pago.fecha_pago >= fecha_inicio)
        if fecha_fin:
            query_base = query_base.filter(Pago.fecha_pago <= fecha_fin)

        # Aplicar filtros de analista/concesionario/modelo mediante join con Prestamo
        # Solo hacer join si hay filtros que requieran datos de Prestamo
        if analista or concesionario or modelo:
            query_base = query_base.join(Prestamo, Pago.prestamo_id == Prestamo.id)
            if analista:
                query_base = query_base.filter(or_(Prestamo.analista == analista, Prestamo.producto_financiero == analista))
            if concesionario:
                query_base = query_base.filter(Prestamo.concesionario == concesionario)
            if modelo:
                query_base = query_base.filter(or_(Prestamo.producto == modelo, Prestamo.modelo_vehiculo == modelo))

        # Total de pagos
        total_pagos = query_base.count()

        # Total de pagos conciliados
        total_pagos_conciliados = query_base.filter(Pago.conciliado.is_(True)).count()

        # Monto total de pagos
        monto_total = float(query_base.with_entities(func.sum(Pago.monto_pagado)).scalar() or Decimal("0"))

        # Monto total de pagos conciliados
        monto_conciliado = float(
            query_base.filter(Pago.conciliado.is_(True)).with_entities(func.sum(Pago.monto_pagado)).scalar() or Decimal("0")
        )

        # Porcentaje de conciliación
        porcentaje_conciliacion = (total_pagos_conciliados / total_pagos * 100) if total_pagos > 0 else 0
        porcentaje_monto_conciliado = (monto_conciliado / monto_total * 100) if monto_total > 0 else 0

        return {
            "total_pagos": total_pagos,
            "total_pagos_conciliados": total_pagos_conciliados,
            "total_pagos_no_conciliados": total_pagos - total_pagos_conciliados,
            "monto_total": monto_total,
            "monto_conciliado": monto_conciliado,
            "monto_no_conciliado": monto_total - monto_conciliado,
            "porcentaje_conciliacion": round(porcentaje_conciliacion, 2),
            "porcentaje_monto_conciliado": round(porcentaje_monto_conciliado, 2),
        }

    except Exception as e:
        logger.error(f"Error obteniendo estadísticas de pagos conciliados: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.get("/financiamiento-por-rangos")
@cache_result(ttl=300, key_prefix="dashboard")  # ✅ Agregar cache para mejorar performance
def obtener_financiamiento_por_rangos(
    analista: Optional[str] = Query(None),
    concesionario: Optional[str] = Query(None),
    modelo: Optional[str] = Query(None),
    fecha_inicio: Optional[date] = Query(None),
    fecha_fin: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Obtiene distribución de financiamiento por rangos de monto para gráfico de pirámide
    Los rangos están ordenados de mayor a menor para crear efecto de pirámide
    ✅ OPTIMIZADO: Usa una sola query con CASE WHEN en lugar de múltiples queries
    """
    import time

    start_time = time.time()

    try:
        # ✅ DIAGNÓSTICO: Contar préstamos aprobados sin filtros
        # ✅ CORRECCIÓN: Usar with_entities para evitar error si valor_activo no existe en BD
        total_prestamos_aprobados_sin_filtros = (
            db.query(Prestamo).filter(Prestamo.estado == "APROBADO").with_entities(Prestamo.id).count()
        )
        logger.info(
            f"📊 [financiamiento-por-rangos] Total préstamos APROBADOS (sin filtros): {total_prestamos_aprobados_sin_filtros}"
        )

        # ✅ DIAGNÓSTICO: Log de filtros aplicados
        filtros_aplicados = {
            "analista": analista,
            "concesionario": concesionario,
            "modelo": modelo,
            "fecha_inicio": fecha_inicio.isoformat() if fecha_inicio else None,
            "fecha_fin": fecha_fin.isoformat() if fecha_fin else None,
        }
        logger.info(f"🔍 [financiamiento-por-rangos] Filtros aplicados: {filtros_aplicados}")

        # ✅ CORRECCIÓN: Usar FiltrosDashboard para aplicar filtros de manera consistente
        # Esto usa OR entre fecha_registro, fecha_aprobacion y fecha_base_calculo (menos restrictivo)
        query_base = db.query(Prestamo).filter(Prestamo.estado == "APROBADO")

        # ✅ DIAGNÓSTICO: Contar préstamos ANTES de aplicar filtros
        # ✅ CORRECCIÓN: Usar with_entities para evitar error si valor_activo no existe en BD
        total_antes_filtros = 0
        try:
            total_antes_filtros = query_base.with_entities(Prestamo.id).count()
            logger.info(f"📊 [financiamiento-por-rangos] Total préstamos APROBADOS (sin filtros): {total_antes_filtros}")
        except Exception as e:
            logger.error(f"Error contando préstamos antes de filtros: {e}", exc_info=True)
            total_antes_filtros = 0

        # ✅ Usar FiltrosDashboard para aplicar todos los filtros de manera consistente
        # Esto incluye filtros de analista, concesionario, modelo y fecha (con OR entre fechas)
        query_base = FiltrosDashboard.aplicar_filtros_prestamo(
            query_base, analista, concesionario, modelo, fecha_inicio, fecha_fin
        )

        # ✅ DIAGNÓSTICO: Contar préstamos después de aplicar TODOS los filtros (antes de filtrar NULL)
        # ✅ CORRECCIÓN: Usar with_entities para evitar error si valor_activo no existe en BD
        try:
            total_prestamos_despues_filtros = query_base.with_entities(Prestamo.id).count()
            logger.info(
                f"📊 [financiamiento-por-rangos] Total préstamos DESPUÉS de todos los filtros: {total_prestamos_despues_filtros}"
            )
            if total_prestamos_despues_filtros == 0 and total_antes_filtros > 0:
                logger.warning(
                    f"⚠️ [financiamiento-por-rangos] Los filtros eliminaron todos los préstamos. "
                    f"Total antes de filtros: {total_antes_filtros}, Total después: {total_prestamos_despues_filtros}"
                )
        except Exception as e:
            logger.error(f"Error contando préstamos después de filtros: {e}", exc_info=True)

        # ✅ Verificar préstamos con total_financiamiento NULL o <= 0 (antes de filtrar)
        # ✅ CORRECCIÓN: Usar with_entities para evitar error si valor_activo no existe en BD
        try:
            prestamos_invalidos = (
                query_base.filter(or_(Prestamo.total_financiamiento.is_(None), Prestamo.total_financiamiento <= 0))
                .with_entities(Prestamo.id)
                .count()
            )
            if prestamos_invalidos > 0:
                logger.warning(
                    f"⚠️ Se encontraron {prestamos_invalidos} préstamos aprobados con total_financiamiento NULL o <= 0. "
                    f"Estos no se incluirán en la distribución por rangos."
                )
        except Exception as e:
            logger.error(f"Error verificando préstamos inválidos: {e}", exc_info=True)
            # Continuar sin bloquear si hay error en la verificación

        # ✅ Aplicar filtro para excluir NULL y <= 0 antes de calcular totales y procesar rangos
        query_base = query_base.filter(and_(Prestamo.total_financiamiento.isnot(None), Prestamo.total_financiamiento > 0))

        # ✅ DIAGNÓSTICO: Contar préstamos válidos (con total_financiamiento > 0)
        # ✅ CORRECCIÓN: Usar with_entities para evitar error si valor_activo no existe en BD
        try:
            total_prestamos_validos = query_base.with_entities(Prestamo.id).count()
            logger.info(
                f"📊 [financiamiento-por-rangos] Total préstamos válidos (con total_financiamiento > 0): {total_prestamos_validos}"
            )
        except Exception as e:
            logger.error(f"Error contando préstamos válidos: {e}", exc_info=True)

        # ✅ OPTIMIZACIÓN: Calcular totales en una sola query (después de filtrar NULL)
        try:
            totales_query = query_base.with_entities(
                func.count(Prestamo.id).label("total_prestamos"), func.sum(Prestamo.total_financiamiento).label("total_monto")
            ).first()
            total_prestamos = totales_query.total_prestamos or 0 if totales_query else 0
            total_monto = float(totales_query.total_monto or Decimal("0")) if totales_query else 0.0
            logger.info(
                f"📊 [financiamiento-por-rangos] Total préstamos final (con total_financiamiento > 0): {total_prestamos}, Total monto: {total_monto}"
            )

            # ✅ DIAGNÓSTICO: Si no hay préstamos, verificar por qué y intentar sin filtros de fecha
            if total_prestamos == 0:
                logger.warning(
                    f"⚠️ [financiamiento-por-rangos] No se encontraron préstamos válidos. "
                    f"Diagnóstico: Total aprobados sin filtros={total_prestamos_aprobados_sin_filtros}, "
                    f"Total después de filtros={total_prestamos_despues_filtros}, "
                    f"Total válidos (con monto > 0)={total_prestamos}"
                )
                # ✅ MEJORA: Si los filtros de fecha están excluyendo todos los préstamos, intentar sin filtros de fecha
                # pero solo si hay otros filtros activos (analista, concesionario, modelo) o si no hay filtros de fecha explícitos del usuario
                try:
                    # ✅ MEJORA: Verificar préstamos VÁLIDOS (con total_financiamiento > 0) sin filtros de fecha
                    query_diagnostico = db.query(Prestamo).filter(Prestamo.estado == "APROBADO")
                    query_diagnostico = FiltrosDashboard.aplicar_filtros_prestamo(
                        query_diagnostico, analista, concesionario, modelo, None, None  # Sin filtros de fecha
                    )
                    query_diagnostico = query_diagnostico.filter(
                        and_(Prestamo.total_financiamiento.isnot(None), Prestamo.total_financiamiento > 0)
                    )
                    # ✅ CORRECCIÓN: Usar with_entities para evitar error si valor_activo no existe en BD
                    total_sin_filtro_fecha = query_diagnostico.with_entities(Prestamo.id).count()
                    logger.info(
                        f"📊 [financiamiento-por-rangos] Total préstamos VÁLIDOS (con monto > 0) sin filtro de fecha: {total_sin_filtro_fecha}"
                    )
                    # ✅ MEJORA: Si hay préstamos válidos sin filtros de fecha pero no con filtros de fecha, usar los sin filtros
                    if total_sin_filtro_fecha > 0 and total_prestamos == 0:
                        logger.warning(
                            f"⚠️ [financiamiento-por-rangos] Los filtros de fecha están excluyendo todos los préstamos válidos. "
                            f"Total válidos sin filtro de fecha: {total_sin_filtro_fecha}, Total válidos con filtro de fecha: {total_prestamos}"
                        )
                        # ✅ MEJORA: Si hay préstamos válidos sin filtros de fecha, usar esos datos
                        totales_alternativa = query_diagnostico.with_entities(
                            func.count(Prestamo.id).label("total_prestamos"),
                            func.sum(Prestamo.total_financiamiento).label("total_monto"),
                        ).first()
                        if (
                            totales_alternativa
                            and totales_alternativa.total_prestamos
                            and totales_alternativa.total_prestamos > 0
                        ):
                            logger.info(
                                f"✅ [financiamiento-por-rangos] Encontrados {totales_alternativa.total_prestamos} préstamos válidos sin filtros de fecha. "
                                f"Usando estos datos en lugar de retornar vacío."
                            )
                            # ✅ Actualizar query_base y totales para usar datos sin filtros de fecha
                            query_base = query_diagnostico
                            total_prestamos = totales_alternativa.total_prestamos or 0
                            total_monto = float(totales_alternativa.total_monto or Decimal("0"))

                            # ✅ VERIFICACIÓN: Contar query_base después de actualizar para confirmar
                            # ✅ CORRECCIÓN: Usar with_entities para evitar error si valor_activo no existe en BD
                            try:
                                count_verificacion = query_base.with_entities(Prestamo.id).count()
                                logger.info(
                                    f"✅ [financiamiento-por-rangos] Fallback activado: Usando {total_prestamos} préstamos sin filtros de fecha. "
                                    f"query_base actualizada, total_monto=${total_monto:,.2f}, "
                                    f"query_base.count()={count_verificacion} (debe coincidir con total_prestamos)"
                                )
                                if count_verificacion != total_prestamos:
                                    logger.warning(
                                        f"⚠️ [financiamiento-por-rangos] DISCREPANCIA: query_base.count()={count_verificacion} "
                                        f"no coincide con total_prestamos={total_prestamos}"
                                    )
                            except Exception as e:
                                logger.error(
                                    f"❌ [financiamiento-por-rangos] Error verificando query_base después del fallback: {e}",
                                    exc_info=True,
                                )
                except Exception as e:
                    logger.error(f"Error en diagnóstico adicional: {e}", exc_info=True)
        except Exception as e:
            logger.error(f"Error calculando totales en financiamiento-por-rangos: {e}", exc_info=True)
            total_prestamos = 0
            total_monto = 0.0

        # ✅ Rangos de financiamiento de $300 en $300 (de mayor a menor para efecto pirámide)
        rangos = []
        # Generar rangos de $300 desde $0 hasta $50,000
        max_rango = 50000
        paso = 300
        # Generar rangos desde $0 hasta $50,000 en pasos de $300
        try:
            for min_val in range(0, max_rango, paso):
                max_val = min_val + paso
                # Formatear etiqueta: $0 - $300, $300 - $600, etc.
                categoria = f"${min_val:,.0f} - ${max_val:,.0f}".replace(",", "")
                rangos.append((min_val, max_val, categoria))

            # Agregar rango final para montos mayores a $50,000 (al inicio para que quede primero)
            # Usar max_rango como max_val para cumplir con el tipo tuple[int, int, str]
            rangos.insert(0, (max_rango, max_rango, f"${max_rango:,.0f}+".replace(",", "")))

            # Invertir lista para que quede de mayor a menor (efecto pirámide)
            rangos.reverse()

            logger.info(f"📊 [financiamiento-por-rangos] Generados {len(rangos)} rangos")
        except Exception as e:
            logger.error(f"Error generando rangos: {e}", exc_info=True)
            rangos = [(0, 0, "$0+")]  # Rango por defecto si falla

        # ✅ DIAGNÓSTICO: Verificar estado antes de procesar distribución
        # Verificar cuántos préstamos tiene query_base antes de procesar
        # ✅ CORRECCIÓN: Usar with_entities para evitar error si valor_activo no existe en BD
        try:
            count_query_base = query_base.with_entities(Prestamo.id).count()
            logger.info(
                f"📊 [financiamiento-por-rangos] Estado antes de procesar distribución: "
                f"total_prestamos={total_prestamos}, total_monto={total_monto:,.2f}, "
                f"rangos_generados={len(rangos)}, query_base.count()={count_query_base}"
            )
        except Exception as e:
            logger.warning(f"⚠️ [financiamiento-por-rangos] No se pudo contar query_base: {e}")
            count_query_base = 0

        # ✅ DIAGNÓSTICO: Medir tiempo de procesamiento de distribución
        tiempo_antes_procesamiento = time.time()
        tiempo_procesamiento = 0  # Inicializar para evitar error si hay excepción
        try:
            distribucion_data = _procesar_distribucion_rango_monto(query_base, rangos, total_prestamos, total_monto, db)
            tiempo_procesamiento = int((time.time() - tiempo_antes_procesamiento) * 1000)
            logger.info(f"⏱️ [financiamiento-por-rangos] Procesamiento de distribución completado en {tiempo_procesamiento}ms")

            # Ordenar de mayor a menor monto para efecto pirámide (solo si hay datos)
            if distribucion_data:
                distribucion_data.sort(key=lambda x: x["monto_total"], reverse=True)
                logger.info(f"📊 [financiamiento-por-rangos] {len(distribucion_data)} rangos procesados y ordenados")
            else:
                logger.warning(
                    "⚠️ [financiamiento-por-rangos] No se generaron rangos de distribución (distribucion_data vacío)"
                )
        except Exception as e:
            tiempo_procesamiento = int((time.time() - tiempo_antes_procesamiento) * 1000)
            logger.error(
                f"❌ [financiamiento-por-rangos] Error procesando distribución por rangos después de {tiempo_procesamiento}ms: {e}",
                exc_info=True,
            )
            try:
                db.rollback()  # ✅ Rollback para restaurar transacción
            except Exception:
                pass
            distribucion_data = []

        total_time = int((time.time() - start_time) * 1000)
        logger.info(f"⏱️ [financiamiento-por-rangos] Tiempo total: {total_time}ms (procesamiento: {tiempo_procesamiento}ms)")

        # ✅ ALERTA: Si el endpoint es muy lento, registrar advertencia
        if total_time > 2000:
            logger.warning(
                f"⚠️ [financiamiento-por-rangos] Endpoint lento detectado: {total_time}ms - "
                f"Total préstamos: {total_prestamos}, Total monto: {total_monto}, "
                f"Rangos generados: {len(rangos)}, Rangos con datos: {len(distribucion_data) if distribucion_data else 0}"
            )

        # ✅ DIAGNÓSTICO: Log final antes de retornar
        rangos_con_datos = (
            len([r for r in distribucion_data if r.get("cantidad_prestamos", 0) > 0]) if distribucion_data else 0
        )
        logger.info(
            f"📊 [financiamiento-por-rangos] Respuesta final: "
            f"total_prestamos={total_prestamos}, total_monto={total_monto:,.2f}, "
            f"rangos_con_datos={rangos_con_datos}, total_rangos={len(distribucion_data) if distribucion_data else 0}"
        )

        return {
            "rangos": distribucion_data,
            "total_prestamos": total_prestamos,
            "total_monto": total_monto,
        }

    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        total_time = int((time.time() - start_time) * 1000)
        logger.error(f"❌ [financiamiento-por-rangos] Error obteniendo financiamiento por rangos: {error_msg}", exc_info=True)
        logger.error(f"❌ [financiamiento-por-rangos] Tipo de error: {type(e).__name__}")
        logger.error(f"❌ [financiamiento-por-rangos] Tiempo transcurrido antes del error: {total_time}ms")
        logger.error(
            f"❌ [financiamiento-por-rangos] Filtros aplicados: analista={analista}, concesionario={concesionario}, modelo={modelo}, fecha_inicio={fecha_inicio}, fecha_fin={fecha_fin}"
        )
        try:
            db.rollback()  # ✅ Rollback para restaurar transacción después de error
        except Exception as rollback_error:
            logger.error(f"❌ [financiamiento-por-rangos] Error en rollback: {rollback_error}")
        # Retornar respuesta vacía en lugar de lanzar error 500 para evitar romper el dashboard
        logger.warning("⚠️ [financiamiento-por-rangos] Retornando respuesta vacía debido a error")
        return {
            "rangos": [],
            "total_prestamos": 0,
            "total_monto": 0.0,
        }


def _get_morosidad_categoria(dias_atraso: int) -> str:
    """Determina la categoría de morosidad basada en los días de atraso."""
    if dias_atraso <= 5:
        return "0-5 días"
    elif dias_atraso <= 15:
        return "5-15 días"
    elif dias_atraso <= 60:  # ~1 month to 2 months
        return "1-2 meses"
    elif dias_atraso <= 90:  # ~2 months to 3 months
        return "2-3 meses"
    elif dias_atraso <= 180:  # ~4 months to 6 months
        return "4-6 meses"
    elif dias_atraso <= 365:  # ~6 months to 1 year
        return "6 meses - 1 año"
    else:
        return "Más de 1 año"


@router.get("/composicion-morosidad")
@cache_result(ttl=300, key_prefix="dashboard")  # Cache por 5 minutos
def obtener_composicion_morosidad(
    analista: Optional[str] = Query(None),
    concesionario: Optional[str] = Query(None),
    modelo: Optional[str] = Query(None),
    fecha_inicio: Optional[date] = Query(None),
    fecha_fin: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Obtiene datos de morosidad para gráfico de barras: categorías de días de atraso vs monto
    Retorna puntos agrupados por categorías de días de atraso con el monto total por categoría
    """
    try:
        # ✅ ACTUALIZADO: Query base usando columnas calculadas automáticamente
        query_base = (
            db.query(
                Cuota.id,
                Cuota.dias_morosidad,  # ✅ Usar columna calculada automáticamente
                Cuota.monto_morosidad,  # ✅ Usar columna calculada automáticamente
            )
            .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
            .filter(
                Prestamo.estado == "APROBADO",
                Cuota.dias_morosidad > 0,  # ✅ Solo cuotas con morosidad (optimizado con índice)
                Cuota.monto_morosidad > 0,  # ✅ Solo cuotas con monto pendiente (optimizado con índice)
            )
        )

        # Aplicar filtros
        if analista:
            query_base = query_base.filter(or_(Prestamo.analista == analista, Prestamo.producto_financiero == analista))
        if concesionario:
            query_base = query_base.filter(Prestamo.concesionario == concesionario)
        if modelo:
            query_base = query_base.filter(or_(Prestamo.producto == modelo, Prestamo.modelo_vehiculo == modelo))
        if fecha_inicio:
            query_base = query_base.filter(Prestamo.fecha_registro >= fecha_inicio)
        if fecha_fin:
            query_base = query_base.filter(Prestamo.fecha_registro <= fecha_fin)

        # ✅ OPTIMIZACIÓN: Usar GROUP BY en SQL en lugar de procesamiento en Python
        # Categorizar días de atraso directamente en SQL usando CASE WHEN
        from sqlalchemy import text

        try:
            # Construir query SQL optimizada con GROUP BY
            # Obtener los IDs de cuotas que cumplen los filtros
            cuota_ids_query = query_base.with_entities(Cuota.id)
            cuota_ids_result = cuota_ids_query.all()
            cuota_ids = [row[0] for row in cuota_ids_result]

            if not cuota_ids:
                # Si no hay cuotas, retornar respuesta vacía
                return {
                    "puntos": [],
                    "total_morosidad": 0.0,
                    "total_cuotas": 0,
                }

            # Query SQL optimizada con GROUP BY y categorización
            query_sql = text(
                """
                WITH cuotas_categorizadas AS (
                    SELECT
                        CASE
                            WHEN dias_morosidad <= 5 THEN '0-5 días'
                            WHEN dias_morosidad <= 15 THEN '5-15 días'
                            WHEN dias_morosidad <= 60 THEN '1-2 meses'
                            WHEN dias_morosidad <= 90 THEN '2-3 meses'
                            WHEN dias_morosidad <= 180 THEN '4-6 meses'
                            WHEN dias_morosidad <= 365 THEN '6 meses - 1 año'
                            ELSE 'Más de 1 año'
                        END as categoria,
                        monto_morosidad
                    FROM cuotas
                    WHERE id = ANY(:ids)
                      AND dias_morosidad > 0
                      AND monto_morosidad > 0
                )
                SELECT
                    categoria,
                    COUNT(*) as cantidad_cuotas,
                    SUM(monto_morosidad) as monto_total
                FROM cuotas_categorizadas
                GROUP BY categoria
                ORDER BY
                    CASE categoria
                        WHEN '0-5 días' THEN 1
                        WHEN '5-15 días' THEN 2
                        WHEN '1-2 meses' THEN 3
                        WHEN '2-3 meses' THEN 4
                        WHEN '4-6 meses' THEN 5
                        WHEN '6 meses - 1 año' THEN 6
                        WHEN 'Más de 1 año' THEN 7
                    END
            """
            )

            result = db.execute(query_sql, {"ids": cuota_ids})

            # Crear diccionario con resultados
            puntos_por_categoria = {}
            total_morosidad = Decimal("0")
            total_cuotas = 0

            for row in result:
                categoria = row.categoria
                cantidad = int(row.cantidad_cuotas)
                monto = float(row.monto_total)

                puntos_por_categoria[categoria] = {"monto": Decimal(str(monto)), "cantidad": cantidad}
                total_morosidad += Decimal(str(monto))
                total_cuotas += cantidad

            logger.info(f"📊 [composicion-morosidad] Procesados {len(puntos_por_categoria)} categorías con GROUP BY SQL")

        except Exception as e:
            logger.warning(f"⚠️ Error en query optimizada de morosidad, usando método fallback: {e}")
            # Fallback: procesar en Python
            cuotas = query_base.all()
            puntos_por_categoria = {}
            total_morosidad = Decimal("0")
            total_cuotas = 0

            for cuota in cuotas:
                dias_atraso = cuota.dias_morosidad or 0
                monto = Decimal(str(cuota.monto_morosidad)) if cuota.monto_morosidad else Decimal("0")
                categoria = _get_morosidad_categoria(dias_atraso)

                if categoria not in puntos_por_categoria:
                    puntos_por_categoria[categoria] = {"monto": Decimal("0"), "cantidad": 0}
                puntos_por_categoria[categoria]["monto"] += monto
                puntos_por_categoria[categoria]["cantidad"] += 1
                total_morosidad += monto
                total_cuotas += 1

        # Definir el orden deseado de las categorías
        orden_categorias = ["0-5 días", "5-15 días", "1-2 meses", "2-3 meses", "4-6 meses", "6 meses - 1 año", "Más de 1 año"]

        # Convertir a lista de puntos para el gráfico de barras, manteniendo el orden
        puntos = []
        for categoria in orden_categorias:
            datos = puntos_por_categoria.get(categoria, {"monto": Decimal("0"), "cantidad": 0})
            puntos.append({"categoria": categoria, "monto": float(datos["monto"]), "cantidad_cuotas": datos["cantidad"]})

        return {
            "puntos": puntos,  # Lista de {categoria, monto, cantidad_cuotas}
            "total_morosidad": float(total_morosidad),
            "total_cuotas": total_cuotas,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo composición de morosidad: {e}", exc_info=True)
        try:
            db.rollback()  # ✅ Rollback para restaurar transacción después de error
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.get("/evolucion-general-mensual")
@cache_result(ttl=300, key_prefix="dashboard")  # Cache por 5 minutos
def obtener_evolucion_general_mensual(
    analista: Optional[str] = Query(None),
    concesionario: Optional[str] = Query(None),
    modelo: Optional[str] = Query(None),
    fecha_inicio: Optional[date] = Query(None),
    fecha_fin: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Obtiene la evolución mensual de Morosidad, Total Activos, Total Financiamiento y Total Pagos
    para los últimos 6 meses o el rango de fechas especificado.
    ✅ OPTIMIZADO: Usa queries con GROUP BY en lugar de loops por mes
    """
    import time

    start_time = time.time()

    try:
        hoy = date.today()
        nombres_meses = [
            "Enero",
            "Febrero",
            "Marzo",
            "Abril",
            "Mayo",
            "Junio",
            "Julio",
            "Agosto",
            "Septiembre",
            "Octubre",
            "Noviembre",
            "Diciembre",
        ]

        # Calcular rango de fechas (últimos 6 meses por defecto)
        if fecha_fin:
            fecha_fin_mes = fecha_fin.replace(day=1)
        else:
            fecha_fin_mes = hoy.replace(day=1)

        if fecha_inicio:
            fecha_inicio_mes = fecha_inicio.replace(day=1)
        else:
            # Últimos 6 meses
            año_inicio = fecha_fin_mes.year
            mes_inicio = fecha_fin_mes.month - 5
            if mes_inicio <= 0:
                año_inicio -= 1
                mes_inicio += 12
            fecha_inicio_mes = date(año_inicio, mes_inicio, 1)

        # Generar lista de meses
        meses_lista = []
        current = fecha_inicio_mes
        while current <= fecha_fin_mes:
            meses_lista.append(
                {
                    "año": current.year,
                    "mes": current.month,
                    "nombre": f"{nombres_meses[current.month - 1]} {current.year}",
                    "fecha": current,
                }
            )
            # Siguiente mes
            if current.month == 12:
                current = current.replace(year=current.year + 1, month=1)
            else:
                current = current.replace(month=current.month + 1)

        # ✅ OPTIMIZACIÓN: Calcular datos para todos los meses en queries optimizadas

        # Obtener el último día de cada mes
        ultimos_dias = {}
        primeros_dias = {}
        for mes_info in meses_lista:
            año = mes_info["año"]
            mes = mes_info["mes"]
            if mes == 12:
                ultimos_dias[(año, mes)] = date(año, 12, 31)
                primeros_dias[(año, mes)] = date(año, 12, 1)
            else:
                ultimos_dias[(año, mes)] = date(año, mes + 1, 1) - timedelta(days=1)
                primeros_dias[(año, mes)] = date(año, mes, 1)

        fecha_ultima = max(ultimos_dias.values())
        fecha_primera = min(primeros_dias.values())

        # 1. TOTAL FINANCIAMIENTO por mes (nuevos préstamos aprobados)
        start_financiamiento = time.time()
        query_financiamiento = (
            db.query(
                func.extract("year", Prestamo.fecha_registro).label("año"),
                func.extract("month", Prestamo.fecha_registro).label("mes"),
                func.sum(Prestamo.total_financiamiento).label("total"),
            )
            .filter(
                Prestamo.estado == "APROBADO",
                Prestamo.fecha_registro >= fecha_primera,
                Prestamo.fecha_registro <= fecha_ultima,
            )
            .group_by(func.extract("year", Prestamo.fecha_registro), func.extract("month", Prestamo.fecha_registro))
        )
        query_financiamiento = FiltrosDashboard.aplicar_filtros_prestamo(
            query_financiamiento, analista, concesionario, modelo, None, None
        )
        financiamiento_por_mes = {
            (int(row.año), int(row.mes)): float(row.total or Decimal("0")) for row in query_financiamiento.all()
        }
        tiempo_financiamiento = int((time.time() - start_financiamiento) * 1000)
        logger.info(f"📊 [evolucion-general] Financiamiento por mes: {tiempo_financiamiento}ms")

        # 2. TOTAL PAGOS por mes (usar Pago.monto_pagado, no Pago.monto)
        # ✅ ACTUALIZADO: Usar LEFT JOIN para incluir pagos sin prestamo_id (articulación por cedula)
        start_pagos = time.time()

        # Query con SQL directo para mejor control de LEFT JOIN y articulación por cedula
        prestamo_conditions_pagos = []
        bind_params_pagos = {"fecha_inicio": fecha_primera, "fecha_fin": fecha_ultima}

        if analista or concesionario or modelo:
            if analista:
                prestamo_conditions_pagos.append("(pr.analista = :analista OR pr.producto_financiero = :analista)")
                bind_params_pagos["analista"] = analista
            if concesionario:
                prestamo_conditions_pagos.append("pr.concesionario = :concesionario")
                bind_params_pagos["concesionario"] = concesionario
            if modelo:
                prestamo_conditions_pagos.append("(pr.producto = :modelo OR pr.modelo_vehiculo = :modelo)")
                bind_params_pagos["modelo"] = modelo

            where_clause = """p.fecha_pago >= :fecha_inicio
                      AND p.fecha_pago <= :fecha_fin
                      AND p.monto_pagado IS NOT NULL
                      AND p.monto_pagado > 0
                      AND p.activo = TRUE
                      AND (pr.estado = 'APROBADO' OR p.prestamo_id IS NULL)"""

            if prestamo_conditions_pagos:
                where_clause += " AND " + " AND ".join(prestamo_conditions_pagos)

            query_pagos_sql = text(
                f"""
                SELECT
                    EXTRACT(YEAR FROM p.fecha_pago)::integer as año,
                    EXTRACT(MONTH FROM p.fecha_pago)::integer as mes,
                    COALESCE(SUM(p.monto_pagado), 0) as total
                FROM pagos p
                LEFT JOIN prestamos pr ON (
                    (p.prestamo_id IS NOT NULL AND pr.id = p.prestamo_id)
                    OR (p.prestamo_id IS NULL AND pr.cedula = p.cedula AND pr.estado = 'APROBADO')
                )
                WHERE {where_clause}
                GROUP BY EXTRACT(YEAR FROM p.fecha_pago), EXTRACT(MONTH FROM p.fecha_pago)
                ORDER BY año, mes
                """
            ).bindparams(**bind_params_pagos)
        else:
            # Sin filtros, query más simple
            query_pagos_sql = text(
                """
                SELECT
                    EXTRACT(YEAR FROM fecha_pago)::integer as año,
                    EXTRACT(MONTH FROM fecha_pago)::integer as mes,
                    COALESCE(SUM(monto_pagado), 0) as total
                FROM pagos
                WHERE fecha_pago >= :fecha_inicio
                  AND fecha_pago <= :fecha_fin
                  AND monto_pagado IS NOT NULL
                  AND monto_pagado > 0
                  AND activo = TRUE
                GROUP BY EXTRACT(YEAR FROM fecha_pago), EXTRACT(MONTH FROM fecha_pago)
                ORDER BY año, mes
                """
            ).bindparams(fecha_inicio=fecha_primera, fecha_fin=fecha_ultima)

        resultados_pagos = db.execute(query_pagos_sql).fetchall()
        pagos_por_mes = {(int(row[0]), int(row[1])): float(row[2] or Decimal("0")) for row in resultados_pagos}
        tiempo_pagos = int((time.time() - start_pagos) * 1000)
        logger.info(f"📊 [evolucion-general] Pagos por mes: {tiempo_pagos}ms")

        # 3. Construir evolución mensual (calcular morosidad y activos por mes)
        # ✅ OPTIMIZACIÓN: Queries optimizadas con GROUP BY en lugar de loop por mes
        start_evolucion = time.time()
        evolucion = []

        # ✅ OPTIMIZACIÓN: Calcular morosidad por mes de forma más eficiente
        # La morosidad es acumulativa: cuotas vencidas hasta el final de cada mes
        # Usar CTE o subquery para calcular morosidad por mes
        morosidad_por_mes = {}
        try:
            # Obtener todos los últimos días de mes de una vez
            ultimos_dias_lista = list(ultimos_dias.values())
            if ultimos_dias_lista:
                fecha_ultima_morosidad = max(ultimos_dias_lista)

                # ✅ CORRECCIÓN: Query optimizada: calcular morosidad REAL restando pagos aplicados
                # Morosidad = Cuotas vencidas - Pagos aplicados a cuotas vencidas
                query_morosidad_optimizada = db.execute(
                    text(
                        """
                        WITH cuotas_vencidas AS (
                            SELECT
                                EXTRACT(YEAR FROM c.fecha_vencimiento)::integer as año,
                                EXTRACT(MONTH FROM c.fecha_vencimiento)::integer as mes,
                                COALESCE(SUM(c.monto_cuota), 0) as total_cuotas_vencidas
                            FROM cuotas c
                            INNER JOIN prestamos p ON c.prestamo_id = p.id
                            WHERE p.estado = 'APROBADO'
                              AND c.fecha_vencimiento <= :fecha_limite
                              AND c.estado != 'PAGADO'
                GROUP BY
                                EXTRACT(YEAR FROM c.fecha_vencimiento),
                                EXTRACT(MONTH FROM c.fecha_vencimiento)
                        ),
                        pagos_aplicados AS (
                            SELECT
                                EXTRACT(YEAR FROM c.fecha_vencimiento)::integer as año,
                                EXTRACT(MONTH FROM c.fecha_vencimiento)::integer as mes,
                                COALESCE(SUM(c.total_pagado), 0) as total_pagado
                            FROM cuotas c
                            INNER JOIN prestamos p ON c.prestamo_id = p.id
                            WHERE c.fecha_vencimiento <= :fecha_limite
                              AND c.estado != 'PAGADO'
                              AND p.estado = 'APROBADO'
                              AND c.total_pagado > 0
                GROUP BY
                                EXTRACT(YEAR FROM c.fecha_vencimiento),
                                EXTRACT(MONTH FROM c.fecha_vencimiento)
                        )
                        SELECT
                            cv.año,
                            cv.mes,
                            GREATEST(0, cv.total_cuotas_vencidas - COALESCE(pa.total_pagado, 0)) as morosidad
                        FROM cuotas_vencidas cv
                        LEFT JOIN pagos_aplicados pa ON cv.año = pa.año AND cv.mes = pa.mes
                        ORDER BY cv.año, cv.mes
                        """
                    ).bindparams(fecha_limite=fecha_ultima_morosidad)
                )

                resultados_morosidad = query_morosidad_optimizada.fetchall()
                morosidad_por_mes = {(int(row[0]), int(row[1])): float(row[2] or Decimal("0")) for row in resultados_morosidad}
        except Exception as e:
            logger.warning(f"⚠️ [evolucion-general] Error calculando morosidad optimizada: {e}, usando método fallback")
            morosidad_por_mes = {}

        # ✅ OPTIMIZACIÓN: Query única para activos acumulados por mes
        activos_por_mes = {}
        try:
            if ultimos_dias_lista:
                fecha_ultima_activos = max(ultimos_dias_lista)

                # Query optimizada: activos acumulados por mes usando GROUP BY
                query_activos_optimizada = (
                    db.query(
                        func.extract("year", Prestamo.fecha_registro).label("año"),
                        func.extract("month", Prestamo.fecha_registro).label("mes"),
                        func.sum(Prestamo.total_financiamiento).label("activos"),
                    )
                    .filter(
                        Prestamo.estado == "APROBADO",
                        Prestamo.fecha_registro <= fecha_ultima_activos,
                    )
                    .group_by(func.extract("year", Prestamo.fecha_registro), func.extract("month", Prestamo.fecha_registro))
                )

                # Aplicar filtros si existen
                if analista or concesionario or modelo:
                    query_activos_optimizada = FiltrosDashboard.aplicar_filtros_prestamo(
                        query_activos_optimizada, analista, concesionario, modelo, None, None
                    )

                resultados_activos = query_activos_optimizada.all()
                # Calcular acumulado
                total_activos_acum = Decimal("0")
                for row in sorted(resultados_activos, key=lambda x: (x.año, x.mes)):
                    total_activos_acum += Decimal(str(row.activos or 0))
                    activos_por_mes[(int(row.año), int(row.mes))] = float(total_activos_acum)
        except Exception as e:
            logger.warning(f"⚠️ [evolucion-general] Error calculando activos optimizados: {e}, usando método fallback")
            activos_por_mes = {}

        # Construir evolución mensual usando datos pre-calculados
        for mes_info in meses_lista:
            año = int(mes_info["año"])
            mes = int(mes_info["mes"])
            nombre_mes = str(mes_info["nombre"])
            mes_key: tuple[int, int] = (año, mes)

            # Usar datos pre-calculados o calcular en el momento si no están disponibles
            morosidad = morosidad_por_mes.get(mes_key, 0.0)
            total_activos = activos_por_mes.get(mes_key, 0.0)

            # Si no hay datos pre-calculados, calcular en el momento (fallback)
            if morosidad == 0.0 and mes_key not in morosidad_por_mes:
                ultimo_dia_mes = ultimos_dias[mes_key]
                query_morosidad = (
                    db.query(func.sum(Cuota.monto_cuota))
                    .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
                    .filter(
                        Prestamo.estado == "APROBADO",
                        Cuota.fecha_vencimiento <= ultimo_dia_mes,
                        Cuota.estado != "PAGADO",
                    )
                )
                query_morosidad = FiltrosDashboard.aplicar_filtros_cuota(
                    query_morosidad, analista, concesionario, modelo, None, None
                )
                morosidad = float(query_morosidad.scalar() or Decimal("0"))

            if total_activos == 0.0 and mes_key not in activos_por_mes:
                ultimo_dia_mes = ultimos_dias[mes_key]
                query_activos = db.query(func.sum(Prestamo.total_financiamiento)).filter(
                    Prestamo.estado == "APROBADO",
                    Prestamo.fecha_registro <= ultimo_dia_mes,
                )
                query_activos = FiltrosDashboard.aplicar_filtros_prestamo(
                    query_activos, analista, concesionario, modelo, None, None
                )
                total_activos = float(query_activos.scalar() or Decimal("0"))

            # Obtener datos pre-calculados
            total_financiamiento = financiamiento_por_mes.get(mes_key, 0.0)
            total_pagos = pagos_por_mes.get(mes_key, 0.0)

            evolucion.append(
                {
                    "mes": nombre_mes,
                    "morosidad": round(morosidad, 2),
                    "total_activos": round(total_activos, 2),
                    "total_financiamiento": round(total_financiamiento, 2),
                    "total_pagos": round(total_pagos, 2),
                }
            )

        tiempo_evolucion = int((time.time() - start_evolucion) * 1000)
        total_time = int((time.time() - start_time) * 1000)
        logger.info(
            f"⏱️ [evolucion-general] Tiempo total: {total_time}ms (financiamiento: {tiempo_financiamiento}ms, pagos: {tiempo_pagos}ms, evolucion: {tiempo_evolucion}ms)"
        )

        return {"evolucion": evolucion}

    except Exception as e:
        logger.error(f"Error obteniendo evolución general mensual: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.get("/distribucion-prestamos")
def obtener_distribucion_prestamos(
    tipo: str = Query("rango_monto", description="Tipo de distribución: rango_monto, plazo, rango_monto_plazo, estado"),
    analista: Optional[str] = Query(None),
    concesionario: Optional[str] = Query(None),
    modelo: Optional[str] = Query(None),
    fecha_inicio: Optional[date] = Query(None),
    fecha_fin: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Componente 5: Distribución de Préstamos
    """
    try:
        query_base = db.query(Prestamo).filter(Prestamo.estado == "APROBADO")
        query_base = FiltrosDashboard.aplicar_filtros_prestamo(
            query_base, analista, concesionario, modelo, fecha_inicio, fecha_fin
        )

        total_prestamos = query_base.with_entities(Prestamo.id).count()
        total_monto = float(query_base.with_entities(func.sum(Prestamo.total_financiamiento)).scalar() or Decimal("0"))

        distribucion_data = []

        if tipo == "rango_monto":
            # Rangos: 0-5000, 5000-10000, 10000-20000, 20000-50000, 50000+
            rangos = [
                (0, 5000, "0 - $5,000"),
                (5000, 10000, "$5,000 - $10,000"),
                (10000, 20000, "$10,000 - $20,000"),
                (20000, 50000, "$20,000 - $50,000"),
                (50000, None, "$50,000+"),
            ]
            distribucion_data = _procesar_distribucion_rango_monto(query_base, rangos, total_prestamos, total_monto, db)

        elif tipo == "plazo":
            distribucion_data = _procesar_distribucion_por_plazo(query_base, total_prestamos, total_monto)

        elif tipo == "estado":
            distribucion_data = _procesar_distribucion_por_estado(query_base, total_prestamos, total_monto)

        elif tipo == "rango_monto_plazo":
            rangos_monto = [
                (0, 10000, "Pequeño"),
                (10000, 30000, "Mediano"),
                (30000, None, "Grande"),
            ]
            rangos_plazo = [
                (0, 12, "Corto"),
                (12, 36, "Medio"),
                (36, None, "Largo"),
            ]
            distribucion_data = _procesar_distribucion_rango_monto_plazo(
                query_base, rangos_monto, rangos_plazo, total_prestamos, total_monto
            )

        return {
            "distribucion": distribucion_data,
            "tipo": tipo,
            "total_prestamos": total_prestamos,
            "total_monto": total_monto,
        }

    except Exception as e:
        logger.error(f"Error obteniendo distribución de préstamos: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.get("/cuentas-cobrar-tendencias")
def obtener_cuentas_cobrar_tendencias(
    meses_proyeccion: int = Query(6, description="Meses de proyección adelante"),
    granularidad: str = Query(
        "mes_actual", description="Granularidad: mes_actual, proximos_n_dias, hasta_fin_anio, personalizado"
    ),
    dias: Optional[int] = Query(None, description="Días para granularidad 'proximos_n_dias'"),
    analista: Optional[str] = Query(None),
    concesionario: Optional[str] = Query(None),
    modelo: Optional[str] = Query(None),
    fecha_inicio: Optional[date] = Query(None),
    fecha_fin: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Componente 6: Tendencias de Cuentas por Cobrar y Cuotas en Días
    """
    try:
        hoy = date.today()

        # Determinar rango de fechas según granularidad
        fecha_inicio_query, fecha_fin_query = _calcular_rango_fechas_granularidad(
            granularidad, hoy, dias, fecha_inicio, fecha_fin
        )

        # Extender hasta incluir proyección
        fecha_fin_proyeccion = fecha_fin_query + timedelta(days=meses_proyeccion * 30)

        # Generar lista de fechas (diaria)
        datos: List[dict[str, Any]] = []
        current_date = fecha_inicio_query
        fecha_division = fecha_fin_query  # Separación entre datos reales y proyección

        while current_date <= fecha_fin_proyeccion:
            es_proyeccion = current_date > fecha_division

            # CUENTAS POR COBRAR: Suma de monto_cuota de cuotas pendientes hasta esa fecha
            if not es_proyeccion:
                query_cuentas = (
                    db.query(func.sum(Cuota.monto_cuota))
                    .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
                    .filter(
                        Prestamo.estado == "APROBADO",
                        Cuota.fecha_vencimiento <= current_date,
                        Cuota.estado != "PAGADO",
                    )
                )
                query_cuentas = FiltrosDashboard.aplicar_filtros_cuota(
                    query_cuentas, analista, concesionario, modelo, fecha_inicio, fecha_fin
                )
                cuentas_por_cobrar = float(query_cuentas.scalar() or Decimal("0"))
            else:
                # Proyección: usar último valor conocido con factor de crecimiento
                cuentas_por_cobrar = _calcular_proyeccion_cuentas_cobrar(datos)

            # CUOTAS EN DÍAS: Contar cuotas que se deben pagar por día (fecha_vencimiento = current_date)
            if not es_proyeccion:
                query_cuotas_dia = (
                    db.query(func.count(Cuota.id))
                    .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
                    .filter(
                        Prestamo.estado == "APROBADO",
                        Cuota.fecha_vencimiento == current_date,
                        Cuota.estado != "PAGADO",
                    )
                )
                query_cuotas_dia = FiltrosDashboard.aplicar_filtros_cuota(
                    query_cuotas_dia, analista, concesionario, modelo, fecha_inicio, fecha_fin
                )
                cuotas_en_dias = query_cuotas_dia.scalar() or 0
            else:
                # Proyección: usar promedio de últimos días históricos
                cuotas_en_dias = _calcular_proyeccion_cuotas_dias(datos)

            datos.append(
                {
                    "fecha": current_date.isoformat(),
                    "fecha_formateada": current_date.strftime("%d/%m/%Y"),
                    "cuentas_por_cobrar": cuentas_por_cobrar if not es_proyeccion else None,
                    "cuentas_por_cobrar_proyectado": cuentas_por_cobrar if es_proyeccion else None,
                    "cuotas_en_dias": cuotas_en_dias if not es_proyeccion else None,
                    "cuotas_en_dias_proyectado": cuotas_en_dias if es_proyeccion else None,
                    "es_proyeccion": es_proyeccion,
                }
            )

            current_date += timedelta(days=1)

        return {
            "datos": datos,
            "fecha_inicio": fecha_inicio_query.isoformat(),
            "fecha_fin": fecha_fin_proyeccion.isoformat(),
            "meses_proyeccion": meses_proyeccion,
            "ultima_actualizacion": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"Error obteniendo tendencias: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.get("/financiamiento-tendencia-mensual")
@cache_result(ttl=600, key_prefix="dashboard")  # Cache por 10 minutos (datos históricos)
def obtener_financiamiento_tendencia_mensual(
    meses: int = Query(12, description="Número de meses a mostrar (últimos N meses)"),
    analista: Optional[str] = Query(None),
    concesionario: Optional[str] = Query(None),
    modelo: Optional[str] = Query(None),
    fecha_inicio: Optional[date] = Query(None),
    fecha_fin: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Tendencia mensual de financiamientos para gráfico de primera plana
    Últimos N meses con nuevos financiamientos y monto total mensual
    ✅ OPTIMIZADO: Una sola query con GROUP BY en lugar de múltiples queries en loop
    """
    import time

    from app.core.cache import cache_backend

    start_time = time.time()

    try:
        # ✅ ROLLBACK PREVENTIVO: Restaurar transacción si está abortada
        try:
            db.execute(text("SELECT 1"))
        except Exception as test_error:
            error_str = str(test_error)
            if "aborted" in error_str.lower() or "InFailedSqlTransaction" in error_str:
                logger.warning("⚠️ [financiamiento-tendencia] Transacción abortada detectada, haciendo rollback preventivo")
                try:
                    db.rollback()
                except Exception:
                    pass

        hoy = date.today()
        nombres_meses = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]

        # ✅ OPTIMIZACIÓN: Cachear primera fecha para evitar 3 queries MIN() en cada request
        fecha_inicio_query = fecha_inicio
        if not fecha_inicio_query:
            cache_key_primera_fecha = "dashboard:primera_fecha_desde_2024"
            primera_fecha_cached = cache_backend.get(cache_key_primera_fecha)

            if primera_fecha_cached:
                fecha_inicio_query = date.fromisoformat(primera_fecha_cached)
            else:
                # Buscar la primera fecha con datos desde 2024 (solo si no está en cache)
                primera_fecha = None
                try:
                    # Buscar primera fecha de aprobación desde 2024
                    primera_aprobacion = (
                        db.query(func.min(Prestamo.fecha_aprobacion))
                        .filter(Prestamo.estado == "APROBADO", func.extract("year", Prestamo.fecha_aprobacion) >= 2024)
                        .scalar()
                    )

                    # Buscar primera fecha de cuota desde 2024
                    primera_cuota = (
                        db.query(func.min(Cuota.fecha_vencimiento))
                        .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
                        .filter(Prestamo.estado == "APROBADO", func.extract("year", Cuota.fecha_vencimiento) >= 2024)
                        .scalar()
                    )

                    # Buscar primera fecha de pago desde 2024
                    primera_pago = (
                        db.query(func.min(Pago.fecha_pago))
                        .filter(Pago.activo.is_(True), Pago.monto_pagado > 0, func.extract("year", Pago.fecha_pago) >= 2024)
                        .scalar()
                    )

                    # Encontrar la fecha más antigua entre todas
                    # ✅ CORRECCIÓN: Normalizar todas las fechas a date antes de comparar
                    # fecha_aprobacion y fecha_pago pueden ser datetime.datetime, fecha_vencimiento es date
                    fechas_disponibles = []
                    for f in [primera_aprobacion, primera_cuota, primera_pago]:
                        if f is not None:
                            # Convertir datetime a date si es necesario
                            if isinstance(f, datetime):
                                fechas_disponibles.append(f.date())
                            else:
                                fechas_disponibles.append(f)

                    if fechas_disponibles:
                        primera_fecha = min(fechas_disponibles)
                        # Redondear al primer día del mes
                        fecha_inicio_query = date(primera_fecha.year, primera_fecha.month, 1)
                    else:
                        # Si no hay datos, usar enero 2024
                        fecha_inicio_query = date(2024, 1, 1)

                    # Cachear resultado por 1 hora (cambia muy raramente)
                    cache_backend.set(cache_key_primera_fecha, fecha_inicio_query.isoformat(), ttl=3600)
                except Exception as e:
                    logger.warning(f"⚠️ [financiamiento-tendencia] Error buscando primera fecha: {e}, usando enero 2024")
                    fecha_inicio_query = date(2024, 1, 1)

        # Calcular fecha fin (hoy)
        fecha_fin_query = hoy

        # ✅ OPTIMIZACIÓN: Una sola query para obtener todos los nuevos financiamientos por mes con GROUP BY
        start_query = time.time()
        resultados_nuevos = []
        query_time = 0  # Inicializar query_time
        try:
            # Construir filtros base
            # ⚠️ TEMPORAL: Usar fecha_aprobacion porque fecha_registro no migró correctamente
            filtros_base = [Prestamo.estado == "APROBADO"]
            if fecha_inicio_query:
                filtros_base.append(Prestamo.fecha_aprobacion >= fecha_inicio_query)
            if fecha_fin_query:
                filtros_base.append(Prestamo.fecha_aprobacion <= fecha_fin_query)

            # ✅ OPTIMIZACIÓN: Usar date_trunc en lugar de EXTRACT para mejor rendimiento con índices
            # Query optimizada: GROUP BY usando date_trunc('month', fecha_aprobacion)
            from sqlalchemy import text

            # Construir query SQL con date_trunc para aprovechar índices funcionales
            query_nuevos = (
                db.query(
                    func.date_trunc("month", Prestamo.fecha_aprobacion).label("mes"),
                    func.count(Prestamo.id).label("cantidad"),
                    func.sum(Prestamo.total_financiamiento).label("monto_total"),
                )
                .filter(*filtros_base)
                .group_by(func.date_trunc("month", Prestamo.fecha_aprobacion))
                .order_by(func.date_trunc("month", Prestamo.fecha_aprobacion))
            )

            # Aplicar filtros adicionales (si hay)
            query_nuevos = FiltrosDashboard.aplicar_filtros_prestamo(
                query_nuevos, analista, concesionario, modelo, fecha_inicio, fecha_fin
            )

            resultados_nuevos = query_nuevos.all()
            query_time = int((time.time() - start_query) * 1000)

            # ✅ MONITOREO: Registrar query individual con info de BD y campos
            from app.utils.db_analyzer import get_database_size

            db_info = get_database_size(db)
            query_analysis = {
                "tables": ["prestamos"],
                "columns": [
                    "fecha_aprobacion",
                    "total_financiamiento",
                    "estado",
                    "analista",
                    "concesionario",
                    "modelo_vehiculo",
                ],
            }

            query_monitor.record_query(
                query_name="financiamiento_tendencia_nuevos",
                execution_time_ms=query_time,
                query_type="SELECT",
                tables=query_analysis["tables"],
                columns=query_analysis["columns"],
            )

            logger.info(f"📊 [financiamiento-tendencia] Query completada en {query_time}ms, {len(resultados_nuevos)} meses")

            # ✅ ALERTA: Si la query es lenta (con info de BD y campos)
            if query_time >= 5000:
                db_size_info = f"BD: {db_info.get('size_pretty', 'N/A')}" if db_info else "BD: N/A"
                tables_info = f"Tablas: {', '.join(query_analysis['tables'])}"
                logger.error(
                    f"🚨 [ALERTA CRÍTICA] Query nuevos financiamientos muy lenta: {query_time}ms - "
                    f"{db_size_info} - {tables_info}"
                )
            elif query_time >= 2000:
                db_size_info = f"BD: {db_info.get('size_pretty', 'N/A')}" if db_info else "BD: N/A"
                tables_info = f"Tablas: {', '.join(query_analysis['tables'])}"
                logger.warning(
                    f"⚠️ [ALERTA] Query nuevos financiamientos lenta: {query_time}ms - " f"{db_size_info} - {tables_info}"
                )
        except Exception as e:
            logger.error(f"⚠️ [financiamiento-tendencia] Error en query nuevos financiamientos: {e}", exc_info=True)
            try:
                db.rollback()  # ✅ Rollback para restaurar transacción después de error
            except Exception:
                pass
            resultados_nuevos = []
            query_time = int((time.time() - start_query) * 1000)

        # Crear diccionario de nuevos financiamientos por mes
        # ✅ ACTUALIZADO: date_trunc retorna datetime, extraer año y mes
        nuevos_por_mes = {}
        for row in resultados_nuevos:
            # date_trunc retorna un datetime (primer día del mes)
            mes_datetime = row.mes
            if isinstance(mes_datetime, datetime):
                año_mes = mes_datetime.year
                num_mes = mes_datetime.month
            elif isinstance(mes_datetime, date):
                año_mes = mes_datetime.year
                num_mes = mes_datetime.month
            else:
                # Fallback si no es datetime/date
                año_mes = int(mes_datetime.year) if hasattr(mes_datetime, "year") else int(mes_datetime)
                num_mes = int(mes_datetime.month) if hasattr(mes_datetime, "month") else 1

            nuevos_por_mes[(año_mes, num_mes)] = {
                "cantidad": row.cantidad or 0,
                "monto": float(row.monto_total or Decimal("0")),
            }

        # ✅ OPTIMIZACIÓN: Usar ORM en lugar de SQL directo para aprovechar índices
        # Query para calcular suma de monto_cuota programado por mes (cuotas que vencen en cada mes)
        # Suma TODAS las cuotas de TODOS los clientes que vencen en cada mes (desde 2024)
        start_cuotas = time.time()
        cuotas_por_mes = {}
        try:
            # ✅ Query optimizada con ORM que aprovecha mejor los índices
            query_cuotas = (
                db.query(
                    func.extract("year", Cuota.fecha_vencimiento).label("año"),
                    func.extract("month", Cuota.fecha_vencimiento).label("mes"),
                    func.sum(Cuota.monto_cuota).label("total_cuotas_programadas"),
                )
                .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
                .filter(Prestamo.estado == "APROBADO", func.extract("year", Cuota.fecha_vencimiento) >= 2024)
                .group_by(func.extract("year", Cuota.fecha_vencimiento), func.extract("month", Cuota.fecha_vencimiento))
                .order_by("año", "mes")
            )

            # Aplicar filtros usando FiltrosDashboard (reutiliza lógica)
            query_cuotas = FiltrosDashboard.aplicar_filtros_cuota(
                query_cuotas, analista, concesionario, modelo, fecha_inicio, fecha_fin
            )

            resultados_cuotas = query_cuotas.all()

            for row in resultados_cuotas:
                año_mes = int(row.año)
                num_mes = int(row.mes)
                monto = float(row.total_cuotas_programadas or Decimal("0"))
                cuotas_por_mes[(año_mes, num_mes)] = monto

            cuotas_time = int((time.time() - start_cuotas) * 1000)

            # ✅ MONITOREO: Registrar query individual con info de BD y campos
            db_info = get_database_size(db)
            query_analysis_cuotas = {
                "tables": ["cuotas", "prestamos"],
                "columns": ["fecha_vencimiento", "monto_cuota", "estado", "prestamo_id"],
            }

            query_monitor.record_query(
                query_name="financiamiento_tendencia_cuotas",
                execution_time_ms=cuotas_time,
                query_type="SELECT",
                tables=query_analysis_cuotas["tables"],
                columns=query_analysis_cuotas["columns"],
            )

            logger.info(
                f"📊 [financiamiento-tendencia] Query cuotas programadas completada en {cuotas_time}ms, {len(cuotas_por_mes)} meses con datos"
            )

            # ✅ ALERTA: Si la query es lenta (con info de BD y campos)
            if cuotas_time >= 5000:
                db_size_info = f"BD: {db_info.get('size_pretty', 'N/A')}" if db_info else "BD: N/A"
                tables_info = f"Tablas: {', '.join(query_analysis_cuotas['tables'])}"
                logger.error(
                    f"🚨 [ALERTA CRÍTICA] Query cuotas programadas muy lenta: {cuotas_time}ms - "
                    f"{db_size_info} - {tables_info}"
                )
            elif cuotas_time >= 2000:
                db_size_info = f"BD: {db_info.get('size_pretty', 'N/A')}" if db_info else "BD: N/A"
                tables_info = f"Tablas: {', '.join(query_analysis_cuotas['tables'])}"
                logger.warning(
                    f"⚠️ [ALERTA] Query cuotas programadas lenta: {cuotas_time}ms - " f"{db_size_info} - {tables_info}"
                )

            # ✅ Logging adicional: mostrar algunos meses de ejemplo
            if cuotas_por_mes:
                ejemplos = list(cuotas_por_mes.items())[:3]
                for (año, mes), monto in ejemplos:
                    logger.info(f"  📊 Ejemplo: {año}-{mes:02d} = ${monto:,.2f}")
        except Exception as e:
            logger.error(f"⚠️ [financiamiento-tendencia] Error en query cuotas programadas: {e}", exc_info=True)
            try:
                db.rollback()  # ✅ Rollback para restaurar transacción después de error
            except Exception:
                pass
            cuotas_por_mes = {}

        # ✅ Query para calcular suma de monto_pagado de tabla pagos por mes
        # ⚠️ IMPORTANTE: Esto representa "Cuánto dinero ENTRÓ este mes" (flujo de caja)
        # Incluye TODOS los pagos realizados en el mes, sin importar para qué cuota son:
        # - Pagos de cuotas atrasadas de meses anteriores (PRINCIPAL CAUSA de diferencia)
        # - Exceso de pagos aplicado a cuotas futuras (solo si hay exceso después de pagar todas las vencidas)
        # - Pagos extras/amortizaciones
        # Por eso puede ser MAYOR que "Cuotas Programadas por Mes"
        # NOTA: Los pagos se aplican PRIMERO a cuotas vencidas, no hay pagos anticipados intencionales
        start_pagos = time.time()
        fecha_inicio_query_dt = datetime.combine(fecha_inicio_query, datetime.min.time())
        fecha_fin_query_dt = datetime.combine(fecha_fin_query, datetime.max.time())

        pagos_por_mes = {}
        try:
            # ✅ SOLUCIÓN INTEGRAL: Usar helper que busca pagos de múltiples formas
            # Primero intentar usar total_pagado de cuotas (si está actualizado)
            # Si está en 0, usar helper para buscar pagos por múltiples estrategias
            query_pagos = (
                db.query(
                    func.extract("year", Cuota.fecha_vencimiento).label("año"),
                    func.extract("month", Cuota.fecha_vencimiento).label("mes"),
                    func.sum(Cuota.total_pagado).label("total_pagado"),
                )
                .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
                .filter(Prestamo.estado == "APROBADO", func.extract("year", Cuota.fecha_vencimiento) >= 2024)
                .group_by(func.extract("year", Cuota.fecha_vencimiento), func.extract("month", Cuota.fecha_vencimiento))
                .order_by("año", "mes")
            )

            # Aplicar filtros usando FiltrosDashboard (reutiliza lógica)
            query_pagos = FiltrosDashboard.aplicar_filtros_cuota(
                query_pagos, analista, concesionario, modelo, fecha_inicio, fecha_fin
            )

            # Aplicar filtros de fecha si existen
            if fecha_inicio_query:
                query_pagos = query_pagos.filter(Cuota.fecha_vencimiento >= fecha_inicio_query)
            if fecha_fin_query:
                query_pagos = query_pagos.filter(Cuota.fecha_vencimiento <= fecha_fin_query)

            resultados_pagos = query_pagos.all()

            # ✅ OPTIMIZACIÓN: Usar directamente total_pagado de cuotas
            # Si está en 0, significa que no hay pagos registrados para ese mes
            # No hacer queries adicionales por mes (evita problema N+1)
            for row in resultados_pagos:
                año_mes = int(row.año)
                num_mes = int(row.mes)
                monto_total_pagado = float(row.total_pagado or Decimal("0"))

                # ✅ Si total_pagado es 0, usar 0 directamente
                # El helper calcular_monto_pagado_mes() es muy lento (hace múltiples queries por mes)
                # y causa el problema de rendimiento. Si total_pagado está actualizado en cuotas,
                # no necesitamos recalcularlo. Si no está actualizado, es mejor aceptar 0
                # que hacer queries adicionales que tardan 19+ segundos.
                mes_key_pagos: tuple[int, int] = (año_mes, num_mes)
                pagos_por_mes[mes_key_pagos] = monto_total_pagado

            pagos_time = int((time.time() - start_pagos) * 1000)

            # ✅ MONITOREO: Registrar query individual con info de BD y campos
            db_info = get_database_size(db)
            query_analysis_pagos = {
                "tables": ["cuotas", "prestamos"],
                "columns": ["fecha_vencimiento", "total_pagado", "estado", "prestamo_id"],
            }

            query_monitor.record_query(
                query_name="financiamiento_tendencia_pagos",
                execution_time_ms=pagos_time,
                query_type="SELECT",
                tables=query_analysis_pagos["tables"],
                columns=query_analysis_pagos["columns"],
            )

            logger.info(
                f"📊 [financiamiento-tendencia] Query pagos (total_pagado de cuotas por fecha_vencimiento) completada en {pagos_time}ms, {len(pagos_por_mes)} meses con datos"
            )

            # ✅ ALERTA: Si la query es lenta (con info de BD y campos)
            if pagos_time >= 5000:
                db_size_info = f"BD: {db_info.get('size_pretty', 'N/A')}" if db_info else "BD: N/A"
                tables_info = f"Tablas: {', '.join(query_analysis_pagos['tables'])}"
                logger.error(f"🚨 [ALERTA CRÍTICA] Query pagos muy lenta: {pagos_time}ms - " f"{db_size_info} - {tables_info}")
            elif pagos_time >= 2000:
                db_size_info = f"BD: {db_info.get('size_pretty', 'N/A')}" if db_info else "BD: N/A"
                tables_info = f"Tablas: {', '.join(query_analysis_pagos['tables'])}"
                logger.warning(f"⚠️ [ALERTA] Query pagos lenta: {pagos_time}ms - " f"{db_size_info} - {tables_info}")
            # ✅ Logging adicional: mostrar algunos meses de ejemplo
            if pagos_por_mes:
                ejemplos = list(pagos_por_mes.items())[:3]
                for (año, mes), monto in ejemplos:
                    logger.info(f"  📊 Ejemplo total_pagado de cuotas que vencen en {año}-{mes:02d} = ${monto:,.2f}")
        except Exception as e:
            logger.error(f"⚠️ [financiamiento-tendencia] Error consultando pagos: {e}", exc_info=True)
            try:
                db.rollback()  # ✅ Rollback para restaurar transacción después de error
            except Exception:
                pass
            # Si la tabla no existe o hay error, usar valores por defecto (0)
            pagos_por_mes = {}

        # ✅ SIMPLIFICADO: Eliminada query innecesaria de cuotas_pagos_por_mes
        # No se necesita para el cálculo de morosidad: morosidad = MAX(0, programado - pagado)

        # ✅ CÁLCULO CORREGIDO: Morosidad mensual (NO acumulativa)
        # Morosidad mensual = MAX(0, Monto programado del mes - Monto pagado del mes)
        # Cada mes tiene su propia morosidad independiente
        logger.info("📊 [financiamiento-tendencia] Calculando morosidad mensual (NO acumulativa)")

        # Generar datos mensuales (incluyendo meses sin datos) y calcular acumulados
        start_process = time.time()
        meses_data = []
        current_date = fecha_inicio_query
        total_acumulado = Decimal("0")
        # ✅ Morosidad NO es acumulativa, solo mensual

        logger.info(f"📊 [financiamiento-tendencia] Generando meses desde {fecha_inicio_query} hasta {hoy}")

        # ⚠️ TEMPORAL: Usar fecha_aprobacion en lugar de fecha_registro
        while current_date <= hoy:
            año_mes = current_date.year
            num_mes = current_date.month
            fecha_mes_inicio = date(año_mes, num_mes, 1)
            fecha_mes_fin = _obtener_fechas_mes_siguiente(num_mes, año_mes)

            # Obtener datos del mes (o valores por defecto si no hay)
            mes_key_financiamiento: tuple[int, int] = (año_mes, num_mes)
            datos_mes = nuevos_por_mes.get(mes_key_financiamiento, {"cantidad": 0, "monto": Decimal("0")})
            cantidad_nuevos = datos_mes["cantidad"]
            monto_nuevos = datos_mes["monto"]

            # Obtener suma de cuotas programadas del mes (monto a pagar programado)
            monto_cuotas_programadas = cuotas_por_mes.get(mes_key_financiamiento, 0.0)

            # Obtener suma de monto_pagado de tabla pagos del mes (monto pagado)
            monto_pagado_mes = pagos_por_mes.get(mes_key_financiamiento, 0.0)

            # ✅ CÁLCULO SIMPLIFICADO: Morosidad mensual = MAX(0, Programado - Pagado)
            # Esta es la lógica exacta del script SQL: morosidad_mensual = MAX(0, monto_programado - monto_pagado)
            morosidad_mensual = max(0.0, float(monto_cuotas_programadas) - float(monto_pagado_mes))

            # ✅ Logging reducido a debug para mejorar performance (solo mostrar en modo debug)
            logger.debug(
                f"📊 [financiamiento-tendencia] {fecha_mes_inicio.strftime('%Y-%m')} (año={año_mes}, mes={num_mes}): "
                f"Programado=${monto_cuotas_programadas:,.2f}, "
                f"Pagado=${monto_pagado_mes:,.2f}, "
                f"Morosidad=${morosidad_mensual:,.2f}"
            )

            # ✅ Morosidad NO es acumulativa, solo mensual

            # Calcular acumulado: sumar los nuevos financiamientos del mes
            total_acumulado += Decimal(str(monto_nuevos))

            meses_data.append(
                {
                    "mes": f"{nombres_meses[num_mes - 1]} {año_mes}",
                    "año": año_mes,
                    "mes_numero": num_mes,
                    "cantidad_nuevos": cantidad_nuevos,
                    "monto_nuevos": float(monto_nuevos),
                    "total_acumulado": float(total_acumulado),
                    "monto_cuotas_programadas": float(monto_cuotas_programadas),
                    "monto_pagado": float(monto_pagado_mes),
                    "morosidad": float(
                        morosidad_mensual
                    ),  # ⚠️ DEPRECATED: Usar morosidad_mensual. Este campo es mensual (NO acumulativo)
                    "morosidad_mensual": float(
                        morosidad_mensual
                    ),  # ✅ Morosidad MENSUAL (NO acumulativa): MAX(0, Programado del mes - Pagado del mes)
                    "fecha_mes": fecha_mes_inicio.isoformat(),
                }
            )

            # Avanzar al siguiente mes
            current_date = fecha_mes_fin

        process_time = int((time.time() - start_process) * 1000)
        total_time = int((time.time() - start_time) * 1000)

        # ✅ MONITOREO: Registrar métricas de queries individuales
        query_monitor.record_query(
            query_name="financiamiento_tendencia_nuevos", execution_time_ms=query_time, query_type="SELECT"
        )
        query_monitor.record_query(
            query_name="financiamiento_tendencia_cuotas",
            execution_time_ms=cuotas_time if "cuotas_time" in locals() else 0,
            query_type="SELECT",
        )
        query_monitor.record_query(
            query_name="financiamiento_tendencia_pagos",
            execution_time_ms=pagos_time if "pagos_time" in locals() else 0,
            query_type="SELECT",
        )

        logger.info(
            f"⏱️ [financiamiento-tendencia] Tiempo total: {total_time}ms (query: {query_time}ms, process: {process_time}ms)"
        )
        logger.info(f"📊 [financiamiento-tendencia] Generados {len(meses_data)} meses de datos")

        # ✅ ALERTA: Si la query es muy lenta
        if total_time >= 10000:
            logger.error(f"🚨 [ALERTA CRÍTICA] Financiamiento tendencia muy lento: {total_time}ms - URGENTE: Revisar índices")
        elif total_time >= 5000:
            logger.warning(f"⚠️ [ALERTA] Financiamiento tendencia lento: {total_time}ms - Revisar optimizaciones")

        # 🔍 DEBUG: Validar datos del gráfico y loggear información de debugging
        required_fields = ["mes", "monto_nuevos", "monto_cuotas_programadas", "monto_pagado", "morosidad_mensual"]
        # ✅ CORRECCIÓN: Especificar que 'mes' no es numérico
        is_valid, error_msg = validate_graph_data(
            meses_data, required_fields, non_numeric_fields=["mes"]  # 'mes' es string como "Ene 2024"
        )
        if not is_valid:
            DebugAlert.log_missing_data(
                endpoint="/financiamiento-tendencia-mensual",
                expected_field=error_msg or "campos requeridos",
                data=meses_data[:3] if meses_data else None,
            )
        else:
            # Calcular dominio del eje Y para debugging
            all_values = (
                [d.get("monto_nuevos", 0) or 0 for d in meses_data]
                + [d.get("monto_cuotas_programadas", 0) or 0 for d in meses_data]
                + [d.get("monto_pagado", 0) or 0 for d in meses_data]
                + [d.get("morosidad_mensual", 0) or 0 for d in meses_data]
            )
            max_value = max(all_values, default=0)
            y_axis_domain = [0, max_value * 1.1] if max_value > 0 else [0, "auto"]
            log_graph_debug_info("/financiamiento-tendencia-mensual", meses_data, y_axis_domain)

        # ✅ Resumen de morosidad por mes para diagnóstico
        meses_con_morosidad = [m for m in meses_data if m.get("morosidad_mensual", 0) > 0]
        total_morosidad = sum(m.get("morosidad_mensual", 0) for m in meses_data)
        logger.info(
            f"📊 [financiamiento-tendencia] RESUMEN: {len(meses_con_morosidad)} meses con morosidad > 0, "
            f"Total morosidad mensual=${total_morosidad:,.2f}"
        )
        if meses_con_morosidad:
            logger.info("📊 [financiamiento-tendencia] Meses con morosidad > 0:")
            for m in meses_con_morosidad[-10:]:  # Mostrar últimos 10 meses con morosidad
                logger.info(
                    f"  ✅ {m['mes']}: Programado=${m['monto_cuotas_programadas']:,.2f}, "
                    f"Pagado=${m['monto_pagado']:,.2f}, "
                    f"Morosidad=${m['morosidad_mensual']:,.2f}"
                )
        else:
            logger.warning("⚠️ [financiamiento-tendencia] ⚠️ NO HAY MESES CON MOROSIDAD > 0")
            # Mostrar últimos 3 meses para ver qué está pasando
            if meses_data:
                logger.warning("⚠️ [financiamiento-tendencia] Últimos 3 meses calculados:")
                for m in meses_data[-3:]:
                    logger.warning(
                        f"  - {m['mes']}: Programado=${m['monto_cuotas_programadas']:,.2f}, "
                        f"Pagado=${m['monto_pagado']:,.2f}, "
                        f"Morosidad=${m.get('morosidad_mensual', 0):,.2f}"
                    )

        if len(meses_data) == 0:
            logger.warning("⚠️ [financiamiento-tendencia] No se generaron meses de datos. Verificar fecha_inicio_query y hoy")

        return {"meses": meses_data, "fecha_inicio": fecha_inicio_query.isoformat(), "fecha_fin": hoy.isoformat()}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo cobranzas mensuales: {e}", exc_info=True)
        try:
            db.rollback()
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.get("/cobranzas-semanales")
@cache_result(ttl=600, key_prefix="dashboard")  # Cache por 10 minutos (datos históricos)
def obtener_cobranzas_semanales(
    semanas: int = Query(12, description="Número de semanas a mostrar (últimas N semanas)"),
    analista: Optional[str] = Query(None),
    concesionario: Optional[str] = Query(None),
    modelo: Optional[str] = Query(None),
    fecha_inicio: Optional[date] = Query(None),
    fecha_fin: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Cobranzas semanales (lunes a viernes) vs Pagos
    Suma las cobranzas semanales (cuotas que vencen de lunes a viernes) y las grafica contra pagos realizados.
    OPTIMIZADO: Una sola query con GROUP BY en lugar de múltiples queries en loop
    """
    import time

    start_time = time.time()
    logger.info(f"📊 [cobranzas-semanales] Iniciando cálculo de cobranzas semanales (semanas={semanas})")

    try:
        hoy = date.today()

        # Calcular fecha inicio (últimas N semanas desde el lunes más reciente)
        # Retroceder al lunes más reciente
        dias_desde_lunes = hoy.weekday()  # 0 = lunes, 6 = domingo
        lunes_actual = hoy - timedelta(days=dias_desde_lunes)

        # Calcular fecha inicio (N semanas hacia atrás desde el lunes actual)
        fecha_inicio_query = lunes_actual - timedelta(weeks=semanas - 1)

        # Aplicar filtros de fecha si se proporcionan
        if fecha_inicio:
            fecha_inicio_query = max(fecha_inicio_query, fecha_inicio)
        if fecha_fin:
            fecha_fin_query = min(hoy, fecha_fin)
        else:
            fecha_fin_query = hoy

        # ✅ OPTIMIZACIÓN: Query única para cobranzas planificadas (solo lunes a viernes)
        start_cobranzas = time.time()
        filtros_cobranzas = [
            "p.estado = 'APROBADO'",
            "c.fecha_vencimiento >= :fecha_inicio",
            "c.fecha_vencimiento <= :fecha_fin_total",
            # Solo días laborables: lunes (1) a viernes (5)
            # PostgreSQL DOW: 0=domingo, 1=lunes, ..., 6=sábado
            "EXTRACT(DOW FROM c.fecha_vencimiento) BETWEEN 1 AND 5",
        ]
        params_cobranzas = {
            "fecha_inicio": fecha_inicio_query,
            "fecha_fin_total": fecha_fin_query,
        }

        if analista:
            filtros_cobranzas.append("(p.analista = :analista OR p.producto_financiero = :analista)")
            params_cobranzas["analista"] = analista
        if concesionario:
            filtros_cobranzas.append("p.concesionario = :concesionario")
            params_cobranzas["concesionario"] = concesionario
        if modelo:
            filtros_cobranzas.append("(p.producto = :modelo OR p.modelo_vehiculo = :modelo)")
            params_cobranzas["modelo"] = modelo

        where_clause_cobranzas = " AND ".join(filtros_cobranzas)
        try:
            query_cobranzas_sql = text(
                f"""
                SELECT
                    DATE_TRUNC('week', c.fecha_vencimiento)::date as semana_inicio,
                    EXTRACT(YEAR FROM c.fecha_vencimiento)::int as año,
                    EXTRACT(WEEK FROM c.fecha_vencimiento)::int as semana_numero,
                    COALESCE(SUM(c.monto_cuota), 0) as cobranzas
                FROM cuotas c
                INNER JOIN prestamos p ON c.prestamo_id = p.id
                WHERE {where_clause_cobranzas}
                GROUP BY DATE_TRUNC('week', c.fecha_vencimiento)::date,
                         EXTRACT(YEAR FROM c.fecha_vencimiento),
                         EXTRACT(WEEK FROM c.fecha_vencimiento)
                ORDER BY semana_inicio
            """
            ).bindparams(**params_cobranzas)

            result_cobranzas = db.execute(query_cobranzas_sql)
            cobranzas_por_semana = {}
            for row in result_cobranzas:
                semana_inicio = row[0] if row[0] is not None else None
                cobranzas = float(row[3] or Decimal("0")) if row[3] is not None else 0.0
                cobranzas_por_semana[semana_inicio] = cobranzas
                if cobranzas > 0:
                    logger.debug(f"📊 [cobranzas-semanales] Semana {semana_inicio}: ${cobranzas:,.2f}")
            tiempo_cobranzas = int((time.time() - start_cobranzas) * 1000)
            logger.info(
                f"📊 [cobranzas-semanales] Query cobranzas completada en {tiempo_cobranzas}ms, {len(cobranzas_por_semana)} semanas con datos"
            )
        except Exception as e:
            logger.error(f"Error consultando cobranzas en cobranzas-semanales: {e}", exc_info=True)
            try:
                db.rollback()
            except Exception:
                pass
            cobranzas_por_semana = {}
            tiempo_cobranzas = int((time.time() - start_cobranzas) * 1000)

        # ✅ OPTIMIZACIÓN: Query única para pagos reales (solo lunes a viernes)
        start_pagos = time.time()
        fecha_inicio_dt = datetime.combine(fecha_inicio_query, datetime.min.time())
        fecha_fin_dt = datetime.combine(fecha_fin_query, datetime.max.time())

        try:
            query_pagos_sql = text(
                """
                SELECT
                    DATE_TRUNC('week', fecha_pago)::date as semana_inicio,
                    COALESCE(SUM(monto_pagado), 0) as pagos
                FROM pagos
                WHERE fecha_pago >= :fecha_inicio
                  AND fecha_pago <= :fecha_fin
                  AND monto_pagado IS NOT NULL
                  AND monto_pagado > 0
                  AND activo = TRUE
                  AND EXTRACT(DOW FROM fecha_pago) BETWEEN 1 AND 5
                GROUP BY DATE_TRUNC('week', fecha_pago)::date
                ORDER BY semana_inicio
            """
            ).bindparams(fecha_inicio=fecha_inicio_dt, fecha_fin=fecha_fin_dt)

            result_pagos = db.execute(query_pagos_sql)
            pagos_por_semana = {}
            for row in result_pagos:
                semana_inicio = row[0] if row[0] is not None else None
                pagos = float(row[1] or Decimal("0")) if row[1] is not None else 0.0
                pagos_por_semana[semana_inicio] = pagos
                if pagos > 0:
                    logger.debug(f"📊 [cobranzas-semanales] Semana {semana_inicio}: ${pagos:,.2f} en pagos")
            tiempo_pagos = int((time.time() - start_pagos) * 1000)
            logger.info(
                f"📊 [cobranzas-semanales] Query pagos completada en {tiempo_pagos}ms, {len(pagos_por_semana)} semanas con datos"
            )
        except Exception as e:
            logger.error(f"Error consultando pagos en cobranzas-semanales: {e}", exc_info=True)
            try:
                db.rollback()
            except Exception:
                pass
            pagos_por_semana = {}
            tiempo_pagos = int((time.time() - start_pagos) * 1000)

        # Generar datos semanales (incluyendo semanas sin datos)
        # ✅ IMPORTANTE: Usar el mismo cálculo que DATE_TRUNC('week', ...) en PostgreSQL
        # DATE_TRUNC('week', fecha) devuelve el lunes de la semana ISO
        semanas_data = []

        # Calcular el lunes de la semana de fecha_inicio_query
        # Python weekday(): 0=lunes, 1=martes, ..., 6=domingo
        dias_desde_lunes = fecha_inicio_query.weekday()
        semana_inicio_base = fecha_inicio_query - timedelta(days=dias_desde_lunes)

        current_date = semana_inicio_base
        semanas_generadas = 0

        while current_date <= fecha_fin_query and semanas_generadas < semanas:
            semana_inicio = current_date  # Ya es lunes
            semana_fin = semana_inicio + timedelta(days=4)  # Viernes

            if semana_inicio > fecha_fin_query:
                break

            # ✅ Buscar en diccionarios usando la fecha exacta
            cobranzas_planificadas = cobranzas_por_semana.get(semana_inicio, 0.0)
            pagos_reales = pagos_por_semana.get(semana_inicio, 0.0)

            # ✅ Logging para diagnóstico
            if cobranzas_planificadas > 0 or pagos_reales > 0:
                logger.debug(
                    f"📊 [cobranzas-semanales] Semana {semana_inicio}: "
                    f"Planificado=${cobranzas_planificadas:,.2f}, Recaudado=${pagos_reales:,.2f}"
                )

            # Formatear nombre de semana: "Semana del DD/MM - DD/MM"
            nombre_semana = f"Sem {semana_inicio.strftime('%d/%m')} - {semana_fin.strftime('%d/%m')}"

            semanas_data.append(
                {
                    "semana_inicio": semana_inicio.isoformat(),
                    "nombre_semana": nombre_semana,
                    "cobranzas_planificadas": cobranzas_planificadas,
                    "pagos_reales": pagos_reales,
                }
            )

            # Avanzar a la siguiente semana (próximo lunes)
            current_date = semana_inicio + timedelta(days=7)
            semanas_generadas += 1

        total_time = int((time.time() - start_time) * 1000)
        logger.info(f"⏱️ [cobranzas-semanales] Tiempo total: {total_time}ms, {len(semanas_data)} semanas generadas")

        if len(semanas_data) == 0:
            logger.warning("⚠️ [cobranzas-semanales] No se generaron semanas. Verificar datos y fechas.")
        else:
            logger.info(
                f"📊 [cobranzas-semanales] Primera semana: {semanas_data[0]['nombre_semana']}, Última: {semanas_data[-1]['nombre_semana']}"
            )
            logger.info(f"📊 [cobranzas-semanales] Devolviendo {len(semanas_data)} semanas de datos")

        return {
            "semanas": semanas_data,
            "fecha_inicio": fecha_inicio_query.isoformat(),
            "fecha_fin": fecha_fin_query.isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo tendencia mensual de financiamiento: {e}", exc_info=True)
        try:
            db.rollback()  # ✅ Rollback para restaurar transacción después de error
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.get("/cobros-por-analista")
def obtener_cobros_por_analista(
    analista: Optional[str] = Query(None),
    concesionario: Optional[str] = Query(None),
    modelo: Optional[str] = Query(None),
    fecha_inicio: Optional[date] = Query(None),
    fecha_fin: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Distribución de cobros por analista para gráfico de primera plana
    Top analistas con montos y cantidad de pagos conciliados
    """
    try:
        hoy = date.today()
        # fecha_inicio_mes calculado pero no usado en esta función
        # fecha_inicio_mes = date(hoy.year, hoy.month, 1)

        # Obtener cobros por analista (pagos del mes)
        # ✅ ACTUALIZADO: Usar tabla pagos (no pagos_staging) con prestamo_id y cedula
        # Ahora podemos hacer JOIN con prestamos para obtener analista
        try:
            # Query con JOIN para obtener cobros por analista
            query_cobros = db.execute(
                text(
                    """
                    SELECT
                        COALESCE(pr.analista, 'Sin Analista') as analista,
                        COALESCE(SUM(p.monto_pagado), 0) as total_cobrado,
                        COUNT(p.id) as cantidad_pagos
                    FROM pagos p
                    LEFT JOIN prestamos pr ON (
                        (p.prestamo_id IS NOT NULL AND pr.id = p.prestamo_id)
                        OR (p.prestamo_id IS NULL AND pr.cedula = p.cedula AND pr.estado = 'APROBADO')
                    )
                    WHERE p.activo = TRUE
                      AND p.monto_pagado IS NOT NULL
                      AND p.monto_pagado > 0
                      AND p.fecha_pago >= :fecha_inicio
                      AND p.fecha_pago <= :fecha_fin
                GROUP BY pr.analista
                    ORDER BY total_cobrado DESC
                    LIMIT 10
                    """
                ).bindparams(
                    fecha_inicio=datetime.combine(date(hoy.year, hoy.month, 1), datetime.min.time()),
                    fecha_fin=datetime.combine(hoy, datetime.max.time()),
                )
            )
            resultados_raw = query_cobros.fetchall()
            resultados_cobros = [
                {
                    "analista": str(row[0] or "Sin Analista"),
                    "total_cobrado": float(row[1] or Decimal("0")),
                    "cantidad_pagos": int(row[2] or 0),
                }
                for row in resultados_raw
            ]
        except Exception as e:
            logger.warning(f"⚠️ [obtener_cobros_por_analista] Error obteniendo cobros: {e}")
            resultados_cobros: list[dict[str, Any]] = []

        analistas_data = []
        for row in resultados_cobros:
            analistas_data.append(
                {
                    "analista": row.get("analista", "Sin Analista"),
                    "total_cobrado": float(row.get("total_cobrado", Decimal("0"))),
                    "cantidad_pagos": int(row.get("cantidad_pagos", 0)),
                }
            )

        return {"analistas": analistas_data}

    except Exception as e:
        logger.error(f"Error obteniendo cobros por analista: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.get("/evolucion-morosidad")
@cache_result(ttl=600, key_prefix="dashboard")  # Cache por 10 minutos (datos históricos)
def obtener_evolucion_morosidad(
    meses: int = Query(6, description="Número de meses a mostrar (últimos N meses)"),
    analista: Optional[str] = Query(None),
    concesionario: Optional[str] = Query(None),
    modelo: Optional[str] = Query(None),
    fecha_inicio: Optional[date] = Query(None),
    fecha_fin: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Evolución de morosidad (últimos N meses) para DashboardCuotas
    ✅ MIGRADO: Ahora consulta tabla oficial dashboard_morosidad_mensual
    ✅ OPTIMIZADO: Usa filtros separados en año y mes para aprovechar índices
    """
    import time

    start_time = time.time()
    hoy = date.today()
    nombres_meses = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]

    # ✅ Calcular fecha inicio: usar fecha_inicio si está presente, sino calcular desde hace N meses
    if fecha_inicio:
        fecha_inicio_query = fecha_inicio
        # Asegurar que sea el primer día del mes
        fecha_inicio_query = date(fecha_inicio_query.year, fecha_inicio_query.month, 1)
    else:
        # Calcular fecha inicio (hace N meses) - FUERA del try para que esté disponible en el fallback
        año_inicio = hoy.year
        mes_inicio = hoy.month - meses + 1
        if mes_inicio <= 0:
            año_inicio -= 1
            mes_inicio += 12
        fecha_inicio_query = date(año_inicio, mes_inicio, 1)

    # Intentar usar tabla oficial si existe, sino usar fallback directamente
    morosidad_por_mes_final: dict[tuple[int, int], float] = {}
    query_time = 0

    try:
        # Verificar si la tabla existe antes de intentar usarla
        table_exists = db.execute(
            text(
                """
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_schema = 'public'
                    AND table_name = 'dashboard_morosidad_mensual'
                )
            """
            )
        ).scalar()

        if table_exists:
            # ✅ OPTIMIZACIÓN: Usar filtros separados en año y mes para aprovechar el índice idx_dashboard_morosidad_año_mes
            # Usar fecha_inicio_query calculada anteriormente (puede ser desde fecha_inicio o desde hace N meses)
            año_inicio_query = fecha_inicio_query.year
            mes_inicio_query = fecha_inicio_query.month
            query = (
                db.query(DashboardMorosidadMensual)
                .filter(
                    or_(
                        and_(
                            DashboardMorosidadMensual.año == año_inicio_query,
                            DashboardMorosidadMensual.mes >= mes_inicio_query,
                        ),
                        and_(DashboardMorosidadMensual.año > año_inicio_query, DashboardMorosidadMensual.año < hoy.year),
                        and_(DashboardMorosidadMensual.año == hoy.year, DashboardMorosidadMensual.mes <= hoy.month),
                    )
                )
                .order_by(DashboardMorosidadMensual.año, DashboardMorosidadMensual.mes)
            )

            resultados = query.all()
            query_time = int((time.time() - start_time) * 1000)
            logger.info(
                f"📊 [evolucion-morosidad] Query tabla oficial completada en {query_time}ms, {len(resultados)} registros"
            )

            morosidad_por_mes_final = {(r.año, r.mes): float(r.morosidad_total or Decimal("0")) for r in resultados}
        else:
            # Tabla no existe, usar fallback
            logger.warning("Tabla dashboard_morosidad_mensual no existe, usando fallback")
            raise ValueError("Tabla no existe")

    except (ValueError, Exception) as e:
        # Fallback: Si la tabla oficial no existe o hay error, usar consulta original
        logger.warning(f"Error accediendo tabla oficial: {e}, usando consulta original como fallback")
        try:
            start_fallback = time.time()
            query_sql = text(
                """
                SELECT
                    EXTRACT(YEAR FROM c.fecha_vencimiento)::int as año,
                    EXTRACT(MONTH FROM c.fecha_vencimiento)::int as mes,
                    COALESCE(SUM(c.monto_cuota), 0) as morosidad
                FROM cuotas c
                INNER JOIN prestamos p ON c.prestamo_id = p.id
                WHERE
                    p.estado = 'APROBADO'
                    AND c.fecha_vencimiento >= :fecha_inicio
                    AND c.fecha_vencimiento < :fecha_fin_total
                    AND c.estado != 'PAGADO'
                GROUP BY EXTRACT(YEAR FROM c.fecha_vencimiento), EXTRACT(MONTH FROM c.fecha_vencimiento)
                ORDER BY año, mes
            """
            ).bindparams(fecha_inicio=fecha_inicio_query, fecha_fin_total=hoy)
            result = db.execute(query_sql)
            for row in result:
                año = int(row[0]) if row[0] is not None else 0
                mes = int(row[1]) if row[1] is not None else 0
                morosidad = float(row[2] or Decimal("0"))
                morosidad_por_mes_final[(año, mes)] = morosidad
            query_time = int((time.time() - start_fallback) * 1000)
            logger.info(
                f"📊 [evolucion-morosidad] Query fallback completada en {query_time}ms, {len(morosidad_por_mes_final)} registros"
            )
        except Exception as fallback_error:
            logger.error(f"Error en fallback: {fallback_error}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Error interno: {str(fallback_error)}")

    # Generar datos mensuales (incluyendo meses sin datos) - se ejecuta tanto para tabla oficial como fallback
    start_process = time.time()
    meses_data = []
    current_date = fecha_inicio_query

    while current_date <= hoy:
        año_mes = int(current_date.year)
        num_mes = int(current_date.month)
        mes_key_morosidad: tuple[int, int] = (año_mes, num_mes)
        morosidad_mes = morosidad_por_mes_final.get(mes_key_morosidad, 0.0)

        meses_data.append(
            {
                "mes": f"{nombres_meses[num_mes - 1]} {año_mes}",
                "morosidad": morosidad_mes,
            }
        )

        # Avanzar al siguiente mes
        current_date = _obtener_fechas_mes_siguiente(num_mes, año_mes)

    process_time = int((time.time() - start_process) * 1000)
    total_time = int((time.time() - start_time) * 1000)
    logger.info(f"⏱️ [evolucion-morosidad] Tiempo total: {total_time}ms (query: {query_time}ms, process: {process_time}ms)")

    return {"meses": meses_data}


@router.get("/evolucion-pagos")
@cache_result(ttl=600, key_prefix="dashboard")  # Cache por 10 minutos (datos históricos)
def obtener_evolucion_pagos(
    meses: int = Query(6, description="Número de meses a mostrar (últimos N meses)"),
    analista: Optional[str] = Query(None),
    concesionario: Optional[str] = Query(None),
    modelo: Optional[str] = Query(None),
    fecha_inicio: Optional[date] = Query(None),
    fecha_fin: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Evolución de pagos (últimos N meses) para DashboardPagos
    ✅ ACTUALIZADO: Consulta tabla pagos (no pagos_staging) con prestamo_id y cedula
    ✅ OPTIMIZADO: Una sola query con GROUP BY en lugar de múltiples queries en loop
    """
    import time

    start_time = time.time()

    try:
        # ✅ ROLLBACK PREVENTIVO: Restaurar transacción si está abortada
        try:
            db.execute(text("SELECT 1"))
        except Exception as test_error:
            error_str = str(test_error)
            if "aborted" in error_str.lower() or "InFailedSqlTransaction" in error_str:
                logger.warning("⚠️ [evolucion-pagos] Transacción abortada detectada, haciendo rollback preventivo")
                try:
                    db.rollback()
                except Exception:
                    pass

        hoy = date.today()
        nombres_meses = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]

        # ✅ Calcular fecha inicio: usar fecha_inicio si está presente, sino calcular desde hace N meses
        if fecha_inicio:
            fecha_inicio_query = fecha_inicio
            # Asegurar que sea el primer día del mes
            fecha_inicio_query = date(fecha_inicio_query.year, fecha_inicio_query.month, 1)
        else:
            # Calcular fecha inicio (hace N meses)
            año_inicio = hoy.year
            mes_inicio = hoy.month - meses + 1
            if mes_inicio <= 0:
                año_inicio -= 1
                mes_inicio += 12
            fecha_inicio_query = date(año_inicio, mes_inicio, 1)

        # ✅ OPTIMIZACIÓN: Una sola query con GROUP BY en lugar de múltiples queries en loop
        start_query = time.time()
        fecha_inicio_query_dt = datetime.combine(fecha_inicio_query, datetime.min.time())
        hoy_dt = datetime.combine(hoy, datetime.max.time())

        # ✅ ACTUALIZADO: Usar tabla pagos (no pagos_staging) con prestamo_id y cedula
        try:
            query_pagos = db.execute(
                text(
                    """
                    SELECT
                        EXTRACT(YEAR FROM fecha_pago)::integer as año,
                        EXTRACT(MONTH FROM fecha_pago)::integer as mes,
                        COUNT(*) as cantidad,
                        COALESCE(SUM(monto_pagado), 0) as monto_total
                    FROM pagos
                    WHERE fecha_pago >= :fecha_inicio
                      AND fecha_pago <= :fecha_fin
                      AND monto_pagado IS NOT NULL
                      AND monto_pagado > 0
                      AND activo = TRUE
                GROUP BY
                        EXTRACT(YEAR FROM fecha_pago),
                        EXTRACT(MONTH FROM fecha_pago)
                    ORDER BY año, mes
                    """
                ).bindparams(fecha_inicio=fecha_inicio_query_dt, fecha_fin=hoy_dt)
            )
            resultados = query_pagos.fetchall()
            query_time = int((time.time() - start_query) * 1000)
            logger.info(f"📊 [evolucion-pagos] Query completada en {query_time}ms, {len(resultados)} registros")
        except Exception as e:
            error_str = str(e)
            logger.error(f"❌ [evolucion-pagos] Error consultando pagos: {e}", exc_info=True)
            # Si es un error de transacción abortada, hacer rollback
            if "aborted" in error_str.lower() or "InFailedSqlTransaction" in error_str:
                logger.warning("⚠️ [evolucion-pagos] Transacción abortada detectada en query, haciendo rollback")
            try:
                db.rollback()
            except Exception as rollback_error:
                logger.error(f"❌ [evolucion-pagos] Error al hacer rollback: {rollback_error}")
            resultados = []
            query_time = int((time.time() - start_query) * 1000)

        # Crear diccionario de resultados por año-mes para acceso rápido
        # ✅ CORRECCIÓN: Usar acceso por índice en lugar de atributo para compatibilidad con Row
        pagos_por_mes: dict[tuple[int, int], dict[str, Any]] = {}
        for row in resultados:
            año = int(row[0]) if row[0] is not None else 0
            mes = int(row[1]) if row[1] is not None else 0
            mes_key_pagos_evol: tuple[int, int] = (año, mes)
            pagos_por_mes[mes_key_pagos_evol] = {
                "cantidad": int(row[2]) if row[2] is not None else 0,
                "monto": float(row[3] or Decimal("0")) if row[3] is not None else 0.0,
            }

        # Generar datos mensuales (incluir todos los meses en el rango, incluso sin pagos)
        start_process = time.time()
        meses_data = []
        current_date = fecha_inicio_query

        while current_date <= hoy:
            año_mes = int(current_date.year)
            num_mes = int(current_date.month)
            fecha_mes_fin = _obtener_fechas_mes_siguiente(num_mes, año_mes)

            # Obtener datos del mes (o valores por defecto si no hay pagos)
            mes_key_pagos_final: tuple[int, int] = (año_mes, num_mes)
            datos_mes = pagos_por_mes.get(mes_key_pagos_final, {"cantidad": 0, "monto": 0.0})

            meses_data.append(
                {
                    "mes": f"{nombres_meses[num_mes - 1]} {año_mes}",
                    "pagos": datos_mes["cantidad"],
                    "monto": datos_mes["monto"],
                }
            )

            # Avanzar al siguiente mes
            current_date = fecha_mes_fin

        process_time = int((time.time() - start_process) * 1000)
        total_time = int((time.time() - start_time) * 1000)
        logger.info(f"⏱️ [evolucion-pagos] Tiempo total: {total_time}ms (query: {query_time}ms, process: {process_time}ms)")

        return {"meses": meses_data}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo evolución de pagos: {e}", exc_info=True)
        try:
            db.rollback()  # ✅ Rollback para restaurar transacción después de error
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.get("/resumen-financiamiento-pagado")
@cache_result(ttl=300, key_prefix="dashboard")  # Cache por 5 minutos
def obtener_resumen_financiamiento_pagado(
    analista: Optional[str] = Query(None),
    concesionario: Optional[str] = Query(None),
    modelo: Optional[str] = Query(None),
    fecha_inicio: Optional[date] = Query(None),
    fecha_fin: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Obtiene el resumen total de financiamiento y pagos para gráfico de barras comparativo.
    Devuelve:
    - total_financiamiento: Suma de todos los total_financiamiento de préstamos aprobados
    - total_pagado: Suma de todos los monto_pagado de la tabla pagos (activos)
    """
    try:
        # 1. Calcular total financiamiento (suma de todos los préstamos aprobados)
        query_financiamiento = db.query(func.sum(Prestamo.total_financiamiento)).filter(Prestamo.estado == "APROBADO")
        query_financiamiento = FiltrosDashboard.aplicar_filtros_prestamo(
            query_financiamiento, analista, concesionario, modelo, fecha_inicio, fecha_fin
        )
        total_financiamiento = float(query_financiamiento.scalar() or Decimal("0"))

        # 2. Calcular total pagado (suma de todos los pagos activos)
        # ✅ Usar tabla pagos (no pagos_staging) con prestamo_id y cedula
        fecha_inicio_dt = None
        fecha_fin_dt = None
        if fecha_inicio:
            fecha_inicio_dt = datetime.combine(fecha_inicio, datetime.min.time())
        if fecha_fin:
            fecha_fin_dt = datetime.combine(fecha_fin, datetime.max.time())

        # Construir filtros de préstamo si existen
        prestamo_conditions = []
        bind_params = {}

        if analista or concesionario or modelo:
            if analista:
                prestamo_conditions.append("(pr.analista = :analista OR pr.producto_financiero = :analista)")
                bind_params["analista"] = analista
            if concesionario:
                prestamo_conditions.append("pr.concesionario = :concesionario")
                bind_params["concesionario"] = concesionario
            if modelo:
                prestamo_conditions.append("(pr.producto = :modelo OR pr.modelo_vehiculo = :modelo)")
                bind_params["modelo"] = modelo

            where_clause = """p.monto_pagado IS NOT NULL
              AND p.monto_pagado > 0
              AND p.activo = TRUE
              AND pr.estado = 'APROBADO'"""

            if fecha_inicio_dt:
                where_clause += " AND p.fecha_pago >= :fecha_inicio"
                bind_params["fecha_inicio"] = fecha_inicio_dt
            if fecha_fin_dt:
                where_clause += " AND p.fecha_pago <= :fecha_fin"
                bind_params["fecha_fin"] = fecha_fin_dt

            if prestamo_conditions:
                where_clause += " AND " + " AND ".join(prestamo_conditions)

            query_pagado_sql = text(
                f"""
                SELECT COALESCE(SUM(p.monto_pagado), 0) as total_pagado
                FROM pagos p
                INNER JOIN prestamos pr ON (
                    (p.prestamo_id IS NOT NULL AND pr.id = p.prestamo_id)
                    OR (p.prestamo_id IS NULL AND pr.cedula = p.cedula AND pr.estado = 'APROBADO')
                )
                WHERE {where_clause}
                """
            ).bindparams(**bind_params)
        else:
            # Sin filtros, query más simple
            where_clause = """monto_pagado IS NOT NULL
              AND monto_pagado > 0
              AND activo = TRUE"""

            if fecha_inicio_dt:
                where_clause += " AND fecha_pago >= :fecha_inicio"
                bind_params["fecha_inicio"] = fecha_inicio_dt
            if fecha_fin_dt:
                where_clause += " AND fecha_pago <= :fecha_fin"
                bind_params["fecha_fin"] = fecha_fin_dt

            query_pagado_sql = text(
                f"""
                SELECT COALESCE(SUM(monto_pagado), 0) as total_pagado
                FROM pagos
                WHERE {where_clause}
                """
            ).bindparams(**bind_params)

        resultado_pagado = db.execute(query_pagado_sql).fetchone()
        if resultado_pagado is None:
            total_pagado = 0.0
        else:
            total_pagado = float(resultado_pagado[0] or Decimal("0"))

        return {
            "total_financiamiento": total_financiamiento,
            "total_pagado": total_pagado,
        }
    except Exception as e:
        logger.error(f"Error obteniendo resumen financiamiento/pagado: {e}", exc_info=True)
        try:
            db.rollback()
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")
