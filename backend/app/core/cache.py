"""
Utilidades de cache
Preparación para implementación de Redis
Proporciona interfaz abstracta para cache
"""

import json
import logging
from functools import wraps
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


class CacheBackend:
    """Interfaz abstracta para backend de cache"""

    def get(self, key: str) -> Optional[Any]:
        """Obtener valor del cache"""
        raise NotImplementedError

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Guardar valor en cache"""
        raise NotImplementedError

    def delete(self, key: str) -> bool:
        """Eliminar valor del cache"""
        raise NotImplementedError

    def clear(self) -> bool:
        """Limpiar todo el cache"""
        raise NotImplementedError


class MemoryCache(CacheBackend):
    """
    Implementación de cache en memoria (fallback cuando Redis no está disponible)
    NO usar en producción con múltiples workers
    """

    def __init__(self):
        self._cache: dict = {}
        logger.warning("Usando MemoryCache - NO recomendado para producción con múltiples workers")

    def get(self, key: str) -> Optional[Any]:
        """Obtener valor del cache"""
        if key in self._cache:
            value, expiry = self._cache[key]
            if expiry is None or expiry > self._now():
                return value
            # Expiró, eliminar
            del self._cache[key]
        return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Guardar valor en cache"""
        expiry = (self._now() + ttl) if ttl else None
        self._cache[key] = (value, expiry)
        return True

    def delete(self, key: str) -> bool:
        """Eliminar valor del cache"""
        if key in self._cache:
            del self._cache[key]
            return True
        return False

    def clear(self) -> bool:
        """Limpiar todo el cache"""
        self._cache.clear()
        return True

    @staticmethod
    def _now() -> int:
        """Obtener timestamp actual"""
        import time

        return int(time.time())


# Intentar inicializar Redis, usar MemoryCache como fallback
cache_backend: CacheBackend = MemoryCache()

# Log inicial para diagnóstico
logger.info("🔍 Iniciando inicialización de cache...")

try:
    import redis

    from app.core.config import settings
    
    # Log para verificar que se está intentando conectar
    logger.info(f"🔍 REDIS_URL configurada: {bool(settings.REDIS_URL)}")
    if settings.REDIS_URL:
        logger.info(f"🔍 REDIS_URL valor: {settings.REDIS_URL[:50]}...")  # Primeros 50 caracteres

    # ✅ CONFIGURACIÓN DESDE VARIABLES DE ENTORNO
    # Prioridad: REDIS_URL > REDIS_HOST/REDIS_PORT/REDIS_DB
    if settings.REDIS_URL:
        # Usar URL completa si está disponible
        redis_url = settings.REDIS_URL
        # Si tiene password, incluirla en la URL
        if settings.REDIS_PASSWORD and "@" not in redis_url:
            # Extraer componentes de la URL si es necesario
            if redis_url.startswith("redis://"):
                parts = redis_url.replace("redis://", "").split("/")
                host_port = parts[0]
                db = parts[1] if len(parts) > 1 else str(settings.REDIS_DB)
                redis_url = f"redis://:{settings.REDIS_PASSWORD}@{host_port}/{db}"
        redis_client = redis.from_url(redis_url, decode_responses=False, socket_timeout=settings.REDIS_SOCKET_TIMEOUT)
        logger.info(f"🔗 Conectando a Redis usando REDIS_URL: {redis_url.split('@')[-1] if '@' in redis_url else redis_url}")
    else:
        # Usar componentes individuales
        redis_client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            password=settings.REDIS_PASSWORD,
            decode_responses=False,
            socket_timeout=settings.REDIS_SOCKET_TIMEOUT,
        )
        logger.info(f"🔗 Conectando a Redis: {settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}")

    # Test de conexión
    redis_client.ping()

    class RedisCache(CacheBackend):
        """Implementación de cache usando Redis"""

        def __init__(self, client: redis.Redis):
            self.client = client

        def get(self, key: str) -> Optional[Any]:
            """Obtener valor del cache"""
            try:
                value = self.client.get(key)
                if value:
                    return json.loads(value)
                return None
            except Exception as e:
                logger.error(f"Error obteniendo del cache: {e}")
                return None

        def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
            """Guardar valor en cache"""
            try:
                serialized = json.dumps(value)
                if ttl:
                    self.client.setex(key, ttl, serialized)
                else:
                    self.client.set(key, serialized)
                return True
            except Exception as e:
                logger.error(f"Error guardando en cache: {e}")
                return False

        def delete(self, key: str) -> bool:
            """Eliminar valor del cache"""
            try:
                return bool(self.client.delete(key))
            except Exception as e:
                logger.error(f"Error eliminando del cache: {e}")
                return False

        def clear(self) -> bool:
            """Limpiar todo el cache"""
            try:
                self.client.flushdb()
                return True
            except Exception as e:
                logger.error(f"Error limpiando cache: {e}")
                return False

    cache_backend = RedisCache(redis_client)
    logger.info("✅ Redis cache inicializado correctamente")

