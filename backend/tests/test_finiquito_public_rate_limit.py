# -*- coding: utf-8 -*-
"""Límites por IP en endpoints públicos Finiquito (verificar OTP, registro)."""
import os
import sys

import pytest
from fastapi import HTTPException

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core import cobros_public_rate_limit as rl


def test_finiquito_verificar_codigo_rate_limit_in_memory():
    ip = "192.0.2.50"
    max_ok = rl.FINIQUITO_VERIFICAR_CODIGO_MAX
    for _ in range(max_ok):
        rl.check_rate_limit_finiquito_verificar_codigo(ip)
    with pytest.raises(HTTPException) as exc:
        rl.check_rate_limit_finiquito_verificar_codigo(ip)
    assert exc.value.status_code == 429


def test_finiquito_registro_rate_limit_in_memory():
    ip = "192.0.2.51"
    max_ok = rl.FINIQUITO_REGISTRO_MAX
    for _ in range(max_ok):
        rl.check_rate_limit_finiquito_registro(ip)
    with pytest.raises(HTTPException) as exc:
        rl.check_rate_limit_finiquito_registro(ip)
    assert exc.value.status_code == 429
