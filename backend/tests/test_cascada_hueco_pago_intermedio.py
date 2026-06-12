# -*- coding: utf-8 -*-
"""Cascada: hueco tras borrar pago intermedio y reconstrucción completa."""

from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.services.pagos_aplicacion_prestamo import aplicar_cascada_prestamo_pipeline
from app.services.pagos_cuotas_reaplicacion import (
    prestamo_requiere_correccion_cascada,
    prestamo_tiene_hueco_cascada_cuotas,
)


def _cuota(num: int, monto: float, pagado: float, cid: int) -> SimpleNamespace:
    return SimpleNamespace(
        id=cid,
        numero_cuota=num,
        monto=Decimal(str(monto)),
        total_pagado=Decimal(str(pagado)),
    )


def test_hueco_cascada_cuota_anterior_pendiente_con_pagos_posteriores():
    """Cuota 2 vacía y cuota 3 con articulación → hay hueco."""
    db = MagicMock()
    cuotas = [
        _cuota(1, 100, 100, 1),
        _cuota(2, 100, 0, 2),
        _cuota(3, 100, 100, 3),
    ]
    db.execute.return_value.all.return_value = cuotas
    db.scalar.return_value = 2  # cuota_pagos en cuotas posteriores a la 2

    assert prestamo_tiene_hueco_cascada_cuotas(db, 99) is True


def test_sin_hueco_cuando_solo_faltan_cuotas_al_final():
    db = MagicMock()
    cuotas = [
        _cuota(1, 100, 100, 1),
        _cuota(2, 100, 50, 2),
        _cuota(3, 100, 0, 3),
    ]
    db.execute.return_value.all.return_value = cuotas
    db.scalar.return_value = 0

    assert prestamo_tiene_hueco_cascada_cuotas(db, 99) is False


def test_requiere_correccion_por_hueco():
    db = MagicMock()
    prestamo = MagicMock()
    prestamo.estado = "APROBADO"
    db.get.return_value = prestamo

    with (
        patch(
            "app.services.pagos_cuotas_reaplicacion.prestamo_tiene_hueco_cascada_cuotas",
            return_value=True,
        ),
        patch(
            "app.services.pagos_cuotas_reaplicacion.integridad_cuotas_prestamo",
            return_value={"ok": True, "integridad_ok": True},
        ),
    ):
        assert prestamo_requiere_correccion_cascada(db, 10) is True


def test_pipeline_reconstruir_completa_llama_reset():
    prestamo = MagicMock()
    prestamo.estado = "APROBADO"
    db = MagicMock()
    db.get.return_value = prestamo

    with (
        patch(
            "app.services.pagos_cuotas_reaplicacion.reset_y_reaplicar_cascada_prestamo",
            return_value={"ok": True, "pagos_reaplicados": 3},
        ) as reset_mock,
        patch(
            "app.services.pagos_aplicacion_prestamo.aplicar_pagos_pendientes_prestamo_con_diagnostico"
        ) as inc_mock,
        patch(
            "app.services.pagos_aplicacion_prestamo._restaurar_autoconciliacion_pagos_prestamo",
            return_value=0,
        ),
    ):
        out = aplicar_cascada_prestamo_pipeline(10, db, reconstruir_completa=True)

    assert out["ok"] is True
    assert out["pagos_con_aplicacion"] == 3
    assert out["reaplicacion_completa"] is True
    reset_mock.assert_called_once_with(db, 10)
    inc_mock.assert_not_called()


def test_sincronizacion_no_commit_si_reaplicacion_cascada_falla():
    from app.services.pagos_cuotas_sincronizacion import (
        sincronizar_pagos_pendientes_a_prestamos,
    )

    db = MagicMock()
    with (
        patch(
            "app.api.v1.endpoints.pagos.aplicar_pagos_pendientes_prestamo",
            return_value=1,
        ),
        patch(
            "app.services.pagos_cuotas_reaplicacion.prestamo_requiere_correccion_cascada",
            return_value=True,
        ),
        patch(
            "app.services.pagos_cuotas_reaplicacion.reset_y_reaplicar_cascada_prestamo",
            return_value={"ok": False, "error": "fallo reaplicando"},
        ),
    ):
        out = sincronizar_pagos_pendientes_a_prestamos(db, [10])

    assert out == 0
    db.rollback.assert_called_once()
    db.commit.assert_not_called()
