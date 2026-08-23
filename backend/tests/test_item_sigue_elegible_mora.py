"""Revalidacion al enviar: no notificar si el cliente ya pago o salio de la regla."""
from __future__ import annotations

from datetime import date, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.services.notificacion_service import item_sigue_elegible_mora_para_envio


def _cuota(
    *,
    cid: int = 10,
    pid: int = 100,
    num: int = 1,
    fv: date,
    fecha_pago=None,
    estado: str = "VENCIDO",
    monto: float = 100.0,
    total_pagado: float = 0.0,
):
    return SimpleNamespace(
        id=cid,
        prestamo_id=pid,
        numero_cuota=num,
        fecha_vencimiento=fv,
        fecha_pago=fecha_pago,
        estado=estado,
        monto=monto,
        total_pagado=total_pagado,
    )


def test_pago_1_dia_omite_si_cuota_pagada():
    hoy = date(2026, 8, 23)
    item = {"cuota_id": 10, "prestamo_id": 100, "numero_cuota": 1}
    cuota = _cuota(fv=hoy - timedelta(days=1), fecha_pago=hoy, estado="PAGADO", total_pagado=100)
    db = MagicMock()
    with patch(
        "app.services.notificacion_service._cargar_cuota_fresca_para_item",
        return_value=cuota,
    ):
        ok, motivo = item_sigue_elegible_mora_para_envio(
            db, "PAGO_1_DIA_ATRASADO", item, fecha_referencia=hoy
        )
    assert ok is False
    assert motivo == "cuota_ya_pagada"


def test_pago_1_dia_sigue_si_exactamente_1_dia_impaga():
    hoy = date(2026, 8, 23)
    item = {"cuota_id": 10, "prestamo_id": 100, "numero_cuota": 1}
    cuota = _cuota(fv=hoy - timedelta(days=1))
    db = MagicMock()
    with patch(
        "app.services.notificacion_service._cargar_cuota_fresca_para_item",
        return_value=cuota,
    ):
        ok, motivo = item_sigue_elegible_mora_para_envio(
            db, "PAGO_1_DIA_ATRASADO", item, fecha_referencia=hoy
        )
    assert ok is True
    assert motivo == ""


def test_pago_10_dias_omite_si_ya_no_exactamente_1_cuota():
    hoy = date(2026, 8, 23)
    item = {"cuota_id": 10, "prestamo_id": 100, "numero_cuota": 1}
    cuota = _cuota(fv=hoy - timedelta(days=10))
    db = MagicMock()
    with patch(
        "app.services.notificacion_service._cargar_cuota_fresca_para_item",
        return_value=cuota,
    ), patch(
        "app.services.notificacion_service.contar_cuotas_atraso_por_prestamos",
        return_value={100: 2},
    ):
        ok, motivo = item_sigue_elegible_mora_para_envio(
            db, "PAGO_10_DIAS_ATRASADO", item, fecha_referencia=hoy
        )
    assert ok is False
    assert motivo == "ya_no_exactamente_1_cuota"


def test_prejudicial_omite_si_menos_de_2_atrasadas():
    hoy = date(2026, 8, 23)
    item = {"prestamo_id": 100, "cuota_id": 10}
    db = MagicMock()
    with patch(
        "app.services.notificacion_service.contar_cuotas_atraso_por_prestamos",
        return_value={100: 1},
    ):
        ok, motivo = item_sigue_elegible_mora_para_envio(
            db, "PREJUDICIAL", item, fecha_referencia=hoy
        )
    assert ok is False
    assert motivo == "ya_pagado_o_menos_de_2_cuotas"


def test_prejudicial_sigue_con_2_o_mas():
    hoy = date(2026, 8, 23)
    item = {"prestamo_id": 100}
    db = MagicMock()
    with patch(
        "app.services.notificacion_service.contar_cuotas_atraso_por_prestamos",
        return_value={100: 3},
    ):
        ok, motivo = item_sigue_elegible_mora_para_envio(
            db, "PREJUDICIAL", item, fecha_referencia=hoy
        )
    assert ok is True
    assert motivo == ""
