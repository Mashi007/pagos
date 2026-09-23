# -*- coding: utf-8 -*-
"""Finiquito recrear-ocr must pass staff user into cascada (LIQUIDADO)."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.services.finiquito_conciliacion_visto_service import recrear_pagos_y_ocr_lote
from app.services.pagos_desistimiento_politica import prestamo_bloquea_aplicacion_a_cuotas


def test_politica_liquidado_bloquea_sin_user_permite_staff():
    """Contrato: LIQUIDADO sin user bloquea cascada; staff no."""
    db = MagicMock()
    prestamo = SimpleNamespace(estado="LIQUIDADO")
    db.get.return_value = prestamo

    assert prestamo_bloquea_aplicacion_a_cuotas(db, 10, user=None) is True

    staff = SimpleNamespace(rol="operator", is_admin=False)
    assert prestamo_bloquea_aplicacion_a_cuotas(db, 10, user=staff) is False


async def _ocr_ok(*_a, **_k):
    return {"reserva_id": 1, "ok": True, "pago_id": 99}


def test_recrear_ocr_propaga_user_a_pipeline():
    """Tras Visto wipe, recrear debe llamar cascada con el staff autenticado."""
    caso = SimpleNamespace(id=7, prestamo_id=42, estado="ACEPTADO", cedula="V123")
    reserva = SimpleNamespace(
        id=1,
        pago_id_recriado=99,
        comprobante_imagen_data=b"\xff\xd8\xff\xd9",
        orden=1,
    )
    db = MagicMock()
    db.get.return_value = caso
    mock_exec = MagicMock()
    mock_exec.scalars.return_value.all.return_value = [reserva]
    db.execute.return_value = mock_exec

    staff = SimpleNamespace(rol="admin", is_admin=True, email="a@b.com")
    captured: dict = {}

    def _fake_pipeline(prestamo_id, _db, **kwargs):
        captured["prestamo_id"] = prestamo_id
        captured["user"] = kwargs.get("user")
        return {
            "ok": True,
            "mensaje": "Cascada aplicada: 1 pago(s).",
            "prestamo_estado": "LIQUIDADO",
            "pagos_con_aplicacion": 1,
        }

    with patch(
        "app.services.finiquito_conciliacion_visto_service.caso_tiene_reserva_activa",
        return_value=True,
    ), patch(
        "app.services.finiquito_conciliacion_visto_service._reserva_tiene_imagen_guardada",
        return_value=True,
    ), patch(
        "app.services.finiquito_conciliacion_visto_service._ocr_fila_reserva",
        side_effect=_ocr_ok,
    ), patch(
        "app.services.pagos_aplicacion_prestamo.aplicar_cascada_prestamo_pipeline",
        side_effect=_fake_pipeline,
    ):
        r = asyncio.run(
            recrear_pagos_y_ocr_lote(db, 7, "op@test.com", user=staff)
        )

    assert r["ok"] is True
    assert captured["prestamo_id"] == 42
    assert captured["user"] is staff


def test_recrear_ocr_fail_closed_si_cascada_falla():
    """No marcar ok si hay pagos recreados pero cascada bloqueada/falla."""
    caso = SimpleNamespace(id=7, prestamo_id=42, estado="ACEPTADO", cedula="V123")
    reserva = SimpleNamespace(
        id=1,
        pago_id_recriado=99,
        comprobante_imagen_data=b"\xff\xd8\xff\xd9",
        orden=1,
    )
    db = MagicMock()
    db.get.return_value = caso
    mock_exec = MagicMock()
    mock_exec.scalars.return_value.all.return_value = [reserva]
    db.execute.return_value = mock_exec

    with patch(
        "app.services.finiquito_conciliacion_visto_service.caso_tiene_reserva_activa",
        return_value=True,
    ), patch(
        "app.services.finiquito_conciliacion_visto_service._reserva_tiene_imagen_guardada",
        return_value=True,
    ), patch(
        "app.services.finiquito_conciliacion_visto_service._ocr_fila_reserva",
        side_effect=_ocr_ok,
    ), patch(
        "app.services.pagos_aplicacion_prestamo.aplicar_cascada_prestamo_pipeline",
        return_value={
            "ok": False,
            "error": "Prestamo en DESISTIMIENTO o LIQUIDADO: no se aplican pagos a cuotas",
        },
    ):
        r = asyncio.run(recrear_pagos_y_ocr_lote(db, 7, "op@test.com", user=None))

    assert r["ok"] is False
    assert "cascada" in (r.get("error") or "").lower()
    assert r.get("pagos_recriados") == 1
