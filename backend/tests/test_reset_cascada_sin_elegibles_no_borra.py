# -*- coding: utf-8 -*-
"""Reset cascada: no borrar cuota_pagos si no hay pagos reaplicables."""

from unittest.mock import MagicMock, patch

from app.services.pagos_cuotas_reaplicacion import _reset_y_reaplicar_cascada_prestamo_once


def test_reset_aborta_sin_delete_si_cero_reaplicables():
    db = MagicMock()
    prestamo = MagicMock(estado="APROBADO")
    db.get.return_value = prestamo

    cuota = MagicMock(id=10, prestamo_id=2982, numero_cuota=1)
    db.execute.return_value.scalars.return_value.all.return_value = [cuota]

    diag = {
        "pagos_con_prestamo_monto_gt0": 5,
        "pagos_elegibles_reaplicacion": 0,
        "pagos_reaplicables": 0,
        "pagos_elegibles_con_cuota_pagos_otro_prestamo": 0,
        "pagos_excluidos_operacion": 0,
        "filas_cuota_pagos": 12,
        "muestra_no_elegibles": [
            {"estado": "REPORTADO", "conciliado": False, "verificado": "NO", "n": 5}
        ],
    }

    with (
        patch(
            "app.services.pagos_cascada_lock.adquirir_lock_cascada_prestamo"
        ),
        patch(
            "app.services.pagos_desistimiento_politica.prestamo_bloquea_aplicacion_a_cuotas",
            return_value=False,
        ),
        patch(
            "app.services.pago_huella_funcional.primer_par_huella_duplicada_prestamo",
            return_value=None,
        ),
        patch(
            "app.services.pagos_aplicacion_prestamo.diagnostico_pagos_para_reaplicacion_cascada",
            return_value=diag,
        ),
        patch(
            "app.services.pagos_cuotas_reaplicacion._delete_cuota_pagos_por_prestamo_sql"
        ) as mock_del,
    ):
        res = _reset_y_reaplicar_cascada_prestamo_once(db, 2982)

    assert res["ok"] is False
    assert res["codigo"] == "sin_pagos_elegibles"
    assert res["cuota_pagos_eliminadas"] == 0
    assert "conservaron" in (res.get("error") or "").lower() or "12" in (res.get("error") or "")
    mock_del.assert_not_called()
