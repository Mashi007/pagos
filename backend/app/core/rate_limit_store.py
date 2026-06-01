"""
Almacén de rate limit: Redis (distribuido) o memoria (fallback).
Cuando REDIS_URL está configurada, se usa Redis para que múltiples instancias
del backend compartan los mismos límites por IP. Si no hay Redis, se usa
el diccionario en memoria (comportamiento por proceso).
"""
import logging

from app.core.redis_client import get_redis_client

logger = logging.getLogger(__name__)


def check_rate_limit_redis(
    key_prefix: str,
    ip: str,
    window_sec: int,
    max_count: int,
    detail_429: str,
) -> bool:
    """
    Comprueba límite con ventana fija en Redis. Lanza HTTPException 429 si se supera.
    key_prefix: ej. "ec_solicitar", "ec_verificar"

    Retorna True si el límite se aplicó vía Redis (petición contada).
    Retorna False si no hay cliente Redis (el caller debe usar fallback en memoria).
    """
    from fastapi import HTTPException

    client = get_redis_client()
    if not client:
        return False
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
        return True
    except HTTPException:
        raise
    except Exception as e:
        logger.warning("Rate limit Redis error: %s", e)
        # En fallo de Redis no bloqueamos; el caller usará fallback en memoria
        return False
