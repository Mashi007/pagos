# -*- coding: utf-8 -*-
"""Eliminar pago: realineación liviana sin reset completo cuando la integridad cuadra."""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock, patch

from app.services.pagos_cuotas_reaplicacion import realinear_cuotas_prestamo_desde_cuota_pagos


def test_realinear_omite_reset_si_integridad_ok():
    db = MagicMock()
    prestamo = MagicMock()
    prestamo.estado = "LIQUIDADO"
    cuota = MagicMock()
    cuota.id = 10
    cuota.prestamo_id = 3665
    cuota.numero_cuota = 1
    cuota.monto = Decimal("100")
    cuota.fecha_vencimiento = None

    db.get.return_value = prestamo
    db.execute.return_value.scalars.return_value.all.return_value = [cuota]
    db.scalar.side_effect = [50.0, None]

    with (
        patch(
            "app.services.pagos_cuotas_reaplicacion.integridad_cuotas_prestamo",
            return_value={"ok": True, "integridad_ok": True},
        ),
        patch(
            "app.services.pagos_cuotas_reaplicacion.prestamo_requiere_correccion_cascada",
            return_value=False,
        ),
        patch(
            "app.services.pagos_cascada_aplicacion._marcar_prestamo_liquidado_si_corresponde"
        ),
        patch(
            "app.services.cuota_estado.sincronizar_columna_estado_cuotas",
            return_value=0,
        ),
    ):
        r = realinear_cuotas_prestamo_desde_cuota_pagos(db, 3665)

    assert r["ok"] is True
    assert r["requiere_reset_cascada"] is False
    assert float(cuota.total_pagado) == 50.0
