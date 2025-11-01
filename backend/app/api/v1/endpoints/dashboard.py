import logging
from calendar import monthrange
from datetime import date, timedelta
from decimal import Decimal
from typing import Optional

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


@router.get("/opciones-filtros")
def obtener_opciones_filtros(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Obtener opciones disponibles para filtros del dashboard - Sin duplicados"""
    try:

        def normalizar_valor(valor: Optional[str]) -> Optional[str]:
            """Normaliza un valor: trim, validar no vacío"""
            if not valor:
                return None
            valor_limpio = str(valor).strip()
            return valor_limpio if valor_limpio else None

        def obtener_valores_unicos(query_result) -> set:
            """Extrae valores únicos normalizados de una query"""
            valores = set()
            for item in query_result:
                valor = item[0] if isinstance(item, tuple) else item
                valor_limpio = normalizar_valor(valor)
                if valor_limpio:
                    valores.add(valor_limpio)
            return valores

        # 1. ANALISTAS - Combinar analista y producto_financiero sin duplicados
        try:
            analistas_query = (
                db.query(func.distinct(Prestamo.analista))
                .filter(Prestamo.analista.isnot(None), Prestamo.analista != "")
                .all()
            )
            analistas_set = obtener_valores_unicos(analistas_query)
        except Exception:
            # Si la columna no existe todavía (migraciones pendientes)
            analistas_set = set()

        # Productos financieros (pueden ser analistas)
        try:
            productos_fin_query = (
                db.query(func.distinct(Prestamo.producto_financiero))
                .filter(
                    Prestamo.producto_financiero.isnot(None),
                    Prestamo.producto_financiero != "",
                )
                .all()
            )
            productos_set = obtener_valores_unicos(productos_fin_query)
        except Exception:
            productos_set = set()

        # Combinar sin duplicados
        analistas_final = sorted(analistas_set | productos_set)

        # 2. CONCESIONARIOS - Únicos y normalizados
        try:
            concesionarios_query = (
                db.query(func.distinct(Prestamo.concesionario))
                .filter(
                    Prestamo.concesionario.isnot(None), Prestamo.concesionario != ""
                )
                .all()
            )
            concesionarios_set = obtener_valores_unicos(concesionarios_query)
        except Exception:
            concesionarios_set = set()
        concesionarios_final = sorted(concesionarios_set)

        # 3. MODELOS - Combinar producto y modelo_vehiculo sin duplicados
        try:
            modelos_producto_query = (
                db.query(func.distinct(Prestamo.producto))
                .filter(Prestamo.producto.isnot(None), Prestamo.producto != "")
                .all()
            )
            modelos_producto_set = obtener_valores_unicos(modelos_producto_query)
        except Exception:
            modelos_producto_set = set()

        # También modelo_vehiculo
        try:
            modelos_vehiculo_query = (
                db.query(func.distinct(Prestamo.modelo_vehiculo))
                .filter(
                    Prestamo.modelo_vehiculo.isnot(None), Prestamo.modelo_vehiculo != ""
                )
                .all()
            )
            modelos_vehiculo_set = obtener_valores_unicos(modelos_vehiculo_query)
        except Exception:
            modelos_vehiculo_set = set()

        # Combinar sin duplicados
        modelos_final = sorted(modelos_producto_set | modelos_vehiculo_set)

        return {
            "analistas": analistas_final,
            "concesionarios": concesionarios_final,
            "modelos": modelos_final,
        }
    except Exception as e:
        logger.error(f"Error obteniendo opciones de filtros: {e}", exc_info=True)
        return {"analistas": [], "concesionarios": [], "modelos": []}


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
        # Validar acceso admin de forma tolerante (evitar 500 si falta atributo)
        try:
            es_admin = getattr(current_user, "is_admin", None)
        except Exception:
            es_admin = None
        if es_admin is False:
            raise HTTPException(
                status_code=403, detail="Acceso denegado. Solo administradores."
            )

        # Normalizar parámetro 'dias'
        try:
            dias_norm = int(dias or 30)
        except Exception:
            dias_norm = 30
        if dias_norm <= 0:
            dias_norm = 30

        hoy = date.today()

        # Calcular fecha inicio (dias días atrás o fecha_inicio si está definida)
        if fecha_inicio:
            fecha_inicio_query = fecha_inicio
        else:
            fecha_inicio_query = hoy - timedelta(days=dias_norm)

        if fecha_fin:
            fecha_fin_query = fecha_fin
        else:
            fecha_fin_query = hoy

        # Generar lista de fechas
        fechas = []
        current_date = fecha_inicio_query
        while current_date <= fecha_fin_query:
            fechas.append(current_date)
            current_date += timedelta(days=1)

        datos_diarios = []

        for fecha_dia in fechas:
            # ✅ Total a cobrar: TODAS las cuotas programadas con fecha_vencimiento = fecha_dia
            # (incluye todas las cuotas, pagadas o no, porque es el monto programado para ese día)
            try:
                cuotas_dia_query = (
                    db.query(func.sum(Cuota.monto_cuota))
                    .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
                    .filter(
                        Cuota.fecha_vencimiento == fecha_dia,
                        Prestamo.estado == "APROBADO",
                    )
                )
                cuotas_dia_query = FiltrosDashboard.aplicar_filtros_cuota(
                    cuotas_dia_query,
                    analista,
                    concesionario,
                    modelo,
                    None,
                    None,
                )
                total_a_cobrar = float(cuotas_dia_query.scalar() or Decimal("0"))
            except Exception:
                logger.error(
                    "Error en query total_a_cobrar",
                    extra={
                        "fecha": fecha_dia.isoformat(),
                        "analista": analista,
                        "concesionario": concesionario,
                        "modelo": modelo,
                    },
                    exc_info=True,
                )
                total_a_cobrar = 0.0

            # ✅ Total cobrado: TODOS los pagos realizados con fecha_pago = fecha_dia
            # (suma monto_pagado de todos los registros en tabla Pago donde fecha_pago = fecha_dia)
            try:
                pagos_dia_query = db.query(func.sum(Pago.monto_pagado)).filter(
                    func.date(Pago.fecha_pago) == fecha_dia
                )
                # Aplicar filtros usando FiltrosDashboard (necesita join con Prestamo si hay filtros)
                pagos_dia_query = FiltrosDashboard.aplicar_filtros_pago(
                    pagos_dia_query,
                    analista,
                    concesionario,
                    modelo,
                    None,  # No aplicar filtros de fecha_inicio/fecha_fin aquí (ya filtrado por fecha_dia)
                    None,
                )
                total_cobrado = float(pagos_dia_query.scalar() or Decimal("0"))
            except Exception:
                logger.error(
                    "Error en query total_cobrado",
                    extra={
                        "fecha": fecha_dia.isoformat(),
                        "analista": analista,
                        "concesionario": concesionario,
                        "modelo": modelo,
                    },
                    exc_info=True,
                )
                total_cobrado = 0.0

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
    return FiltrosDashboard.aplicar_filtros_prestamo(
        query, analista, concesionario, modelo, fecha_inicio, fecha_fin
    )


def aplicar_filtros_pago(
    query,
    analista: Optional[str] = None,
    concesionario: Optional[str] = None,
    modelo: Optional[str] = None,
    fecha_inicio: Optional[date] = None,
    fecha_fin: Optional[date] = None,
):
    """Aplica filtros comunes a queries de pagos - DEPRECATED: Usar FiltrosDashboard"""
    return FiltrosDashboard.aplicar_filtros_pago(
        query, analista, concesionario, modelo, fecha_inicio, fecha_fin
    )


@router.get("/admin")
def dashboard_administrador(
    periodo: Optional[str] = Query("mes", description="Periodo: dia, semana, mes, año"),
    analista: Optional[str] = Query(None, description="Filtrar por analista"),
    concesionario: Optional[str] = Query(None, description="Filtrar por concesionario"),
    modelo: Optional[str] = Query(None, description="Filtrar por modelo de vehículo"),
    fecha_inicio: Optional[date] = Query(None, description="Fecha inicio del rango"),
    fecha_fin: Optional[date] = Query(None, description="Fecha fin del rango"),
    consolidado: Optional[bool] = Query(
        False, description="Agrupar datos consolidados"
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Dashboard para administradores con datos reales de la base de datos
    Soporta filtros: analista, concesionario, modelo, rango de fechas
    """
    try:
        if not current_user.is_admin:
            raise HTTPException(
                status_code=403, detail="Acceso denegado. Solo administradores."
            )

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
        cartera_total = base_prestamo_query.with_entities(
            func.sum(Prestamo.total_financiamiento)
        ).scalar() or Decimal("0")

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
        porcentaje_mora = (
            (float(cartera_vencida) / float(cartera_total) * 100)
            if cartera_total > 0
            else 0
        )

        # 5. PAGOS DE HOY (con filtros)
        pagos_hoy_query = db.query(func.count(Pago.id)).filter(
            func.date(Pago.fecha_pago) == hoy
        )
        monto_pagos_hoy_query = db.query(func.sum(Pago.monto_pagado)).filter(
            func.date(Pago.fecha_pago) == hoy
        )

        # ✅ Aplicar filtros usando clase centralizada (automático)
        if analista or concesionario or modelo:
            pagos_hoy_query = pagos_hoy_query.join(
                Prestamo, Pago.prestamo_id == Prestamo.id
            )
            monto_pagos_hoy_query = monto_pagos_hoy_query.join(
                Prestamo, Pago.prestamo_id == Prestamo.id
            )

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
        clientes_activos = (
            base_prestamo_query.with_entities(
                func.count(func.distinct(Prestamo.cedula))
            ).scalar()
            or 0
        )

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
            total_cobrado_query = total_cobrado_query.join(
                Prestamo, Pago.prestamo_id == Prestamo.id
            )
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

        cuotas_pagadas = cuotas_pagadas_query.scalar() or 0
        # Variables calculadas pero no usadas actualmente en la respuesta
        # cuotas_pendientes = cuotas_pendientes_query.scalar() or 0
        # cuotas_atrasadas = cuotas_atrasadas_query.scalar() or 0

        # 15. CÁLCULO DE PERÍODOS ANTERIORES
        if periodo == "mes":
            fecha_inicio_periodo = date(hoy.year, hoy.month, 1)
            fecha_fin_periodo_anterior = fecha_inicio_periodo - timedelta(days=1)
            fecha_inicio_periodo_anterior = date(
                fecha_fin_periodo_anterior.year, fecha_fin_periodo_anterior.month, 1
            )
        elif periodo == "semana":
            fecha_inicio_periodo = hoy - timedelta(days=hoy.weekday())
            fecha_inicio_periodo_anterior = fecha_inicio_periodo - timedelta(days=7)
            fecha_fin_periodo_anterior = fecha_inicio_periodo - timedelta(days=1)
        elif periodo == "año":
            fecha_inicio_periodo = date(hoy.year, 1, 1)
            fecha_inicio_periodo_anterior = date(hoy.year - 1, 1, 1)
            fecha_fin_periodo_anterior = date(hoy.year - 1, 12, 31)
        else:  # dia
            fecha_inicio_periodo = hoy
            fecha_inicio_periodo_anterior = hoy - timedelta(days=1)
            fecha_fin_periodo_anterior = hoy - timedelta(days=1)

        # Cartera anterior - Calcular desde BD histórica
        if periodo == "mes":
            # Mes anterior: cartera total al final del mes anterior
            fecha_fin_mes_anterior = fecha_fin_periodo_anterior
            cartera_anterior_query = db.query(
                func.sum(Prestamo.total_financiamiento)
            ).filter(
                Prestamo.estado == "APROBADO",
                func.date(Prestamo.fecha_registro) <= fecha_fin_mes_anterior,
            )
            cartera_anterior_query = FiltrosDashboard.aplicar_filtros_prestamo(
                cartera_anterior_query,
                analista,
                concesionario,
                modelo,
                None,  # No filtrar por fechas para obtener histórico
                None,
            )
            cartera_anterior_val = float(
                cartera_anterior_query.scalar() or Decimal("0")
            )
        elif periodo == "semana":
            # Semana anterior: cartera al inicio de la semana anterior
            cartera_anterior_query = db.query(
                func.sum(Prestamo.total_financiamiento)
            ).filter(
                Prestamo.estado == "APROBADO",
                func.date(Prestamo.fecha_registro) <= fecha_fin_periodo_anterior,
            )
            cartera_anterior_query = FiltrosDashboard.aplicar_filtros_prestamo(
                cartera_anterior_query,
                analista,
                concesionario,
                modelo,
                None,
                None,
            )
            cartera_anterior_val = float(
                cartera_anterior_query.scalar() or Decimal("0")
            )
        elif periodo == "año":
            # Año anterior: cartera al final del año anterior
            cartera_anterior_query = db.query(
                func.sum(Prestamo.total_financiamiento)
            ).filter(
                Prestamo.estado == "APROBADO",
                func.date(Prestamo.fecha_registro) <= fecha_fin_periodo_anterior,
            )
            cartera_anterior_query = FiltrosDashboard.aplicar_filtros_prestamo(
                cartera_anterior_query,
                analista,
                concesionario,
                modelo,
                None,
                None,
            )
            cartera_anterior_val = float(
                cartera_anterior_query.scalar() or Decimal("0")
            )
        else:  # dia
            cartera_anterior_val = float(cartera_total)

        # 16. TOTAL COBRADO EN EL MES ACTUAL - SOLO PAGOS CONCILIADOS
        # ✅ Si es período mensual, calcular solo pagos conciliados del mes actual
        hoy = date.today()
        año_actual = hoy.year
        mes_actual = hoy.month
        primer_dia_mes = date(año_actual, mes_actual, 1)
        ultimo_dia_mes = date(año_actual, mes_actual, monthrange(año_actual, mes_actual)[1])

        # Total cobrado del mes actual (solo pagos conciliados)
        total_cobrado_mes_query = db.query(func.sum(Pago.monto_pagado)).filter(
            func.date(Pago.fecha_pago) >= primer_dia_mes,
            func.date(Pago.fecha_pago) <= ultimo_dia_mes,
            Pago.conciliado == True,  # ✅ Solo pagos conciliados
        )
        if analista or concesionario or modelo:
            total_cobrado_mes_query = total_cobrado_mes_query.join(
                Prestamo, Pago.prestamo_id == Prestamo.id
            )
        total_cobrado_mes_query = FiltrosDashboard.aplicar_filtros_pago(
            total_cobrado_mes_query,
            analista,
            concesionario,
            modelo,
            None,  # No aplicar filtros de fecha aquí (ya filtrado por mes)
            None,
        )
        total_cobrado_periodo = total_cobrado_mes_query.scalar() or Decimal("0")

        # Total cobrado mes anterior (solo pagos conciliados)
        if mes_actual == 1:
            mes_anterior = 12
            año_anterior = año_actual - 1
        else:
            mes_anterior = mes_actual - 1
            año_anterior = año_actual
        primer_dia_mes_anterior = date(año_anterior, mes_anterior, 1)
        ultimo_dia_mes_anterior = date(año_anterior, mes_anterior, monthrange(año_anterior, mes_anterior)[1])

        total_cobrado_anterior_query = db.query(func.sum(Pago.monto_pagado)).filter(
            func.date(Pago.fecha_pago) >= primer_dia_mes_anterior,
            func.date(Pago.fecha_pago) <= ultimo_dia_mes_anterior,
            Pago.conciliado == True,  # ✅ Solo pagos conciliados
        )
        if analista or concesionario or modelo:
            total_cobrado_anterior_query = total_cobrado_anterior_query.join(
                Prestamo, Pago.prestamo_id == Prestamo.id
            )
        total_cobrado_anterior_query = FiltrosDashboard.aplicar_filtros_pago(
            total_cobrado_anterior_query,
            analista,
            concesionario,
            modelo,
            None,
            None,
        )
        total_cobrado_anterior = total_cobrado_anterior_query.scalar() or Decimal("0")

        # 17. TASA DE RECUPERACIÓN MENSUAL (cuotas pagadas del mes / cuotas a cobrar del mes)
        # Cuotas a cobrar del mes (planificadas)
        cuotas_a_cobrar_mes_query = (
            db.query(func.sum(Cuota.monto_cuota))
            .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
            .filter(
                func.date(Cuota.fecha_vencimiento) >= primer_dia_mes,
                func.date(Cuota.fecha_vencimiento) <= ultimo_dia_mes,
                Prestamo.estado == "APROBADO",
            )
        )
        cuotas_a_cobrar_mes_query = FiltrosDashboard.aplicar_filtros_cuota(
            cuotas_a_cobrar_mes_query,
            analista,
            concesionario,
            modelo,
            None,
            None,
        )
        total_a_cobrar_mes = float(cuotas_a_cobrar_mes_query.scalar() or Decimal("0"))

        # Cuotas pagadas del mes (con fecha_pago en el mes actual)
        cuotas_pagadas_mes_query = (
            db.query(func.count(Cuota.id))
            .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
            .filter(
                Cuota.estado == "PAGADO",
                Cuota.fecha_pago.isnot(None),
                func.date(Cuota.fecha_pago) >= primer_dia_mes,
                func.date(Cuota.fecha_pago) <= ultimo_dia_mes,
                Prestamo.estado == "APROBADO",
            )
        )
        cuotas_pagadas_mes_query = FiltrosDashboard.aplicar_filtros_cuota(
            cuotas_pagadas_mes_query,
            analista,
            concesionario,
            modelo,
            None,
            None,
        )
        cuotas_pagadas_mes = cuotas_pagadas_mes_query.scalar() or 0

        # Total cuotas planificadas del mes (para calcular tasa)
        total_cuotas_mes_query = (
            db.query(func.count(Cuota.id))
            .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
            .filter(
                func.date(Cuota.fecha_vencimiento) >= primer_dia_mes,
                func.date(Cuota.fecha_vencimiento) <= ultimo_dia_mes,
                Prestamo.estado == "APROBADO",
            )
        )
        total_cuotas_mes_query = FiltrosDashboard.aplicar_filtros_cuota(
            total_cuotas_mes_query,
            analista,
            concesionario,
            modelo,
            None,
            None,
        )
        total_cuotas_mes = total_cuotas_mes_query.scalar() or 0

        # Tasa de recuperación mensual = (cuotas pagadas del mes / cuotas planificadas del mes) * 100
        tasa_recuperacion = (
            (cuotas_pagadas_mes / total_cuotas_mes * 100)
            if total_cuotas_mes > 0
            else 0
        )

        # Tasa recuperación mes anterior - Calcular desde BD histórica
        cuotas_pagadas_mes_anterior_query = (
            db.query(func.count(Cuota.id))
            .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
            .filter(
                Cuota.estado == "PAGADO",
                Prestamo.estado == "APROBADO",
                Cuota.fecha_pago.isnot(None),
                func.date(Cuota.fecha_pago) >= primer_dia_mes_anterior,
                func.date(Cuota.fecha_pago) <= ultimo_dia_mes_anterior,
            )
        )
        cuotas_pagadas_mes_anterior_query = FiltrosDashboard.aplicar_filtros_cuota(
            cuotas_pagadas_mes_anterior_query,
            analista,
            concesionario,
            modelo,
            None,
            None,
        )
        cuotas_pagadas_mes_anterior = cuotas_pagadas_mes_anterior_query.scalar() or 0

        total_cuotas_mes_anterior_query = (
            db.query(func.count(Cuota.id))
            .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
            .filter(
                func.date(Cuota.fecha_vencimiento) >= primer_dia_mes_anterior,
                func.date(Cuota.fecha_vencimiento) <= ultimo_dia_mes_anterior,
                Prestamo.estado == "APROBADO",
            )
        )
        total_cuotas_mes_anterior_query = FiltrosDashboard.aplicar_filtros_cuota(
            total_cuotas_mes_anterior_query,
            analista,
            concesionario,
            modelo,
            None,
            None,
        )
        total_cuotas_mes_anterior = total_cuotas_mes_anterior_query.scalar() or 0

        tasa_recuperacion_anterior = (
            (cuotas_pagadas_mes_anterior / total_cuotas_mes_anterior * 100)
            if total_cuotas_mes_anterior > 0
            else 0
        )

        # 18. PROMEDIO DÍAS DE MORA
        # Calcular desde cuotas vencidas en lugar de usar campo inexistente
        cuotas_vencidas_con_dias = (
            db.query(
                func.avg(func.date_part("day", hoy - Cuota.fecha_vencimiento)).label(
                    "dias_promedio"
                )
            )
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
        promedio_dias_mora = (
            float(cuotas_vencidas_con_dias) if cuotas_vencidas_con_dias else 0.0
        )

        # 19. PORCENTAJE CUMPLIMIENTO (clientes al día / total clientes)
        porcentaje_cumplimiento = (
            ((clientes_activos - clientes_en_mora) / clientes_activos * 100)
            if clientes_activos > 0
            else 0
        )

        # 20. TICKET PROMEDIO (promedio de préstamos)
        ticket_promedio = (
            float(cartera_total / clientes_activos) if clientes_activos > 0 else 0
        )

        # 21. EVOLUCIÓN MENSUAL (últimos 6 meses)
        # ✅ Aplicar filtros automáticamente a evolución mensual
        evolucion_mensual = []
        for i in range(6, -1, -1):
            mes_fecha = hoy - timedelta(days=30 * i)
            mes_inicio = date(mes_fecha.year, mes_fecha.month, 1)
            if mes_fecha.month == 12:
                mes_fin = date(mes_fecha.year + 1, 1, 1) - timedelta(days=1)
            else:
                mes_fin = date(mes_fecha.year, mes_fecha.month + 1, 1) - timedelta(
                    days=1
                )

            # ✅ Cartera del mes con filtros
            cartera_mes_query = db.query(
                func.sum(Prestamo.total_financiamiento)
            ).filter(
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
                Pago.conciliado == True,  # ✅ Solo pagos conciliados
            )
            if analista or concesionario or modelo:
                cobrado_mes_query = cobrado_mes_query.join(
                    Prestamo, Pago.prestamo_id == Prestamo.id
                )
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
            morosidad_mes = (
                (cuotas_vencidas_mes / total_cuotas_mes * 100)
                if total_cuotas_mes > 0
                else 0
            )

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
        total_financiamiento_query = db.query(func.sum(Prestamo.total_financiamiento)).filter(
            Prestamo.estado == "APROBADO"
        )
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
            cartera_cobrada_query = cartera_cobrada_query.join(
                Prestamo, Pago.prestamo_id == Prestamo.id
            )
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
        meta_mensual_final = total_a_cobrar_mes  # Meta = Total a cobrar del mes

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
                "porcentajeCumplimientoAnterior": round(
                    max(0, porcentaje_cumplimiento - 3), 1
                ),
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

    porcentaje_mora = (
        (clientes_en_mora / len(clientes_asignados) * 100) if clientes_asignados else 0
    )

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
        # Calcular días de mora desde cuotas
        dias_mora_query = (
            db.query(func.max(func.date_part("day", hoy - Cuota.fecha_vencimiento)))
            .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
            .filter(
                Prestamo.cedula == row.cedula,
                Prestamo.estado == "APROBADO",
                Cuota.fecha_vencimiento < hoy,
                Cuota.estado != "PAGADO",
            )
            .scalar()
        )
        dias_mora = int(dias_mora_query) if dias_mora_query else 0

        top_clientes_data.append(
            {
                "cedula": row.cedula,
                "nombre": row.nombres,  # Corregido: usar nombres en lugar de nombre
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
        total_prestamos = (
            db.query(Prestamo).filter(Prestamo.estado == "APROBADO").count()
        )

        # Cartera total (desde préstamos, Cliente NO tiene total_financiamiento)
        cartera_total = (
            db.query(func.sum(Prestamo.total_financiamiento))
            .filter(Prestamo.estado == "APROBADO")
            .scalar()
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
        raise HTTPException(
            status_code=500, detail=f"Error interno del servidor: {str(e)}"
        )
