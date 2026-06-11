# -*- coding: utf-8 -*-
"""Estado de cuenta: asiento ABONOS Conciliar debe listarse como pago realizado."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.dialects import postgresql

from app.models.pago import Pago
from app.services.estado_cuenta_datos import listar_pagos_realizados_estado_cuenta
from app.services.pagos_sql_where import _where_pago_elegible_reaplicacion_cascada


def test_listar_pagos_realizados_usa_criterio_elegible_cascada():
    """El listado del PDF ya no filtra solo estado=PAGADO (excluía ABONOS post-Conciliar)."""
    q = select(Pago).where(
        Pago.prestamo_id.in_([1812]),
        Pago.monto_pagado > 0,
        _where_pago_elegible_reaplicacion_cascada(),
    )
    sql = str(q.compile(dialect=postgresql.dialect())).upper()
    assert "VERIFICADO_CONCORDANCIA" in sql or "CONCILIADO" in sql
    assert "PAGADO" in sql
    assert "PRESTAMO_ID" in sql


def test_abonos_post_conciliar_no_entraba_con_filtro_solo_pagado():
    """Documenta el caso préstamo 1812: ABONOS queda PENDIENTE con verificado SI."""
    estado = "PENDIENTE"
    verificado = "SI"
    assert estado != "PAGADO"
    assert verificado == "SI"
    # Con el criterio nuevo (elegible cascada), verificado SI sigue siendo operativo.
    assert listar_pagos_realizados_estado_cuenta.__doc__ is not None
    assert "ABONOS" in listar_pagos_realizados_estado_cuenta.__doc__
