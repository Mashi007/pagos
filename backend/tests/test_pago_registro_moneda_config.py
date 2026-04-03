"""Umbral de exencion lista Bs configurable (settings)."""
from app.core.config import settings


def test_pagos_bs_monto_exento_lista_cedula_bounds():
    """Valido en cualquier .env: Pydantic ya fuerza ge/le en Settings."""
    v = settings.PAGOS_BS_MONTO_EXENTO_LISTA_CEDULA
    assert isinstance(v, int)
    assert 1 <= v <= 999_999_999
