# -*- coding: utf-8 -*-
"""Mensajes y detección de errores de sesión al reaplicar cascada."""

from __future__ import annotations

from sqlalchemy.exc import IntegrityError, PendingRollbackError

from app.services.pagos_aplicacion_prestamo import (
    _db_error_aborta_transaccion,
    detalle_excepcion_db,
)


def test_detalle_excepcion_db_prioriza_causa_psycopg():
    raiz = IntegrityError("stmt", {}, Exception("duplicate key value violates unique constraint"))
    envoltorio = PendingRollbackError(
        "This Session's transaction has been rolled back due to a previous exception during flush."
    )
    envoltorio.__cause__ = raiz

    msg = detalle_excepcion_db(envoltorio)

    assert "duplicate key" in msg
    assert "Causa:" in msg


def test_db_error_aborta_transaccion_con_pending_rollback():
    assert _db_error_aborta_transaccion(PendingRollbackError("rolled back"))


def test_db_error_aborta_transaccion_con_sqlalchemy():
    assert _db_error_aborta_transaccion(IntegrityError("x", {}, Exception("fk")))


def test_db_error_no_aborta_value_error_negocio():
    assert not _db_error_aborta_transaccion(ValueError("Suma aplicada supera monto"))
