"""Captura manual BCV: misma omisión que el job programado."""
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.tasa_cambio_diaria import TasaCambioDiaria
from app.services import tasa_cambio_service as svc
from app.services.bcv_widget_tasa_service import intentar_captura_bcv_desde_widget


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


def test_intentar_captura_omite_fin_de_semana(db, monkeypatch):
    sabado = date(2026, 6, 20)
    monkeypatch.setattr(svc, "fecha_hoy_caracas", lambda: sabado)
    res = intentar_captura_bcv_desde_widget(db)
    assert res["omitido"] is True
    assert res["razon"] == "fin_de_semana"


def test_intentar_captura_omite_si_bcv_siguiente_ok(db, monkeypatch):
    jueves = date(2026, 6, 18)
    viernes = date(2026, 6, 19)
    monkeypatch.setattr(svc, "fecha_hoy_caracas", lambda: jueves)
    db.add(
        TasaCambioDiaria(
            fecha=viernes,
            tasa_oficial=Decimal("800.00"),
            tasa_bcv=Decimal("790.00"),
            tasa_binance=None,
        )
    )
    db.commit()
    res = intentar_captura_bcv_desde_widget(db)
    assert res["omitido"] is True
    assert res["razon"] == "bcv_ya_cargado"
    assert res["fecha_valor"] == "2026-06-19"


def test_captura_manual_fuerza_aunque_ya_haya_bcv(db, monkeypatch):
    """El botón Capturar no debe omitir: fuerza el GET (mockeado aquí)."""
    jueves = date(2026, 6, 18)
    viernes = date(2026, 6, 19)
    monkeypatch.setattr(svc, "fecha_hoy_caracas", lambda: jueves)
    db.add(
        TasaCambioDiaria(
            fecha=viernes,
            tasa_oficial=Decimal("800.00"),
            tasa_bcv=Decimal("790.00"),
            tasa_binance=None,
        )
    )
    db.commit()

    called = {"n": 0}

    def _fake_sync(_db):
        called["n"] += 1
        return {
            "ok": True,
            "omitido": False,
            "fecha_valor": viernes.isoformat(),
            "tasa_bcv": "791.50",
            "fila_id": 1,
        }

    import app.services.bcv_widget_tasa_service as bcv_svc

    monkeypatch.setattr(bcv_svc, "sincronizar_tasa_bcv_desde_widget", _fake_sync)
    res = intentar_captura_bcv_desde_widget(
        db,
        omitir_fin_de_semana=False,
        omitir_si_ya_hay_bcv=False,
    )
    assert called["n"] == 1
    assert res["omitido"] is False
    assert res["tasa_bcv"] == "791.50"
