# -*- coding: utf-8 -*-
"""Idempotencia envío diario gestores."""

import os
import sys
from datetime import date
from unittest.mock import MagicMock, patch

os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
os.environ.setdefault("SECRET_KEY", "test-secret-key-with-32-chars-123456")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.cobranzas import gestores_email_diario_job as job


def test_ya_enviado_ok_hoy_true():
    db = MagicMock()
    hoy = date(2026, 8, 25).isoformat()
    with patch.object(
        job,
        "leer_estado_email_gestores_dia",
        return_value={"fecha_referencia_caracas": hoy, "estado": "ok"},
    ):
        assert job.ya_enviado_ok_hoy(db, hoy_iso=hoy) is True


def test_ejecutar_cron_omite_si_ya_ok():
    db = MagicMock()
    hoy = date(2026, 8, 25).isoformat()
    with patch.object(job, "hoy_negocio", return_value=date(2026, 8, 25)):
        with patch.object(job, "ya_enviado_ok_hoy", return_value=True):
            res = job.ejecutar_gestores_email_cron(db, origen="cron")
    assert res.get("omitido") is True
    assert res.get("motivo") == "ya_enviado_hoy"


def test_ejecutar_cron_llama_envio_si_pendiente():
    db = MagicMock()
    with patch.object(job, "hoy_negocio", return_value=date(2026, 8, 25)):
        with patch.object(job, "ya_enviado_ok_hoy", return_value=False):
            with patch.object(job, "_ahora_caracas") as mock_now:
                mock_now.return_value.hour = 18
                with patch(
                    "app.services.cobranzas.gestores_service.enviar_listas_gestores_email",
                    return_value={"ok": True, "adjuntos": 9, "asunto": "Listas actualizadas 2026-08-25"},
                ) as mock_send:
                    with patch.object(job, "guardar_estado_email_gestores_dia") as mock_save:
                        res = job.ejecutar_gestores_email_cron(db, origen="cron")
    mock_send.assert_called_once()
    mock_save.assert_called_once()
    assert res.get("ok") is True
