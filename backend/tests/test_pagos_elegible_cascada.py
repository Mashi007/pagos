# -*- coding: utf-8 -*-
"""Elegibilidad de pagos para cascada / reaplicacion por prestamo."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.dialects import postgresql

from app.models.pago import Pago
from app.services.pagos_sql_where import _where_pago_elegible_reaplicacion_cascada


def test_elegible_cascada_no_incluye_pendiente_sin_verificar():
    """PENDIENTE sin conciliar no debe entrar en cascada solo por tener prestamo_id."""
    q = select(Pago).where(
        Pago.prestamo_id == 782,
        Pago.monto_pagado > 0,
        _where_pago_elegible_reaplicacion_cascada(),
    )
    sql = str(
        q.compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True})
    ).upper()
    assert "CONCILIADO" in sql
    assert "PAGADO" in sql
    assert "PENDIENTE" not in sql
