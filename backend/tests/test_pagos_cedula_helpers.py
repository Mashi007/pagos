"""Regresión: helper de cédula VEJ usado por importar_un_pago_reportado_a_pagos."""
from app.api.v1.endpoints.pagos.pagos_cedula_helpers import looks_like_cedula_vej
from app.api.v1.endpoints.pagos.upload_excel_routes import importar_un_pago_reportado_a_pagos


def test_looks_like_cedula_vej():
    assert looks_like_cedula_vej("V12345678") is True
    assert looks_like_cedula_vej("v12345678") is True
    assert looks_like_cedula_vej("Z12345678") is False
    assert looks_like_cedula_vej("") is False


def test_importar_un_pago_reportado_exporta_helper():
    assert callable(importar_un_pago_reportado_a_pagos)
