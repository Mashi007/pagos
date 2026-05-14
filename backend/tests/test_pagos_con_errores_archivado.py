# -*- coding: utf-8 -*-
"""Pruebas de archivado trazable en pagos_con_errores."""
from __future__ import annotations

import os
import sys
import types
import importlib.util
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pytest
from uuid import uuid4
from sqlalchemy import select
from sqlalchemy.orm import Session

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal
from app.models.pago_con_error import PagoConError
from app.schemas.auth import UserResponse

_ROUTES_PATH = (
    Path(__file__).resolve().parents[1]
    / "app"
    / "api"
    / "v1"
    / "endpoints"
    / "pagos_con_errores"
    / "routes.py"
)
_ROUTES_SPEC = importlib.util.spec_from_file_location(
    "pagos_con_errores_routes_under_test", _ROUTES_PATH
)
assert _ROUTES_SPEC is not None and _ROUTES_SPEC.loader is not None
pagos_con_errores_routes = importlib.util.module_from_spec(_ROUTES_SPEC)
sys.modules[_ROUTES_SPEC.name] = pagos_con_errores_routes
_ROUTES_SPEC.loader.exec_module(pagos_con_errores_routes)

EliminarPorDescargaBody = pagos_con_errores_routes.EliminarPorDescargaBody
LimpiarYaCargadosBody = pagos_con_errores_routes.LimpiarYaCargadosBody
archivar_por_descarga = pagos_con_errores_routes.archivar_por_descarga
limpiar_pagos_con_error_ya_cargados = (
    pagos_con_errores_routes.limpiar_pagos_con_error_ya_cargados
)
listar_pagos_con_errores = pagos_con_errores_routes.listar_pagos_con_errores
mover_a_pagos_normales = pagos_con_errores_routes.mover_a_pagos_normales


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


class _FakeNestedTransaction:
    def __init__(self, db):
        self.db = db

    def __enter__(self):
        self.db.savepoints_started += 1
        return self

    def __exit__(self, exc_type, exc, tb):
        if exc_type is None:
            self.db.savepoints_committed += 1
        else:
            self.db.savepoints_rolled_back += 1
        return False


class _FakeExecuteResult:
    def __init__(self, rows):
        self.rows = rows

    def scalars(self):
        return self.rows


class _FakeSession:
    def __init__(self, rows):
        self.rows = {int(row.id): row for row in rows}
        self.added = []
        self.deleted = []
        self.commits = 0
        self.rollbacks = 0
        self.flushes = 0
        self.savepoints_started = 0
        self.savepoints_committed = 0
        self.savepoints_rolled_back = 0

    def begin_nested(self):
        return _FakeNestedTransaction(self)

    def execute(self, _stmt):
        return _FakeExecuteResult(list(self.rows.values()))

    def get(self, _model, row_id):
        return self.rows.get(int(row_id))

    def add(self, obj):
        if getattr(obj, "id", None) is None:
            obj.id = 700 + len(self.added)
        self.added.append(obj)

    def delete(self, obj):
        self.deleted.append(obj)

    def flush(self):
        self.flushes += 1

    def refresh(self, obj):
        if getattr(obj, "id", None) is None:
            obj.id = 700 + len(self.added)

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1


def _fake_pago_con_error(row_id: int, prestamo_id: int | None = 101):
    return SimpleNamespace(
        id=row_id,
        cedula_cliente="12345678",
        prestamo_id=prestamo_id,
        fecha_pago=datetime.now().replace(hour=0, minute=0, second=0, microsecond=0),
        monto_pagado=Decimal("25.00"),
        numero_documento=f"DOC-{row_id}",
        institucion_bancaria="BNC",
        estado="PENDIENTE",
        conciliado=False,
        notas=None,
        referencia_pago=f"DOC-{row_id}",
    )


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


def test_limpiar_usa_savepoint_por_fila_sin_revertir_exitos_previos(monkeypatch):
    row_ok = _fake_pago_con_error(1)
    row_error = _fake_pago_con_error(2)
    fake_db = _FakeSession([row_ok, row_error])

    def _estricto(_db, row):
        if int(row.id) == 1:
            return 9001
        raise RuntimeError("fallo controlado")

    monkeypatch.setattr(
        pagos_con_errores_routes,
        "pago_con_error_ya_cargado_estricto",
        _estricto,
    )

    out = limpiar_pagos_con_error_ya_cargados(
        payload=LimpiarYaCargadosBody(ids=[1, 2]),
        db=fake_db,
        current_user=_fake_user(),
    )

    assert out["eliminados"] == 1
    assert out["detalles"] == [
        {
            "pago_con_error_id": 1,
            "pago_id": 9001,
            "cedula": row_ok.cedula_cliente,
            "prestamo_id": row_ok.prestamo_id,
            "numero_documento": row_ok.numero_documento,
        }
    ]
    assert len(out["errores"]) == 1
    assert fake_db.deleted == [row_ok]
    assert fake_db.rollbacks == 0
    assert fake_db.savepoints_committed == 1
    assert fake_db.savepoints_rolled_back == 1


def test_mover_retiene_pago_con_error_si_falla_cascada_cuotas(monkeypatch):
    row = _fake_pago_con_error(10, prestamo_id=202)
    fake_db = _FakeSession([row])

    monkeypatch.setattr(
        pagos_con_errores_routes,
        "pago_con_error_ya_cargado_estricto",
        lambda _db, _row: None,
    )
    monkeypatch.setattr(
        pagos_con_errores_routes,
        "numero_documento_ya_registrado",
        lambda *_args, **_kwargs: False,
    )
    monkeypatch.setattr(
        pagos_con_errores_routes,
        "resolver_cedula_almacenada_en_clientes",
        lambda _db, _cedula: "V12345678",
    )

    def _fallar_cascada(_pago, _db):
        raise RuntimeError("cuota bloqueada")

    api_module = types.ModuleType("app.api")
    v1_module = types.ModuleType("app.api.v1")
    endpoints_module = types.ModuleType("app.api.v1.endpoints")
    pagos_module = types.ModuleType("app.api.v1.endpoints.pagos")
    pagos_module._aplicar_pago_a_cuotas_interno = _fallar_cascada
    api_module.v1 = v1_module
    v1_module.endpoints = endpoints_module
    endpoints_module.pagos = pagos_module
    monkeypatch.setitem(sys.modules, "app.api", api_module)
    monkeypatch.setitem(sys.modules, "app.api.v1", v1_module)
    monkeypatch.setitem(sys.modules, "app.api.v1.endpoints", endpoints_module)
    monkeypatch.setitem(sys.modules, "app.api.v1.endpoints.pagos", pagos_module)

    out = mover_a_pagos_normales(
        payload=EliminarPorDescargaBody(ids=[10]),
        db=fake_db,
    )

    assert out["movidos"] == 0
    assert out["cuotas_aplicadas"] == 0
    assert any("cuotas: cuota bloqueada" in err for err in out["errores"])
    assert fake_db.deleted == []
    assert fake_db.rollbacks == 0
    assert fake_db.savepoints_rolled_back == 1
