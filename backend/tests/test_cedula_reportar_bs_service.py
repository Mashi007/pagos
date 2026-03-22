"""Tests unitarios: normalización y coincidencia lista Bs (sin BD)."""
import pytest

from app.services.cobros.cedula_reportar_bs_service import (
    normalize_cedula_lookup_key,
    expand_cedula_variants_for_bs_list,
    cedula_coincide_autorizados_bs,
    normalize_cedula_para_almacenar_lista_bs,
)


def test_normalize_lookup_strips_leading_zeros():
    assert normalize_cedula_lookup_key("V08752971") == "V8752971"
    assert normalize_cedula_lookup_key("v-10341284") == "V10341284"


def test_expand_variants():
    v = expand_cedula_variants_for_bs_list("V10341284")
    assert "V10341284" in v
    assert "10341284" in v


def test_coincide_con_interseccion():
    auth = frozenset({"V10341284", "10341284"})
    assert cedula_coincide_autorizados_bs("V10341284", auth)
    # El listado admin pasa cédula ya normalizada (ceros a la izquierda quitados en el número)
    assert cedula_coincide_autorizados_bs(normalize_cedula_lookup_key("V010341284"), auth)


def test_para_almacenar_rechaza_corta():
    assert normalize_cedula_para_almacenar_lista_bs("V12") is None


def test_para_almacenar_digitos_solo():
    assert normalize_cedula_para_almacenar_lista_bs("10341284") == "V10341284"
