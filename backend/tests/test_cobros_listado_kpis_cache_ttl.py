# -*- coding: utf-8 -*-
"""TTL configurable del cache listado-y-kpis."""

import os
import sys

os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
os.environ.setdefault("SECRET_KEY", "test-secret-key-with-32-chars-123456")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_resolve_ttl_default_1800(monkeypatch):
    monkeypatch.delenv("COBROS_LISTADO_KPIS_CACHE_TTL_SEC", raising=False)
    from app.api.v1.endpoints.cobros import listado_kpis_cache as mod

    assert mod._resolve_cobros_listado_kpis_cache_ttl_sec() == 1800


def test_resolve_ttl_env_override(monkeypatch):
    monkeypatch.setenv("COBROS_LISTADO_KPIS_CACHE_TTL_SEC", "2400")
    from app.api.v1.endpoints.cobros import listado_kpis_cache as mod

    assert mod._resolve_cobros_listado_kpis_cache_ttl_sec() == 2400
