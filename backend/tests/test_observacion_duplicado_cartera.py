"""Observaciones de duplicado: mismo crédito vs otro préstamo vs otros bancos."""

import os
import sys

os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
os.environ.setdefault("SECRET_KEY", "test-secret-key-with-32-chars-123456")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.api.v1.endpoints.cobros.reportados_dedup_helpers import (
    DUPLICADO_COLA_OBS,
    DUPLICADO_EN_CARTERA_OBS,
    DUPLICADO_MISMO_PRESTAMO_OBS,
    DUPLICADO_OTRO_PRESTAMO_OBS,
    _texto_observacion_duplicado_cartera,
)


def test_mismo_prestamo_mercantil_no_sugiere_visto():
    txt = _texto_observacion_duplicado_cartera(
        mercantil=True,
        mismo_prestamo=True,
        prestamo_existente_id=1071,
        prestamo_objetivo_id=1071,
        pago_existente_id=88,
    )
    assert txt.startswith(DUPLICADO_MISMO_PRESTAMO_OBS)
    assert "préstamo #1071" in txt
    assert "pago #88" in txt
    assert "ya aplicado en este crédito" in txt
    assert "Mercantil/Visto no aplica" in txt
    assert "añade _P" not in txt


def test_otro_prestamo_mercantil_si_menciona_excepcion():
    txt = _texto_observacion_duplicado_cartera(
        mercantil=True,
        mismo_prestamo=False,
        prestamo_existente_id=200,
        prestamo_objetivo_id=1071,
        pago_existente_id=9,
    )
    assert txt.startswith(DUPLICADO_OTRO_PRESTAMO_OBS)
    assert "préstamo #200" in txt
    assert "préstamo #1071" in txt
    assert "Excepción Mercantil/Visto" in txt
    assert "_P/_A" in txt


def test_otro_prestamo_otros_bancos_analizado_sin_visto():
    txt = _texto_observacion_duplicado_cartera(
        mercantil=False,
        mismo_prestamo=False,
        prestamo_existente_id=200,
        prestamo_objetivo_id=1071,
        pago_existente_id=9,
    )
    assert txt.startswith(DUPLICADO_OTRO_PRESTAMO_OBS)
    assert "Otros bancos no tienen excepción Visto" in txt
    assert "Excepción Mercantil" not in txt


def test_cartera_sin_resolver_otros_bancos_queda_analizado():
    txt = _texto_observacion_duplicado_cartera(
        mercantil=False,
        mismo_prestamo=None,
        prestamo_existente_id=55,
        prestamo_objetivo_id=None,
        pago_existente_id=3,
    )
    assert txt.startswith(DUPLICADO_EN_CARTERA_OBS)
    assert "Analizado" in txt
    assert "no reaplican" in txt


def test_cartera_sin_resolver_mercantil_no_es_evidencia_de_excepcion():
    txt = _texto_observacion_duplicado_cartera(
        mercantil=True,
        mismo_prestamo=None,
        prestamo_existente_id=55,
        prestamo_objetivo_id=None,
        pago_existente_id=3,
    )
    assert txt.startswith(DUPLICADO_EN_CARTERA_OBS)
    assert "No es evidencia de excepción Mercantil" in txt


def test_constante_cola_no_es_excepcion_mercantil():
    assert DUPLICADO_COLA_OBS == "DUPLICADO COLA"
