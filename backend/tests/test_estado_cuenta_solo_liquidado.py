from app.services.estado_cuenta_datos import (
    MSG_PORTAL_ESTADO_CUENTA_DESISTIMIENTO,
    estado_prestamo_es_desistimiento,
    estado_prestamo_es_liquidado,
    estado_prestamo_permite_estado_cuenta,
    mensaje_no_elegible_estado_cuenta_portal,
)


def test_estado_prestamo_es_liquidado_normaliza():
    assert estado_prestamo_es_liquidado("LIQUIDADO") is True
    assert estado_prestamo_es_liquidado(" liquidado ") is True
    assert estado_prestamo_es_liquidado("APROBADO") is False
    assert estado_prestamo_es_liquidado("DESISTIMIENTO") is False
    assert estado_prestamo_es_liquidado(None) is False
    assert estado_prestamo_es_liquidado("") is False


def test_estado_cuenta_permite_aprobado_y_liquidado_nunca_desistimiento():
    assert estado_prestamo_permite_estado_cuenta("APROBADO") is True
    assert estado_prestamo_permite_estado_cuenta("aprobado") is True
    assert estado_prestamo_permite_estado_cuenta("LIQUIDADO") is True
    assert estado_prestamo_permite_estado_cuenta("DESISTIMIENTO") is False
    assert estado_prestamo_permite_estado_cuenta("DESESTIMADO") is False
    assert estado_prestamo_permite_estado_cuenta("DESISTIDO") is False
    assert estado_prestamo_permite_estado_cuenta("RECHAZADO") is False
    assert estado_prestamo_permite_estado_cuenta(None) is False


def test_mensaje_portal_desistimiento_sin_elegible():
    from unittest.mock import MagicMock

    db = MagicMock()
    calls = {"n": 0}

    def _first(*_args, **_kwargs):
        calls["n"] += 1
        return (1,) if calls["n"] == 1 else None

    db.execute.return_value.first.side_effect = _first
    msg = mensaje_no_elegible_estado_cuenta_portal(db, "V12345678")
    assert msg == MSG_PORTAL_ESTADO_CUENTA_DESISTIMIENTO


def test_estado_prestamo_es_desistimiento_variantes():
    assert estado_prestamo_es_desistimiento("DESISTIMIENTO") is True
    assert estado_prestamo_es_desistimiento(" desestimado ") is True
    assert estado_prestamo_es_desistimiento("DESISTIDO") is True
    assert estado_prestamo_es_desistimiento("APROBADO") is False
    assert estado_prestamo_es_desistimiento("LIQUIDADO") is False
