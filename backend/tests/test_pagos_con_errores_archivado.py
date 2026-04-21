# -*- coding: utf-8 -*-
"""Pruebas de archivado trazable en pagos_con_errores."""
from __future__ import annotations

import os
import sys
from datetime import datetime
from decimal import Decimal

import pytest
from uuid import uuid4
from sqlalchemy import select
from sqlalchemy.orm import Session

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal
from app.api.v1.endpoints.pagos_con_errores.routes import (
    EliminarPorDescargaBody,
    archivar_por_descarga,
    listar_pagos_con_errores,
)
from app.models.pago_con_error import PagoConError
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
