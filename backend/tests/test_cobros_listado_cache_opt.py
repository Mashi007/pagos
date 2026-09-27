"""Tests for cobros listado-y-kpis cache / SWR low-risk optimizations."""
import os
import sys
import time
from unittest.mock import MagicMock, patch

os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
os.environ.setdefault("SECRET_KEY", "test-secret-key-with-32-chars-123456")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.api.v1.endpoints.cobros import listado_kpis_cache as cache_mod
from app.api.v1.endpoints.cobros.listado_kpis_cache import (
    _cobros_listado_kpis_release_global_swr,
    _cobros_listado_kpis_try_acquire_global_swr,
    _upsert_pago_item_in_listado_kpis_cache,
)
from app.api.v1.endpoints.cobros.reportados_listado_payload import (
    _clausulas_filtro_falla_validadores_scan,
)
from app.api.v1.endpoints.cobros.reportados_routes import (
    _refrescar_cache_tras_editar_reportado,
    _reportado_en_cola_manual_listado,
)


def test_filtro_falla_validadores_en_revision_es_noop():
    db = MagicMock()
    with patch(
        "app.api.v1.endpoints.cobros.reportados_listado_payload._falla_validadores_columna_disponible",
        return_value=True,
    ):
        assert _clausulas_filtro_falla_validadores_scan(db, estado="en_revision") == []


def test_filtro_falla_validadores_pendiente_sin_or_estado():
    db = MagicMock()
    with patch(
        "app.api.v1.endpoints.cobros.reportados_listado_payload._falla_validadores_columna_disponible",
        return_value=True,
    ):
        clauses = _clausulas_filtro_falla_validadores_scan(db, estado="pendiente")
    assert len(clauses) == 1


def test_filtro_falla_validadores_default_tiene_or():
    db = MagicMock()
    with patch(
        "app.api.v1.endpoints.cobros.reportados_listado_payload._falla_validadores_columna_disponible",
        return_value=True,
    ):
        clauses = _clausulas_filtro_falla_validadores_scan(db, estado=None)
    assert len(clauses) == 1


def test_cola_manual_membership_helpers():
    assert _reportado_en_cola_manual_listado("en_revision", False) is True
    assert _reportado_en_cola_manual_listado("pendiente", True) is True
    assert _reportado_en_cola_manual_listado("pendiente", None) is True
    assert _reportado_en_cola_manual_listado("pendiente", False) is False
    assert _reportado_en_cola_manual_listado("rechazado", True) is False


def test_upsert_pago_item_updates_mem_cache_preserves_ttl():
    key = "cobros:listado_y_kpis:v2:test_upsert"
    stale_key = f"{key}:stale"
    payload = {
        "items": [
            {"id": 1, "monto": 10.0, "nombres": "A"},
            {"id": 2, "monto": 20.0, "nombres": "B"},
        ],
        "total": 2,
        "kpis": {"pendiente": 2, "total": 2},
    }
    exp = time.time() + 600
    with cache_mod._cobros_listado_kpis_mem_lock:
        cache_mod._cobros_listado_kpis_mem_cache[key] = (exp, dict(payload))
        cache_mod._cobros_listado_kpis_mem_stale_cache[stale_key] = (
            exp,
            dict(payload),
        )

    with patch(
        "app.api.v1.endpoints.cobros.listado_kpis_cache.get_redis_client",
        return_value=None,
    ):
        ok = _upsert_pago_item_in_listado_kpis_cache(
            {"id": 2, "monto": 99.5, "nombres": "B2"}
        )
    assert ok is True
    with cache_mod._cobros_listado_kpis_mem_lock:
        _, fresh = cache_mod._cobros_listado_kpis_mem_cache[key]
        _, stale = cache_mod._cobros_listado_kpis_mem_stale_cache[stale_key]
        assert fresh["items"][1]["monto"] == 99.5
        assert fresh["items"][1]["nombres"] == "B2"
        assert fresh["items"][0]["monto"] == 10.0
        assert stale["items"][1]["monto"] == 99.5
        # TTL (exp_ts) preserved
        assert cache_mod._cobros_listado_kpis_mem_cache[key][0] == exp
        # cleanup
        cache_mod._cobros_listado_kpis_mem_cache.pop(key, None)
        cache_mod._cobros_listado_kpis_mem_stale_cache.pop(stale_key, None)


