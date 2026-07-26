# -*- coding: utf-8 -*-
"""Regresion: seriales bancarios reutilizados no deben enlazar/corromper pagos."""

from __future__ import annotations

from datetime import date, datetime
from types import SimpleNamespace

from app.services.conciliacion_bancos_service import (
    _clave_paquete_ref,
    _paquete_banco_coherente_con_pago,
    _resolver_match_por_digitos,
    _similitud,
)


def _pago(**kwargs):
    base = dict(
        id=1,
        numero_documento="2058270",
        monto_pagado=50.0,
        fecha_pago=datetime(2026, 6, 1, 12, 0, 0),
        cedula_cliente="V123",
        prestamo_id=10,
        institucion_bancaria="BNV",
    )
    base.update(kwargs)
    return SimpleNamespace(**base)


def test_paquete_incoherente_por_monto():
    p = _pago(monto_pagado=50.0)
    assert (
        _paquete_banco_coherente_con_pago(
            p, fecha_banco=date(2026, 6, 1), monto_usd=100.0
        )
        is False
    )


def test_paquete_incoherente_por_fecha():
    p = _pago(fecha_pago=datetime(2026, 6, 1))
    assert (
        _paquete_banco_coherente_con_pago(
            p, fecha_banco=date(2026, 7, 15), monto_usd=50.0
        )
        is False
    )


def test_paquete_coherente():
    p = _pago(monto_pagado=50.0, fecha_pago=datetime(2026, 6, 1))
    assert (
        _paquete_banco_coherente_con_pago(
            p, fecha_banco=date(2026, 6, 1), monto_usd=50.0
        )
        is True
    )


def test_mismo_serial_paquete_distinto_es_serial_reusado_no_match():
    """BNV reutiliza 2058270: no MATCH_EXACTO ni caer a parcial."""
    historico = _pago(id=1, monto_pagado=50.0, fecha_pago=datetime(2026, 6, 1))
    accion, pago, pool = _resolver_match_por_digitos(
        [historico],
        fecha_banco=date(2026, 7, 15),
        monto_usd=100.0,
    )
    assert accion == "SERIAL_REUSADO"
    assert pago is None
    assert pool == []


def test_mismo_serial_paquete_igual_es_match_exacto():
    p = _pago(id=2, monto_pagado=100.0, fecha_pago=datetime(2026, 7, 15))
    accion, pago, pool = _resolver_match_por_digitos(
        [p],
        fecha_banco=date(2026, 7, 15),
        monto_usd=100.0,
    )
    assert accion == "MATCH_EXACTO"
    assert pago is p
    assert pool == []


def test_varios_seriales_desambiguar_por_monto_fecha():
    a = _pago(id=1, monto_pagado=50.0, fecha_pago=datetime(2026, 6, 1))
    b = _pago(id=2, monto_pagado=100.0, fecha_pago=datetime(2026, 7, 15))
    accion, pago, pool = _resolver_match_por_digitos(
        [a, b],
        fecha_banco=date(2026, 7, 15),
        monto_usd=100.0,
    )
    assert accion == "MATCH_EXACTO"
    assert pago is b
    assert pool == []


def test_varios_seriales_sin_desambiguar_es_ambiguo():
    a = _pago(id=1, monto_pagado=100.0, fecha_pago=datetime(2026, 7, 15))
    b = _pago(id=2, monto_pagado=100.0, fecha_pago=datetime(2026, 7, 15))
    accion, pago, pool = _resolver_match_por_digitos(
        [a, b],
        fecha_banco=date(2026, 7, 15),
        monto_usd=100.0,
    )
    assert accion == "AMBIGUO"
    assert pago is None
    assert {p.id for p in pool} == {1, 2}


def test_similitud_mismo_serial_es_100():
    """Documenta el riesgo: sin corte SERIAL_REUSADO, MATCH_PARCIAL enlazaria igual."""
    assert _similitud("2058270", "2058270") == 100.0


def test_clave_paquete_distingue_reuso_mismo_serial():
    k1 = _clave_paquete_ref("2058270", date(2026, 6, 1), 50.0)
    k2 = _clave_paquete_ref("2058270", date(2026, 7, 15), 100.0)
    assert k1 is not None and k2 is not None
    assert k1 != k2
    assert k1[0] == k2[0] == "2058270"
