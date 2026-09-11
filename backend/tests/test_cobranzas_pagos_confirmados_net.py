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


def test_netear_usa_confirmados_de_esa_columna():
    """Cada columna resta solo los confirmados de su ventana, no el stock global."""
    hoy = "2026-09-10"
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
            {"fecha": "2026-08-01", "cantidad": 15, "monto_usd": 5526.0},
            {"fecha": hoy, "cantidad": 2, "monto_usd": 200.0},
        ]
    }
    _netear_total_vencidos_con_confirmados(desempeno, confirmados)
    L_ago = desempeno["total"]["lecturas"][0]
    L_hoy = desempeno["total"]["lecturas"][1]
    assert L_ago["confirmados_monto_usd"] == 5526.0
    assert L_ago["monto_usd"] == 44474.0
    assert L_hoy["confirmados_cantidad"] == 2
    assert L_hoy["confirmados_monto_usd"] == 200.0
    assert L_hoy["monto_usd"] == 1974745.13


def test_lecturas_confirmados_reparte_por_mes(monkeypatch):
    from datetime import date

    from app.services.cobranzas import universo_analisis_service as svc

    por_dia = {
        date(2026, 7, 10): (10, 1000.0),
        date(2026, 8, 5): (5, 500.0),
        date(2026, 9, 2): (3, 300.0),
        date(2026, 9, 10): (2, 200.0),
    }
    monkeypatch.setattr(
        svc, "_load_confirmados_activos_por_dia", lambda _db, _a, _b: por_dia
    )
    monkeypatch.setattr(
        svc, "_load_confirmados_activos_totales", lambda _db: (999, 99_999.0)
    )
    out = svc._lecturas_pagos_confirmados(object(), date(2026, 9, 10))
    by = {L["fecha"]: L for L in out["lecturas"]}
    assert by["2026-07-01"]["cantidad"] == 10
    assert by["2026-07-01"]["monto_usd"] == 1000.0
    assert by["2026-08-01"]["cantidad"] == 5
    assert by["2026-08-01"]["monto_usd"] == 500.0
    assert by["2026-09-01"]["cantidad"] == 3
    assert by["2026-09-01"]["monto_usd"] == 300.0
    assert by["2026-09-10"]["cantidad"] == 2
    assert by["2026-09-10"]["monto_usd"] == 200.0


def test_universo_analisis_response_conserva_pagos_confirmados():
    """FastAPI response_model no debe recortar la fila ni el desglose neto."""
    from app.schemas.cobranza import UniversoAnalisisResponse

    payload = {
        "buckets": {},
        "desempeno_lecturas": {
            "columnas": [
                {"fecha": "2026-09-10", "etiqueta": "Hoy", "es_hoy": True}
            ],
            "buckets": {},
            "total": {
                "clave": "total",
                "lecturas": [
                    {
                        "fecha": "2026-09-10",
                        "cantidad": 90,
                        "monto_usd": 9000.0,
                        "monto_usd_bruto": 10000.0,
                        "confirmados_monto_usd": 1000.0,
                        "confirmados_cantidad": 5,
                    }
                ],
            },
            "pagos_confirmados": {
                "clave": "pagos_confirmados",
                "lecturas": [
                    {"fecha": "2026-09-10", "cantidad": 5, "monto_usd": 1000.0}
                ],
            },
        },
    }
    dumped = UniversoAnalisisResponse.model_validate(payload).model_dump()
    dl = dumped["desempeno_lecturas"]
    assert dl["pagos_confirmados"]["lecturas"][0]["monto_usd"] == 1000.0
    assert dl["total"]["lecturas"][0]["confirmados_monto_usd"] == 1000.0
    assert dl["total"]["lecturas"][0]["monto_usd_bruto"] == 10000.0


def test_invalidate_universo_analisis_cache_limpia_snapshot():
    import app.services.cobranzas.universo_analisis_service as svc

    with svc._analisis_cache_lock:
        svc._analisis_cache["k"] = (0.0, {"x": 1})
    invalidate_universo_analisis_cache()
    with svc._analisis_cache_lock:
        assert svc._analisis_cache == {}
