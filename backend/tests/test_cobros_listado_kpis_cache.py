import os
import sys
from datetime import date
from unittest.mock import MagicMock, patch

os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
os.environ.setdefault("SECRET_KEY", "test-secret-key-with-32-chars-123456")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.api.v1.endpoints.cobros import listado_kpis_cache as cache


def _cache_payload(fecha_desde: date, fecha_hasta: date) -> str:
    return cache._cobros_listado_kpis_cache_key_payload(
        estado=None,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        cedula=None,
        institucion=None,
        page=1,
        per_page=20,
        incluir_exportados=False,
    )


def test_stale_default_snapshot_is_not_reused_for_different_dates():
    previous_day = _cache_payload(date(2026, 7, 1), date(2026, 7, 15))
    current_day = _cache_payload(date(2026, 7, 2), date(2026, 7, 16))

    with patch.object(cache, "get_redis_client", return_value=None):
        cache._invalidate_cobros_listado_kpis_cache()
        cache._cobros_listado_kpis_cache_set(previous_day, {"items": [{"id": 1}]})

        assert cache._cobros_listado_kpis_cache_get_stale(previous_day) is not None
        assert cache._cobros_listado_kpis_cache_get_stale(current_day) is None


def test_invalidation_removes_fresh_and_stale_snapshots():
    cache_payload = _cache_payload(date(2026, 7, 1), date(2026, 7, 15))

    with patch.object(cache, "get_redis_client", return_value=None):
        cache._invalidate_cobros_listado_kpis_cache()
        cache._cobros_listado_kpis_cache_set(cache_payload, {"items": [{"id": 1}]})

        cache._invalidate_cobros_listado_kpis_cache()

        assert cache._cobros_listado_kpis_cache_get(cache_payload) is None
        assert cache._cobros_listado_kpis_cache_get_stale(cache_payload) is None


def test_snapshot_started_before_surgical_cache_patch_cannot_repopulate_cache():
    cache_payload = _cache_payload(date(2026, 7, 1), date(2026, 7, 15))

    with patch.object(cache, "get_redis_client", return_value=None):
        cache._invalidate_cobros_listado_kpis_cache()
        generation_before_mutation = cache._cobros_listado_kpis_cache_generation()

        cache._drop_pagos_from_listado_kpis_cache([1])
        published = cache._cobros_listado_kpis_cache_set(
            cache_payload,
            {"items": [{"id": 1}]},
            expected_generation=generation_before_mutation,
        )

        assert published is False
        assert cache._cobros_listado_kpis_cache_get(cache_payload) is None
        assert cache._cobros_listado_kpis_cache_get_stale(cache_payload) is None


def test_redis_invalidation_deletes_stale_snapshots_too():
    redis_client = MagicMock()
    redis_client.scan_iter.return_value = [
        b"cobros:listado_y_kpis:v2:fresh",
        b"cobros:listado_y_kpis:v2:fresh:stale",
        b"cobros:listado_y_kpis:v2:latest_default",
    ]

    with patch.object(cache, "get_redis_client", return_value=redis_client):
        cache._invalidate_cobros_listado_kpis_cache()

    redis_client.delete.assert_called_once_with(*redis_client.scan_iter.return_value)
