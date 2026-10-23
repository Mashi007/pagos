# -*- coding: utf-8 -*-
"""Pago y estado de cuenta cuando prestamos.cedula es de otra persona."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.models.cliente import Cliente
from app.models.cuota import Cuota
from app.models.cuota_pago import CuotaPago
from app.models.pago import Pago
from app.models.prestamo import Prestamo
from app.services.estado_cuenta_datos import listar_pagos_realizados_estado_cuenta
from app.utils.cedula_almacenamiento import asegurar_cedula_pago_para_fk


def _session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(
        engine,
        tables=[
            Cliente.__table__,
            Prestamo.__table__,
            Pago.__table__,
            Cuota.__table__,
            CuotaPago.__table__,
        ],
    )
    return sessionmaker(bind=engine)()


def _cliente(cedula: str, nombre: str) -> Cliente:
    return Cliente(
        nombres=nombre,
        cedula=cedula,
        telefono="04120000000",
        email=f"{cedula.lower()}@example.com",
        direccion="Caracas",
        fecha_nacimiento=date(1990, 1, 1),
        ocupacion="Empleado",
        estado="ACTIVO",
        usuario_registro="test",
        notas="",
    )


def _prestamo(cliente_id: int, cedula_columna: str) -> Prestamo:
    return Prestamo(
        cliente_id=cliente_id,
        cedula=cedula_columna,
        nombres="Titular del credito",
        total_financiamiento=Decimal("1000.00"),
        fecha_requerimiento=date(2026, 1, 1),
        modalidad_pago="MENSUAL",
        numero_cuotas=12,
        cuota_periodo=Decimal("100.00"),
        producto="Financiamiento",
        estado="APROBADO",
        analista="Analista",
    )


def _pago(prestamo_id: int, cedula: str, monto: str = "50.00") -> Pago:
    return Pago(
        prestamo_id=prestamo_id,
        cedula_cliente=cedula,
        fecha_pago=datetime(2026, 10, 1, 0, 0, 0),
        monto_pagado=Decimal(monto),
        estado="PAGADO",
        referencia_pago="REF-1",
        conciliado=True,
    )


def test_asegurar_cedula_pago_prioriza_titular_no_columna_huerfana():
    """V99999999 es el dueño; prestamos.cedula apunta a V13068140, que existe."""
    db = _session()
    dueno_documento = _cliente("V13068140", "Dueno documento")
    titular = _cliente("V99999999", "Titular del prestamo")
    db.add_all([dueno_documento, titular])
    db.flush()
    prestamo = _prestamo(titular.id, "V13068140")
    db.add(prestamo)
    db.commit()

    resuelta = asegurar_cedula_pago_para_fk(
        db,
        cedula_raw="V13068140",
        prestamo_id=prestamo.id,
    )
    assert resuelta == "V99999999"


def test_estado_cuenta_conserva_pago_del_titular_y_descarta_un_tercero():
    db = _session()
    dueno_documento = _cliente("V13068140", "Dueno documento")
    titular = _cliente("V99999999", "Titular del prestamo")
    db.add_all([dueno_documento, titular])
    db.flush()
    prestamo = _prestamo(titular.id, "V13068140")
    db.add(prestamo)
    db.flush()
    db.add_all(
        [
            _pago(prestamo.id, "V99999999", "40.00"),
            _pago(prestamo.id, "V13068140", "25.00"),
            _pago(prestamo.id, "V11111111", "10.00"),
        ]
    )
    db.commit()

    filas = listar_pagos_realizados_estado_cuenta(db, [prestamo.id])
    cedulas = {f["cedula_comprobante"] for f in filas}
    assert "V99999999" in cedulas
    assert "V13068140" in cedulas
    assert "V11111111" not in cedulas
