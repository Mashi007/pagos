# -*- coding: utf-8 -*-
"""Regresion: historial de correo no debe adivinar cedula si hay ambiguedad."""

from __future__ import annotations

from unittest.mock import MagicMock

from app.services.cliente_email_historial_service import cedula_por_email_historial


def test_cedula_historial_unico_ok():
    db = MagicMock()
    db.execute.return_value.all.return_value = [(10, "V123", "V123")]
    assert cedula_por_email_historial(db, "ex@mail.com") == "V123"


def test_cedula_historial_ambiguo_retorna_none():
    db = MagicMock()
    db.execute.return_value.all.return_value = [
        (10, "V111", "V111"),
        (20, "V222", "V222"),
    ]
    assert cedula_por_email_historial(db, "shared@mail.com") is None


def test_cedula_historial_vacio():
    db = MagicMock()
    db.execute.return_value.all.return_value = []
    assert cedula_por_email_historial(db, "nadie@mail.com") is None
