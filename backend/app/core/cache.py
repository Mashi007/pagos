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

    _warning_logged = False  # Variable de clase para evitar logs repetidos

    def __init__(self):
        self._cache: dict = {}
        if not MemoryCache._warning_logged:
            logger.warning("Usando MemoryCache - NO recomendado para producción con múltiples workers")
            MemoryCache._warning_logged = True

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


# Variable de módulo para evitar logs repetidos
_cache_logs_shown = False

# Intentar inicializar Redis, usar MemoryCache como fallback
cache_backend: CacheBackend = MemoryCache()

try:
    import redis

    from app.core.config import settings

    # ✅ CONFIGURACIÓN DESDE VARIABLES DE ENTORNO
    # Prioridad: REDIS_URL > REDIS_HOST/REDIS_PORT/REDIS_DB
    if settings.REDIS_URL:
        # Usar URL completa si está disponible
        redis_url = settings.REDIS_URL
        
        # ✅ MEJORA: Manejar URLs de Render.com que pueden venir sin password
        # Render.com puede proporcionar URLs en formato: redis://red-xxxxx:6379
        # Si no tiene password en la URL pero REDIS_PASSWORD está configurado, agregarlo
        # Si no tiene password, intentar conectar sin autenticación
        if settings.REDIS_PASSWORD and "@" not in redis_url:
            # Extraer componentes de la URL
            if redis_url.startswith("redis://"):
                # Remover protocolo
                url_without_protocol = redis_url.replace("redis://", "")
                
                # Separar host:port y db (si existe)
                if "/" in url_without_protocol:
                    host_port, db = url_without_protocol.split("/", 1)
                else:
                    host_port = url_without_protocol
                    db = str(settings.REDIS_DB)
                
                # Construir URL con password: redis://default:password@host:port/db
                # Render.com usa 'default' como usuario
                redis_url = f"redis://default:{settings.REDIS_PASSWORD}@{host_port}/{db}"
                logger.info(f"🔗 Configurando Redis con password desde REDIS_PASSWORD")
            else:
                # Si no es formato redis://, intentar agregar password de otra forma
                logger.warning(f"⚠️ Formato de REDIS_URL no reconocido: {redis_url[:20]}...")
        elif "@" not in redis_url:
            # ✅ NUEVO: Si no hay password configurado y la URL no tiene autenticación
            # Agregar /0 si no tiene base de datos especificada
            if not redis_url.endswith("/0") and "/" not in redis_url.replace("redis://", ""):
                if not redis_url.endswith("/"):
                    redis_url = f"{redis_url}/0"
            logger.info(f"🔗 Conectando a Redis sin autenticación (sin usuario/password)")
        
        # Log de URL (sin mostrar password completo)
        if "@" in redis_url:
            # Ocultar password en logs
            safe_url = redis_url.split("@")[0].split(":")[0] + ":***@" + redis_url.split("@")[1]
            logger.info(f"🔗 Conectando a Redis: {safe_url}")
        else:
            logger.info(f"🔗 Conectando a Redis: {redis_url}")
        
        # ✅ Intentar conexión sin password primero si no hay @ en la URL
        # Si falla, el error se capturará en el except general
        redis_client = redis.from_url(redis_url, decode_responses=False, socket_timeout=settings.REDIS_SOCKET_TIMEOUT)
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
    if not _cache_logs_shown:
        logger.info("✅ Redis cache inicializado correctamente")
        _cache_logs_shown = True

except ImportError:
    if not _cache_logs_shown:
        # Los logs de MemoryCache ya se mostraron en __init__, solo mostrar info adicional
        logger.info("   Para usar Redis en producción, instala: pip install 'redis>=5.0.0,<6.0.0'")
        _cache_logs_shown = True
