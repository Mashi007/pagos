# -*- coding: utf-8 -*-
"""Asiento ABONOS/CONC-IMG: serial con espacios no se demota como limbo."""
from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
from zoneinfo import ZoneInfo

from app.services.cuota_pago_integridad import pago_quedaria_limbo_pagado_sin_cuotas
from app.services.pago_autoconciliacion import pago_asiento_abonos_o_conciliar_cartera


def _pago(**kwargs):
    base = dict(
        id=1,
        prestamo_id=7,
        numero_documento="",
        referencia_pago="",
        notas="",
        conciliado=True,
        verificado_concordancia="SI",
        fecha_conciliacion=datetime.now(ZoneInfo("America/Caracas")),
        estado="PAGADO",
    )
    base.update(kwargs)
    return SimpleNamespace(**base)


def test_abonos_drive_con_espacios_es_asiento():
    p = _pago(numero_documento="ABONOS - DRIVE - 3402 - ABCDEF12")
    assert pago_asiento_abonos_o_conciliar_cartera(p) is True


def test_limbo_no_demota_abonos_con_espacios_si_hay_cupo(monkeypatch):
    p = _pago(numero_documento="ABONOS - DRIVE - 3402 - ABCDEF12")
    monkeypatch.setattr(
        "app.services.cuota_pago_integridad.pago_tiene_aplicaciones_cuotas",
        lambda *_a, **_k: False,
    )
    monkeypatch.setattr(
        "app.services.cuota_pago_integridad.prestamo_tiene_cupo_aplicable_en_cuotas",
        lambda *_a, **_k: True,
    )
    assert pago_quedaria_limbo_pagado_sin_cuotas(object(), p) is False


def test_conc_img_con_espacios_es_asiento():
    p = _pago(numero_documento="CONC - IMG - 1812 - 1 - abc")
    assert pago_asiento_abonos_o_conciliar_cartera(p) is True
