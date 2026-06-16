# -*- coding: utf-8 -*-
from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.api.v1.endpoints.pagos import routes as pagos_routes
from app.api.v1.endpoints.pagos.payload_models import PagoBatchBody
from app.core.database import Base
from app.models.analista import Analista
from app.models.cliente import Cliente
from app.models.pago import Pago
from app.models.prestamo import Prestamo
from app.schemas.auth import UserResponse
from app.schemas.pago import PagoCreate


@pytest.fixture()
def db() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Analista.__table__.create(engine)
    Cliente.__table__.create(engine)
    Prestamo.__table__.create(engine)
    Pago.__table__.create(engine)
    with engine.begin() as conn:
        conn.exec_driver_sql(
            "CREATE TABLE pagos_con_errores (id INTEGER PRIMARY KEY, numero_documento VARCHAR(100))"
        )

    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(autouse=True)
def batch_side_effects_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(pagos_routes, "preload_autorizados_bs", lambda _db: frozenset())
    monkeypatch.setattr(pagos_routes, "_debe_aplicar_cascada_pago", lambda _row: False)
    monkeypatch.setattr(pagos_routes, "conflicto_huella_para_creacion", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        pagos_routes,
        "enriquecer_items_link_comprobante_desde_gmail",
        lambda _db, _items: None,
    )


def _user() -> UserResponse:
    return UserResponse(
        id=1,
        email="tester@example.com",
        nombre="Tester",
        rol="admin",
        is_active=True,
        created_at="2026-01-01T00:00:00",
    )


def _cliente(db: Session, cedula: str, nombre: str) -> Cliente:
    cliente = Cliente(
        cedula=cedula,
        nombres=nombre,
        telefono="0000000000",
        email=f"{cedula.lower()}@example.com",
        direccion="Test",
        fecha_nacimiento=date(1990, 1, 1),
        ocupacion="Test",
        estado="ACTIVO",
        usuario_registro="test",
        notas="test",
    )
    db.add(cliente)
    db.flush()
    return cliente


def _prestamo(db: Session, cliente: Cliente) -> Prestamo:
    prestamo = Prestamo(
        cliente_id=cliente.id,
        cedula=cliente.cedula,
        nombres=cliente.nombres,
        total_financiamiento=Decimal("1000.00"),
        fecha_requerimiento=date(2026, 1, 1),
        modalidad_pago="MENSUAL",
        numero_cuotas=5,
        cuota_periodo=Decimal("200.00"),
        producto="Test",
        estado="APROBADO",
        analista="test",
    )
    db.add(prestamo)
    db.flush()
    return prestamo


def _pago_create(
    *,
    cedula: str,
    prestamo_id: int,
    monto: Decimal,
    documento: str,
) -> PagoCreate:
    return PagoCreate(
        cedula_cliente=cedula,
        prestamo_id=prestamo_id,
        fecha_pago=date(2026, 1, 15),
        monto_pagado=monto,
        numero_documento=documento,
        conciliado=True,
        moneda_registro="USD",
    )


def test_batch_rejects_cedula_that_does_not_match_selected_loan(db: Session) -> None:
    cliente_a = _cliente(db, "V11111111", "Cliente A")
    cliente_b = _cliente(db, "V22222222", "Cliente B")
    _prestamo(db, cliente_a)
    prestamo_b = _prestamo(db, cliente_b)

    body = PagoBatchBody(
        pagos=[
            _pago_create(
                cedula=cliente_a.cedula,
                prestamo_id=prestamo_b.id,
                monto=Decimal("100.00"),
                documento="BATCH-MISMATCH-1",
            )
        ]
    )

    result = pagos_routes.crear_pagos_batch(body=body, db=db, current_user=_user())

    assert result["ok_count"] == 0
    assert result["fail_count"] == 1
    assert "no coincide" in result["results"][0]["error"]
    assert db.execute(select(Pago)).scalars().all() == []


def test_batch_amount_errors_do_not_roll_back_other_valid_rows(db: Session) -> None:
    cliente_a = _cliente(db, "V33333333", "Cliente A")
    cliente_b = _cliente(db, "V44444444", "Cliente B")
    prestamo_a = _prestamo(db, cliente_a)
    prestamo_b = _prestamo(db, cliente_b)

    body = PagoBatchBody(
        pagos=[
            _pago_create(
                cedula=cliente_a.cedula,
                prestamo_id=prestamo_a.id,
                monto=Decimal("100.00"),
                documento="BATCH-VALID-1",
            ),
            _pago_create(
                cedula=cliente_b.cedula,
                prestamo_id=prestamo_b.id,
                monto=Decimal("0.00"),
                documento="BATCH-BAD-AMOUNT-1",
            ),
        ]
    )

    result = pagos_routes.crear_pagos_batch(body=body, db=db, current_user=_user())

    assert result["ok_count"] == 1
    assert result["fail_count"] == 1
    pagos = db.execute(select(Pago)).scalars().all()
    assert len(pagos) == 1
    assert pagos[0].cedula_cliente == cliente_a.cedula
    assert pagos[0].prestamo_id == prestamo_a.id
