# -*- coding: utf-8 -*-
"""
Recálculo de fechas de amortización: validación del body en lote y auditoría con usuario autenticado.

Ejecutar desde backend/:
  pytest tests/test_recalcular_fechas_amortizacion.py -v
"""
from __future__ import annotations

import os
import sys
from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest
from pydantic import ValidationError
from sqlalchemy import select

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.api.v1.endpoints.prestamos.routes import (  # noqa: E402
    RecalcularFechasAmortizacionLoteBody,
    _RECALCULAR_FECHAS_LOTE_MAX,
    _ejecutar_recalculo_fechas_amortizacion_por_id,
)
from app.core.database import SessionLocal  # noqa: E402
from app.models.auditoria import Auditoria  # noqa: E402
from app.models.cliente import Cliente  # noqa: E402
from app.models.cuota import Cuota  # noqa: E402
from app.models.prestamo import Prestamo  # noqa: E402
from app.models.user import User  # noqa: E402
from app.schemas.auth import UserResponse  # noqa: E402


def test_lote_body_rechaza_lista_vacia():
    with pytest.raises(ValidationError):
        RecalcularFechasAmortizacionLoteBody(prestamo_ids=[])


def test_lote_body_rechaza_mas_de_max_ids():
    ids = list(range(1, _RECALCULAR_FECHAS_LOTE_MAX + 2))
    assert len(ids) == _RECALCULAR_FECHAS_LOTE_MAX + 1
    with pytest.raises(ValidationError):
        RecalcularFechasAmortizacionLoteBody(prestamo_ids=ids)


def test_lote_body_acepta_exactamente_max_ids():
    ids = list(range(1, _RECALCULAR_FECHAS_LOTE_MAX + 1))
    assert len(ids) == _RECALCULAR_FECHAS_LOTE_MAX
    body = RecalcularFechasAmortizacionLoteBody(prestamo_ids=ids)
    assert body.prestamo_ids == ids


def _user_response_from_db_row(u: User) -> UserResponse:
    ca = u.created_at
    ua = getattr(u, "updated_at", None)
    ll = getattr(u, "last_login", None)
    return UserResponse(
        id=u.id,
        email=(u.email or "").strip(),
        nombre=(u.nombre or "").strip(),
        apellido="",
        cargo=u.cargo,
        rol=(u.rol or "viewer").strip(),
        is_active=bool(u.is_active),
        created_at=ca.isoformat(sep=" ") if ca else "",
        updated_at=ua.isoformat(sep=" ") if ua else None,
        last_login=ll.isoformat(sep=" ") if ll else None,
    )


@pytest.fixture(scope="function")
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.mark.db
def test_ejecutar_recalculo_auditoria_usuario_id_coincide_con_current_user(db, monkeypatch):
    """
    Tras recalcular, la fila de auditoría usa el id del usuario de sesión (vía _audit_user_id),
    no un usuario arbitrario. commit se sustituye por flush para no persistir en BD real.
    """
    u = db.scalars(select(User).where(User.is_active.is_(True)).order_by(User.id).limit(1)).first()
    if u is None:
        pytest.skip("No hay usuarios activos en BD para enlazar auditoría.")

    def _commit_es_flush() -> None:
        db.flush()

    monkeypatch.setattr(db, "commit", _commit_es_flush)

    cedula = f"VRECALC{datetime.now().strftime('%H%M%S%f')}"
    cliente = Cliente(
        cedula=cedula,
        nombres="Test recalc fechas amort",
        telefono="0000000000",
        email=f"{cedula.lower()}@test.local",
        direccion="Calle Test",
        fecha_nacimiento=date(1990, 1, 1),
        ocupacion="Test",
        estado="ACTIVO",
        usuario_registro="test@test.local",
        notas="test_recalcular_fechas_amortizacion",
    )
    db.add(cliente)
    db.flush()

    hoy = date.today()
    fa = datetime.combine(hoy, datetime.min.time())
    prestamo = Prestamo(
        cliente_id=cliente.id,
        cedula=cliente.cedula,
        nombres=cliente.nombres,
        total_financiamiento=Decimal("600.00"),
        fecha_requerimiento=hoy - timedelta(days=1),
        modalidad_pago="MENSUAL",
        numero_cuotas=3,
        cuota_periodo=Decimal("200.00"),
        producto="Test recalc",
        analista="test@test.local",
        estado="APROBADO",
        fecha_aprobacion=fa,
        fecha_base_calculo=hoy,
    )
    db.add(prestamo)
    db.flush()

    for n in range(1, 4):
        vto = hoy + timedelta(days=30 * n)
        db.add(
            Cuota(
                prestamo_id=prestamo.id,
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
        )
    db.flush()

    current = _user_response_from_db_row(u)
    _ejecutar_recalculo_fechas_amortizacion_por_id(db, prestamo.id, current)

    audit = db.scalars(
        select(Auditoria)
        .where(
            Auditoria.accion == "RECALCULO_FECHAS_AMORTIZACION",
            Auditoria.entidad == "prestamos",
            Auditoria.entidad_id == prestamo.id,
        )
        .order_by(Auditoria.id.desc())
        .limit(1)
    ).first()

    assert audit is not None, "Debe insertarse una fila en auditoria tras el recálculo."
    assert audit.usuario_id == u.id, "usuario_id debe corresponder al usuario de la sesión (tabla usuarios)."
