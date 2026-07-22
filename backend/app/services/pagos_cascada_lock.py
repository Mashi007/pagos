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
