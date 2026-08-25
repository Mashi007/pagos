# -*- coding: utf-8 -*-
"""Binance Gmail: fecha ausente en imagen → hoy Caracas (solo plantilla C)."""
from __future__ import annotations

from datetime import date, datetime

from app.api.v1.endpoints.pagos_gmail.routes import _parse_fecha_pago_gmail_temporal
from app.services.pagos_gmail.plantilla_abcd_proceso_negocio import (
    completar_fecha_gmail_binance_si_ausente,
    es_gmail_plantilla_binance,
    fecha_pago_date_gmail_plantilla_c,
)
from app.utils.dias_laborales_caracas import fecha_hoy_caracas


def test_es_gmail_plantilla_binance():
    assert es_gmail_plantilla_binance(fmt="C")
    assert es_gmail_plantilla_binance(banco="BINANCE")
    assert not es_gmail_plantilla_binance(fmt="A", banco="Mercantil")


def test_completar_fecha_binance_na_usa_hoy():
    hoy = fecha_hoy_caracas().strftime("%d/%m/%Y")
    assert completar_fecha_gmail_binance_si_ausente("") == hoy
    assert completar_fecha_gmail_binance_si_ausente("NA") == hoy
    assert completar_fecha_gmail_binance_si_ausente("15/03/2026") == "15/03/2026"


def test_fecha_pago_date_gmail_plantilla_c_na_es_hoy():
    assert fecha_pago_date_gmail_plantilla_c("NA") == fecha_hoy_caracas()
    assert fecha_pago_date_gmail_plantilla_c("") == fecha_hoy_caracas()
    assert fecha_pago_date_gmail_plantilla_c("10/02/2026") == date(2026, 2, 10)


def test_parse_fecha_temporal_binance_na_marca_desde_imagen():
    fallback = datetime(2020, 1, 1, 12, 0, 0)
    dt, desde_imagen = _parse_fecha_pago_gmail_temporal(
        "NA", fallback, es_binance=True
    )
    assert desde_imagen is True
    assert dt.date() == fecha_hoy_caracas()


def test_parse_fecha_temporal_otros_bancos_na_no_desde_imagen():
    fallback = datetime(2020, 1, 1, 12, 0, 0)
    dt, desde_imagen = _parse_fecha_pago_gmail_temporal(
        "NA", fallback, es_binance=False
    )
    assert desde_imagen is False
    assert dt.date() == date(2020, 1, 1)
