from __future__ import annotations

import pytest

from app.api.v1.endpoints.cobros import routes as cobros_routes


def test_listado_y_kpis_fresh_does_not_read_cached_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    """fresh=true must force a recalculation, even when the same key is cached."""

    def fail_cache_read(*args, **kwargs):
        raise AssertionError("fresh requests must not read listado-y-kpis cache")

    monkeypatch.setattr(cobros_routes, "_cobros_listado_kpis_cache_get", fail_cache_read)
    monkeypatch.setattr(cobros_routes, "_cobros_listado_kpis_cache_get_stale", fail_cache_read)
    monkeypatch.setattr(
        cobros_routes,
        "_cobros_listado_kpis_try_acquire_singleflight",
        lambda *args, **kwargs: pytest.fail("fresh requests must not join single-flight cache wait"),
    )
    monkeypatch.setattr(
        cobros_routes,
        "_cobros_listado_kpis_cache_set",
        lambda *args, **kwargs: pytest.fail("fresh requests must not write listado-y-kpis cache"),
    )

    def fake_list_payload(*args, **kwargs):
        return {
            "items": [{"id": 42, "estado": "pendiente"}],
            "total": 1,
            "page": kwargs["page"],
            "per_page": kwargs["per_page"],
            "_manual_kpi_counts": {"pendiente": 1, "en_revision": 0},
        }

    monkeypatch.setattr(cobros_routes, "_list_pagos_reportados_payload", fake_list_payload)
    monkeypatch.setattr(
        cobros_routes,
        "_kpis_pagos_reportados_payload",
        lambda *args, **kwargs: {
            "pendiente": 1,
            "en_revision": 0,
            "rechazado": 0,
            "importado": 0,
            "total": 1,
        },
    )

    result = cobros_routes.list_pagos_reportados_y_kpis(
        db=object(),
        page=1,
        per_page=20,
        fresh=True,
    )

    assert result == {
        "items": [{"id": 42, "estado": "pendiente"}],
        "total": 1,
        "page": 1,
        "per_page": 20,
        "kpis": {
            "pendiente": 1,
            "en_revision": 0,
            "rechazado": 0,
            "importado": 0,
            "total": 1,
        },
    }
