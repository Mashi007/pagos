"""
Almacén de rate limit: Redis (distribuido) o memoria (fallback).
Cuando REDIS_URL está configurada, se usa Redis para que múltiples instancias
del backend compartan los mismos límites por IP. Si no hay Redis, se usa
el diccionario en memoria (comportamiento por proceso).
"""
import logging
import time
from typing import Optional

logger = logging.getLogger(__name__)

_redis_client: Optional["Redis"] = None


def get_redis_client():  # noqa: ANN201
    """Devuelve cliente Redis si REDIS_URL está configurada y la conexión funciona."""
    global _redis_client
    if _redis_client is not None:
        return _redis_client
    try:
        from app.core.config import settings
        if not (getattr(settings, "REDIS_URL", None) or "").strip():
            return None
        import redis
        client = redis.from_url(settings.REDIS_URL, decode_responses=True)
        client.ping()
        _redis_client = client
        logger.info("Rate limit: usando Redis para límites distribuidos.")
        return _redis_client
    except Exception as e:
        logger.debug("Rate limit: Redis no disponible (%s), usando memoria.", e)
        return None


def check_rate_limit_redis(
    key_prefix: str,
    ip: str,
    window_sec: int,
    max_count: int,
    detail_429: str,
) -> None:
    """
    Comprueba límite con ventana fija en Redis. Lanza HTTPException 429 si se supera.
    key_prefix: ej. "ec_solicitar", "ec_verificar"
    """
    from fastapi import HTTPException
    client = get_redis_client()
    if not client:
        return
    key = f"rate_limit:{key_prefix}:{ip}"
    try:
        pipe = client.pipeline()
        pipe.incr(key)
        pipe.ttl(key)
        incr_result, ttl = pipe.execute()
        if ttl == -1:
            client.expire(key, window_sec)
        if incr_result > max_count:
            raise HTTPException(status_code=429, detail=detail_429)
    except HTTPException:
        raise
    except Exception as e:
        logger.warning("Rate limit Redis error: %s", e)
        # En fallo de Redis no bloqueamos; el caller usará fallback en memoria
