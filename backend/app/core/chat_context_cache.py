"""
Caché en memoria para el contexto del Chat AI.
Reduce la carga en BD cuando los datos cambian poco (TTL 90 segundos).
"""
import threading
import time
from typing import Optional

logger = __import__("logging").getLogger(__name__)

# TTL en segundos (1.5 minutos)
CHAT_CONTEXT_CACHE_TTL = 90

# Clave fija: el contexto es global (no por usuario)
_cache: dict[str, tuple[str, float]] = {}  # "context" -> (value, expires_at)
_lock = threading.Lock()


def get_cached_context() -> Optional[str]:
    """Devuelve el contexto cacheado si existe y no ha expirado."""
    with _lock:
        if "context" not in _cache:
            return None
        value, expires_at = _cache["context"]
        if time.monotonic() >= expires_at:
            del _cache["context"]
            return None
        return value


def set_cached_context(context: str) -> None:
    """Guarda el contexto en caché con TTL."""
    with _lock:
        _cache["context"] = (context, time.monotonic() + CHAT_CONTEXT_CACHE_TTL)
        logger.debug("Chat context cache: stored (TTL=%ds)", CHAT_CONTEXT_CACHE_TTL)


def invalidate_cache() -> None:
    """Invalida el caché (útil tras cambios en BD)."""
    with _lock:
        _cache.clear()
        logger.debug("Chat context cache: invalidated")
