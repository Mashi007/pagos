# -*- coding: utf-8 -*-
"""Integridad sum(cuota_pagos) <= monto_pago e idempotencia de aplicacion en cascada."""
from __future__ import annotations

import os
import sys
from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal
from app.models.cliente import Cliente
from app.models.cuota import Cuota
from app.models.cuota_pago import CuotaPago
from app.models.pago import Pago
from app.models.prestamo import Prestamo
from app.services.cuota_pago_integridad import validar_suma_aplicada_vs_monto_pago


@pytest.fixture(scope="function")
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


def test_validar_suma_supera_monto_pago_raises(db: Session):
    hoy = date.today()
    cedula = f"VINT{datetime.now().strftime('%H%M%S')}"
    cliente = Cliente(
        cedula=cedula,
        nombres="Test Integridad",
        telefono="0",
        email="i@test.local",
        direccion="X",
        fecha_nacimiento=date(1990, 1, 1),
        ocupacion="T",
        estado="ACTIVO",
        usuario_registro="test@test.local",
        notas="cuota_pago_integridad",
    )
    db.add(cliente)
    db.flush()
    prestamo = Prestamo(
        cliente_id=cliente.id,
        cedula=cliente.cedula,
        nombres=cliente.nombres,
        total_financiamiento=Decimal("200.00"),
        fecha_requerimiento=hoy,
        modalidad_pago="MENSUAL",
        numero_cuotas=1,
        cuota_periodo=Decimal("200.00"),
        producto="T",
        analista="test@test.local",
    )
    db.add(prestamo)
    db.flush()
    cuota = Cuota(
        prestamo_id=prestamo.id,
        numero_cuota=1,
        fecha_vencimiento=hoy + timedelta(days=30),
        monto=Decimal("200.00"),
        saldo_capital_inicial=Decimal("200.00"),
        saldo_capital_final=Decimal("0.00"),
        monto_capital=Decimal("200.00"),
        monto_interes=Decimal("0.00"),
        total_pagado=None,
        estado="PENDIENTE",
    )
    db.add(cuota)
    db.flush()
    doc = f"INT-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    pago = Pago(
        prestamo_id=prestamo.id,
        cedula_cliente=cliente.cedula,
        fecha_pago=datetime.now(),
        monto_pagado=Decimal("10.00"),
        numero_documento=doc,
        referencia_pago=doc,
    )
    db.add(pago)
    db.flush()
    db.add(
        CuotaPago(
            cuota_id=cuota.id,
            pago_id=pago.id,
            monto_aplicado=Decimal("50.00"),
            orden_aplicacion=0,
            es_pago_completo=False,
        )
    )
    db.flush()
    with pytest.raises(ValueError, match="Suma aplicada"):
        validar_suma_aplicada_vs_monto_pago(db, pago.id, pago.monto_pagado)


def test_aplicar_pago_cuotas_segunda_llamada_idempotente(db: Session):
    from app.api.v1.endpoints.pagos import _aplicar_pago_a_cuotas_interno

    hoy = date.today()
    cedula = f"VIDP{datetime.now().strftime('%H%M%S')}"
    cliente = Cliente(
        cedula=cedula,
        nombres="Test Idempotencia",
        telefono="0",
        email="idp@test.local",
        direccion="X",
        fecha_nacimiento=date(1990, 1, 1),
        ocupacion="T",
        estado="ACTIVO",
        usuario_registro="test@test.local",
        notas="idempotencia aplicar",
    )
    db.add(cliente)
    db.flush()
    prestamo = Prestamo(
        cliente_id=cliente.id,
        cedula=cliente.cedula,
        nombres=cliente.nombres,
        total_financiamiento=Decimal("300.00"),
        fecha_requerimiento=hoy,
        modalidad_pago="MENSUAL",
        numero_cuotas=3,
        cuota_periodo=Decimal("100.00"),
        producto="T",
        analista="test@test.local",
    )
    db.add(prestamo)
    db.flush()
    for n in range(1, 4):
        db.add(
            Cuota(
                prestamo_id=prestamo.id,
                numero_cuota=n,
                fecha_vencimiento=hoy + timedelta(days=30 * n),
                monto=Decimal("100.00"),
                saldo_capital_inicial=Decimal("100.00"),
                saldo_capital_final=Decimal("0.00"),
                monto_capital=Decimal("100.00"),
                monto_interes=Decimal("0.00"),
                total_pagado=None,
                estado="PENDIENTE",
            )
        )
    db.flush()
    doc = f"IDP-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    pago = Pago(
        prestamo_id=prestamo.id,
        cedula_cliente=cliente.cedula,
        fecha_pago=datetime.now(),
        monto_pagado=Decimal("80.00"),
        numero_documento=doc,
        referencia_pago=doc,
    )
    db.add(pago)
    db.flush()

    _aplicar_pago_a_cuotas_interno(pago, db)
    db.flush()
    n1 = db.scalar(
        select(func.count()).select_from(CuotaPago).where(CuotaPago.pago_id == pago.id)
    )
    assert int(n1 or 0) >= 1

    cc2, cp2 = _aplicar_pago_a_cuotas_interno(pago, db)
    db.flush()
    assert cc2 == 0 and cp2 == 0
    n2 = db.scalar(
        select(func.count()).select_from(CuotaPago).where(CuotaPago.pago_id == pago.id)
    )
    assert int(n2 or 0) == int(n1 or 0)
