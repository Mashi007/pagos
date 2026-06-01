"""
Cliente Redis/Valkey compartido con timeout corto y reintentos espaciados.

Evita bloquear peticiones HTTP si REDIS_URL apunta a un host inaccesible
(p. ej. URL externa con ipAllowList vacío). Usar siempre la URL **interna**
de Render (redis://red-...@...:6379) en pagos-backend.
"""
from __future__ import annotations

import logging
import os
import time
from typing import Any, Optional

logger = logging.getLogger(__name__)

_REDIS_CLIENT: Any = None
_REDIS_PROBE_BLOCKED_UNTIL: float = 0.0
_REDIS_NO_URL = object()


def _connect_timeout_sec() -> float:
    raw = os.environ.get("REDIS_CONNECT_TIMEOUT_SEC", "2")
    try:
        return max(0.5, min(float(raw), 10.0))
    except (TypeError, ValueError):
        return 2.0


def _retry_interval_sec() -> float:
    raw = os.environ.get("REDIS_RETRY_INTERVAL_SEC", "60")
    try:
        return max(10.0, min(float(raw), 600.0))
    except (TypeError, ValueError):
        return 60.0


def _mark_unavailable(reason: str, *, retry: bool) -> None:
    global _REDIS_CLIENT, _REDIS_PROBE_BLOCKED_UNTIL
    _REDIS_CLIENT = _REDIS_NO_URL
    if retry:
        interval = _retry_interval_sec()
        _REDIS_PROBE_BLOCKED_UNTIL = time.monotonic() + interval
        logger.warning(
            "Redis no disponible (%s); fallback en memoria. Reintento en %ss.",
            reason,
            int(interval),
        )
    else:
        _REDIS_PROBE_BLOCKED_UNTIL = time.monotonic() + 3600.0
        logger.info("REDIS_URL no configurada; rate limit/caché en memoria por proceso.")


def get_redis_client():  # noqa: ANN201
    """
    Cliente Redis si REDIS_URL es válida y responde a PING.
    None si no hay URL, falló la conexión o aún no toca reintentar.
    """
    global _REDIS_CLIENT, _REDIS_PROBE_BLOCKED_UNTIL

    if _REDIS_CLIENT is _REDIS_NO_URL:
        if time.monotonic() < _REDIS_PROBE_BLOCKED_UNTIL:
            return None
        _REDIS_CLIENT = None

    if _REDIS_CLIENT is not None:
        return _REDIS_CLIENT

    try:
        from app.core.config import settings

        url = (getattr(settings, "REDIS_URL", None) or "").strip()
        if not url:
            _mark_unavailable("REDIS_URL vacía", retry=False)
            return None

        if url.startswith("rediss://") and "onrender.com" in url:
            logger.warning(
                "REDIS_URL parece URL externa (rediss). En Render use la Internal Key Value URL "
                "(redis://red-... sin TLS) en pagos-backend."
            )

        import redis

        timeout = _connect_timeout_sec()
        client = redis.from_url(
            url,
            decode_responses=True,
            socket_connect_timeout=timeout,
            socket_timeout=timeout,
        )
        client.ping()
        _REDIS_CLIENT = client
        logger.info("Redis conectado (socket_timeout=%ss).", timeout)
        return _REDIS_CLIENT
    except Exception as e:
        _mark_unavailable(str(e)[:200], retry=True)
        return None
