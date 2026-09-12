# -*- coding: utf-8 -*-
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.importacion_extracto import ImportacionExtractoPagoConfirmado
from app.models.tasa_cambio_diaria import TasaCambioDiaria
from app.services.importacion_extracto_service import (
    _MARCA_MONTO_BS_USD,
    _anotar_detalle_conversion_bs_usd,
    _monto_usd_desde_extracto,
    reparar_confirmados_activos_monto_bs,
)


@pytest.fixture()
def db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TasaCambioDiaria.__table__.create(bind=engine, checkfirst=True)
    ImportacionExtractoPagoConfirmado.__table__.create(bind=engine, checkfirst=True)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()


def test_monto_mercantil_bs_se_convierte_a_usd(db):
    db.add(
        TasaCambioDiaria(
            fecha=date(2026, 7, 10),
            tasa_oficial=Decimal("900"),
            tasa_bcv=Decimal("800"),
            tasa_binance=None,
        )
    )
    db.commit()
    usd = _monto_usd_desde_extracto(
        db, monto=800_000.0, fecha=date(2026, 7, 10), banco="Mercantil"
    )
    assert usd == pytest.approx(1000.0)


def test_monto_zelle_no_convierte(db):
    usd = _monto_usd_desde_extracto(
        db, monto=800_000.0, fecha=date(2026, 7, 10), banco="Zelle"
    )
    assert usd == pytest.approx(800_000.0)


def test_reparar_confirmados_julio_inflado_bs(db, monkeypatch):
    monkeypatch.setattr(
        "app.services.cobranzas.universo_analisis_service.invalidate_universo_analisis_cache",
        lambda: None,
    )
    db.add(
        TasaCambioDiaria(
            fecha=date(2026, 7, 5),
            tasa_oficial=Decimal("900"),
            tasa_bcv=Decimal("800"),
            tasa_binance=None,
        )
    )
    db.add(
        ImportacionExtractoPagoConfirmado(
            serial="ABC",
            serial_norm="ABC",
            monto_usd=Decimal("5526535.00"),
            fecha_deposito=date(2026, 7, 5),
            banco="Mercantil",
            estado="ACTIVO",
        )
    )
    db.commit()
    n = reparar_confirmados_activos_monto_bs(db)
    assert n == 1
    row = db.execute(select(ImportacionExtractoPagoConfirmado)).scalars().first()
    assert float(row.monto_usd) == pytest.approx(5526535.0 / 800.0)
    assert _MARCA_MONTO_BS_USD in (row.detalle or "")
    assert reparar_confirmados_activos_monto_bs(db) == 0


def test_reparar_no_divide_confirmado_ya_convertido(db, monkeypatch):
    """Haber 5.5M Bs → ~$6908 al importar. Cobranzas no debe volver a dividir."""
    monkeypatch.setattr(
        "app.services.cobranzas.universo_analisis_service.invalidate_universo_analisis_cache",
        lambda: None,
    )
    db.add(
        TasaCambioDiaria(
            fecha=date(2026, 7, 5),
            tasa_oficial=Decimal("900"),
            tasa_bcv=Decimal("800"),
            tasa_binance=None,
        )
    )
    db.add(
        ImportacionExtractoPagoConfirmado(
            serial="ABC2",
            serial_norm="ABC2",
            monto_usd=Decimal("6908.17"),
            fecha_deposito=date(2026, 7, 5),
            banco="Mercantil",
            estado="ACTIVO",
            detalle=(
                "[IMPORTACION_EXTRACTO] confirmado sin cédula; KPI Pagos confirmados"
            ),
        )
    )
    db.commit()
    assert reparar_confirmados_activos_monto_bs(db) == 0
    row = db.execute(select(ImportacionExtractoPagoConfirmado)).scalars().first()
    assert float(row.monto_usd) == pytest.approx(6908.17)


def test_reparar_no_divide_si_detalle_ya_marca_conversion(db, monkeypatch):
    monkeypatch.setattr(
        "app.services.cobranzas.universo_analisis_service.invalidate_universo_analisis_cache",
        lambda: None,
    )
    detalle = _anotar_detalle_conversion_bs_usd(
        "[IMPORTACION_EXTRACTO] confirmado",
        tasa=800.0,
        bruto=96_000_000.0,
    )
    db.add(
        TasaCambioDiaria(
            fecha=date(2026, 7, 5),
            tasa_oficial=Decimal("900"),
            tasa_bcv=Decimal("800"),
            tasa_binance=None,
        )
    )
    db.add(
        ImportacionExtractoPagoConfirmado(
            serial="ABC3",
            serial_norm="ABC3",
            monto_usd=Decimal("120000.00"),
            fecha_deposito=date(2026, 7, 5),
            banco="Mercantil",
            estado="ACTIVO",
            detalle=detalle,
        )
    )
    db.commit()
    assert reparar_confirmados_activos_monto_bs(db) == 0
    row = db.execute(select(ImportacionExtractoPagoConfirmado)).scalars().first()
    assert float(row.monto_usd) == pytest.approx(120000.0)
