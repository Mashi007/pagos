# -*- coding: utf-8 -*-
"""
Test: Relacionamiento único entre prestamos, cuotas y pagos.

Verifica que cuando se genera/crea un pago con prestamo_id:
- El pago queda vinculado únicamente al préstamo indicado (pago.prestamo_id).
- La aplicación del pago a cuotas solo afecta cuotas de ese préstamo (FIFO por numero_cuota).
- Las cuotas de otros préstamos no reciben ninguna parte del pago.

Ejecutar desde backend/:
  pytest tests/test_relacionamiento_pago_prestamo_cuotas.py -v
  python -m pytest tests/test_relacionamiento_pago_prestamo_cuotas.py -v
"""
from datetime import date, datetime, timedelta
from decimal import Decimal
import os
import sys

import pytest

# Permitir importar app cuando se ejecuta desde backend/
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.cliente import Cliente
from app.models.prestamo import Prestamo
from app.models.cuota import Cuota
from app.models.pago import Pago
from app.models.cuota_pago import CuotaPago


def _aplicar_pago_a_cuotas_interno(pago: Pago, db: Session):
    """Reutiliza la lógica del endpoint para no duplicar código."""
    from app.api.v1.endpoints.pagos import _aplicar_pago_a_cuotas_interno as aplicar
    return aplicar(pago, db)


