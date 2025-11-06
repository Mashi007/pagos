"""
Helper para vincular pagos con cuotas usando múltiples estrategias
Soluciona el problema de pagos no vinculados correctamente a cuotas
"""

import logging
from datetime import date, timedelta
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session

from app.models.amortizacion import Cuota
from app.models.pago import Pago
from app.models.prestamo import Prestamo

logger = logging.getLogger(__name__)


def obtener_pagos_cuota(
    db: Session,
    prestamo_id: int,
    numero_cuota: int,
    cedula: str,
    fecha_vencimiento: date,
    monto_cuota: Optional[Decimal] = None,
) -> List[Pago]:
    """
    Obtiene pagos de una cuota usando múltiples estrategias de búsqueda.

    Estrategias (en orden de prioridad):
    1. prestamo_id + numero_cuota (ideal, más preciso)
    2. cedula + fecha_vencimiento exacta (buena aproximación)
    3. cedula + rango de fechas (±30 días) (última opción)
    4. cedula + monto_cuota similar (si se proporciona)

    Args:
        db: Sesión de base de datos
        prestamo_id: ID del préstamo
        numero_cuota: Número de cuota
        cedula: Cédula del cliente
        fecha_vencimiento: Fecha de vencimiento de la cuota
        monto_cuota: Monto de la cuota (opcional, para validación)

    Returns:
        Lista de pagos asociados a la cuota
    """
    pagos_encontrados = []
    pagos_ids = set()  # Para evitar duplicados

    # ESTRATEGIA 1: prestamo_id + numero_cuota (más precisa)
    if prestamo_id and numero_cuota:
        pagos = (
            db.query(Pago)
            .filter(
                and_(
                    Pago.prestamo_id == prestamo_id,
                    Pago.numero_cuota == numero_cuota,
                    Pago.activo.is_(True),
                    Pago.monto_pagado > 0,
                )
            )
            .all()
        )

        for pago in pagos:
            if pago.id not in pagos_ids:
                pagos_encontrados.append(pago)
                pagos_ids.add(pago.id)

        if pagos_encontrados:
            logger.debug(
                f"✅ [obtener_pagos_cuota] Encontrados {len(pagos_encontrados)} pagos "
                f"por prestamo_id={prestamo_id} + numero_cuota={numero_cuota}"
            )
            return pagos_encontrados

    # ESTRATEGIA 2: cedula + fecha_vencimiento exacta
    if cedula and fecha_vencimiento:
        pagos = (
            db.query(Pago)
            .filter(
                and_(
                    Pago.cedula == cedula,
                    func.date(Pago.fecha_pago) == fecha_vencimiento,
                    Pago.activo.is_(True),
                    Pago.monto_pagado > 0,
                )
            )
            .all()
        )

        for pago in pagos:
            if pago.id not in pagos_ids:
                # Validar que el monto sea razonable (opcional)
                if monto_cuota is None or abs(float(pago.monto_pagado) - float(monto_cuota)) <= float(monto_cuota) * 0.2:
                    pagos_encontrados.append(pago)
                    pagos_ids.add(pago.id)

        if pagos_encontrados:
            logger.debug(
                f"✅ [obtener_pagos_cuota] Encontrados {len(pagos_encontrados)} pagos "
                f"por cedula={cedula} + fecha_vencimiento={fecha_vencimiento}"
            )
            return pagos_encontrados

    # ESTRATEGIA 3: cedula + rango de fechas (±30 días)
    if cedula and fecha_vencimiento:
        fecha_inicio = fecha_vencimiento - timedelta(days=30)
        fecha_fin = fecha_vencimiento + timedelta(days=30)

        pagos = (
            db.query(Pago)
            .filter(
                and_(
                    Pago.cedula == cedula,
                    func.date(Pago.fecha_pago) >= fecha_inicio,
                    func.date(Pago.fecha_pago) <= fecha_fin,
                    Pago.activo.is_(True),
                    Pago.monto_pagado > 0,
                )
            )
            .order_by(Pago.fecha_pago)
            .all()
        )

        for pago in pagos:
            if pago.id not in pagos_ids:
                # Validar que el monto sea razonable
                if monto_cuota is None or abs(float(pago.monto_pagado) - float(monto_cuota)) <= float(monto_cuota) * 0.3:
                    pagos_encontrados.append(pago)
                    pagos_ids.add(pago.id)

        if pagos_encontrados:
            logger.debug(
                f"✅ [obtener_pagos_cuota] Encontrados {len(pagos_encontrados)} pagos "
                f"por cedula={cedula} + rango de fechas ({fecha_inicio} a {fecha_fin})"
            )
            return pagos_encontrados

    # ESTRATEGIA 4: cedula + monto similar (si se proporciona monto_cuota)
    if cedula and monto_cuota:
        # Buscar pagos con monto similar (±20%)
        monto_min = monto_cuota * Decimal("0.8")
        monto_max = monto_cuota * Decimal("1.2")

        pagos = (
            db.query(Pago)
            .filter(
                and_(
                    Pago.cedula == cedula,
                    Pago.monto_pagado >= monto_min,
                    Pago.monto_pagado <= monto_max,
                    Pago.activo.is_(True),
                    func.date(Pago.fecha_pago) >= fecha_vencimiento - timedelta(days=60),
                    func.date(Pago.fecha_pago) <= fecha_vencimiento + timedelta(days=60),
                )
            )
            .order_by(func.abs(Pago.monto_pagado - monto_cuota))
            .limit(1)
            .all()
        )

        for pago in pagos:
            if pago.id not in pagos_ids:
                pagos_encontrados.append(pago)
                pagos_ids.add(pago.id)

        if pagos_encontrados:
            logger.debug(f"✅ [obtener_pagos_cuota] Encontrado 1 pago " f"por cedula={cedula} + monto similar a {monto_cuota}")
            return pagos_encontrados

    if not pagos_encontrados:
        logger.debug(
            f"⚠️ [obtener_pagos_cuota] No se encontraron pagos para "
            f"prestamo_id={prestamo_id}, numero_cuota={numero_cuota}, "
            f"cedula={cedula}, fecha_vencimiento={fecha_vencimiento}"
        )

    return pagos_encontrados


