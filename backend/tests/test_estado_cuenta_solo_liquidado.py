from app.services.estado_cuenta_datos import estado_prestamo_es_liquidado


def test_estado_prestamo_es_liquidado_normaliza():
    assert estado_prestamo_es_liquidado("LIQUIDADO") is True
    assert estado_prestamo_es_liquidado(" liquidado ") is True
    assert estado_prestamo_es_liquidado("APROBADO") is False
    assert estado_prestamo_es_liquidado("DESISTIMIENTO") is False
    assert estado_prestamo_es_liquidado(None) is False
    assert estado_prestamo_es_liquidado("") is False
