# -*- coding: utf-8 -*-
"""Fail-fast / batch helpers for mover-a-pagos (pagos_con_errores)."""
from __future__ import annotations

from datetime import date

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.models.cliente import Cliente
from app.models.prestamo import Prestamo
from app.services.prestamos.prestamos_por_cedula_titular import (
    mensaje_sin_prestamo_aprobado_para_mover,
    prestamo_ids_activos_por_cedulas_batch,
    resumen_estados_prestamos_por_cedula_titular,
)
from app.utils.cedula_almacenamiento import (
    resolver_cedulas_almacenadas_en_clientes_batch,
)


def _session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine, tables=[Cliente.__table__, Prestamo.__table__])
    return sessionmaker(bind=engine)()


def _cliente(db, cedula: str, nombres: str = "Titular") -> Cliente:
    cli = Cliente(
        nombres=nombres,
        cedula=cedula,
        telefono="04120000000",
        email=f"{cedula.lower()}@t.com",
        direccion="N/A",
        fecha_nacimiento=date(1990, 1, 1),
        ocupacion="N/A",
        estado="ACTIVO",
        usuario_registro="test",
        notas="",
    )
    db.add(cli)
    db.flush()
    return cli


def _prestamo(db, cliente: Cliente, *, estado: str) -> Prestamo:
    p = Prestamo(
        cliente_id=cliente.id,
        cedula=cliente.cedula,
        nombres=cliente.nombres,
        total_financiamiento=1000,
        fecha_requerimiento=date(2024, 1, 1),
        modalidad_pago="MENSUAL",
        numero_cuotas=12,
        cuota_periodo=100,
        producto="TEST",
        estado=estado,
        analista="test",
    )
    db.add(p)
    db.flush()
    return p


def test_mensaje_sin_aprobado_incluye_otros_estados():
    msg = mensaje_sin_prestamo_aprobado_para_mover(
        "V8902484", ["LIQUIDADO", "DESEMBOLSADO"]
    )
    assert "sin préstamo APROBADO" in msg
    assert "LIQUIDADO" in msg
    assert "DESEMBOLSADO" in msg
    assert "asigne el préstamo en edición" in msg
    assert "tiene:" in msg

    msg_vacio = mensaje_sin_prestamo_aprobado_para_mover("V8902484", [])
    assert "sin préstamo APROBADO:" in msg_vacio
    assert "tiene:" not in msg_vacio


def test_batch_cedulas_y_resumen_estados_sin_aprobado():
    db = _session()
    cli = _cliente(db, "V8902484")
    _prestamo(db, cli, estado="LIQUIDADO")
    _prestamo(db, cli, estado="DESEMBOLSADO")
    db.commit()

    batch = resolver_cedulas_almacenadas_en_clientes_batch(
        db, ["8902484", "V8902484", ""]
    )
    assert batch.get("8902484") == "V8902484"
    assert batch.get("V8902484") == "V8902484"

    estados = resumen_estados_prestamos_por_cedula_titular(db, "V8902484")
    assert "LIQUIDADO" in estados
    assert "DESEMBOLSADO" in estados
    assert "APROBADO" not in estados

    aprobados = prestamo_ids_activos_por_cedulas_batch(
        db, ["V8902484"], estados=("APROBADO",)
    )
    assert aprobados.get("V8902484") == []

    msg = mensaje_sin_prestamo_aprobado_para_mover("V8902484", estados)
    assert "LIQUIDADO" in msg


def test_batch_aprobados_unico():
    db = _session()
    cli = _cliente(db, "V11111111", nombres="Ok")
    p = _prestamo(db, cli, estado="APROBADO")
    db.commit()

    aprobados = prestamo_ids_activos_por_cedulas_batch(
        db, ["V11111111"], estados=("APROBADO",)
    )
    assert aprobados.get("V11111111") == [p.id]
