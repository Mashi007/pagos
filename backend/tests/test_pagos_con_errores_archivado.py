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
    limpiar_pagos_con_error_ya_cargados,
    listar_pagos_con_errores,
    mover_a_pagos_normales,
)
from app.api.v1.endpoints.pagos_con_errores import routes as pagos_con_errores_routes
from app.models.pago import Pago
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
        fecha_pago=None,
        numero_documento=None,
        tipo_revision=None,
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
        fecha_pago=None,
        numero_documento=None,
        tipo_revision=None,
        conciliado=None,
        include_exportados=True,
        db=db,
    )
    ids_all = {int(x["id"]) for x in resp_all.get("pagos", [])}
    assert p_visible.id in ids_all
    assert p_archivado.id in ids_all


def test_mover_a_pagos_mantiene_filas_previas_si_una_falla(monkeypatch, db: Session):
    p_ok = _crear_pago_con_error(db, "MOVE-SAVEPOINT-OK")
    p_error = _crear_pago_con_error(db, "MOVE-SAVEPOINT-ERR")
    doc_ok = p_ok.numero_documento
    doc_error = p_error.numero_documento
    db.commit()

    monkeypatch.setattr(
        pagos_con_errores_routes,
        "pago_con_error_ya_cargado_estricto",
        lambda _db, _row: None,
    )
    monkeypatch.setattr(
        pagos_con_errores_routes,
        "resolver_cedula_almacenada_en_clientes",
        lambda _db, cedula: cedula,
    )

    def _duplicado_o_falla(_db, numero_documento, **_kwargs):
        if numero_documento == doc_error:
            raise RuntimeError("fallo simulado")
        return False

    monkeypatch.setattr(
        pagos_con_errores_routes,
        "numero_documento_ya_registrado",
        _duplicado_o_falla,
    )

    out = mover_a_pagos_normales(
        payload=EliminarPorDescargaBody(ids=[p_ok.id, p_error.id]),
        db=db,
    )

    assert out["movidos"] == 1
    assert out["errores"]
    assert db.get(PagoConError, p_ok.id) is None
    assert db.get(PagoConError, p_error.id) is not None
    pago_ok = db.execute(
        select(Pago).where(Pago.numero_documento == doc_ok)
    ).scalar_one_or_none()
    assert pago_ok is not None


def test_limpiar_ya_cargados_mantiene_borrados_previos_si_una_falla(
    monkeypatch, db: Session
):
    p_ok = _crear_pago_con_error(db, "CLEAN-SAVEPOINT-OK")
    p_error = _crear_pago_con_error(db, "CLEAN-SAVEPOINT-ERR")
    db.commit()

    def _ya_cargado_o_falla(_db, row):
        if int(row.id) == int(p_error.id):
            raise RuntimeError("fallo simulado")
        return 999

    monkeypatch.setattr(
        pagos_con_errores_routes,
        "pago_con_error_ya_cargado_estricto",
        _ya_cargado_o_falla,
    )

    out = limpiar_pagos_con_error_ya_cargados(
        payload=pagos_con_errores_routes.LimpiarYaCargadosBody(
            ids=[p_ok.id, p_error.id]
        ),
        db=db,
        current_user=_fake_user(),
    )

    assert out["eliminados"] == 1
    assert out["errores"]
    assert db.get(PagoConError, p_ok.id) is None
    assert db.get(PagoConError, p_error.id) is not None
