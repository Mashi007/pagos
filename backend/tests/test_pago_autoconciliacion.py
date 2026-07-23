# -*- coding: utf-8 -*-
"""Autoconciliación persistente: ABONOS y asientos Conciliar cartera."""

from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
from zoneinfo import ZoneInfo

from app.api.v1.endpoints.pagos.pago_conciliacion_estado import _estado_conciliacion_post_cascada
from app.services.pago_autoconciliacion import (
    marcar_pago_autoconciliado,
    pago_preserva_autoconciliacion_sin_cuotas,
)


def _pago(**kwargs):
    base = dict(
        numero_documento="",
        referencia_pago="",
        notas="",
        conciliado=False,
        verificado_concordancia=None,
        fecha_conciliacion=None,
        estado="PENDIENTE",
    )
    base.update(kwargs)
    return SimpleNamespace(**base)


def test_abonos_notif_preserva_autoconciliacion():
    p = _pago(numero_documento="ABONOS-NOTIF-1812-A1B2C3D4", conciliado=True, verificado_concordancia="SI")
    assert pago_preserva_autoconciliacion_sin_cuotas(p) is True


def test_abonos_drive_preserva_autoconciliacion():
    p = _pago(referencia_pago="ABONOS-DRIVE-99-ABCDEF1234", conciliado=True, verificado_concordancia="SI")
    assert pago_preserva_autoconciliacion_sin_cuotas(p) is True


def test_conc_img_preserva_autoconciliacion():
    p = _pago(
        numero_documento="CONC-IMG-1812-1-abc123",
        notas="Conciliar cartera: asiento comprobante (monto y datos del reescaneo OCR).",
        conciliado=True,
        verificado_concordancia="SI",
        fecha_conciliacion=datetime.now(ZoneInfo("America/Caracas")),
    )
    assert pago_preserva_autoconciliacion_sin_cuotas(p) is True


def test_pago_sin_marca_no_preserva():
    p = _pago(conciliado=False, verificado_concordancia=None)
    assert pago_preserva_autoconciliacion_sin_cuotas(p) is False


def test_estado_post_cascada_abonos_sin_cuotas_queda_pagado_conciliado():
    p = _pago(
        numero_documento="ABONOS-NOTIF-1812-DEADBEEF",
        conciliado=True,
        verificado_concordancia="SI",
        fecha_conciliacion=datetime.now(ZoneInfo("America/Caracas")),
        estado="PAGADO",
    )
    estado = _estado_conciliacion_post_cascada(p, 0, 0)
    assert estado == "PAGADO"
    assert p.conciliado is True
    assert p.fecha_conciliacion is not None


def test_estado_post_cascada_pago_normal_sin_cuotas_queda_autoconciliado():
    p = _pago(conciliado=False, verificado_concordancia="NO", estado="PENDIENTE")
    estado = _estado_conciliacion_post_cascada(p, 0, 0)
    assert estado == "PAGADO"
    assert p.conciliado is True
    assert (p.verificado_concordancia or "").upper() == "SI"
    assert p.fecha_conciliacion is not None


def test_marcar_pago_autoconciliado_fija_banderas():
    p = _pago(estado="PENDIENTE", conciliado=False, verificado_concordancia=None)
    marcar_pago_autoconciliado(p)
    assert p.conciliado is True
    assert p.verificado_concordancia == "SI"
    assert p.estado == "PAGADO"
    assert p.fecha_conciliacion is not None
