"""Regresiones de concurrencia del cache listado-y-kpis de Cobros."""
from __future__ import annotations

import os
import sys

import pytest

os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
os.environ.setdefault("SECRET_KEY", "test-secret-key-with-32-chars-123456")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.api.v1.endpoints.cobros import listado_kpis_cache as cache


@pytest.fixture(autouse=True)
def _isolated_memory_cache(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(cache, "get_redis_client", lambda: None)
    with cache._cobros_listado_kpis_mem_lock:
        cache._cobros_listado_kpis_mem_cache.clear()
        cache._cobros_listado_kpis_mem_stale_cache.clear()
        cache._cobros_listado_kpis_inflight.clear()
        cache._cobros_listado_kpis_mem_latest_default = None
        cache._cobros_listado_kpis_mem_generation = 0
    yield
    with cache._cobros_listado_kpis_mem_lock:
        cache._cobros_listado_kpis_mem_cache.clear()
        cache._cobros_listado_kpis_mem_stale_cache.clear()
        cache._cobros_listado_kpis_inflight.clear()
        cache._cobros_listado_kpis_mem_latest_default = None
        cache._cobros_listado_kpis_mem_generation = 0


def _cache_payload() -> str:
    return cache._cobros_listado_kpis_cache_key_payload(
        estado=None,
        fecha_desde=None,
        fecha_hasta=None,
        cedula=None,
        institucion=None,
        page=1,
        per_page=20,
        incluir_exportados=False,
    )


def _payload_with_payment(payment_id: int) -> dict:
    return {
        "items": [{"id": payment_id, "estado": "pendiente"}],
        "total": 1,
        "page": 1,
        "per_page": 20,
        "kpis": {
            "pendiente": 1,
            "en_revision": 0,
            "aprobado": 0,
            "rechazado": 0,
            "total": 1,
        },
    }


def test_swr_started_before_drop_cannot_resurrect_payment() -> None:
    cache_payload = _cache_payload()
    stale_computation = _payload_with_payment(123)
    cache._cobros_listado_kpis_cache_set(cache_payload, stale_computation)
    generation_at_swr_start = cache._cobros_listado_kpis_generation_snapshot()

    cache._drop_pagos_from_listado_kpis_cache(
        [123],
        estados_previos={123: "pendiente"},
    )

    assert cache._cobros_listado_kpis_cache_set_if_generation(
        cache_payload,
        stale_computation,
        generation_at_swr_start,
    ) is False
    fresh = cache._cobros_listado_kpis_cache_get(cache_payload)
    stale = cache._cobros_listado_kpis_cache_get_stale(cache_payload)
    assert fresh is not None
    assert stale is not None
    assert fresh["items"] == []
    assert stale["items"] == []
    assert fresh["kpis"]["pendiente"] == 0
    assert stale["kpis"]["pendiente"] == 0


def test_swr_started_before_invalidation_cannot_republish_old_snapshot() -> None:
    cache_payload = _cache_payload()
    old_payload = _payload_with_payment(456)
    cache._cobros_listado_kpis_cache_set(cache_payload, old_payload)
    generation_at_swr_start = cache._cobros_listado_kpis_generation_snapshot()

    cache._invalidate_cobros_listado_kpis_cache()

    assert cache._cobros_listado_kpis_cache_set_if_generation(
        cache_payload,
        old_payload,
        generation_at_swr_start,
    ) is False
    assert cache._cobros_listado_kpis_cache_get(cache_payload) is None

    current_generation = cache._cobros_listado_kpis_generation_snapshot()
    current_payload = {
        **old_payload,
        "items": [],
        "total": 0,
        "kpis": {**old_payload["kpis"], "pendiente": 0, "total": 0},
    }
    assert cache._cobros_listado_kpis_cache_set_if_generation(
        cache_payload,
        current_payload,
        current_generation,
    ) is True
    assert cache._cobros_listado_kpis_cache_get(cache_payload)["items"] == []
