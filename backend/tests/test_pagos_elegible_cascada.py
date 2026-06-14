# -*- coding: utf-8 -*-
"""Elegibilidad de pagos para cascada / reaplicacion por prestamo."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.dialects import postgresql

from app.models.pago import Pago
from app.services.pagos_sql_where import _where_pago_elegible_reaplicacion_cascada


def test_elegible_cascada_incluye_pendiente_con_prestamo():
    """PENDIENTE sin conciliar pero con prestamo_id entra en cascada (revision manual)."""
    q = select(Pago).where(
        Pago.prestamo_id == 782,
        Pago.monto_pagado > 0,
        _where_pago_elegible_reaplicacion_cascada(),
    )
    sql = str(
        q.compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True})
    ).upper()
    assert "PENDIENTE" in sql
    assert "PRESTAMO_ID IS NOT NULL" in sql
    assert "CONCILIADO" in sql
    assert "PAGADO" in sql
