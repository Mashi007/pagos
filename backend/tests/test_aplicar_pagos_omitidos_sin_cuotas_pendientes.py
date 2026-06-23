# -*- coding: utf-8 -*-
"""Aplicacion incremental: omitir pagos huérfanos cuando no hay cuotas con saldo."""

from unittest.mock import MagicMock, patch

from app.services.pagos_aplicacion_prestamo import (
    aplicar_pagos_pendientes_prestamo_con_diagnostico,
)


def test_omite_aplicacion_incremental_si_no_hay_cuotas_con_saldo():
    db = MagicMock()
    db.get.return_value = MagicMock(estado="APROBADO")

    pago_huerfano = MagicMock()
    pago_huerfano.id = 75548
    pago_huerfano.prestamo_id = 1157
    pago_huerfano.monto_pagado = 114.0

    scalar_side = [2, 1]  # n_oper, prestamo_tiene_cuotas count=0 via patch
    db.scalar.side_effect = lambda *a, **k: scalar_side.pop(0) if scalar_side else 0

    db.execute.return_value.scalars.return_value.all.return_value = [pago_huerfano]

    with (
        patch(
            "app.services.pagos_aplicacion_prestamo.prestamo_tiene_cuotas_con_saldo_pendiente",
            return_value=False,
        ),
        patch(
            "app.services.pagos_aplicacion_prestamo._aplicar_pago_a_cuotas_interno"
        ) as mock_aplicar,
    ):
        res = aplicar_pagos_pendientes_prestamo_con_diagnostico(1157, db)

    mock_aplicar.assert_not_called()
    assert res["pagos_con_aplicacion"] == 0
    assert res["diagnostico"]["pagos_omitidos_sin_cuotas_pendientes_ids"] == [75548]
    assert res["diagnostico"]["pagos_elegibles_cascada_sin_cuota_pagos"] == 1
