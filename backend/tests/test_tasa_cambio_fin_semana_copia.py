"""Copia fin de semana: viernes parcial o completo → sábado sin ingreso manual."""
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.tasa_cambio_diaria import TasaCambioDiaria
from app.services import tasa_cambio_service as svc
from app.services.tasa_cambio_service import (
    asegurar_tasa_fin_semana_desde_viernes,
    guardar_tasa_para_fecha,
    obtener_tasa_por_fecha,
)


@pytest.fixture()
def db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TasaCambioDiaria.__table__.create(bind=engine, checkfirst=True)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()


def test_copia_sabado_desde_viernes_solo_euro(db, monkeypatch):
    viernes = date(2026, 6, 19)
    sabado = date(2026, 6, 20)
    db.add(
        TasaCambioDiaria(
            fecha=viernes,
            tasa_oficial=Decimal("100.50"),
            tasa_bcv=None,
            tasa_binance=None,
            usuario_email="admin@test",
        )
    )
    db.commit()

    row = asegurar_tasa_fin_semana_desde_viernes(db, sabado)
    assert row is not None
    assert row.fecha == sabado
    assert float(row.tasa_oficial) == 100.50
    assert row.usuario_email == f"sistema:fin_semana<-{viernes.isoformat()}"


def test_obtener_tasa_sabado_fallback_viernes_sin_fila_sabado(db, monkeypatch):
    viernes = date(2026, 6, 19)
    sabado = date(2026, 6, 20)
    db.add(
        TasaCambioDiaria(
            fecha=viernes,
            tasa_oficial=Decimal("200.00"),
            tasa_bcv=Decimal("199.00"),
            tasa_binance=Decimal("201.00"),
            usuario_email="admin@test",
        )
    )
    db.commit()

    row = obtener_tasa_por_fecha(db, sabado)
    assert row is not None
    assert row.fecha == sabado
    assert float(row.tasa_bcv) == 199.00


def test_guardar_por_fecha_hoy_laboral_exige_tres_tasas(db, monkeypatch):
    hoy = date(2026, 6, 19)  # viernes
    monkeypatch.setattr(svc, "fecha_hoy_caracas", lambda: hoy)

    with pytest.raises(ValueError, match="Euro, BCV y Binance"):
        guardar_tasa_para_fecha(
            db,
            fecha=hoy,
            tasa_oficial=100.0,
            usuario_email="admin@test",
        )

    row = guardar_tasa_para_fecha(
        db,
        fecha=hoy,
        tasa_oficial=100.0,
        tasa_bcv=99.0,
        tasa_binance=101.0,
        usuario_email="admin@test",
    )
    assert float(row.tasa_bcv) == 99.0


def test_guardar_por_fecha_hoy_sabado_permite_solo_euro(db, monkeypatch):
    sabado = date(2026, 6, 20)
    monkeypatch.setattr(svc, "fecha_hoy_caracas", lambda: sabado)

    row = guardar_tasa_para_fecha(
        db,
        fecha=sabado,
        tasa_oficial=100.0,
        usuario_email="admin@test",
    )
    assert float(row.tasa_oficial) == 100.0
