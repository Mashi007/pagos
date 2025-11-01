"""
Sistema de cache inteligente para analistas
"""

import logging
from datetime import datetime, timedelta
from functools import wraps
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# Cache simple en memoria
_cache: Dict[str, Any] = {}
_cache_timestamps: Dict[str, datetime] = {}


def cache_result(ttl_seconds: int = 300):
    """Decorador para cachear resultados con TTL"""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generar clave de cache
            cache_key = f"{func.__name__}_{hash(str(args) + str(kwargs))}"

            # Verificar si existe en cache y no ha expirado
            if cache_key in _cache:
                timestamp = _cache_timestamps.get(cache_key)
                if timestamp and datetime.now() - timestamp < timedelta(seconds=ttl_seconds):
                    logger.debug(f"Cache hit para {cache_key}")
                    return _cache[cache_key]

            # Ejecutar función y cachear resultado
            result = func(*args, **kwargs)
            _cache[cache_key] = result
            _cache_timestamps[cache_key] = datetime.now()

            logger.debug(f"Resultado cacheado para {cache_key}")
            return result

        return wrapper

    return decorator


def generate_cache_key(
    activo: Optional[bool] = None,
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
) -> str:
    """
    Generar clave de cache para consultas de analistas

    Args:
        activo: Filtro de estado activo
        search: Término de búsqueda
        skip: Offset de paginación
        limit: Límite de resultados

    Returns:
        str: Clave de cache generada
    """
    key_parts = [
        f"activo_{activo}" if activo is not None else "activo_all",
        f"search_{search}" if search else "search_none",
        f"skip_{skip}",
        f"limit_{limit}",
    ]
    return "_".join(key_parts)


def clear_cache():
    """Limpiar todo el cache"""
    _cache.clear()
    _cache_timestamps.clear()
    logger.info("Cache limpiado completamente")


def clear_expired_cache():
    """Limpiar entradas expiradas del cache"""
    now = datetime.now()
    expired_keys = []

    for key, timestamp in _cache_timestamps.items():
        if now - timestamp > timedelta(hours=1):  # Limpiar entradas de más de 1 hora
            expired_keys.append(key)

    for key in expired_keys:
        _cache.pop(key, None)
        _cache_timestamps.pop(key, None)

    if expired_keys:
        logger.info(f"Limpiadas {len(expired_keys)} entradas expiradas del cache")