def test_refrescar_cache_field_edit_upserts_not_invalidate():
    pr = MagicMock()
    pr.id = 42
    pr.estado = "en_revision"
    pr.falla_validadores_manual = True
    item = MagicMock()
    item.model_dump.return_value = {"id": 42, "monto": 1.0, "estado": "en_revision"}

    with patch(
        "app.api.v1.endpoints.cobros.reportados_routes._pago_reportado_list_items_from_rows",
        return_value=[item],
    ) as build_items, patch(
        "app.api.v1.endpoints.cobros.reportados_routes._upsert_pago_item_in_listado_kpis_cache"
    ) as upsert, patch(
        "app.api.v1.endpoints.cobros.reportados_routes._invalidate_cobros_listado_kpis_cache"
    ) as inv, patch(
        "app.api.v1.endpoints.cobros.reportados_routes._drop_pagos_from_listado_kpis_cache"
    ) as drop:
        _refrescar_cache_tras_editar_reportado(
            MagicMock(),
            pr,
            estado_previo="en_revision",
            falla_previa=True,
        )
    build_items.assert_called_once()
    upsert.assert_called_once()
    inv.assert_not_called()
    drop.assert_not_called()


def test_refrescar_cache_sale_cola_hace_drop():
    pr = MagicMock()
    pr.id = 7
    pr.estado = "pendiente"
    pr.falla_validadores_manual = False

    with patch(
        "app.api.v1.endpoints.cobros.reportados_routes._drop_pagos_from_listado_kpis_cache"
    ) as drop, patch(
        "app.api.v1.endpoints.cobros.reportados_routes._invalidate_cobros_listado_kpis_cache"
    ) as inv:
        _refrescar_cache_tras_editar_reportado(
            MagicMock(),
            pr,
            estado_previo="pendiente",
            falla_previa=True,
        )
    drop.assert_called_once()
    inv.assert_not_called()


def test_refrescar_cache_entra_cola_invalida_fresco():
    pr = MagicMock()
    pr.id = 9
    pr.estado = "pendiente"
    pr.falla_validadores_manual = True

    with patch(
        "app.api.v1.endpoints.cobros.reportados_routes._invalidate_cobros_listado_kpis_cache"
    ) as inv, patch(
        "app.api.v1.endpoints.cobros.reportados_routes._drop_pagos_from_listado_kpis_cache"
    ) as drop:
        _refrescar_cache_tras_editar_reportado(
            MagicMock(),
            pr,
            estado_previo="rechazado",
            falla_previa=False,
        )
    inv.assert_called_once()
    drop.assert_not_called()


def test_global_swr_singleflight_coalesce():
    # Ensure clean state
    _cobros_listado_kpis_release_global_swr()
    assert _cobros_listado_kpis_try_acquire_global_swr() is True
    assert _cobros_listado_kpis_try_acquire_global_swr() is False
    _cobros_listado_kpis_release_global_swr()
    assert _cobros_listado_kpis_try_acquire_global_swr() is True
    _cobros_listado_kpis_release_global_swr()


def test_cedulas_matching_norms_targeted():
    from app.api.v1.endpoints.cobros.reportados_dedup_helpers import (
        _cedulas_en_clientes_matching_norms,
    )

    db = MagicMock()
    db.execute.return_value.scalars.return_value.all.return_value = ["V20588848"]
    matched = _cedulas_en_clientes_matching_norms(db, {"V20588848", "V99999999"})
    assert "V20588848" in matched
    assert "V99999999" not in matched
    # Should not have issued a full-table unfiltered select of all clientes
    db.execute.assert_called()
