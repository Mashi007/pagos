# -*- coding: utf-8 -*-
from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.base import Base
from app.models.cliente import Cliente
from app.models.prestamo import Prestamo
from app.services.prestamos.prestamos_por_cedula_titular import (
    ESTADOS_CREDITO_ACTIVO_CARGA_STAFF,
    select_prestamo_ids_por_cedula_titular,
)


def _session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def test_solo_titular_y_normaliza_digitos():
    db = _session()
    titular = Cliente(
        nombres="A",
        cedula="V13068140",
        telefono="04120000000",
        email="a@t.com",
    )
    otro = Cliente(
        nombres="B",
        cedula="V99999999",
        telefono="04121111111",
        email="b@t.com",
    )
    db.add_all([titular, otro])
    db.flush()
    p_ok = Prestamo(cliente_id=titular.id, cedula="V13068140", estado="APROBADO")
    p_huerf = Prestamo(cliente_id=otro.id, cedula="V13068140", estado="DESEMBOLSADO")
    db.add_all([p_ok, p_huerf])
    db.commit()

    ids = select_prestamo_ids_por_cedula_titular(
        db, "13068140", estados=ESTADOS_CREDITO_ACTIVO_CARGA_STAFF
    )
    assert ids == [p_ok.id]
