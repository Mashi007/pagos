from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session

from app.models.analista import Analista
from app.models.cliente import Cliente
from app.models.prestamo import Prestamo
from app.utils.cedula_almacenamiento import asegurar_cedula_pago_para_fk


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Cliente.__table__.create(engine)
    Analista.__table__.create(engine)
    Prestamo.__table__.create(engine)
    session = Session(engine)
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def _crear_cliente_y_prestamo(db: Session) -> tuple[Cliente, Prestamo]:
    cliente = Cliente(
        cedula="VLOW123",
        nombres="Legacy",
        telefono="000",
        email="legacy@example.test",
        direccion="Test",
        fecha_nacimiento=date(1990, 1, 1),
        ocupacion="Test",
        estado="ACTIVO",
        usuario_registro="test",
        notas="test",
    )
    db.add(cliente)
    db.flush()

    prestamo = Prestamo(
        cliente_id=cliente.id,
        cedula=cliente.cedula,
        nombres=cliente.nombres,
        total_financiamiento=Decimal("100.00"),
        fecha_requerimiento=date.today(),
        modalidad_pago="MENSUAL",
        numero_cuotas=1,
        cuota_periodo=Decimal("100.00"),
        producto="Test",
        analista="test",
        estado="APROBADO",
    )
    db.add(prestamo)
    db.flush()
    return cliente, prestamo


def test_asegurar_cedula_pago_para_fk_alinea_cliente_legacy_con_prestamo(db_session: Session):
    cliente, prestamo = _crear_cliente_y_prestamo(db_session)
    db_session.execute(text("UPDATE clientes SET cedula = 'vlow123' WHERE id = :id"), {"id": cliente.id})
    db_session.expire_all()

    cedula_fk = asegurar_cedula_pago_para_fk(
        db_session,
        cedula_raw="vlow123",
        prestamo_id=prestamo.id,
    )

    assert cedula_fk == "VLOW123"
    cedula_bd = db_session.execute(
        select(Cliente.cedula).where(Cliente.id == cliente.id)
    ).scalar_one()
    assert cedula_bd == "VLOW123"