except Exception as e:
    if not _cache_logs_shown:
        error_msg = str(e)
        error_type = type(e).__name__
        
        # ✅ MEJORA: Mensajes más específicos según el tipo de error
        if "NOAUTH" in error_msg or "Authentication" in error_msg:
            logger.warning(f"⚠️ Redis requiere autenticación pero no se proporcionó password")
            logger.info("   Opciones:")
            logger.info("   1. Agregar REDIS_PASSWORD en variables de entorno")
            logger.info("   2. O usar URL completa: redis://default:password@host:port")
        elif "Connection refused" in error_msg or "Name or service not known" in error_msg:
            logger.warning(f"⚠️ No se pudo conectar a Redis: {error_type}")
            logger.info("   Verificar que Redis esté corriendo y la URL sea correcta")
        else:
            logger.warning(f"⚠️ No se pudo conectar a Redis: {error_type}: {error_msg}")
        
        logger.info("   Usando MemoryCache como fallback")
        _cache_logs_shown = True


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
                    logger.info(f"✅ Cache HIT: {cache_key}")
                    return cached_result

                # Ejecutar función
                logger.info(f"❌ Cache MISS: {cache_key} - Ejecutando función...")
                result = await func(*args, **kwargs)

                # Guardar en cache
                cache_saved = cache_backend.set(cache_key, result, ttl=ttl)
                if cache_saved:
                    logger.info(f"💾 Cache guardado: {cache_key} (TTL: {ttl}s)")
                else:
                    logger.warning(f"⚠️  Error guardando en cache: {cache_key}")

                return result

            return async_wrapper
        else:

            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                try:
                    # Construir clave del cache
                    if key_prefix:
                        cache_key = f"{key_prefix}:{func.__name__}"
                    else:
                        cache_key = f"cache:{func.__name__}"

                    # Incluir argumentos en la clave (excluir db y current_user que son dependencias)
                    # Filtrar kwargs para excluir objetos que no se pueden serializar
                    cacheable_kwargs = {}
                    for key, value in kwargs.items():
                        # Excluir dependencias de FastAPI y objetos de sesión
                        if key not in ["db", "current_user"] and value is not None:
                            # Intentar serializar para verificar si es cacheable
                            try:
                                json.dumps(value, default=str)
                                cacheable_kwargs[key] = value
                            except (TypeError, ValueError):
                                # Si no se puede serializar, usar su representación string
                                cacheable_kwargs[key] = str(value)

                    # Filtrar args también (normalmente db y current_user están en kwargs, pero por si acaso)
                    cacheable_args = []
                    for arg in args:
                        # Excluir objetos de sesión y usuarios
                        if not hasattr(arg, "execute") and not hasattr(arg, "email"):
                            try:
                                json.dumps(arg, default=str)
                                cacheable_args.append(arg)
                            except (TypeError, ValueError):
                                cacheable_args.append(str(arg))

                    # Crear hash solo con argumentos cacheables
                    if cacheable_args or cacheable_kwargs:
                        import hashlib

                        try:
                            key_data = json.dumps(
                                {"args": cacheable_args, "kwargs": cacheable_kwargs}, sort_keys=True, default=str
                            )
                            key_hash = hashlib.md5(key_data.encode()).hexdigest()[:8]
                            cache_key = f"{cache_key}:{key_hash}"
                        except Exception as e:
                            logger.warning(
                                f"⚠️  Error construyendo clave de cache para {func.__name__}: {e}, usando clave sin hash"
                            )
                            # Continuar sin hash si hay error

                    # Intentar obtener del cache
                    cached_result = cache_backend.get(cache_key)
                    if cached_result is not None:
                        logger.info(f"✅ Cache HIT: {cache_key}")
                        return cached_result

                    # Ejecutar función
                    logger.info(f"❌ Cache MISS: {cache_key} - Ejecutando función...")
                    result = func(*args, **kwargs)

                    # Guardar en cache
                    try:
                        cache_saved = cache_backend.set(cache_key, result, ttl=ttl)
                        if cache_saved:
                            logger.info(f"💾 Cache guardado: {cache_key} (TTL: {ttl}s)")
                        else:
                            logger.warning(f"⚠️  Error guardando en cache: {cache_key}")
                    except Exception as e:
                        logger.error(f"❌ Error al guardar en cache {cache_key}: {e}", exc_info=True)
                        # Continuar aunque falle el cache

                    return result
                except Exception as e:
                    # Si hay error en el decorador, ejecutar función sin cache
                    logger.error(f"❌ Error en decorador de cache para {func.__name__}: {e}", exc_info=True)
                    logger.warning(f"⚠️  Ejecutando {func.__name__} sin cache debido a error")
                    return func(*args, **kwargs)

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
