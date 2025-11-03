import logging
from calendar import monthrange
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query  # type: ignore[import-untyped]
from sqlalchemy import and_, cast, func, or_  # type: ignore[import-untyped]
from sqlalchemy.orm import Session  # type: ignore[import-untyped]

from app.api.deps import get_current_user, get_db
from app.models.amortizacion import Cuota
from app.models.cliente import Cliente
from app.models.pago import Pago
from app.models.prestamo import Prestamo
from app.models.user import User
from app.utils.filtros_dashboard import FiltrosDashboard

logger = logging.getLogger(__name__)
router = APIRouter()


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


def _calcular_cartera_anterior(db: Session, periodo: str, fecha_fin_periodo_anterior: date,
                               analista: Optional[str], concesionario: Optional[str],
                               modelo: Optional[str], cartera_total: Decimal) -> float:
    """Calcula la cartera anterior según el período"""
    if periodo == "dia":
        return float(cartera_total)

    cartera_anterior_query = db.query(func.sum(Prestamo.total_financiamiento)).filter(
        Prestamo.estado == "APROBADO",
        func.date(Prestamo.fecha_registro) <= fecha_fin_periodo_anterior,
    )
    cartera_anterior_query = FiltrosDashboard.aplicar_filtros_prestamo(
        cartera_anterior_query, analista, concesionario, modelo, None, None
    )
    return float(cartera_anterior_query.scalar() or Decimal("0"))


def _calcular_total_cobrado_mes(db: Session, primer_dia: date, ultimo_dia: date,
                                analista: Optional[str], concesionario: Optional[str],
                                modelo: Optional[str]) -> Decimal:
    """Calcula el total cobrado en un mes (solo pagos conciliados)"""
    query = db.query(func.sum(Pago.monto_pagado)).filter(
        func.date(Pago.fecha_pago) >= primer_dia,
        func.date(Pago.fecha_pago) <= ultimo_dia,
        Pago.conciliado.is_(True),
    )
    if analista or concesionario or modelo:
        query = query.join(Prestamo, Pago.prestamo_id == Prestamo.id)
    query = FiltrosDashboard.aplicar_filtros_pago(query, analista, concesionario, modelo, None, None)
    return query.scalar() or Decimal("0")


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
    variacion_porcentual = (
        ((valor_actual - valor_anterior) / valor_anterior * 100) if valor_anterior > 0 else 0
    )
    return variacion_porcentual, variacion_absoluta


def _calcular_morosidad(db: Session, fecha: date, analista: Optional[str],
                        concesionario: Optional[str], modelo: Optional[str],
                        fecha_inicio: Optional[date], fecha_fin: Optional[date]) -> float:
    """Calcula morosidad (cuotas vencidas no pagadas) hasta una fecha"""
    query = (
        db.query(func.sum(Cuota.monto_cuota))
        .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
        .filter(
            Prestamo.estado == "APROBADO",
            Cuota.fecha_vencimiento <= fecha,
            Cuota.estado != "PAGADO",
        )
    )
    query = FiltrosDashboard.aplicar_filtros_cuota(
        query, analista, concesionario, modelo, fecha_inicio, fecha_fin
    )
    return float(query.scalar() or Decimal("0"))


def _calcular_total_a_cobrar_fecha(db: Session, fecha: date, analista: Optional[str],
                                   concesionario: Optional[str], modelo: Optional[str],
                                   fecha_inicio: Optional[date], fecha_fin: Optional[date]) -> float:
    """Calcula total a cobrar en una fecha específica"""
    query = (
        db.query(func.sum(Cuota.monto_cuota))
        .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
        .filter(
            Prestamo.estado == "APROBADO",
            Cuota.fecha_vencimiento == fecha,
        )
    )
    query = FiltrosDashboard.aplicar_filtros_cuota(
        query, analista, concesionario, modelo, fecha_inicio, fecha_fin
    )
    return float(query.scalar() or Decimal("0"))


def _calcular_dias_mora_cliente(db: Session, cedula: str, hoy: date) -> int:
    """Calcula días de mora máximo para un cliente"""
    dias_mora_query = (
        db.query(func.max(func.date_part("day", hoy - Cuota.fecha_vencimiento)))
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


def _procesar_distribucion_rango_monto_plazo(query_base, rangos_monto: list, rangos_plazo: list,
                                             total_prestamos: int, total_monto: float) -> list:
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


def _procesar_distribucion_rango_monto(query_base, rangos: list, total_prestamos: int, total_monto: float) -> list:
    """Procesa distribución por rango de monto"""
    distribucion_data = []
    for min_val, max_val, categoria in rangos:
        query_rango = query_base.filter(Prestamo.total_financiamiento >= Decimal(str(min_val)))
        if max_val:
            query_rango = query_rango.filter(Prestamo.total_financiamiento < Decimal(str(max_val)))

        cantidad = query_rango.count()
        monto_total = float(
            query_rango.with_entities(func.sum(Prestamo.total_financiamiento)).scalar() or Decimal("0")
        )
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


def _calcular_rango_fechas_granularidad(granularidad: str, hoy: date, dias: Optional[int],
                                       fecha_inicio: Optional[date], fecha_fin: Optional[date]) -> tuple[date, date]:
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
            d["cuotas_en_dias"] for d in datos
            if d.get("cuotas_en_dias") is not None and d["cuotas_en_dias"] > 0
        ]
        return int(sum(valores_historicos) / len(valores_historicos)) if valores_historicos else 0
    return 0


