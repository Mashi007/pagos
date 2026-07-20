# -*- coding: utf-8 -*-
"""Tests de exclusion LIQUIDADO/DESISTIMIENTO en envios de notificaciones."""
from __future__ import annotations

from unittest.mock import MagicMock

from app.services.notificaciones_exclusion_desistimiento import (
    cliente_sin_cartera_activa_notif,
    item_bloqueado_para_envio_notificacion,
    motivo_bloqueo_prestamo_notificacion,
)


def test_motivo_bloqueo_prestamo_liquidado():
    db = MagicMock()
    db.scalar.return_value = "liquidado"
    assert motivo_bloqueo_prestamo_notificacion(db, 10) == "LIQUIDADO"


def test_motivo_bloqueo_prestamo_desistimiento():
    db = MagicMock()
    db.scalar.return_value = " Desistimiento "
    assert motivo_bloqueo_prestamo_notificacion(db, 11) == "DESISTIMIENTO"


def test_motivo_bloqueo_prestamo_aprobado_no_bloquea():
    db = MagicMock()
    db.scalar.return_value = "APROBADO"
    assert motivo_bloqueo_prestamo_notificacion(db, 12) is None


def test_item_bloqueado_por_prestamo_liquidado():
    db = MagicMock()
    db.scalar.return_value = "LIQUIDADO"
    bloqueado, motivo = item_bloqueado_para_envio_notificacion(
        db, {"prestamo_id": 99, "cliente_id": 1}
    )
    assert bloqueado is True
    assert motivo == "LIQUIDADO"


def test_item_bloqueado_por_cliente_desistimiento():
    calls = {"n": 0}

    def _scalar(stmt):
        calls["n"] += 1
        if calls["n"] == 1:
            return "APROBADO"  # estado prestamo
        if calls["n"] == 2:
            return 1  # count desistimiento
        return 0

    db = MagicMock()
    db.scalar.side_effect = _scalar
    bloqueado, motivo = item_bloqueado_para_envio_notificacion(
        db, {"prestamo_id": 5, "cliente_id": 7}
    )
    assert bloqueado is True
    assert motivo == "DESISTIMIENTO"


def test_item_bloqueado_cliente_solo_liquidado():
    calls = {"n": 0}

    def _scalar(stmt):
        calls["n"] += 1
        # Sin prestamo_id: 1) count desistimiento 2) total prestamos 3) activos
        return {1: 0, 2: 2, 3: 0}.get(calls["n"], 0)

    db = MagicMock()
    db.scalar.side_effect = _scalar
    bloqueado, motivo = item_bloqueado_para_envio_notificacion(
        db, {"cliente_id": 3, "prestamo_id": None}
    )
    assert bloqueado is True
    assert motivo == "LIQUIDADO"


def test_cliente_sin_cartera_activa_true():
    calls = {"n": 0}

    def _scalar(stmt):
        calls["n"] += 1
        return 2 if calls["n"] == 1 else 0

    db = MagicMock()
    db.scalar.side_effect = _scalar
    assert cliente_sin_cartera_activa_notif(db, 42) is True


def test_cliente_sin_cartera_activa_false_con_aprobado():
    calls = {"n": 0}

    def _scalar(stmt):
        calls["n"] += 1
        return 2 if calls["n"] == 1 else 1

    db = MagicMock()
    db.scalar.side_effect = _scalar
    assert cliente_sin_cartera_activa_notif(db, 42) is False


def test_item_no_bloqueado_aprobado():
    calls = {"n": 0}

    def _scalar(stmt):
        calls["n"] += 1
        if calls["n"] == 1:
            return "APROBADO"
        if calls["n"] == 2:
            return 0  # desistimiento
        if calls["n"] == 3:
            return 1  # total
        return 1  # activos

    db = MagicMock()
    db.scalar.side_effect = _scalar
    bloqueado, motivo = item_bloqueado_para_envio_notificacion(
        db, {"prestamo_id": 1, "cliente_id": 2}
    )
    assert bloqueado is False
    assert motivo == ""
