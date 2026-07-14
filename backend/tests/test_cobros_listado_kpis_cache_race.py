"""Regresiones de concurrencia del cache listado-y-kpis de Cobros."""
from __future__ import annotations

import os
import sys

import pytest

os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
os.environ.setdefault("SECRET_KEY", "test-secret-key-with-32-chars-123456")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.api.v1.endpoints.cobros import listado_kpis_cache as cache


class _FakeRedisPipeline:
    def __init__(self, redis: "_FakeRedis") -> None:
        self.redis = redis
        self.watched_generation = 0
        self.commands = []

    def watch(self, key: str) -> None:
        self.watched_generation = int(self.redis.values.get(key) or 0)

    def get(self, key: str):
        return self.redis.get(key)

    def unwatch(self) -> None:
        self.commands = []

    def multi(self) -> None:
        self.commands = []

    def setex(self, key: str, ttl: int, value: str) -> None:
        self.commands.append((key, ttl, value))

    def execute(self):
        if self.redis.increment_generation_on_execute:
            self.redis.increment_generation_on_execute = False
            self.redis.incr(cache._COBROS_LISTADO_KPIS_GENERATION_KEY)
        current_generation = int(
            self.redis.values.get(cache._COBROS_LISTADO_KPIS_GENERATION_KEY) or 0
        )
        if current_generation != self.watched_generation:
            raise RuntimeError("generation changed while watched")
        for key, _ttl, value in self.commands:
            self.redis.values[key] = value
        return [True] * len(self.commands)

    def reset(self) -> None:
        self.commands = []


class _FakeRedis:
    def __init__(self) -> None:
        self.values = {}
        self.increment_generation_on_execute = False

    def get(self, key: str):
        return self.values.get(key)

    def incr(self, key: str) -> int:
        value = int(self.values.get(key) or 0) + 1
        self.values[key] = str(value)
        return value

    def pipeline(self) -> _FakeRedisPipeline:
        return _FakeRedisPipeline(self)


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


def test_redis_watch_rejects_mutation_between_generation_check_and_exec(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    redis = _FakeRedis()
    monkeypatch.setattr(cache, "get_redis_client", lambda: redis)
    cache_payload = _cache_payload()
    payload = _payload_with_payment(789)
    generation_at_swr_start = cache._cobros_listado_kpis_generation_snapshot()

    # Simula INCR de otro worker después del GET observado pero antes de EXEC.
    redis.increment_generation_on_execute = True
    assert cache._cobros_listado_kpis_cache_set_if_generation(
        cache_payload,
        payload,
        generation_at_swr_start,
    ) is False
    assert cache._cobros_listado_kpis_storage_key(cache_payload) not in redis.values

    current_generation = cache._cobros_listado_kpis_generation_snapshot()
    assert cache._cobros_listado_kpis_cache_set_if_generation(
        cache_payload,
        payload,
        current_generation,
    ) is True
    assert cache._cobros_listado_kpis_storage_key(cache_payload) in redis.values
    assert cache._cobros_listado_kpis_stale_storage_key(cache_payload) in redis.values
    assert cache._COBROS_LISTADO_KPIS_LATEST_DEFAULT_KEY in redis.values
