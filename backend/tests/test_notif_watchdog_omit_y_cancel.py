# -*- coding: utf-8 -*-
"""Regresiones criticas: omit window al reanudar y cancel sticky."""
from __future__ import annotations

from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock

import app.services.notificaciones_lote_watchdog as watchdog
from app.services.cuota_estado import hoy_negocio
from app.services.notificaciones_envio_cancel import cancelacion_lote_activa


def test_cancelacion_lote_activa_no_cancela_otro_tipo():
    db = MagicMock()
    row = SimpleNamespace(
        valor='{"activo": true, "tipo_caso": "PREJUDICIAL", "token_seguimiento": "abc"}'
    )
    db.get.return_value = row
    assert cancelacion_lote_activa(db) is True  # pipeline sin scope
    assert cancelacion_lote_activa(db, tipo_caso="PREJUDICIAL") is True
    assert cancelacion_lote_activa(db, tipo_caso="COBRANZAS_EXCEL") is False
    assert cancelacion_lote_activa(db, token_seguimiento="abc") is True
    assert cancelacion_lote_activa(db, token_seguimiento="zzz") is False


def test_omitir_iso_fallback_inicio_utc_sin_fecha_negocio():
    hoy = hoy_negocio()
    ayer = hoy - timedelta(days=1)
    ultimo = {
        "origen": "api_enviar_caso_manual",
        "inicio_utc": f"{ayer.isoformat()}T16:00:00+00:00",
        "detalles": {
            "procesados": 40,
            "cerrado_por_stale": True,
        },
    }
    assert watchdog.omitir_iso_desde_ultimo(ultimo) == ayer.isoformat()


def test_omitir_iso_prefiere_fecha_negocio_inicio():
    ultimo = {
        "inicio_utc": "2026-08-01T16:00:00+00:00",
        "detalles": {
            "fecha_negocio_inicio": "2026-08-05",
            "fecha_negocio_pausa": "2026-08-06",
        },
    }
    assert watchdog.omitir_iso_desde_ultimo(ultimo) == "2026-08-05"


def test_lote_reanudable_stale_dia_siguiente():
    hoy = hoy_negocio()
    ayer = hoy - timedelta(days=1)
    ultimo = {
        "origen": "api_enviar_caso_manual",
        "estado": "finalizado",
        "tipo_caso": "PREJUDICIAL",
        "inicio_utc": f"{ayer.isoformat()}T16:00:00+00:00",
        "total_en_lista": 100,
        "detalles": {
            "procesados": 40,
            "total_en_lista": 100,
            "cerrado_por_stale": True,
            "tipo_caso": "PREJUDICIAL",
        },
    }
    out = watchdog.lote_reanudable(ultimo)
    assert out is not None
    assert out[0] == "PREJUDICIAL"
    assert out[2] == 40
