"""
Servicio para generar tablas de amortización de préstamos
Calcula automáticamente cuotas con base en fecha_base_calculo
"""

import logging
from datetime import date, timedelta
from decimal import Decimal
from typing import List

from sqlalchemy.orm import Session

from app.models.amortizacion import Cuota
from app.models.prestamo import Prestamo

logger = logging.getLogger(__name__)


def generar_tabla_amortizacion(
    prestamo: Prestamo,
    fecha_base: date,
    db: Session,
) -> List[Cuota]:
    """
    Genera tabla de amortización para un préstamo aprobado.

    Args:
        prestamo: Préstamo para el cual generar la tabla
        fecha_base: Fecha desde la cual se calculan las cuotas
        db: Sesión de base de datos

    Returns:
        Lista de cuotas generadas
    """

    # Eliminar cuotas existentes si las hay
    db.query(Cuota).filter(Cuota.prestamo_id == prestamo.id).delete()

    # Validar datos del préstamo
    if prestamo.total_financiamiento <= Decimal("0.00"):
        raise ValueError("El monto del préstamo debe ser mayor a cero")
    if prestamo.numero_cuotas <= 0:
        raise ValueError("El número de cuotas debe ser mayor a cero")

    cuotas_generadas = []
    saldo_capital = prestamo.total_financiamiento

    # Calcular intervalo entre cuotas según modalidad
    intervalo_dias = _calcular_intervalo_dias(prestamo.modalidad_pago)

    # Tasa de interés mensual (convertir anual a mensual)
    # Manejar caso especial de tasa 0%
    if prestamo.tasa_interes == Decimal("0.00"):
        tasa_mensual = Decimal("0.00")
    else:
        tasa_mensual = Decimal(prestamo.tasa_interes) / Decimal(100) / Decimal(12)

    # Generar cada cuota
    for numero_cuota in range(1, prestamo.numero_cuotas + 1):
        # Fecha de vencimiento
        fecha_vencimiento = fecha_base + timedelta(days=intervalo_dias * numero_cuota)

        # Método Francés (cuota fija)
        monto_cuota = prestamo.cuota_periodo

        # Calcular interés sobre saldo pendiente
        # Si tasa es 0%, interés es 0
        if tasa_mensual == Decimal("0.00"):
            monto_interes = Decimal("0.00")
            monto_capital = monto_cuota
        else:
            monto_interes = saldo_capital * tasa_mensual
            # Capital = Cuota - Interés
            monto_capital = monto_cuota - monto_interes

        # Actualizar saldo
        saldo_capital_inicial = saldo_capital
        saldo_capital = saldo_capital - monto_capital
        saldo_capital_final = saldo_capital

        # Crear cuota
        cuota = Cuota(
            prestamo_id=prestamo.id,
            numero_cuota=numero_cuota,
            fecha_vencimiento=fecha_vencimiento.isoformat(),
            monto_cuota=monto_cuota,
            monto_capital=monto_capital,
            monto_interes=monto_interes,
            saldo_capital_inicial=saldo_capital_inicial,
            saldo_capital_final=saldo_capital_final,
            capital_pagado=Decimal("0.00"),
            interes_pagado=Decimal("0.00"),
            mora_pagada=Decimal("0.00"),
            total_pagado=Decimal("0.00"),
            capital_pendiente=monto_capital,
            interes_pendiente=monto_interes,
            estado="PENDIENTE",
        )

        cuotas_generadas.append(cuota)
        db.add(cuota)

    try:
        db.commit()

        # Validar consistencia de la tabla generada
        total_calculado = sum(c.monto_cuota for c in cuotas_generadas)
        diferencia = abs(total_calculado - prestamo.total_financiamiento)

        if diferencia > Decimal("0.01"):  # Tolerancia de 1 centavo
            logger.warning(
                f"Diferencia en total de cuotas: Calculado={total_calculado}, "
                f"Esperado={prestamo.total_financiamiento}, "
                f"Diferencia={diferencia}"
            )

        logger.info(
            f"Tabla de amortización generada: {prestamo.numero_cuotas} cuotas para préstamo {prestamo.id}"
        )
    except Exception as e:
        db.rollback()
        logger.error(f"Error generando tabla de amortización: {str(e)}")
        raise

    return cuotas_generadas


def _calcular_intervalo_dias(modalidad_pago: str) -> int:
    """
    Calcula días entre cuotas según modalidad.

    Args:
        modalidad_pago: MENSUAL, QUINCENAL o SEMANAL

    Returns:
        Número de días entre cada cuota
    """
    intervalos = {
        "MENSUAL": 30,
        "QUINCENAL": 15,
        "SEMANAL": 7,
    }

    return intervalos.get(modalidad_pago, 30)  # Default mensual


def obtener_cuotas_prestamo(
    prestamo_id: int,
    db: Session,
) -> List[Cuota]:
    """
    Obtiene todas las cuotas de un préstamo.

    Args:
        prestamo_id: ID del préstamo
        db: Sesión de base de datos

    Returns:
        Lista de cuotas ordenadas por número
    """
    return (
        db.query(Cuota)
        .filter(Cuota.prestamo_id == prestamo_id)
        .order_by(Cuota.numero_cuota)
        .all()
    )


def obtener_cuotas_pendientes(
    prestamo_id: int,
    db: Session,
) -> List[Cuota]:
    """
    Obtiene cuotas pendientes de un préstamo.

    Args:
        prestamo_id: ID del préstamo
        db: Sesión de base de datos

    Returns:
        Lista de cuotas pendientes
    """
    return (
        db.query(Cuota)
        .filter(
            Cuota.prestamo_id == prestamo_id,
            Cuota.estado.in_(["PENDIENTE", "VENCIDA", "PARCIAL"]),
        )
        .order_by(Cuota.numero_cuota)
        .all()
    )


def obtener_cuotas_vencidas(
    prestamo_id: int,
    db: Session,
) -> List[Cuota]:
    """
    Obtiene cuotas vencidas de un préstamo.

    Args:
        prestamo_id: ID del préstamo
        db: Sesión de base de datos

    Returns:
        Lista de cuotas vencidas
    """
    from datetime import date

    fecha_hoy = date.today()

    return (
        db.query(Cuota)
        .filter(
            Cuota.prestamo_id == prestamo_id,
            Cuota.fecha_vencimiento < fecha_hoy.isoformat(),
            Cuota.estado != "PAGADA",
        )
        .order_by(Cuota.numero_cuota)
        .all()
    )
