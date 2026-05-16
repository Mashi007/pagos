# -*- coding: utf-8 -*-
"""Pruebas de archivado trazable en pagos_con_errores."""
from __future__ import annotations

import os
import sys
from datetime import date, datetime
from decimal import Decimal

import pytest
from uuid import uuid4
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal
from app.api.v1.endpoints.pagos_con_errores.routes import (
    EliminarPorDescargaBody,
    archivar_por_descarga,
    listar_pagos_con_errores,
    mover_a_pagos_normales,
)
from app.models.cliente import Cliente
from app.models.pago import Pago
from app.models.pago_con_error import PagoConError
from app.models.prestamo import Prestamo
from app.schemas.auth import UserResponse


@pytest.fixture(scope="function")
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


def _fake_user() -> UserResponse:
    return UserResponse(
        id=99,
        email="auditoria@test.local",
        nombre="Auditoria",
        apellido="QA",
        cargo="Tester",
        rol="administrador",
        is_active=True,
        created_at="2025-01-01T00:00:00Z",
        updated_at="2025-01-01T00:00:00Z",
        last_login="2025-01-01T00:00:00Z",
    )


def _crear_pago_con_error(db: Session, doc: str, estado: str | None = "PENDIENTE") -> PagoConError:
    doc_unico = f"{doc}-{uuid4().hex[:8]}"
    row = PagoConError(
        cedula_cliente="V12345678",
        prestamo_id=None,
        fecha_pago=datetime.now().replace(hour=0, minute=0, second=0, microsecond=0),
        monto_pagado=Decimal("25.00"),
        numero_documento=doc_unico,
        institucion_bancaria="BNC",
        estado=estado,
        conciliado=False,
        usuario_registro="seed@test.local",
        notas=None,
        referencia_pago=doc_unico,
    )
    db.add(row)
    db.flush()
    db.refresh(row)
    return row


def test_archivar_por_descarga_marca_estado_y_observacion(db: Session):
    p1 = _crear_pago_con_error(db, "ARCH-001")
    p2 = _crear_pago_con_error(db, "ARCH-002")
    db.commit()

    out = archivar_por_descarga(
        payload=EliminarPorDescargaBody(ids=[p1.id, p2.id]),
        db=db,
        current_user=_fake_user(),
    )

    assert int(out.get("archivados") or 0) == 2

    rows = db.execute(
        select(PagoConError).where(PagoConError.id.in_([p1.id, p2.id]))
    ).scalars().all()
    assert len(rows) == 2
    for row in rows:
        assert row.estado == "EXPORTADO_REVISION"
        obs = (row.observaciones or "").lower()
        assert "exportado a revisión" in obs
        assert "auditoria@test.local" in obs


def test_listar_pagos_con_errores_oculta_exportados_por_defecto(db: Session):
    p_visible = _crear_pago_con_error(db, "ARCH-003", estado="PENDIENTE")
    p_archivado = _crear_pago_con_error(db, "ARCH-004", estado="EXPORTADO_REVISION")
    db.commit()

    resp_default = listar_pagos_con_errores(
        page=1,
        per_page=20,
        cedula=None,
        estado=None,
        fecha_desde=None,
        fecha_hasta=None,
        conciliado=None,
        include_exportados=False,
        db=db,
    )
    ids_default = {int(x["id"]) for x in resp_default.get("pagos", [])}
    assert p_visible.id in ids_default
    assert p_archivado.id not in ids_default

    resp_all = listar_pagos_con_errores(
        page=1,
        per_page=20,
        cedula=None,
        estado=None,
        fecha_desde=None,
        fecha_hasta=None,
        conciliado=None,
        include_exportados=True,
        db=db,
    )
    ids_all = {int(x["id"]) for x in resp_all.get("pagos", [])}
    assert p_visible.id in ids_all
    assert p_archivado.id in ids_all


def test_mover_a_pagos_rollback_por_fila_no_borra_revision_si_falla_cascada(
    db: Session, monkeypatch: pytest.MonkeyPatch
):
    cedula = f"V9{datetime.now().strftime('%H%M%S%f')[:10]}"
    doc_ok = f"MOV-OK-{uuid4().hex[:10]}"
    doc_fail = f"MOV-FAIL-{uuid4().hex[:10]}"

    cliente = Cliente(
        cedula=cedula,
        nombres="Cliente Movimiento",
        telefono="0000000000",
        email="movimiento@test.local",
        direccion="Calle Test",
        fecha_nacimiento=date(1990, 1, 1),
        ocupacion="Test",
        estado="ACTIVO",
        usuario_registro="test@test.local",
        notas="Test mover pagos con errores",
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
        analista="test@test.local",
    )
    db.add(prestamo)
    db.flush()

    ok_row = PagoConError(
        cedula_cliente=cliente.cedula,
        prestamo_id=None,
        fecha_pago=datetime.now().replace(microsecond=0),
        monto_pagado=Decimal("10.00"),
        numero_documento=doc_ok,
        institucion_bancaria="BNC",
        estado="PENDIENTE",
        conciliado=False,
        usuario_registro="seed@test.local",
        referencia_pago=doc_ok,
    )
    fail_row = PagoConError(
        cedula_cliente=cliente.cedula,
        prestamo_id=prestamo.id,
        fecha_pago=datetime.now().replace(microsecond=0),
        monto_pagado=Decimal("25.00"),
        numero_documento=doc_fail,
        institucion_bancaria="BNC",
        estado="PENDIENTE",
        conciliado=False,
        usuario_registro="seed@test.local",
        referencia_pago=doc_fail,
    )
    db.add_all([ok_row, fail_row])
    db.commit()

    def _fallar_cascada(_pago: Pago, _db: Session):
        raise RuntimeError("fallo simulado de cuotas")

    import app.api.v1.endpoints.pagos as pagos_endpoint

    monkeypatch.setattr(
        pagos_endpoint, "_aplicar_pago_a_cuotas_interno", _fallar_cascada
    )

    try:
        out = mover_a_pagos_normales(
            payload=EliminarPorDescargaBody(ids=[ok_row.id, fail_row.id]),
            db=db,
        )

        assert out["movidos"] == 1
        assert any("fallo simulado de cuotas" in e for e in out.get("errores", []))

        assert db.get(PagoConError, ok_row.id) is None
        assert db.get(PagoConError, fail_row.id) is not None

        pago_ok = db.execute(
            select(Pago).where(Pago.numero_documento == doc_ok)
        ).scalar_one_or_none()
        pago_fail = db.execute(
            select(Pago).where(Pago.numero_documento == doc_fail)
        ).scalar_one_or_none()

        assert pago_ok is not None
        assert pago_fail is None
    finally:
        db.execute(delete(Pago).where(Pago.numero_documento.in_([doc_ok, doc_fail])))
        db.execute(
            delete(PagoConError).where(
                PagoConError.numero_documento.in_([doc_ok, doc_fail])
            )
        )
        db.execute(delete(Prestamo).where(Prestamo.id == prestamo.id))
        db.execute(delete(Cliente).where(Cliente.cedula == cedula))
        db.commit()
