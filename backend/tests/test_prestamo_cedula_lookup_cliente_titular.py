# -*- coding: utf-8 -*-
"""Préstamos por cédula: solo los del cliente titular (no Prestamo.cedula huérfana)."""
from __future__ import annotations

from types import SimpleNamespace

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.models.base import Base
from app.models.cliente import Cliente
from app.models.prestamo import Prestamo
from app.utils.cedula_almacenamiento import (
    expr_cedula_normalizada_para_comparar,
    texto_cedula_comparable_bd,
)
from app.services.prestamo_candidatos_drive_validadores import (
    conteo_prestamos_aprobados_por_cedula_norm,
)


def _session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def test_conteo_aprobados_solo_cliente_titular():
    db = _session()
    titular = Cliente(
        nombres="Titular",
        cedula="V13068140",
        telefono="04120000000",
        email="t@example.com",
    )
    otro = Cliente(
        nombres="Otro",
        cedula="V99999999",
        telefono="04121111111",
        email="o@example.com",
    )
    db.add_all([titular, otro])
    db.flush()
    db.add_all(
        [
            Prestamo(cliente_id=titular.id, cedula="V13068140", estado="LIQUIDADO"),
            Prestamo(
                cliente_id=otro.id,
                cedula="V13068140",
                estado="APROBADO",
            ),
        ]
    )
    db.commit()

    counts = conteo_prestamos_aprobados_por_cedula_norm(db)
    assert counts.get("V13068140", 0) == 0

    norm = texto_cedula_comparable_bd("V13068140")
    rows = db.execute(
        select(Prestamo.id)
        .select_from(Prestamo)
        .join(Cliente, Prestamo.cliente_id == Cliente.id)
        .where(expr_cedula_normalizada_para_comparar(Cliente.cedula) == norm)
    ).all()
    assert len(rows) == 1
    p = db.get(Prestamo, rows[0][0])
    assert p.cliente_id == titular.id
