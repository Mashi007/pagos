# -*- coding: utf-8 -*-
from datetime import date
from decimal import Decimal

from app.services.bcv_widget_tasa_service import (
    _ssl_context_para_bcv,
    extraer_usd_y_fecha_valor,
)

_HTML_RECUADRO = """
<div class="view-cambio">
  <div class="row recuadrotsmc">
    <div class="col-sm-6"><span>EUR</span></div>
    <div class="col-sm-6"><strong>916,00808978</strong></div>
  </div>
  <div class="row recuadrotsmc">
    <div class="col-sm-6"><span>CNY</span></div>
    <div class="col-sm-6"><strong>116,75668477</strong></div>
  </div>
  <div class="row recuadrotsmc">
    <div class="col-sm-6"><span>TRY</span></div>
    <div class="col-sm-6"><strong>16,32674365</strong></div>
  </div>
  <div class="row recuadrotsmc">
    <div class="col-sm-6"><span>RUB</span></div>
    <div class="col-sm-6"><strong>9,48718559</strong></div>
  </div>
  <div class="row recuadrotsmc">
    <div class="col-sm-6"><span>USD</span></div>
    <div class="col-sm-6"><strong>784,66330000</strong></div>
  </div>
  <span class="date-display-single" content="2026-08-24T00:00:00-04:00">
    Fecha Valor: Lunes, 24 Agosto 2026
  </span>
</div>
"""


def test_extraer_usd_y_fecha_valor_del_recuadro():
    fecha, usd = extraer_usd_y_fecha_valor(_HTML_RECUADRO)
    assert fecha == date(2026, 8, 24)
    assert usd == Decimal("784.66330000")


def test_ssl_context_bcv_mantiene_verificacion_activa():
    import ssl

    ctx = _ssl_context_para_bcv()
    assert ctx.verify_mode == ssl.CERT_REQUIRED
    assert ctx.check_hostname is True
