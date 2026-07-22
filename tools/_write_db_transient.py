from pathlib import Path
content = r'''
"""
Reintentos ante errores transitorios de Postgres (Render: SSL cerrada, reset, deadlock).
"""
from __future__ import annotations

import logging
import random
import time
from typing import Callable, TypeVar

from sqlalchemy.exc import DBAPIError, OperationalError
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

T = TypeVar("T")


def _pgcode(exc: BaseException) -> str | None:
    orig = getattr(exc, "orig", None)
    if orig is not None and orig is not exc:
        code = getattr(orig, "pgcode", None) or getattr(orig, "sqlstate", None)
        if code:
            return str(code)
        nested = _pgcode(orig)
        if nested:
            return nested
    code = getattr(exc, "pgcode", None) or getattr(exc, "sqlstate", None)
    return str(code) if code else None


def is_deadlock_error(exc: BaseException) -> bool:
    """True si Postgres aborto por deadlock (40P01) o serialization failure (40001)."""
    code = _pgcode(exc)
    if code in ("40P01", "40001"):
        return True
    msg = str(exc).lower()
    if "deadlock detected" in msg:
        return True
    if "could not serialize access" in msg:
        return True
    if isinstance(exc, (OperationalError, DBAPIError)):
        orig = getattr(exc, "orig", None)
        if orig is not None and orig is not exc:
            return is_deadlock_error(orig)
    return False


def is_transient_operational_error(exc: BaseException) -> bool:
    if is_deadlock_error(exc):
        return True
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


def run_with_deadlock_retry(
    db: Session,
    fn: Callable[[], T],
    *,
    attempts: int = 3,
    log_prefix: str = "[CASCADA]",
) -> T:
    """
    Reintenta fn ante deadlock / serialization failure.

    Hace rollback (sin invalidar el pool) entre intentos; el caller debe
    re-adquirir locks advisory dentro de fn.
    """
    last: BaseException | None = None
    max_attempts = max(1, attempts)
    for attempt in range(max_attempts):
        try:
            return fn()
        except (OperationalError, DBAPIError) as e:
            last = e
            if attempt + 1 >= max_attempts or not is_deadlock_error(e):
                raise
            logger.warning(
                "%s deadlock (reintento %s/%s): %s",
                log_prefix,
                attempt + 1,
                max_attempts,
                e,
            )
            try:
                db.rollback()
            except Exception:
                pass
            time.sleep(0.05 + random.random() * 0.15 * (attempt + 1))
    if last is not None:
        raise last
    raise RuntimeError("run_with_deadlock_retry: sin resultado")
'''
Path('backend/app/core/db_transient.py').write_text(content.lstrip('\n'), encoding='utf-8')
print('ok', Path('backend/app/core/db_transient.py').stat().st_size)
