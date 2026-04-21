# -*- coding: utf-8 -*-
"""Pruebas del flujo de conciliación automática sin limbo."""
from __future__ import annotations

import os
import sys
from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal
from app.models.cliente import Cliente
from app.models.cuota import Cuota
from app.models.pago import Pago
from app.models.prestamo import Prestamo
from app.services.conciliacion_automatica_service import ConciliacionAutomaticaService


@pytest.fixture(scope="function")
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


def test_conciliacion_remanente_marca_pago_pendiente_y_no_conciliado(db: Session):
    hoy = date.today()
    cedula = f"VCA{datetime.now().strftime('%H%M%S')}"
    cliente = Cliente(
        cedula=cedula,
        nombres="Cliente CA",
        telefono="0",
        email="ca@test.local",
        direccion="X",
        fecha_nacimiento=date(1990, 1, 1),
        ocupacion="T",
        estado="ACTIVO",
        usuario_registro="test@test.local",
        notas="test conciliacion automatica",
    )
    db.add(cliente)
    db.flush()

    prestamo = Prestamo(
        cliente_id=cliente.id,
        cedula=cliente.cedula,
        nombres=cliente.nombres,
        total_financiamiento=Decimal("100.00"),
        fecha_requerimiento=hoy,
        modalidad_pago="MENSUAL",
        numero_cuotas=1,
        cuota_periodo=Decimal("100.00"),
        producto="T",
        analista="test@test.local",
    )
    db.add(prestamo)
    db.flush()

    cuota = Cuota(
        prestamo_id=prestamo.id,
        numero_cuota=1,
        fecha_vencimiento=hoy + timedelta(days=30),
        monto=Decimal("100.00"),
        saldo_capital_inicial=Decimal("100.00"),
        saldo_capital_final=Decimal("0.00"),
        monto_capital=Decimal("100.00"),
        monto_interes=Decimal("0.00"),
        total_pagado=None,
        estado="PENDIENTE",
    )
    db.add(cuota)
    db.flush()

    pago = Pago(
        prestamo_id=prestamo.id,
        cedula_cliente=cliente.cedula,
        fecha_pago=datetime.now(),
        monto_pagado=Decimal("120.00"),  # deja remanente de 20 tras cubrir cuota 100
        numero_documento=f"CA-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        referencia_pago=f"CA-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        conciliado=True,
        verificado_concordancia="SI",
        estado="PAGADO",
        notas=None,
    )
    db.add(pago)
    db.commit()
    db.refresh(pago)

    out = ConciliacionAutomaticaService.asignar_pagos_no_conciliados(
        db, prestamo_id=prestamo.id
    )
    db.refresh(pago)

    errores = out.get("errores") or []
    assert any(f"Pago {pago.id}: Sobra" in e for e in errores)
    assert int(out.get("fallidas") or 0) >= 1
    assert pago.conciliado is False
    assert (pago.verificado_concordancia or "").upper() == "NO"
    assert (pago.estado or "").upper() == "PENDIENTE"
    assert "Remanente sin asignar en conciliación automática" in (pago.notas or "")
