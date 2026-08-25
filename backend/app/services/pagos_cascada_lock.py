"""
Bloqueo transaccional por prestamo para operaciones de cascada / amortizacion.

Evita deadlocks entre PUT de pago, aplicar-cuotas y reset_y_reaplicar cuando
varios requests tocan las mismas filas de `cuotas` / `cuota_pagos` en distinto orden.

Usa pg_advisory_xact_lock (se libera al commit/rollback). Reentrante en la misma
transaccion.
"""
from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Namespace distinto al de conciliar cartera (887766560).
_LOCK_NS_CASCADA_PRESTAMO = 887766561


def adquirir_lock_cascada_prestamo(db: Session, prestamo_id: int) -> None:
    """
    Serializa mutaciones de amortizacion del prestamo en PostgreSQL.

    En motores que no sean Postgres (p. ej. tests SQLite) no hace nada.
    """
    bind = db.get_bind()
    if bind is None or bind.dialect.name != "postgresql":
        return
    try:
        pid = int(prestamo_id)
    except (TypeError, ValueError):
        return
    if pid <= 0 or pid > 2147483647:
        return
    db.execute(
        text("SELECT pg_advisory_xact_lock(:ns, :pid)"),
        {"ns": _LOCK_NS_CASCADA_PRESTAMO, "pid": pid},
    )
    logger.debug("Lock cascada adquirido prestamo_id=%s", pid)


def adquirir_lock_cascada_prestamo_con_timeout(
    db: Session, prestamo_id: int, *, timeout_ms: int = 15000
) -> Optional[str]:
    """
    Igual que adquirir_lock_cascada_prestamo pero con lock_timeout local.
    Si otra transaccion retiene el lock (p. ej. mover-a-pagos en curso),
    retorna mensaje en lugar de entrar en deadlock / espera indefinida.
    """
    bind = db.get_bind()
    if bind is None or bind.dialect.name != "postgresql":
        return None
    try:
        pid = int(prestamo_id)
    except (TypeError, ValueError):
        return "Prestamo invalido para bloqueo de cascada."
    if pid <= 0 or pid > 2147483647:
        return "Prestamo invalido para bloqueo de cascada."
    ms = max(1000, min(int(timeout_ms), 120000))
    try:
        db.execute(text(f"SET LOCAL lock_timeout = '{ms}'"))
        db.execute(
            text("SELECT pg_advisory_xact_lock(:ns, :pid)"),
            {"ns": _LOCK_NS_CASCADA_PRESTAMO, "pid": pid},
        )
        # No limitar el resto de la cascada (solo la espera del advisory).
        db.execute(text("SET LOCAL lock_timeout = '0'"))
        logger.debug(
            "Lock cascada adquirido (timeout=%sms) prestamo_id=%s", ms, pid
        )
        return None
    except Exception as exc:
        msg = str(exc).lower()
        if (
            "lock timeout" in msg
            or "canceling statement due to lock timeout" in msg
            or "deadlock detected" in msg
        ):
            logger.warning(
                "Lock cascada no disponible prestamo_id=%s timeout_ms=%s: %s",
                pid,
                ms,
                exc,
            )
            try:
                db.rollback()
            except Exception:
                pass
            return (
                "Otra aplicación a cuotas está en curso para este préstamo "
                "(p. ej. mover a cartera). Espere a que termine e intente de nuevo."
            )
        raise


def intentar_lock_cascada_prestamo(db: Session, prestamo_id: int) -> Optional[str]:
    """
    Variante no bloqueante. Retorna mensaje de error si no se pudo adquirir; None si OK.
    """
    bind = db.get_bind()
    if bind is None or bind.dialect.name != "postgresql":
        return None
    try:
        pid = int(prestamo_id)
    except (TypeError, ValueError):
        return "Prestamo invalido para bloqueo de cascada."
    if pid <= 0 or pid > 2147483647:
        return "Prestamo invalido para bloqueo de cascada."
    acquired = db.execute(
        text("SELECT pg_try_advisory_xact_lock(:ns, :pid)"),
        {"ns": _LOCK_NS_CASCADA_PRESTAMO, "pid": pid},
    ).scalar()
    if acquired:
        return None
    return (
        "Otra aplicacion a cuotas esta en curso para este prestamo. "
        "Espere un momento y vuelva a intentar."
    )
