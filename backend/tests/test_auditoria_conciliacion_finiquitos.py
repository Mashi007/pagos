"""Tests Conciliacion_finiquitos: Excel cédulas → estado real del préstamo."""
from __future__ import annotations

import io
from datetime import date, datetime
from decimal import Decimal

import pytest
from openpyxl import Workbook
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.cliente import Cliente
from app.models.finiquito import FiniquitoCaso
from app.models.prestamo import Prestamo
from app.services.auditoria_conciliacion_finiquitos_service import (
    _variantes_clave_cedula,
    comparar_cedulas_archivo_vs_sistema,
)


@pytest.fixture()
def db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Cliente.__table__.create(bind=engine, checkfirst=True)
    Prestamo.__table__.create(bind=engine, checkfirst=True)
    FiniquitoCaso.__table__.create(bind=engine, checkfirst=True)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()


def _xlsx_cedulas(cedulas: list[str]) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.append(["cedula"])
    for c in cedulas:
        ws.append([c])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def test_variantes_clave_cedula_digitos_y_prefijo():
    assert "V123" in _variantes_clave_cedula("123")
    assert "123" in _variantes_clave_cedula("V123")


def test_comparar_cedulas_estado_sistema_y_no_encontrada(db, monkeypatch):
    # SQLite de test no tiene regexp_replace; forzar rama no-Postgres del helper.
    monkeypatch.setattr(
        "app.utils.cedula_almacenamiento._database_url_es_postgresql",
        lambda: False,
    )
    cli = Cliente(
        cedula="V12345678",
        nombres="Test Finiquito",
        telefono="000",
        email="t@example.com",
        direccion="x",
        fecha_nacimiento=date(1990, 1, 1),
        ocupacion="x",
        estado="ACTIVO",
        usuario_registro="test",
        notas="",
        fecha_registro=datetime(2024, 1, 1),
        fecha_actualizacion=datetime(2024, 1, 1),
    )
    db.add(cli)
    db.flush()
    p = Prestamo(
        cliente_id=cli.id,
        cedula="V12345678",
        nombres="Test Finiquito",
        total_financiamiento=Decimal("1000.00"),
        fecha_requerimiento=date(2024, 1, 1),
        modalidad_pago="MENSUAL",
        numero_cuotas=12,
        cuota_periodo=Decimal("100.00"),
        producto="MOTO",
        estado="LIQUIDADO",
        estado_gestion_finiquito="TERMINADO",
        analista="a",
        fecha_registro=datetime(2024, 1, 1),
        fecha_actualizacion=datetime(2024, 1, 1),
    )
    db.add(p)
    db.flush()
    db.add(
        FiniquitoCaso(
            prestamo_id=p.id,
            cliente_id=cli.id,
            cedula="V12345678",
            total_financiamiento=Decimal("1000.00"),
            sum_total_pagado=Decimal("1000.00"),
            estado="TERMINADO",
        )
    )
    db.commit()

    out = comparar_cedulas_archivo_vs_sistema(
        db, _xlsx_cedulas(["12345678", "99999999"])
    )
    assert out["total_cedulas_archivo"] == 2
    assert out["encontradas"] == 1
    assert out["no_encontradas"] == 1

    found = next(i for i in out["items"] if i["en_sistema"])
    missing = next(i for i in out["items"] if not i["en_sistema"])
    assert found["estado_sistema"] == "LIQUIDADO"
    assert found["estado_prestamo"] == "LIQUIDADO"
    assert found["estado_caso_finiquito"] == "TERMINADO"
    assert found["estado_gestion_finiquito"] == "TERMINADO"
    assert missing["estado_sistema"] == "NO_ENCONTRADA"