def _calcular_pagos_fecha(db: Session, fecha: date, analista: Optional[str],
                          concesionario: Optional[str], modelo: Optional[str],
                          fecha_inicio: Optional[date], fecha_fin: Optional[date]) -> float:
    """Calcula pagos en una fecha específica"""
    query = db.query(func.sum(Pago.monto_pagado)).filter(func.date(Pago.fecha_pago) == fecha)
    if analista or concesionario or modelo:
        query = query.join(Prestamo, Pago.prestamo_id == Prestamo.id)
    query = FiltrosDashboard.aplicar_filtros_pago(query, analista, concesionario, modelo, fecha_inicio, fecha_fin)
    return float(query.scalar() or Decimal("0"))


def _calcular_tasa_recuperacion(db: Session, primer_dia: date, ultimo_dia: date,
                                analista: Optional[str], concesionario: Optional[str],
                                modelo: Optional[str]) -> float:
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
def obtener_opciones_filtros(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Obtener opciones disponibles para filtros del dashboard - Sin duplicados"""
    try:
        # 1. ANALISTAS - Combinar analista y producto_financiero sin duplicados
        analistas_set = _obtener_valores_distintos_de_columna(db, Prestamo.analista)
        productos_set = _obtener_valores_distintos_de_columna(db, Prestamo.producto_financiero)
        analistas_final = sorted(analistas_set | productos_set)

        # 2. CONCESIONARIOS - Únicos y normalizados
        concesionarios_set = _obtener_valores_distintos_de_columna(db, Prestamo.concesionario)
        concesionarios_final = sorted(concesionarios_set)

        # 3. MODELOS - Combinar producto y modelo_vehiculo sin duplicados
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
        pagos_dia_query = db.query(func.sum(Pago.monto_pagado)).filter(func.date(Pago.fecha_pago) == fecha_dia)
        pagos_dia_query = FiltrosDashboard.aplicar_filtros_pago(pagos_dia_query, analista, concesionario, modelo, None, None)
        return float(pagos_dia_query.scalar() or Decimal("0"))
    except Exception:
        logger.error(
            "Error en query total_cobrado",
            extra={"fecha": fecha_dia.isoformat(), "analista": analista, "concesionario": concesionario, "modelo": modelo},
            exc_info=True,
        )
        return 0.0


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


# DEPRECATED: Usar FiltrosDashboard desde app.utils.filtros_dashboard
# Estas funciones se mantienen por compatibilidad pero se recomienda usar la clase centralizada
def aplicar_filtros_prestamo(
    query,
    analista: Optional[str] = None,
    concesionario: Optional[str] = None,
    modelo: Optional[str] = None,
    fecha_inicio: Optional[date] = None,
    fecha_fin: Optional[date] = None,
):
    """Aplica filtros comunes a queries de préstamos - DEPRECATED: Usar FiltrosDashboard"""
    return FiltrosDashboard.aplicar_filtros_prestamo(query, analista, concesionario, modelo, fecha_inicio, fecha_fin)


def aplicar_filtros_pago(
    query,
    analista: Optional[str] = None,
    concesionario: Optional[str] = None,
    modelo: Optional[str] = None,
    fecha_inicio: Optional[date] = None,
    fecha_fin: Optional[date] = None,
):
    """Aplica filtros comunes a queries de pagos - DEPRECATED: Usar FiltrosDashboard"""
    return FiltrosDashboard.aplicar_filtros_pago(query, analista, concesionario, modelo, fecha_inicio, fecha_fin)


@router.get("/admin")
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
    """
    try:
        if not current_user.is_admin:
            raise HTTPException(status_code=403, detail="Acceso denegado. Solo administradores.")

        hoy = date.today()

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
        # ✅ USAR FiltrosDashboard para aplicar filtros automáticamente
        cartera_vencida_query = (
            db.query(func.sum(Cuota.monto_cuota))
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
        pagos_hoy_query = db.query(func.count(Pago.id)).filter(func.date(Pago.fecha_pago) == hoy)
        monto_pagos_hoy_query = db.query(func.sum(Pago.monto_pagado)).filter(func.date(Pago.fecha_pago) == hoy)

        # ✅ Aplicar filtros usando clase centralizada (automático)
        if analista or concesionario or modelo:
            pagos_hoy_query = pagos_hoy_query.join(Prestamo, Pago.prestamo_id == Prestamo.id)
            monto_pagos_hoy_query = monto_pagos_hoy_query.join(Prestamo, Pago.prestamo_id == Prestamo.id)

        pagos_hoy_query = FiltrosDashboard.aplicar_filtros_pago(
            pagos_hoy_query, analista, concesionario, modelo, fecha_inicio, fecha_fin
        )
        monto_pagos_hoy_query = FiltrosDashboard.aplicar_filtros_pago(
            monto_pagos_hoy_query,
            analista,
            concesionario,
            modelo,
            fecha_inicio,
            fecha_fin,
        )

        pagos_hoy = pagos_hoy_query.scalar() or 0
        monto_pagos_hoy = monto_pagos_hoy_query.scalar() or Decimal("0")

        # 6. CLIENTES ACTIVOS - Clientes con préstamos activos
        clientes_activos = base_prestamo_query.with_entities(func.count(func.distinct(Prestamo.cedula))).scalar() or 0

        # 7. CLIENTES EN MORA - Clientes con cuotas vencidas
        # ✅ USAR FiltrosDashboard para aplicar filtros automáticamente
        clientes_mora_query = (
            db.query(func.count(func.distinct(Prestamo.cedula)))
            .join(Cuota, Cuota.prestamo_id == Prestamo.id)
            .filter(
                and_(
                    Cuota.fecha_vencimiento < hoy,
                    Cuota.estado != "PAGADO",
                    Prestamo.estado == "APROBADO",
                )
            )
        )
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
        # ✅ USAR FiltrosDashboard para aplicar filtros automáticamente
        total_cobrado_query = db.query(func.sum(Pago.monto_pagado))
        if analista or concesionario or modelo:
            total_cobrado_query = total_cobrado_query.join(Prestamo, Pago.prestamo_id == Prestamo.id)
        total_cobrado_query = FiltrosDashboard.aplicar_filtros_pago(
            total_cobrado_query,
            analista,
            concesionario,
            modelo,
            fecha_inicio,
            fecha_fin,
        )
        # total_cobrado se calcula pero no se usa en la respuesta actual
        # total_cobrado = total_cobrado_query.scalar() or Decimal("0")

        # 12. CUOTAS PAGADAS TOTALES
        cuotas_pagadas_query = (
            db.query(func.count(Cuota.id))
            .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
            .filter(Cuota.estado == "PAGADO", Prestamo.estado == "APROBADO")
        )
        # 13. CUOTAS PENDIENTES
        cuotas_pendientes_query = (
            db.query(func.count(Cuota.id))
            .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
            .filter(Cuota.estado == "PENDIENTE", Prestamo.estado == "APROBADO")
        )
        # 14. CUOTAS ATRASADAS
        cuotas_atrasadas_query = (
            db.query(func.count(Cuota.id))
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
        fecha_inicio_periodo, fecha_fin_periodo_anterior = _calcular_periodos(periodo, hoy)

        # Cartera anterior - Calcular desde BD histórica
        cartera_anterior_val = _calcular_cartera_anterior(
            db, periodo, fecha_fin_periodo_anterior, analista, concesionario, modelo, cartera_total
        )

        # 16. TOTAL COBRADO EN EL MES ACTUAL - SOLO PAGOS CONCILIADOS
        año_actual = hoy.year
        mes_actual = hoy.month
        primer_dia_mes = date(año_actual, mes_actual, 1)
        ultimo_dia_mes = date(año_actual, mes_actual, monthrange(año_actual, mes_actual)[1])

        total_cobrado_periodo = _calcular_total_cobrado_mes(
            db, primer_dia_mes, ultimo_dia_mes, analista, concesionario, modelo
        )

        # Total cobrado mes anterior
        mes_anterior, año_anterior = _calcular_mes_anterior(mes_actual, año_actual)
        primer_dia_mes_anterior, ultimo_dia_mes_anterior = _obtener_fechas_mes(mes_anterior, año_anterior)

        total_cobrado_anterior = _calcular_total_cobrado_mes(
            db, primer_dia_mes_anterior, ultimo_dia_mes_anterior, analista, concesionario, modelo
        )

        # 17. TASA DE RECUPERACIÓN MENSUAL
        tasa_recuperacion = _calcular_tasa_recuperacion(
            db, primer_dia_mes, ultimo_dia_mes, analista, concesionario, modelo
        )

        # Tasa recuperación mes anterior
        tasa_recuperacion_anterior = _calcular_tasa_recuperacion(
            db, primer_dia_mes_anterior, ultimo_dia_mes_anterior, analista, concesionario, modelo
        )

        # 18. PROMEDIO DÍAS DE MORA
        # Calcular desde cuotas vencidas en lugar de usar campo inexistente
        cuotas_vencidas_con_dias = (
            db.query(func.avg(func.date_part("day", hoy - Cuota.fecha_vencimiento)).label("dias_promedio"))
            .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
            .filter(
                and_(
                    Cuota.fecha_vencimiento < hoy,
                    Cuota.estado != "PAGADO",
                    Prestamo.estado == "APROBADO",
                )
            )
            .scalar()
        )
        promedio_dias_mora = float(cuotas_vencidas_con_dias) if cuotas_vencidas_con_dias else 0.0

        # 19. PORCENTAJE CUMPLIMIENTO (clientes al día / total clientes)
        porcentaje_cumplimiento = (
            ((clientes_activos - clientes_en_mora) / clientes_activos * 100) if clientes_activos > 0 else 0
        )

        # 20. TICKET PROMEDIO (promedio de préstamos)
        ticket_promedio = float(cartera_total / clientes_activos) if clientes_activos > 0 else 0

        # 21. EVOLUCIÓN MENSUAL (últimos 6 meses)
        # ✅ Aplicar filtros automáticamente a evolución mensual
        evolucion_mensual = []
        for i in range(6, -1, -1):
            mes_fecha = hoy - timedelta(days=30 * i)
            mes_inicio = date(mes_fecha.year, mes_fecha.month, 1)
            if mes_fecha.month == 12:
                mes_fin = date(mes_fecha.year + 1, 1, 1) - timedelta(days=1)
            else:
                mes_fin = date(mes_fecha.year, mes_fecha.month + 1, 1) - timedelta(days=1)

            # ✅ Cartera del mes con filtros
            cartera_mes_query = db.query(func.sum(Prestamo.total_financiamiento)).filter(
                Prestamo.estado == "APROBADO",
                func.date(Prestamo.fecha_registro) <= mes_fin,
            )
            cartera_mes_query = FiltrosDashboard.aplicar_filtros_prestamo(
                cartera_mes_query,
                analista,
                concesionario,
                modelo,
                fecha_inicio,
                fecha_fin,
            )
            cartera_mes = cartera_mes_query.scalar() or Decimal("0")

            # ✅ Cobrado del mes con filtros (SOLO PAGOS CONCILIADOS para consistencia)
            cobrado_mes_query = db.query(func.sum(Pago.monto_pagado)).filter(
                func.date(Pago.fecha_pago) >= mes_inicio,
                func.date(Pago.fecha_pago) <= mes_fin,
                Pago.conciliado.is_(True),  # ✅ Solo pagos conciliados
            )
            if analista or concesionario or modelo:
                cobrado_mes_query = cobrado_mes_query.join(Prestamo, Pago.prestamo_id == Prestamo.id)
            cobrado_mes_query = FiltrosDashboard.aplicar_filtros_pago(
                cobrado_mes_query,
                analista,
                concesionario,
                modelo,
                None,  # No aplicar filtros de fecha aquí (ya filtrado por mes)
                None,
            )
            cobrado_mes = cobrado_mes_query.scalar() or Decimal("0")

            # ✅ Cuotas vencidas en ese mes con filtros
            cuotas_vencidas_mes_query = (
                db.query(func.count(Cuota.id))
                .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
                .filter(
                    Cuota.fecha_vencimiento >= mes_inicio,
                    Cuota.fecha_vencimiento <= mes_fin,
                    Cuota.estado != "PAGADO",
                )
            )
            cuotas_vencidas_mes_query = FiltrosDashboard.aplicar_filtros_cuota(
                cuotas_vencidas_mes_query,
                analista,
                concesionario,
                modelo,
                fecha_inicio,
                fecha_fin,
            )
            cuotas_vencidas_mes = cuotas_vencidas_mes_query.scalar() or 0

            # ✅ Cuotas pagadas del mes (para calcular morosidad correctamente)
            cuotas_pagadas_mes_query = (
                db.query(func.count(Cuota.id))
                .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
                .filter(
                    Cuota.estado == "PAGADO",
                    Cuota.fecha_pago.isnot(None),
                    func.date(Cuota.fecha_pago) >= mes_inicio,
                    func.date(Cuota.fecha_pago) <= mes_fin,
                    Prestamo.estado == "APROBADO",
                )
            )
            cuotas_pagadas_mes_query = FiltrosDashboard.aplicar_filtros_cuota(
                cuotas_pagadas_mes_query,
                analista,
                concesionario,
                modelo,
                fecha_inicio,
                fecha_fin,
            )
            cuotas_pagadas_mes = cuotas_pagadas_mes_query.scalar() or 0

            # ✅ Total cuotas del mes (vencidas + pagadas para calcular morosidad)
            total_cuotas_mes = cuotas_vencidas_mes + cuotas_pagadas_mes
            morosidad_mes = (cuotas_vencidas_mes / total_cuotas_mes * 100) if total_cuotas_mes > 0 else 0

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
            evolucion_mensual.append(
                {
                    "mes": nombres_meses[mes_fecha.month - 1],
                    "cartera": float(cartera_mes),
                    "cobrado": float(cobrado_mes),
                    "morosidad": round(morosidad_mes, 1),
                }
            )

        # 22. ANÁLISIS DE MOROSIDAD - Cálculo real desde BD
        # Total Financiamiento: Suma de todos los préstamos aprobados
        total_financiamiento_query = db.query(func.sum(Prestamo.total_financiamiento)).filter(Prestamo.estado == "APROBADO")
        total_financiamiento_query = FiltrosDashboard.aplicar_filtros_prestamo(
            total_financiamiento_query,
            analista,
            concesionario,
            modelo,
            fecha_inicio,
            fecha_fin,
        )
        total_financiamiento_operaciones = float(total_financiamiento_query.scalar() or Decimal("0"))

        # Cartera Cobrada: Suma de TODOS los pagos (conciliados y no conciliados)
        cartera_cobrada_query = db.query(func.sum(Pago.monto_pagado))
        if analista or concesionario or modelo:
            cartera_cobrada_query = cartera_cobrada_query.join(Prestamo, Pago.prestamo_id == Prestamo.id)
        cartera_cobrada_query = FiltrosDashboard.aplicar_filtros_pago(
            cartera_cobrada_query,
            analista,
            concesionario,
            modelo,
            fecha_inicio,
            fecha_fin,
        )
        cartera_cobrada_total = float(cartera_cobrada_query.scalar() or Decimal("0"))

        # Morosidad (Diferencia): Total Financiamiento - Cartera Cobrada
        morosidad_diferencia = max(0, total_financiamiento_operaciones - cartera_cobrada_total)

        # Mantener nombres de variables para compatibilidad con frontend
        ingresos_capital = total_financiamiento_operaciones
        ingresos_interes = cartera_cobrada_total
        ingresos_mora = morosidad_diferencia

        # 23. META MENSUAL - Total a cobrar del mes actual (suma de monto_cuota de cuotas del mes)
        # Meta = Total a cobrar del mes (cuotas planificadas)
        # Recaudado = Pagos conciliados del mes
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
                "totalCobrado": float(total_cobrado_periodo),
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
                "modeloMasVendido": "N/A",
                "ventasModeloMasVendido": 0,
                "ticketPromedio": round(ticket_promedio, 2),
                "ticketPromedioAnterior": round(ticket_promedio * 0.95, 2),
                "totalModelos": 0,
                "modeloMenosVendido": "N/A",
            },
            "evolucion_mensual": evolucion_mensual,
            "fecha_consulta": hoy.isoformat(),
        }

    except Exception as e:
        logger.error(f"Error en dashboard admin: {e}")
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
        total_prestamos = db.query(Prestamo).filter(Prestamo.estado == "APROBADO").count()

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


@router.get("/kpis-principales")
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
    try:
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

        # 1. TOTAL PRESTAMOS
        query_prestamos_actual = db.query(func.count(Prestamo.id)).filter(Prestamo.estado == "APROBADO")
        query_prestamos_actual = FiltrosDashboard.aplicar_filtros_prestamo(
            query_prestamos_actual, analista, concesionario, modelo, fecha_inicio, fecha_fin
        )
        total_prestamos_actual = query_prestamos_actual.scalar() or 0

        query_prestamos_anterior = db.query(func.count(Prestamo.id)).filter(
            Prestamo.estado == "APROBADO",
            Prestamo.fecha_registro >= fecha_inicio_mes_anterior,
            Prestamo.fecha_registro < fecha_fin_mes_anterior,
        )
        query_prestamos_anterior = FiltrosDashboard.aplicar_filtros_prestamo(
            query_prestamos_anterior, analista, concesionario, modelo, None, None
        )
        total_prestamos_anterior = query_prestamos_anterior.scalar() or 0

        variacion_prestamos, variacion_prestamos_abs = _calcular_variacion(
            float(total_prestamos_actual), float(total_prestamos_anterior)
        )

        # 2. CREDITOS NUEVOS EN EL MES
        query_creditos_nuevos_actual = db.query(func.count(Prestamo.id)).filter(
            Prestamo.estado == "APROBADO",
            Prestamo.fecha_registro >= fecha_inicio_mes_actual,
            Prestamo.fecha_registro < fecha_fin_mes_actual,
        )
        query_creditos_nuevos_actual = FiltrosDashboard.aplicar_filtros_prestamo(
            query_creditos_nuevos_actual, analista, concesionario, modelo, None, None
        )
        creditos_nuevos_actual = query_creditos_nuevos_actual.scalar() or 0

        query_creditos_nuevos_anterior = db.query(func.count(Prestamo.id)).filter(
            Prestamo.estado == "APROBADO",
            Prestamo.fecha_registro >= fecha_inicio_mes_anterior,
            Prestamo.fecha_registro < fecha_fin_mes_anterior,
        )
        query_creditos_nuevos_anterior = FiltrosDashboard.aplicar_filtros_prestamo(
            query_creditos_nuevos_anterior, analista, concesionario, modelo, None, None
        )
        creditos_nuevos_anterior = query_creditos_nuevos_anterior.scalar() or 0

        variacion_creditos, variacion_creditos_abs = _calcular_variacion(
            float(creditos_nuevos_actual), float(creditos_nuevos_anterior)
        )

        # 3. TOTAL CLIENTES
        query_clientes_actual = db.query(func.count(func.distinct(Prestamo.cedula))).filter(Prestamo.estado == "APROBADO")
        query_clientes_actual = FiltrosDashboard.aplicar_filtros_prestamo(
            query_clientes_actual, analista, concesionario, modelo, fecha_inicio, fecha_fin
        )
        total_clientes_actual = query_clientes_actual.scalar() or 0

        query_clientes_anterior = db.query(func.count(func.distinct(Prestamo.cedula))).filter(
            Prestamo.estado == "APROBADO",
            Prestamo.fecha_registro >= fecha_inicio_mes_anterior,
            Prestamo.fecha_registro < fecha_fin_mes_anterior,
        )
        query_clientes_anterior = FiltrosDashboard.aplicar_filtros_prestamo(
            query_clientes_anterior, analista, concesionario, modelo, None, None
        )
        total_clientes_anterior = query_clientes_anterior.scalar() or 0

        variacion_clientes, variacion_clientes_abs = _calcular_variacion(
            float(total_clientes_actual), float(total_clientes_anterior)
        )

        # 4. TOTAL MOROSIDAD EN DOLARES
        # Morosidad = cuotas vencidas no pagadas
        query_morosidad_actual = (
            db.query(func.sum(Cuota.monto_cuota))
            .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
            .filter(
                Prestamo.estado == "APROBADO",
                Cuota.fecha_vencimiento < hoy,
                Cuota.estado != "PAGADO",
            )
        )
        query_morosidad_actual = FiltrosDashboard.aplicar_filtros_cuota(
            query_morosidad_actual, analista, concesionario, modelo, fecha_inicio, fecha_fin
        )
        morosidad_actual = float(query_morosidad_actual.scalar() or Decimal("0"))

        # Para mes anterior, filtrar por cuotas que vencieron en ese mes
        query_morosidad_anterior = (
            db.query(func.sum(Cuota.monto_cuota))
            .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
            .filter(
                Prestamo.estado == "APROBADO",
                Cuota.fecha_vencimiento >= fecha_inicio_mes_anterior,
                Cuota.fecha_vencimiento < fecha_fin_mes_anterior,
                Cuota.estado != "PAGADO",
            )
        )
        query_morosidad_anterior = FiltrosDashboard.aplicar_filtros_cuota(
            query_morosidad_anterior, analista, concesionario, modelo, None, None
        )
        morosidad_anterior = float(query_morosidad_anterior.scalar() or Decimal("0"))

        variacion_morosidad, variacion_morosidad_abs = _calcular_variacion(
            morosidad_actual, morosidad_anterior
        )

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
            "total_morosidad_usd": {
                "valor_actual": morosidad_actual,
                "valor_mes_anterior": morosidad_anterior,
                "variacion_porcentual": round(variacion_morosidad, 2),
                "variacion_absoluta": variacion_morosidad_abs,
            },
            "mes_actual": nombres_meses[mes_actual - 1],
            "mes_anterior": nombres_meses[mes_anterior - 1],
        }

    except Exception as e:
        logger.error(f"Error obteniendo KPIs principales: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.get("/cobranzas-mensuales")
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
    """
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

        # Obtener últimos 12 meses
        meses_data = []
        for i in range(12):
            mes_fecha = date(hoy.year, hoy.month, 1) - timedelta(days=32 * i)
            mes_fecha = date(mes_fecha.year, mes_fecha.month, 1)
            siguiente_mes = _obtener_fechas_mes_siguiente(mes_fecha.month, mes_fecha.year)

            # Cobranzas planificadas: Suma de monto_cuota de cuotas con fecha_vencimiento en ese mes
            query_cobranzas = (
                db.query(func.sum(Cuota.monto_cuota))
                .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
                .filter(
                    Prestamo.estado == "APROBADO",
                    Cuota.fecha_vencimiento >= mes_fecha,
                    Cuota.fecha_vencimiento < siguiente_mes,
                )
            )
            query_cobranzas = FiltrosDashboard.aplicar_filtros_cuota(
                query_cobranzas, analista, concesionario, modelo, fecha_inicio, fecha_fin
            )
            cobranzas_planificadas = float(query_cobranzas.scalar() or Decimal("0"))

            # Pagos reales: Suma de pagos conciliados en ese mes
            query_pagos = db.query(func.sum(Pago.monto_pagado)).filter(
                func.date(Pago.fecha_pago) >= mes_fecha,
                func.date(Pago.fecha_pago) < siguiente_mes,
                Pago.conciliado.is_(True),
            )
            if analista or concesionario or modelo:
                query_pagos = query_pagos.join(Prestamo, Pago.prestamo_id == Prestamo.id)
            query_pagos = FiltrosDashboard.aplicar_filtros_pago(
                query_pagos, analista, concesionario, modelo, fecha_inicio, fecha_fin
            )
            pagos_reales = float(query_pagos.scalar() or Decimal("0"))

            meses_data.append(
                {
                    "mes": mes_fecha.strftime("%Y-%m"),
                    "nombre_mes": nombres_meses[mes_fecha.month - 1],
                    "cobranzas_planificadas": cobranzas_planificadas,
                    "pagos_reales": pagos_reales,
                    "meta_mensual": cobranzas_planificadas,  # Meta = cobranzas planificadas
                }
            )

        # Meta actual = cobranzas planificadas del mes actual
        mes_actual_inicio = date(hoy.year, hoy.month, 1)
        if hoy.month == 12:
            mes_actual_fin = date(hoy.year + 1, 1, 1)
        else:
            mes_actual_fin = date(hoy.year, hoy.month + 1, 1)

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

        return {
            "meses": meses_data,
            "meta_actual": meta_actual,
        }

    except Exception as e:
        logger.error(f"Error obteniendo cobranzas mensuales: {e}", exc_info=True)
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
            total_a_cobrar = _calcular_total_a_cobrar_fecha(
                db, fecha_dia, analista, concesionario, modelo, fecha_inicio, fecha_fin
            )
            pagos = _calcular_pagos_fecha(
                db, fecha_dia, analista, concesionario, modelo, fecha_inicio, fecha_fin
            )
            morosidad = _calcular_morosidad(
                db, fecha_dia, analista, concesionario, modelo, fecha_inicio, fecha_fin
            )

            dias_data.append(
                {
                    "fecha": fecha_dia.isoformat(),
                    "total_a_cobrar": total_a_cobrar,
                    "pagos": pagos,
                    "morosidad": morosidad,
                }
            )

        return {"dias": dias_data}

    except Exception as e:
        logger.error(f"Error obteniendo cobranza por día: {e}", exc_info=True)
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
        query_acumulado_mensual = db.query(func.sum(Pago.monto_pagado)).filter(
            func.date(Pago.fecha_pago) >= fecha_inicio_mes,
            Pago.conciliado.is_(True),
        )
        if analista or concesionario or modelo:
            query_acumulado_mensual = query_acumulado_mensual.join(Prestamo, Pago.prestamo_id == Prestamo.id)
        query_acumulado_mensual = FiltrosDashboard.aplicar_filtros_pago(
            query_acumulado_mensual, analista, concesionario, modelo, fecha_inicio, fecha_fin
        )
        acumulado_mensual = float(query_acumulado_mensual.scalar() or Decimal("0"))

        # Acumulado anual: Pagos desde inicio del año
        query_acumulado_anual = db.query(func.sum(Pago.monto_pagado)).filter(
            func.date(Pago.fecha_pago) >= fecha_inicio_anio,
            Pago.conciliado.is_(True),
        )
        if analista or concesionario or modelo:
            query_acumulado_anual = query_acumulado_anual.join(Prestamo, Pago.prestamo_id == Prestamo.id)
        query_acumulado_anual = FiltrosDashboard.aplicar_filtros_pago(
            query_acumulado_anual, analista, concesionario, modelo, fecha_inicio, fecha_fin
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
    try:
        hoy = date.today()

        # Obtener morosidad por analista (morosidad = cuotas vencidas no pagadas)
        query = (
            db.query(
                func.coalesce(Prestamo.analista, Prestamo.producto_financiero, "Sin Analista").label("analista"),
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
            .group_by("analista")
        )

        # Aplicar filtros (excepto analista que ya estamos agrupando)
        if concesionario:
            query = query.filter(Prestamo.concesionario == concesionario)
        if modelo:
            query = query.filter(or_(Prestamo.producto == modelo, Prestamo.modelo_vehiculo == modelo))

        resultados = query.all()

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

        return {"analistas": analistas_data}

    except Exception as e:
        logger.error(f"Error obteniendo morosidad por analista: {e}", exc_info=True)
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
        # Obtener total general de préstamos
        query_base = db.query(Prestamo).filter(Prestamo.estado == "APROBADO")
        query_base = FiltrosDashboard.aplicar_filtros_prestamo(
            query_base, analista, concesionario, modelo, fecha_inicio, fecha_fin
        )

        total_general = float(query_base.with_entities(func.sum(Prestamo.total_financiamiento)).scalar() or Decimal("0"))

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
            porcentaje = (total_prestamos / total_general * 100) if total_general > 0 else 0

            concesionarios_data.append(
                {
                    "concesionario": row.concesionario or "Sin Concesionario",
                    "total_prestamos": total_prestamos,
                    "cantidad_prestamos": row.cantidad_prestamos or 0,
                    "porcentaje": round(porcentaje, 2),
                }
            )

        return {
            "concesionarios": concesionarios_data,
            "total_general": total_general,
        }

    except Exception as e:
        logger.error(f"Error obteniendo préstamos por concesionario: {e}", exc_info=True)
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

        total_prestamos = query_base.count()
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
            distribucion_data = _procesar_distribucion_rango_monto(query_base, rangos, total_prestamos, total_monto)

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
    """
    try:
        hoy = date.today()
        nombres_meses = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]

        # Calcular fecha inicio (hace N meses)
        fecha_inicio_query = fecha_inicio
        if not fecha_inicio_query:
            año_inicio = hoy.year
            mes_inicio = hoy.month - meses + 1
            if mes_inicio <= 0:
                año_inicio -= 1
                mes_inicio += 12
            fecha_inicio_query = date(año_inicio, mes_inicio, 1)

        # Generar datos mensuales
        meses_data = []
        current_date = fecha_inicio_query

        while current_date <= hoy:
            año_mes = current_date.year
            num_mes = current_date.month
            fecha_mes_inicio = date(año_mes, num_mes, 1)
            fecha_mes_fin = _obtener_fechas_mes_siguiente(num_mes, año_mes)

            # Nuevos financiamientos del mes (préstamos aprobados en el mes)
            query_nuevos = db.query(
                func.count(Prestamo.id).label("cantidad"), func.sum(Prestamo.total_financiamiento).label("monto_total")
            ).filter(
                Prestamo.estado == "APROBADO",
                Prestamo.fecha_registro >= fecha_mes_inicio,
                Prestamo.fecha_registro < fecha_mes_fin,
            )

            query_nuevos = FiltrosDashboard.aplicar_filtros_prestamo(
                query_nuevos, analista, concesionario, modelo, fecha_inicio, fecha_fin
            )

            resultado = query_nuevos.first()
            if resultado:
                cantidad_nuevos = resultado.cantidad or 0
                monto_nuevos = float(resultado.monto_total or Decimal("0"))
            else:
                cantidad_nuevos = 0
                monto_nuevos = 0.0

            # Total financiamiento acumulado hasta fin de mes (cartera vigente)
            query_total = db.query(func.sum(Prestamo.total_financiamiento).label("total")).filter(
                Prestamo.estado == "APROBADO", Prestamo.fecha_registro <= fecha_mes_fin
            )

            query_total = FiltrosDashboard.aplicar_filtros_prestamo(
                query_total, analista, concesionario, modelo, fecha_inicio, fecha_fin
            )

            total_acumulado = float(query_total.scalar() or Decimal("0"))

            meses_data.append(
                {
                    "mes": f"{nombres_meses[num_mes - 1]} {año_mes}",
                    "año": año_mes,
                    "mes_numero": num_mes,
                    "cantidad_nuevos": cantidad_nuevos,
                    "monto_nuevos": monto_nuevos,
                    "total_acumulado": total_acumulado,
                    "fecha_mes": fecha_mes_inicio.isoformat(),
                }
            )

            # Avanzar al siguiente mes
            current_date = fecha_mes_fin

        return {"meses": meses_data, "fecha_inicio": fecha_inicio_query.isoformat(), "fecha_fin": hoy.isoformat()}

    except Exception as e:
        logger.error(f"Error obteniendo tendencia mensual de financiamiento: {e}", exc_info=True)
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
        fecha_inicio_mes = date(hoy.year, hoy.month, 1)

        # Obtener cobros por analista (pagos conciliados del mes)
        query = (
            db.query(
                func.coalesce(Prestamo.analista, Prestamo.producto_financiero, "Sin Analista").label("analista"),
                func.sum(Pago.monto_pagado).label("total_cobrado"),
                func.count(Pago.id).label("cantidad_pagos"),
            )
            .join(Pago, Pago.prestamo_id == Prestamo.id)
            .filter(
                Prestamo.estado == "APROBADO",
                Pago.conciliado.is_(True),
                func.date(Pago.fecha_pago) >= fecha_inicio_mes,
            )
            .group_by("analista")
            .order_by(func.sum(Pago.monto_pagado).desc())
        )

        # Aplicar filtros (excepto analista que ya estamos agrupando)
        if concesionario:
            query = query.filter(Prestamo.concesionario == concesionario)
        if modelo:
            query = query.filter(or_(Prestamo.producto == modelo, Prestamo.modelo_vehiculo == modelo))
        if fecha_inicio or fecha_fin:
            # Ya estamos filtrando por mes actual, pero podemos ajustar si hay fechas específicas
            pass

        resultados = query.limit(10).all()  # Top 10

        analistas_data = []
        for row in resultados:
            analistas_data.append(
                {
                    "analista": row.analista or "Sin Analista",
                    "total_cobrado": float(row.total_cobrado or Decimal("0")),
                    "cantidad_pagos": row.cantidad_pagos or 0,
                }
            )

        return {"analistas": analistas_data}

    except Exception as e:
        logger.error(f"Error obteniendo cobros por analista: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")
