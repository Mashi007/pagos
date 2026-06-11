# -*- coding: utf-8 -*-
"""Visto finiquito: continuar sin comprobantes tras confirmación."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.services.finiquito_conciliacion_visto_service import iniciar_visto_reserva


def test_visto_sin_pagos_requiere_confirmacion():
    caso = SimpleNamespace(
        id=1,
        prestamo_id=99,
        estado="ACEPTADO",
    )
    db = MagicMock()
    db.get.return_value = caso
    db.scalar.return_value = 0

    with patch(
        "app.services.finiquito_conciliacion_visto_service.caso_tiene_reserva_activa",
        return_value=False,
    ), patch(
        "app.services.finiquito_conciliacion_visto_service.select"
    ) as mock_select:
        mock_execute = MagicMock()
        mock_execute.scalars.return_value.all.return_value = []
        db.execute.return_value = mock_execute

        r = iniciar_visto_reserva(db, 1, confirmar_sin_comprobantes=False)
        assert r["ok"] is False
        assert r.get("requiere_confirmacion_sin_comprobantes") is True


def test_visto_sin_pagos_con_confirmacion_continua():
    caso = SimpleNamespace(
        id=1,
        prestamo_id=99,
        estado="ACEPTADO",
    )
    db = MagicMock()
    db.get.return_value = caso
    db.scalar.return_value = 0

    with patch(
        "app.services.finiquito_conciliacion_visto_service.caso_tiene_reserva_activa",
        return_value=False,
    ), patch(
        "app.services.finiquito_conciliacion_visto_service.eliminar_todos_pagos_prestamo",
        return_value={"ok": True, "pagos_eliminados": 0},
    ):
        mock_execute = MagicMock()
        mock_execute.scalars.return_value.all.return_value = []
        db.execute.return_value = mock_execute

        r = iniciar_visto_reserva(db, 1, confirmar_sin_comprobantes=True)
        assert r["ok"] is True
        assert r.get("reservas") == 0