@pytest.fixture(scope="function")
def db():
    """Sesión de BD; al finalizar se hace rollback para no persistir datos de prueba."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


def test_relacionamiento_unico_pago_prestamo_cuotas(db: Session):
    """
    Verifica el mecanismo de relacionamiento único:
    - Un pago con prestamo_id=X se asocia solo al préstamo X.
    - Al aplicar el pago a cuotas, solo se modifican cuotas del préstamo X.
    """
    from datetime import date as date_type

    # 1) Cliente de prueba
    cedula_test = f"VREL{datetime.now().strftime('%H%M%S')}"
    cliente = Cliente(
        cedula=cedula_test,
        nombres="Test Relacionamiento",
        telefono="0000000000",
        email="test@test.local",
        direccion="Calle Test",
        fecha_nacimiento=date_type(1990, 1, 1),
        ocupacion="Test",
        estado="ACTIVO",
        usuario_registro="test@test.local",
        notas="Test relacionamiento pago-prestamo-cuotas",
    )
    db.add(cliente)
    db.flush()

    # 2) Dos préstamos del mismo cliente
    hoy = date_type.today()
    prestamo_a = Prestamo(
        cliente_id=cliente.id,
        cedula=cliente.cedula,
        nombres=cliente.nombres,
        total_financiamiento=Decimal("600.00"),
        fecha_requerimiento=hoy,
        modalidad_pago="MENSUAL",
        numero_cuotas=3,
        cuota_periodo=Decimal("200.00"),
        producto="Test",
        analista="test@test.local",
    )
    db.add(prestamo_a)
    db.flush()

    prestamo_b = Prestamo(
        cliente_id=cliente.id,
        cedula=cliente.cedula,
        nombres=cliente.nombres,
        total_financiamiento=Decimal("400.00"),
        fecha_requerimiento=hoy,
        modalidad_pago="MENSUAL",
        numero_cuotas=2,
        cuota_periodo=Decimal("200.00"),
        producto="Test",
        analista="test@test.local",
    )
    db.add(prestamo_b)
    db.flush()

    # 3) Cuotas para préstamo A (3 cuotas de 200)
    for n in range(1, 4):
        vto = hoy + timedelta(days=30 * n)
        c = Cuota(
            prestamo_id=prestamo_a.id,
            numero_cuota=n,
            fecha_vencimiento=vto,
            monto=Decimal("200.00"),
            saldo_capital_inicial=Decimal("200.00"),
            saldo_capital_final=Decimal("0.00") if n == 3 else Decimal("200.00"),
            monto_capital=Decimal("200.00"),
            monto_interes=Decimal("0.00"),
            total_pagado=None,
            estado="PENDIENTE",
        )
        db.add(c)
    db.flush()

    # 4) Cuotas para préstamo B (2 cuotas de 200)
    for n in range(1, 3):
        vto = hoy + timedelta(days=30 * n)
        c = Cuota(
            prestamo_id=prestamo_b.id,
            numero_cuota=n,
            fecha_vencimiento=vto,
            monto=Decimal("200.00"),
            saldo_capital_inicial=Decimal("200.00"),
            saldo_capital_final=Decimal("0.00") if n == 2 else Decimal("200.00"),
            monto_capital=Decimal("200.00"),
            monto_interes=Decimal("0.00"),
            total_pagado=None,
            estado="PENDIENTE",
        )
        db.add(c)
    db.flush()

    # 5) Pago asociado SOLO al préstamo A
    numero_doc = f"REL-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    pago = Pago(
        prestamo_id=prestamo_a.id,
        cedula_cliente=cliente.cedula,
        fecha_pago=datetime.now(),
        monto_pagado=Decimal("250.00"),  # Cubre cuota 1 y 50 de cuota 2 de A
        numero_documento=numero_doc,
        referencia_pago=numero_doc,
    )
    db.add(pago)
    db.flush()

    # 6) Aserciones de relacionamiento: pago -> préstamo
    assert pago.prestamo_id == prestamo_a.id, (
        "El pago debe quedar vinculado al préstamo indicado (prestamo_id)."
    )
    assert pago.prestamo_id != prestamo_b.id

    # 7) Aplicar pago a cuotas (misma lógica que el endpoint)
    _aplicar_pago_a_cuotas_interno(pago, db)
    db.flush()

    # 8) Solo las cuotas del préstamo A deben tener aplicaciones (cuota_pagos) y total_pagado > 0
    cuotas_a = (
        db.execute(select(Cuota).where(Cuota.prestamo_id == prestamo_a.id))
    ).scalars().all()
    cuotas_b = (
        db.execute(select(Cuota).where(Cuota.prestamo_id == prestamo_b.id))
    ).scalars().all()

    aplicaciones_a = (
        db.execute(
            select(CuotaPago).join(Cuota, CuotaPago.cuota_id == Cuota.id).where(
                Cuota.prestamo_id == prestamo_a.id
            )
        )
    ).scalars().all()
    aplicaciones_b = (
        db.execute(
            select(CuotaPago).join(Cuota, CuotaPago.cuota_id == Cuota.id).where(
                Cuota.prestamo_id == prestamo_b.id
            )
        )
    ).scalars().all()

    assert len(aplicaciones_a) >= 1, (
        "El pago debe aplicarse al menos a una cuota del préstamo al que está asociado."
    )
    assert len(aplicaciones_b) == 0, (
        "El pago NO debe aplicarse a cuotas de otro préstamo (relacionamiento único)."
    )

    # 9) Suma de monto_aplicado en cuota_pagos debe ser solo sobre cuotas de A
    total_aplicado_a = sum(float(cp.monto_aplicado) for cp in aplicaciones_a)
    assert total_aplicado_a > 0
    assert total_aplicado_a <= float(pago.monto_pagado)

    # 10) Cuotas de B siguen con total_pagado nulo o 0
    for c in cuotas_b:
        assert c.total_pagado is None or float(c.total_pagado or 0) == 0, (
            "Las cuotas del préstamo B no deben recibir ningún monto del pago."
        )


def test_pago_sin_prestamo_id_no_aplica_a_cuotas(db: Session):
    """
    Si un pago no tiene prestamo_id, la aplicación a cuotas no debe modificar ninguna cuota.
    """
    from datetime import date as date_type
    from app.models.cuota_pago import CuotaPago
    from sqlalchemy import func

    # Cliente mínimo (FK pagos.cedula -> clientes.cedula)
    cedula_null = f"VNULL{datetime.now().strftime('%H%M%S')}"
    cliente = Cliente(
        cedula=cedula_null,
        nombres="Test Null Prestamo",
        telefono="0000000000",
        email="null@test.local",
        direccion="Calle Test",
        fecha_nacimiento=date_type(1990, 1, 1),
        ocupacion="Test",
        estado="ACTIVO",
        usuario_registro="test@test.local",
        notas="Test pago sin prestamo_id",
    )
    db.add(cliente)
    db.flush()

    # Crear un pago sin préstamo
    numero_doc = f"REL-NULL-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    pago = Pago(
        prestamo_id=None,
        cedula_cliente=cliente.cedula,
        fecha_pago=datetime.now(),
        monto_pagado=Decimal("100.00"),
        numero_documento=numero_doc,
        referencia_pago=numero_doc,
    )
    db.add(pago)
    db.flush()

    count_before = db.scalar(select(func.count()).select_from(CuotaPago)) or 0
    _aplicar_pago_a_cuotas_interno(pago, db)
    db.flush()
    count_after = db.scalar(select(func.count()).select_from(CuotaPago)) or 0

    assert count_after == count_before, (
        "Un pago sin prestamo_id no debe crear registros en cuota_pagos."
    )
