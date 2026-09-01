# -*- coding: utf-8 -*-
from app.services.cobranzas.universo_analisis_service import (
    _netear_total_vencidos_con_confirmados,
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