except ImportError:
    logger.error("⚠️ Redis no disponible (paquete no instalado), usando MemoryCache")
    logger.error("   Instala redis: pip install redis==5.0.1")
except Exception as e:
    logger.error(f"⚠️ ERROR al conectar a Redis: {type(e).__name__}: {str(e)}")
    logger.error(f"   REDIS_URL configurada: {bool(settings.REDIS_URL) if 'settings' in locals() else 'N/A'}")
    if 'settings' in locals() and settings.REDIS_URL:
        logger.error(f"   REDIS_URL valor: {settings.REDIS_URL[:80]}...")
    logger.error("   Usando MemoryCache como fallback")


def cache_result(ttl: int = 300, key_prefix: Optional[str] = None):
    """
    Decorador para cachear resultados de funciones (soporta sync y async)

    Args:
        ttl: Tiempo de vida del cache en segundos (default: 5 minutos)
        key_prefix: Prefijo para la clave del cache

    Ejemplo:
        @cache_result(ttl=600, key_prefix="dashboard")
        def get_dashboard_stats(...):  # Sync
            ...

        @cache_result(ttl=600, key_prefix="dashboard")
        async def get_dashboard_stats_async(...):  # Async
            ...
    """
    import asyncio
    import inspect

    def decorator(func: Callable) -> Callable:
        is_async = inspect.iscoroutinefunction(func)

        if is_async:

            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                # Construir clave del cache
                if key_prefix:
                    cache_key = f"{key_prefix}:{func.__name__}"
                else:
                    cache_key = f"cache:{func.__name__}"

                # Incluir argumentos en la clave
                if args or kwargs:
                    import hashlib

                    key_data = json.dumps({"args": str(args), "kwargs": str(kwargs)}, sort_keys=True)
                    key_hash = hashlib.md5(key_data.encode()).hexdigest()[:8]
                    cache_key = f"{cache_key}:{key_hash}"

                # Intentar obtener del cache
                cached_result = cache_backend.get(cache_key)
                if cached_result is not None:
                    logger.debug(f"Cache hit: {cache_key}")
                    return cached_result

                # Ejecutar función
                logger.debug(f"Cache miss: {cache_key}")
                result = await func(*args, **kwargs)

                # Guardar en cache
                cache_backend.set(cache_key, result, ttl=ttl)

                return result

            return async_wrapper
        else:

            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                # Construir clave del cache
                if key_prefix:
                    cache_key = f"{key_prefix}:{func.__name__}"
                else:
                    cache_key = f"cache:{func.__name__}"

                # Incluir argumentos en la clave
                if args or kwargs:
                    import hashlib

                    key_data = json.dumps({"args": str(args), "kwargs": str(kwargs)}, sort_keys=True)
                    key_hash = hashlib.md5(key_data.encode()).hexdigest()[:8]
                    cache_key = f"{cache_key}:{key_hash}"

                # Intentar obtener del cache
                cached_result = cache_backend.get(cache_key)
                if cached_result is not None:
                    logger.debug(f"Cache hit: {cache_key}")
                    return cached_result

                # Ejecutar función
                logger.debug(f"Cache miss: {cache_key}")
                result = func(*args, **kwargs)

                # Guardar en cache
                cache_backend.set(cache_key, result, ttl=ttl)

                return result

            return sync_wrapper

    return decorator


def invalidate_cache(pattern: str):
    """
    Invalidar cache por patrón (requiere implementación específica según backend)

    Args:
        pattern: Patrón para buscar claves a invalidar
    """
    # Implementación básica - solo para MemoryCache
    if isinstance(cache_backend, MemoryCache):
        keys_to_delete = [key for key in cache_backend._cache.keys() if pattern in key]
        for key in keys_to_delete:
            cache_backend.delete(key)
        logger.info(f"Invalidado {len(keys_to_delete)} entradas de cache con patrón: {pattern}")
    else:
        logger.warning("Invalidación por patrón no implementada para este backend")