def calcular_total_pagado_cuota(
    db: Session,
    cuota: Cuota,
) -> Decimal:
    """
    Calcula el total pagado de una cuota usando múltiples estrategias.

    Args:
        db: Sesión de base de datos
        cuota: Objeto Cuota

    Returns:
        Total pagado (Decimal)
    """
    # Obtener cédula del préstamo (solo necesitamos cedula, no todo el objeto)
    # ✅ CORRECCIÓN: Usar query directo de cedula para evitar error si valor_activo no existe en BD
    prestamo_cedula = db.query(Prestamo.cedula).filter(Prestamo.id == cuota.prestamo_id).scalar()
    if not prestamo_cedula:
        return Decimal("0")

    # Obtener pagos usando helper
    pagos = obtener_pagos_cuota(
        db=db,
        prestamo_id=cuota.prestamo_id,
        numero_cuota=cuota.numero_cuota,
        cedula=prestamo_cedula,
        fecha_vencimiento=cuota.fecha_vencimiento,
        monto_cuota=cuota.monto_cuota,
    )

    # Sumar montos
    total = sum(pago.monto_pagado for pago in pagos)
    return Decimal(str(total))


def calcular_monto_pagado_mes(
    db: Session,
    mes: date,  # Primer día del mes
    prestamo_id: Optional[int] = None,
    cedula: Optional[str] = None,
) -> Decimal:
    """
    Calcula el monto pagado en un mes específico.

    Busca pagos que correspondan a cuotas que vencen en ese mes.

    Args:
        db: Sesión de base de datos
        mes: Primer día del mes
        prestamo_id: ID del préstamo (opcional, para filtrar)
        cedula: Cédula del cliente (opcional, para filtrar)

    Returns:
        Monto total pagado en ese mes
    """
    from calendar import monthrange

    # Último día del mes
    ultimo_dia = date(mes.year, mes.month, monthrange(mes.year, mes.month)[1])

    # Obtener cuotas que vencen en ese mes
    query_cuotas = (
        db.query(Cuota)
        .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
        .filter(and_(Cuota.fecha_vencimiento >= mes, Cuota.fecha_vencimiento <= ultimo_dia, Prestamo.estado == "APROBADO"))
    )

    if prestamo_id:
        query_cuotas = query_cuotas.filter(Cuota.prestamo_id == prestamo_id)
    if cedula:
        query_cuotas = query_cuotas.filter(Prestamo.cedula == cedula)

    cuotas = query_cuotas.all()

    # Calcular total pagado sumando pagos de cada cuota
    total_pagado = Decimal("0")
    for cuota in cuotas:
        # ✅ CORRECCIÓN: Usar with_entities para evitar error si valor_activo no existe en BD
        # Solo necesitamos cedula, así que especificamos solo esa columna
        prestamo_cedula = db.query(Prestamo.cedula).filter(Prestamo.id == cuota.prestamo_id).scalar()
        if prestamo_cedula:
            pagos = obtener_pagos_cuota(
                db=db,
                prestamo_id=cuota.prestamo_id,
                numero_cuota=cuota.numero_cuota,
                cedula=prestamo_cedula,
                fecha_vencimiento=cuota.fecha_vencimiento,
                monto_cuota=cuota.monto_cuota,
            )
            total_pagado += sum(pago.monto_pagado for pago in pagos)

    return total_pagado


def reconciliar_pago_cuota(
    db: Session,
    pago: Pago,
) -> Optional[Cuota]:
    """
    Intenta reconciliar un pago con una cuota.

    Args:
        db: Sesión de base de datos
        pago: Objeto Pago a reconciliar

    Returns:
        Cuota reconciliada o None
    """
    # Si ya tiene prestamo_id y numero_cuota, verificar que la cuota existe
    if pago.prestamo_id and pago.numero_cuota:
        cuota = db.query(Cuota).filter(Cuota.prestamo_id == pago.prestamo_id, Cuota.numero_cuota == pago.numero_cuota).first()

        if cuota:
            return cuota

    # Buscar por cédula y fecha
    if pago.cedula and pago.fecha_pago:
        fecha_pago_date = pago.fecha_pago.date()

        # Buscar préstamos por cédula (solo necesitamos id, no todo el objeto)
        # ✅ CORRECCIÓN: Usar query directo de id para evitar error si valor_activo no existe en BD
        prestamo_ids = [
            row[0] for row in db.query(Prestamo.id).filter(Prestamo.cedula == pago.cedula, Prestamo.estado == "APROBADO").all()
        ]

        for prestamo_id in prestamo_ids:
            # Buscar cuota que coincida con fecha de pago
            cuota = (
                db.query(Cuota)
                .filter(
                    and_(
                        Cuota.prestamo_id == prestamo_id,
                        Cuota.fecha_vencimiento <= fecha_pago_date + timedelta(days=30),
                        Cuota.fecha_vencimiento >= fecha_pago_date - timedelta(days=30),
                        Cuota.estado != "PAGADO",
                    )
                )
                .order_by(func.abs(func.extract("day", Cuota.fecha_vencimiento - fecha_pago_date)))
                .first()
            )

            if cuota:
                # Vincular pago a cuota
                pago.prestamo_id = prestamo_id
                pago.numero_cuota = cuota.numero_cuota
                return cuota

    return None
