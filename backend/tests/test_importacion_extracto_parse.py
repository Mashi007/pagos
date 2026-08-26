# -*- coding: utf-8 -*-
from app.services.importacion_extracto_service import extraer_cedula_descripcion


def test_extraer_cedula_dp_con_guion():
    assert extraer_cedula_descripcion("DP:V-019200177 JOSE ARTEAGA") in (
        "V019200177",
        "V19200177",
    )


def test_extraer_cedula_rt():
    c = extraer_cedula_descripcion("RT:V-013793738 JOSE RUIZ")
    assert c and c.startswith("V") and "13793738" in c


def test_extraer_cedula_vacia():
    assert extraer_cedula_descripcion("") is None
    assert extraer_cedula_descripcion("SIN CEDULA AQUI") is None
