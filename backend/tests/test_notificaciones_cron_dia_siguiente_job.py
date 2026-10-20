# -*- coding: utf-8 -*-
"""Cron día siguiente: gate = ENABLE_CRON_*, no el toggle UI Envío."""
from __future__ import annotations

from unittest.mock import MagicMock

from app.services import notificaciones_cron_dia_siguiente_job as job


def test_cron_dia_siguiente_envia_aunque_toggle_ui_off(monkeypatch):
    """
    Regresión: con habilitado=false el cron marcaba omitido_tipo y no enviaba,
    mientras el botón manual sí enviaba (respetar_toggle_envio=False).
    """
    db = MagicMock()
    monkeypatch.setattr(job, "_cargar_estado", lambda _db: {})
    monkeypatch.setattr(
        job,
        "get_notificaciones_envios_dict",
        lambda _db: {"PAGO_1_DIA_ATRASADO": {"habilitado": False}},
    )
    monkeypatch.setattr(job, "hoy_negocio", lambda: __import__("datetime").date(2026, 10, 19))

    calls = []

    def _fake_envio(db, tipo, fecha_referencia=None, *, respetar_toggle_envio=False, **_kw):
        calls.append({"tipo": tipo, "respetar_toggle_envio": respetar_toggle_envio})
        return {
            "enviados": 3,
            "total_en_lista": 3,
            "fallidos": 0,
            "sin_email": 0,
            "omitidos_config": 0,
        }

    monkeypatch.setattr(
        "app.api.v1.endpoints.notificaciones_tabs.ejecutar_envio_caso_manual",
        _fake_envio,
    )
    monkeypatch.setattr(job, "_guardar_slot", lambda *a, **k: None)

    out = job.ejecutar_cron_dia_siguiente(db, slot="17:15")

    assert out.get("omitido") is False
    assert out.get("enviados") == 3
    assert calls == [
        {"tipo": "PAGO_1_DIA_ATRASADO", "respetar_toggle_envio": False}
    ]


def test_cron_dia_siguiente_sigue_omitido_si_ya_terminal_hoy(monkeypatch):
    db = MagicMock()
    monkeypatch.setattr(
        job,
        "_cargar_estado",
        lambda _db: {
            "fecha_referencia_caracas": "2026-10-19",
            "slots": {"17:15": {"estado": "ok"}},
        },
    )
    monkeypatch.setattr(job, "hoy_negocio", lambda: __import__("datetime").date(2026, 10, 19))

    out = job.ejecutar_cron_dia_siguiente(db, slot="17:15")
    assert out.get("omitido") is True
    assert out.get("motivo") == "ya_resultado_terminal_slot_hoy"
