# -*- coding: utf-8 -*-
from app.services.cobranzas.universo_analisis_service import (
    _netear_total_vencidos_con_confirmados,
    invalidate_universo_analisis_cache,
)


def test_netear_total_vencidos_resta_confirmados():
    desempeno = {
        "total": {
            "lecturas": [
                {"fecha": "2026-01-01", "cantidad": 100, "monto_usd": 50000.0},
            ]
        }
    }
    confirmados = {
        "lecturas": [
            {"fecha": "2026-01-01", "cantidad": 3, "monto_usd": 450.0},
        ]
    }
    _netear_total_vencidos_con_confirmados(desempeno, confirmados)
    L = desempeno["total"]["lecturas"][0]
    assert L["cantidad_bruta"] == 100
    assert L["monto_usd_bruto"] == 50000.0
    assert L["cantidad"] == 97
    assert L["monto_usd"] == 49550.0
    assert L["confirmados_cantidad"] == 3
    assert L["confirmados_monto_usd"] == 450.0
    assert L["cobranzas_monto_usd"] == 0.0


def test_netear_total_vencidos_resta_cobranzas_y_confirmados():
    desempeno = {
        "total": {
            "lecturas": [
                {
                    "fecha": "2026-08-01",
                    "cantidad": 100,
                    "monto_usd": 50000.0,
                    "cobrado_usd": 5000.0,
                    "cantidad_cobrada": 10,
                },
            ]
        }
    }
    confirmados = {
        "lecturas": [
            {"fecha": "2026-08-01", "cantidad": 3, "monto_usd": 450.0},
        ]
    }
    _netear_total_vencidos_con_confirmados(desempeno, confirmados)
    L = desempeno["total"]["lecturas"][0]
    assert L["monto_usd_bruto"] == 50000.0
    assert L["cobranzas_monto_usd"] == 5000.0
    assert L["confirmados_monto_usd"] == 450.0
    assert L["monto_usd"] == 44550.0
    assert L["cantidad"] == 87


def test_netear_total_vencidos_no_negativo():
    desempeno = {
        "total": {
            "lecturas": [
                {"fecha": "2026-02-01", "cantidad": 2, "monto_usd": 100.0},
            ]
        }
    }
    confirmados = {
        "lecturas": [
            {"fecha": "2026-02-01", "cantidad": 5, "monto_usd": 200.0},
        ]
    }
    _netear_total_vencidos_con_confirmados(desempeno, confirmados)
    L = desempeno["total"]["lecturas"][0]
    assert L["cantidad"] == 0
    assert L["monto_usd"] == 0.0


def test_netear_hoy_usa_stock_total_activo_fuera_de_ventana():
    """Confirmados viejos (p. ej. abr-2025) deben restar en columna Hoy."""
    hoy = "2026-09-01"
    desempeno = {
        "total": {
            "lecturas": [
                {"fecha": "2026-08-01", "cantidad": 100, "monto_usd": 50000.0},
                {
                    "fecha": hoy,
                    "cantidad": 3830,
                    "monto_usd": 1975395.13,
                    "cobrado_usd": 450.0,
                    "cantidad_cobrada": 7,
                },
            ]
        }
    }
    confirmados = {
        "lecturas": [
            {"fecha": "2026-08-01", "cantidad": 0, "monto_usd": 0.0},
            {"fecha": hoy, "cantidad": 200, "monto_usd": 45000.0},
        ]
    }
    _netear_total_vencidos_con_confirmados(desempeno, confirmados)
    L_hoy = desempeno["total"]["lecturas"][1]
    assert L_hoy["cantidad"] == 3623
    assert L_hoy["monto_usd"] == 1929945.13
    assert L_hoy["confirmados_cantidad"] == 200
    assert L_hoy["cobranzas_monto_usd"] == 450.0


def test_invalidate_universo_analisis_cache_limpia_snapshot():
    import app.services.cobranzas.universo_analisis_service as svc

    with svc._analisis_cache_lock:
        svc._analisis_cache["k"] = (0.0, {"x": 1})
    invalidate_universo_analisis_cache()
    with svc._analisis_cache_lock:
        assert svc._analisis_cache == {}
