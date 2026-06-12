# -*- coding: utf-8 -*-
"""RBAC guards for destructive payment endpoints."""

import os
import sys

os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
os.environ.setdefault("SECRET_KEY", "test-secret-key-with-32-chars-123456")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.deps import require_operator_or_higher
from app.main import app


def _dependency_calls_for_endpoint(endpoint_name: str) -> set[object]:
    for route in app.routes:
        endpoint = getattr(route, "endpoint", None)
        if getattr(endpoint, "__name__", "") == endpoint_name:
            return {dep.call for dep in route.dependant.dependencies}
    raise AssertionError(f"No se encontro endpoint {endpoint_name}")


def test_eliminar_pago_requiere_operario_o_superior():
    assert require_operator_or_higher in _dependency_calls_for_endpoint("eliminar_pago")


def test_reaplicar_pagos_por_prestamo_requiere_operario_o_superior():
    assert require_operator_or_higher in _dependency_calls_for_endpoint(
        "aplicar_pagos_pendientes_cuotas_por_prestamo"
    )
