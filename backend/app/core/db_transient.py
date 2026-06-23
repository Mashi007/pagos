"""
Reintentos ante errores transitorios de Postgres (Render: SSL cerrada, reset, etc.).
"""
from __future__ import annotations

import logging
from typing import Any, Callable, TypeVar

from sqlalchemy.exc import DBAPIError, OperationalError
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

T = TypeVar("T")


def is_transient_operational_error(exc: BaseException) -> bool:
    msg = str(exc).lower()
    if "ssl connection has been closed" in msg:
        return True
    if "server closed the connection unexpectedly" in msg:
        return True
    if "connection reset by peer" in msg:
        return True
    if "could not receive data from server" in msg:
        return True
    if "connection already closed" in msg:
        return True
    if "broken pipe" in msg:
        return True
    if isinstance(exc, OperationalError):
        orig = getattr(exc, "orig", None)
        if orig is not None and orig is not exc:
            return is_transient_operational_error(orig)
    return False


def invalidate_db_session_connection(db: Session) -> None:
    try:
        db.rollback()
    except Exception:
        pass
    try:
        db.connection().invalidate()
    except Exception:
        pass


def run_db_with_transient_retry(
    db: Session,
    fn: Callable[[], T],
    *,
    attempts: int = 2,
    log_prefix: str = "[DB]",
) -> T:
    last: BaseException | None = None
    for attempt in range(max(1, attempts)):
        try:
            return fn()
        except (OperationalError, DBAPIError) as e:
            last = e
            if attempt + 1 >= attempts or not is_transient_operational_error(e):
                raise
            logger.warning(
                "%s error transitorio (reintento %s/%s): %s",
                log_prefix,
                attempt + 1,
                attempts,
                e,
            )
            invalidate_db_session_connection(db)
    if last is not None:
        raise last
    raise RuntimeError("run_db_with_transient_retry: sin resultado")
