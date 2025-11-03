"""
Funciones helper para trabajar con pagos_staging
Evita problemas con columnas que no existen usando SQL directo
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import text
from sqlalchemy.orm import Session


def sumar_monto_pagado_staging(
    db: Session,
    fecha_inicio: Optional[datetime] = None,
    fecha_fin: Optional[datetime] = None,
) -> Decimal:
    """
    Suma monto_pagado de pagos_staging con filtros de fecha opcionales
    Usa SQL directo porque fecha_pago y monto_pagado son TEXT en BD
    """
    query_sql = """
        SELECT COALESCE(SUM(monto_pagado::numeric), 0)
        FROM pagos_staging
        WHERE monto_pagado IS NOT NULL
          AND monto_pagado != ''
          AND monto_pagado ~ '^[0-9]+(\.[0-9]+)?$'
    """

    params = {}
    conditions = []

    if fecha_inicio:
        conditions.append("fecha_pago::timestamp >= :fecha_inicio")
        params["fecha_inicio"] = fecha_inicio

    if fecha_fin:
        conditions.append("fecha_pago::timestamp <= :fecha_fin")
        params["fecha_fin"] = fecha_fin

    if fecha_inicio or fecha_fin:
        conditions.append("fecha_pago IS NOT NULL")
        conditions.append("fecha_pago != ''")
        conditions.append("LENGTH(TRIM(fecha_pago)) >= 10")
        conditions.append("fecha_pago ~ '^\\d{4}-\\d{2}-\\d{2}'")

    if conditions:
        query_sql += " AND " + " AND ".join(conditions)

    result = db.execute(text(query_sql).bindparams(**params))
    return Decimal(str(result.scalar() or 0))


def contar_pagos_staging(
    db: Session,
    fecha_inicio: Optional[datetime] = None,
    fecha_fin: Optional[datetime] = None,
    cedula_cliente: Optional[str] = None,
) -> int:
    """
    Cuenta registros en pagos_staging con filtros opcionales
    """
    query_sql = """
        SELECT COUNT(*)
        FROM pagos_staging
        WHERE 1=1
    """

    params = {}
    conditions = []

    if fecha_inicio:
        conditions.append("fecha_pago::timestamp >= :fecha_inicio")
        params["fecha_inicio"] = fecha_inicio

    if fecha_fin:
        conditions.append("fecha_pago::timestamp <= :fecha_fin")
        params["fecha_fin"] = fecha_fin

    if fecha_inicio or fecha_fin:
        conditions.append("fecha_pago IS NOT NULL")
        conditions.append("fecha_pago != ''")
        conditions.append("LENGTH(TRIM(fecha_pago)) >= 10")
        conditions.append("fecha_pago ~ '^\\d{4}-\\d{2}-\\d{2}'")

    if cedula_cliente:
        conditions.append("cedula_cliente = :cedula_cliente")
        params["cedula_cliente"] = cedula_cliente

    if conditions:
        query_sql += " AND " + " AND ".join(conditions)

    result = db.execute(text(query_sql).bindparams(**params))
    return result.scalar() or 0
