# -*- coding: utf-8 -*-
"""Regresion: tasa del recibo por pago reportado alineada con listados (tasa_y_equivalente_usd_excel)."""
from __future__ import annotations

import os
import sys
from datetime import date
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.cobros.recibo_pago_reportado_centro import tasa_bs_usd_para_recibo_pago_reportado


@patch("app.services.cobros.recibo_pago_reportado_centro.tasa_y_equivalente_usd_excel")
def test_tasa_bs_usd_delega_en_misma_funcion_que_listados(mock_excel):
    mock_excel.return_value = (40.5, 12.34)
    db = MagicMock()
    pr = MagicMock()
    pr.fecha_pago = date(2025, 1, 2)
    pr.monto = 500
    pr.moneda = "BS"
    assert tasa_bs_usd_para_recibo_pago_reportado(db, pr) == 40.5
    mock_excel.assert_called_once_with(db, pr.fecha_pago, 500.0, "BS")


@patch("app.services.cobros.recibo_pago_reportado_centro.tasa_y_equivalente_usd_excel")
def test_tasa_usd_devuelve_none_en_primera_posicion(mock_excel):
    mock_excel.return_value = (None, 100.0)
    db = MagicMock()
    pr = MagicMock()
    pr.fecha_pago = date(2025, 1, 2)
    pr.monto = 100
    pr.moneda = "USD"
    assert tasa_bs_usd_para_recibo_pago_reportado(db, pr) is None
