# -*- coding: utf-8 -*-
"""Staff puede alta en LIQUIDADO; sin user se bloquea (portal/auto)."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

from app.services.pagos_desistimiento_politica import bloquear_alta_pago_salvo_staff


def test_sin_user_bloquea_liquidado(monkeypatch):
    db = MagicMock()
    monkeypatch.setattr(
        "app.services.pagos_desistimiento_politica.obtener_estado_prestamo",
        lambda *_a, **_k: "LIQUIDADO",
    )
    msg = bloquear_alta_pago_salvo_staff(db, 3183, user=None)
    assert msg is not None
    assert "LIQUIDADO" in msg


def test_staff_admin_permite_liquidado(monkeypatch):
    db = MagicMock()
    monkeypatch.setattr(
        "app.services.pagos_desistimiento_politica.obtener_estado_prestamo",
        lambda *_a, **_k: "LIQUIDADO",
    )
    staff = SimpleNamespace(rol="admin", is_admin=True)
    assert bloquear_alta_pago_salvo_staff(db, 3183, user=staff) is None


def test_aprobado_no_bloquea(monkeypatch):
    db = MagicMock()
    monkeypatch.setattr(
        "app.services.pagos_desistimiento_politica.obtener_estado_prestamo",
        lambda *_a, **_k: "APROBADO",
    )
    assert bloquear_alta_pago_salvo_staff(db, 1, user=None) is None
