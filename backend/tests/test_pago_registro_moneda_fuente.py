"""resolver_monto_registro_pago usa fuente de cedulas_reportar_bs (bcv|euro|binance)."""
from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from app.services.pago_registro_moneda import resolver_monto_registro_pago


@pytest.fixture()
def tasa_row():
    return SimpleNamespace(
        tasa_oficial=Decimal("900"),
        tasa_bcv=Decimal("800"),
        tasa_binance=Decimal("950"),
    )


def _base_patches(monkeypatch, *, autorizada=True, fuente="bcv", tasa_row=None):
    monkeypatch.setattr(
        "app.services.pago_registro_moneda.cliente_existe_upper",
        lambda _db, _c: True,
    )
    monkeypatch.setattr(
        "app.services.pago_registro_moneda.cedula_autorizada_para_bs",
        lambda _db, _c: autorizada,
    )
    monkeypatch.setattr(
        "app.services.pago_registro_moneda.fuente_tasa_bs_efectiva_para_cedula",
        lambda _db, _c, fuente_almacenada=None: fuente,
    )
    monkeypatch.setattr(
        "app.services.pago_registro_moneda.obtener_tasa_por_fecha",
        lambda _db, _f: tasa_row,
    )


def test_bs_autorizado_bcv_convierte_con_tasa_bcv(monkeypatch, tasa_row):
    _base_patches(monkeypatch, autorizada=True, fuente="bcv", tasa_row=tasa_row)
    db = MagicMock()
    monto_usd, moneda, monto_bs, tasa, fecha = resolver_monto_registro_pago(
        db,
        cedula_normalizada="V12345678",
        fecha_pago=date(2026, 10, 20),
        monto_pagado=Decimal("800000.00"),
        moneda_registro="BS",
        tasa_cambio_manual=None,
    )
    assert moneda == "BS"
    assert float(monto_bs) == pytest.approx(800000.0)
    assert float(tasa) == pytest.approx(800.0)
    assert float(monto_usd) == pytest.approx(1000.0)
    assert fecha == date(2026, 10, 20)


def test_bs_autorizado_euro_usa_tasa_oficial(monkeypatch, tasa_row):
    _base_patches(monkeypatch, autorizada=True, fuente="euro", tasa_row=tasa_row)
    db = MagicMock()
    monto_usd, moneda, monto_bs, tasa, _fecha = resolver_monto_registro_pago(
        db,
        cedula_normalizada="V12345678",
        fecha_pago=date(2026, 10, 20),
        monto_pagado=Decimal("900000.00"),
        moneda_registro="BS",
        tasa_cambio_manual=None,
    )
    assert moneda == "BS"
    assert float(tasa) == pytest.approx(900.0)
    assert float(monto_usd) == pytest.approx(1000.0)
    assert float(monto_bs) == pytest.approx(900000.0)


def test_bs_bcv_sin_tasa_bcv_no_cae_a_euro(monkeypatch):
    tasa_sin_bcv = SimpleNamespace(
        tasa_oficial=Decimal("900"),
        tasa_bcv=None,
        tasa_binance=None,
    )
    _base_patches(monkeypatch, autorizada=True, fuente="bcv", tasa_row=tasa_sin_bcv)
    db = MagicMock()
    with pytest.raises(HTTPException) as ei:
        resolver_monto_registro_pago(
            db,
            cedula_normalizada="V12345678",
            fecha_pago=date(2026, 10, 20),
            monto_pagado=Decimal("800000.00"),
            moneda_registro="BS",
            tasa_cambio_manual=None,
        )
    assert ei.value.status_code == 400
    assert "BCV" in str(ei.value.detail)


def test_usd_no_convierte(monkeypatch, tasa_row):
    _base_patches(monkeypatch, autorizada=True, fuente="bcv", tasa_row=tasa_row)
    db = MagicMock()
    monto_usd, moneda, monto_bs, tasa, fecha = resolver_monto_registro_pago(
        db,
        cedula_normalizada="V12345678",
        fecha_pago=date(2026, 10, 20),
        monto_pagado=Decimal("100.00"),
        moneda_registro="USD",
        tasa_cambio_manual=None,
    )
    assert moneda == "USD"
    assert float(monto_usd) == pytest.approx(100.0)
    assert monto_bs is None
    assert tasa is None
    assert fecha is None
