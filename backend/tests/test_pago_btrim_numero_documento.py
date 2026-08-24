"""Tests helper btrim de numero_documento (índice único global)."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.pago import Pago
from app.services.pago_numero_documento import primer_pago_id_por_btrim_numero_documento


@pytest.fixture()
def db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    # SQLite no tiene btrim; registrar alias a trim.
    from sqlalchemy import event

    @event.listens_for(engine, "connect")
    def _sqlite_btrim(dbapi_conn, _connection_record):
        dbapi_conn.create_function("btrim", 1, lambda s: (s or "").strip())

    Pago.__table__.create(bind=engine, checkfirst=True)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()


def test_primer_pago_id_por_btrim_encuentra_con_espacios(db):
    db.add(
        Pago(
            cedula_cliente="V1",
            prestamo_id=1,
            fecha_pago=datetime(2026, 1, 1),
            monto_pagado=Decimal("10.00"),
            numero_documento=" 740087408103031 ",
            institucion_bancaria="BNC",
            estado="PAGADO",
            usuario_registro="test",
        )
    )
    db.commit()
    assert primer_pago_id_por_btrim_numero_documento(db, "740087408103031") is not None
    assert primer_pago_id_por_btrim_numero_documento(db, "999") is None
