from datetime import date
from decimal import Decimal

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.models.analista import Analista
from app.models.cliente import Cliente
from app.models.prestamo import Prestamo
from app.utils.cedula_almacenamiento import asegurar_cedula_pago_para_fk


def test_asegurar_cedula_pago_alinea_cliente_legacy_minusculas_con_prestamo():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(
        engine,
        tables=[Analista.__table__, Cliente.__table__, Prestamo.__table__],
    )
    SessionLocal = sessionmaker(bind=engine)

    with SessionLocal() as db:
        cliente_result = db.execute(
            Cliente.__table__.insert().values(
                cedula="v12345678",
                nombres="Cliente Legacy",
                telefono="0000",
                email="legacy@example.com",
                direccion="Direccion",
                fecha_nacimiento=date(1990, 1, 1),
                ocupacion="Empleado",
                estado="ACTIVO",
                usuario_registro="test",
                notas="",
            )
        )
        cliente_id = cliente_result.inserted_primary_key[0]
        prestamo_result = db.execute(
            Prestamo.__table__.insert().values(
                cliente_id=cliente_id,
                cedula="v12345678",
                nombres="Cliente Legacy",
                total_financiamiento=Decimal("100.00"),
                fecha_requerimiento=date(2026, 1, 1),
                modalidad_pago="MENSUAL",
                numero_cuotas=1,
                cuota_periodo=Decimal("100.00"),
                producto="AUTO",
                estado="APROBADO",
                analista="Analista Test",
            )
        )
        prestamo_id = prestamo_result.inserted_primary_key[0]

        cedula_pago = asegurar_cedula_pago_para_fk(
            db,
            cedula_raw="v12345678",
            prestamo_id=prestamo_id,
        )

        assert cedula_pago == "V12345678"
        assert (
            db.execute(select(Cliente.cedula).where(Cliente.id == cliente_id)).scalar_one()
            == "V12345678"
        )
