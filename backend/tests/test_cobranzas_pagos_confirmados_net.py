# -*- coding: utf-8 -*-
from datetime import date
from unittest.mock import MagicMock

from app.services.cobranzas.universo_analisis_service import (
    _netear_total_vencidos_con_confirmados,
    aplicar_overlays_manual_pagos_confirmados_cobranzas_ui,
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

    class _Row(tuple):
        pass

    class _FakeDb:
        def execute(self, *_a, **_k):
            # residual < 2026-07-01
            return type("R", (), {"one": lambda self: (4, 400.0)})()

    monkeypatch.setattr(
        svc, "_load_confirmados_activos_por_dia", lambda _db, _a, _b: por_dia
    )
    out = svc._lecturas_pagos_confirmados(_FakeDb(), date(2026, 9, 10))
    by = {L["fecha"]: L for L in out["lecturas"]}
    assert by["2026-07-01"]["cantidad"] == 10
    assert by["2026-07-01"]["monto_usd"] == 1000.0
    assert by["2026-08-01"]["cantidad"] == 5
    assert by["2026-08-01"]["monto_usd"] == 500.0
    assert by["2026-09-01"]["cantidad"] == 3
    assert by["2026-09-01"]["monto_usd"] == 300.0
    # Hoy = depósitos de hoy + residual anterior a julio
    assert by["2026-09-10"]["cantidad"] == 2 + 4
    assert by["2026-09-10"]["monto_usd"] == 600.0


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


def test_propagar_manual_mes_suma_en_columna_hoy():
    from app.services.cobranzas.pagos_confirmados_manual_service import (
        propagar_manual_acumulado_mes_a_columna_hoy,
    )

    class _Row:
        cantidad = 0
        monto_usd = 1503600.0

    hoy = date(2026, 10, 11)
    lecturas = [
        {"fecha": "2026-10-01", "cantidad": 0, "monto_usd": 1503600.0},
        {
            "fecha": "2026-10-11",
            "cantidad": 436,
            "monto_usd": 57821.95,
            "cantidad_automatica": 436,
            "monto_usd_automatico": 57821.95,
        },
    ]
    propagar_manual_acumulado_mes_a_columna_hoy(
        lecturas, hoy=hoy, manual={date(2026, 10, 1): _Row()}
    )
    h = lecturas[1]
    assert h["cantidad"] == 436
    assert h["monto_usd"] == 1503600.0 + 57821.95
    assert h["manual_override"] is True


def test_overlay_ui_aplica_manual_y_neto_solo_en_payload(monkeypatch):
    class _Row:
        fecha_lectura = date(2026, 10, 1)
        cantidad = 0
        monto_usd = 1503600.0

    monkeypatch.setattr(
        "app.services.cobranzas.pagos_confirmados_manual_service.load_manual_pagos_confirmados_map",
        lambda _db: {date(2026, 10, 1): _Row()},
    )
    payload = {
        "desempeno_lecturas": {
            "total": {
                "lecturas": [
                    {
                        "fecha": "2026-10-01",
                        "cantidad": 3544,
                        "monto_usd": 2008048.89,
                        "cobrado_usd": 75351.07,
                        "cantidad_cobrada": 535,
                    }
                ]
            },
            "pagos_confirmados": {
                "lecturas": [
                    {"fecha": "2026-10-01", "cantidad": 0, "monto_usd": 0.0}
                ]
            },
        }
    }
    aplicar_overlays_manual_pagos_confirmados_cobranzas_ui(MagicMock(), payload)
    pc = payload["desempeno_lecturas"]["pagos_confirmados"]["lecturas"][0]
    tot = payload["desempeno_lecturas"]["total"]["lecturas"][0]
    assert pc["monto_usd"] == 1503600.0
    assert pc["manual_override"] is True
    assert tot["confirmados_monto_usd"] == 1503600.0
    assert tot["monto_usd"] == 429097.82


def test_invalidate_universo_analisis_cache_limpia_snapshot():
    import app.services.cobranzas.universo_analisis_service as svc

    with svc._analisis_cache_lock:
        svc._analisis_cache["k"] = (0.0, {"x": 1})
    invalidate_universo_analisis_cache()
    with svc._analisis_cache_lock:
        assert svc._analisis_cache == {}
