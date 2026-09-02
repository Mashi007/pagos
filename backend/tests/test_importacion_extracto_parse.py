# -*- coding: utf-8 -*-
from app.services.importacion_extracto_service import (
    _serial_norm_comparacion,
    extraer_cedula_descripcion,
)


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


def test_serial_norm_ignora_prefijo_bnc():
    assert _serial_norm_comparacion("BNC/24803998") == "24803998"
    assert _serial_norm_comparacion("24803998") == "24803998"
    assert _serial_norm_comparacion("BNC / REF.24803998") == "24803998"


def test_serial_norm_ignora_letras_y_signos_izquierda():
    """Extracto vs sistema: solo números; BNC/, VE /, espacios y signos no cuentan."""
    assert _serial_norm_comparacion("BNC/153403928") == "153403928"
    assert _serial_norm_comparacion("VE / 139422742") == "139422742"
    assert _serial_norm_comparacion("VE / 139422448") == "139422448"
    assert _serial_norm_comparacion("VE/139422742") == "139422742"
    assert _serial_norm_comparacion("BNC / 153403928") == "153403928"
    # Match extracto (solo dígitos) ↔ pago en cartera con prefijo mostrado en UI.
    assert _serial_norm_comparacion("153403928") == _serial_norm_comparacion(
        "BNC/153403928"
    )
    assert _serial_norm_comparacion("139422742") == _serial_norm_comparacion(
        "VE / 139422742"
    )


def test_serial_norm_ceros_izquierda():
    assert _serial_norm_comparacion("BNC/024803998") == "24803998"
    assert _serial_norm_comparacion("00024803998") == "24803998"


def test_seriales_norm_multiples_campos():
    from app.services.importacion_extracto_service import _seriales_norm_desde_campos

    assert _seriales_norm_desde_campos("BNC/24803998", "24803998", None) == ["24803998"]
    assert _seriales_norm_desde_campos("BNC/111", "REF.222") == ["111", "222"]


def test_agregar_pago_campos_al_indice_serial_compuesto():
    from app.services.importacion_extracto_service import (
        _agregar_pago_campos_al_indice_serial,
    )

    pagos_global: dict = {}
    filtro = {"740087436120310", "999"}
    _agregar_pago_campos_al_indice_serial(
        pagos_global,
        filtro=filtro,
        pago_id=37329,
        prestamo_id=4413,
        num_doc="740087405865859/740087436120310",
        ref="740087405865859/740087436120310",
        ref_n=None,
        doc_c=None,
        doc_cr=None,
    )
    assert pagos_global["740087436120310"] == [(37329, 4413)]
    assert "740087405865859" not in pagos_global


def test_cedula_canon_ceros_y_guion():
    from app.services.importacion_extracto_service import _cedula_canon_match

    assert _cedula_canon_match("V-015276832") == "V15276832"
    assert _cedula_canon_match("V15276832") == "V15276832"
    assert _cedula_canon_match("015276832") == "V15276832"


def test_verif_cedula_serial_texto():
    from app.services.importacion_extracto_service import _verif_cedula_serial

    t = _verif_cedula_serial("V-019200177", "BNC/24803998")
    assert t == "cedula=V19200177 serial=24803998"


def test_serial_mixto_partes():
    from app.services.importacion_extracto_service import (
        _MARCA_OBS_SERIAL_COMPUESTO,
        _anotar_serial_mixto,
        _es_serial_mixto_texto,
        _normalizar_detalle_observaciones,
        _partes_serial_texto,
        _seriales_norm_desde_campos,
    )

    raw = "BNC/125201931 - BNC/103917175"
    assert _es_serial_mixto_texto(raw) is True
    assert _partes_serial_texto(raw) == ["125201931", "103917175"]
    assert "125201931" in _seriales_norm_desde_campos(raw)
    assert "103917175" in _seriales_norm_desde_campos(raw)
    assert not _es_serial_mixto_texto("BNC/125201931")
    assert _serial_norm_comparacion("125201931.0") == "125201931"
    ev = _anotar_serial_mixto({"detalle": "100%"}, {"mixto_by_prestamo": {1: [9]}}, 1, 9)
    assert _MARCA_OBS_SERIAL_COMPUESTO in ev["detalle"]
    assert ev["alerta_serial_mixto"] is True
    assert (
        _normalizar_detalle_observaciones("100% | serial Mixto")
        == f"100% | {_MARCA_OBS_SERIAL_COMPUESTO}"
    )


def test_similitud_serial_alineada_conciliacion():
    from app.services.importacion_extracto_service import _similitud_serial

    assert _similitud_serial("125201931", "125201931") == 100.0
    # Contención ceros (regla Conciliación Bancos)
    assert _similitud_serial("90694665", "00090694665") >= 90.0
    # Distintos → no inflar a semejante
    assert _similitud_serial("125201931", "103917175") < 70.0


def test_seriales_extracto_multiparte():
    from app.services.importacion_extracto_service import _seriales_extracto_comparar

    assert _seriales_extracto_comparar("BNC/111 - BNC/222", "111") == ["111", "222"]
    assert _seriales_extracto_comparar("125201931.0", "125201931") == ["125201931"]


def test_buscar_igual_100_serial_compuesto_bd():
    from app.services.importacion_extracto_service import _buscar_igual_100_en_prestamo

    pagos = [(99, "125201931"), (99, "103917175")]
    hit = _buscar_igual_100_en_prestamo(pagos, ["125201931"])
    assert hit == (99, "125201931")


def test_normalizar_observaciones_drive_y_compuesto():
    from app.services.importacion_extracto_service import (
        _MARCA_OBS_DRIVE,
        _MARCA_OBS_SERIAL_COMPUESTO,
        _detalle_tiene_marca_drive,
        _detalle_tiene_marca_serial_compuesto,
        _normalizar_detalle_observaciones,
        _texto_obs_banco_drive,
    )

    assert _texto_obs_banco_drive([10, 20]).startswith(_MARCA_OBS_DRIVE)
    leg = _normalizar_detalle_observaciones("x | banco Drive (1 pago(s): 10)")
    assert leg == f"x | {_MARCA_OBS_DRIVE} (1 pago(s): 10)"
    assert _detalle_tiene_marca_drive(leg)
    assert _detalle_tiene_marca_serial_compuesto(
        _normalizar_detalle_observaciones("match | serial Mixto")
    )
    assert _MARCA_OBS_SERIAL_COMPUESTO in _normalizar_detalle_observaciones("serial Mixto")


def test_normalizar_banco_extracto():
    from app.services.importacion_extracto_service import _normalizar_banco_extracto

    assert _normalizar_banco_extracto("BNC") == "BNC"
    assert _normalizar_banco_extracto("bnc") == "BNC"
    assert _normalizar_banco_extracto("Mercantil") == "Mercantil"
    assert _normalizar_banco_extracto("Binance") == "Binance"
    assert _normalizar_banco_extracto("") is None
    assert _normalizar_banco_extracto("Otros") is None
