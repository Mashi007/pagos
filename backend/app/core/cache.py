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
# NO inicializar MemoryCache aquí para evitar warning innecesario
# Se inicializará solo si Redis no está disponible
cache_backend: CacheBackend = None  # type: ignore

# ============================================================================
# FUNCIONES HELPER PARA INICIALIZACIÓN DE REDIS - Refactorización
# ============================================================================


def _construir_redis_url_con_password(redis_url: str, password: str) -> str:
    """
    Construye URL de Redis con password para Render.com.
    Retorna URL con password agregado.
    """
    if redis_url.startswith("redis://"):
        # Remover protocolo
        url_without_protocol = redis_url.replace("redis://", "")

        # Separar host:port y db (si existe)
        if "/" in url_without_protocol:
            host_port, db = url_without_protocol.split("/", 1)
        else:
            host_port = url_without_protocol
            db = "0"

        # Construir URL con password: redis://default:password@host:port/db
        # Render.com usa 'default' como usuario
        return f"redis://default:{password}@{host_port}/{db}"
    return redis_url


def _normalizar_redis_url(redis_url: str) -> str:
    """
    Normaliza URL de Redis agregando /0 si no tiene base de datos.
    Retorna URL normalizada.
    """
    if not redis_url.endswith("/0") and "/" not in redis_url.replace("redis://", ""):
        if not redis_url.endswith("/"):
            return f"{redis_url}/0"
    return redis_url


def _crear_cliente_redis_desde_url(redis_url: str) -> Any:
    """
    Crea cliente Redis desde URL.
    Retorna cliente Redis o lanza excepción.
    """
    import redis

    from app.core.config import settings

    return redis.from_url(
        redis_url,
        decode_responses=False,
        socket_timeout=settings.REDIS_SOCKET_TIMEOUT,
        socket_connect_timeout=settings.REDIS_SOCKET_TIMEOUT,
        retry_on_timeout=True,
        health_check_interval=30,
    )


def _crear_cliente_redis_desde_componentes() -> Any:
    """
    Crea cliente Redis desde componentes individuales (HOST/PORT/DB).
    Retorna cliente Redis.
    """
    import redis

    from app.core.config import settings

    return redis.Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        db=settings.REDIS_DB,
        password=settings.REDIS_PASSWORD,
        decode_responses=False,
        socket_timeout=settings.REDIS_SOCKET_TIMEOUT,
    )


def _intentar_conexion_redis_con_autenticacion(redis_url: str) -> Any:
    """
    Intenta conectar a Redis con manejo de errores de autenticación.
    Retorna cliente Redis o lanza excepción.
    """
    import redis

    from app.core.config import settings

    try:
        redis_client = _crear_cliente_redis_desde_url(redis_url)
        logger.debug("Cliente Redis creado")

        # Test de conexión inmediato
        redis_client.ping()
        logger.debug("Test de conexión a Redis exitoso")
        return redis_client

    except (redis.AuthenticationError, redis.ResponseError) as auth_err:
        # Si falla por autenticación, intentar con password si está disponible
        error_msg = str(auth_err)
        if (
            "NOAUTH" in error_msg
            or "Authentication" in error_msg
            or "authentication" in error_msg.lower()
            or isinstance(auth_err, redis.AuthenticationError)
        ):
            logger.debug("Intentando reconectar con password...")
            if settings.REDIS_PASSWORD and "@" not in redis_url:
                logger.warning(f"⚠️ Error de autenticación Redis: {auth_err}")
                logger.debug("Intentando con password desde REDIS_PASSWORD...")
                # Reconstruir URL con password
                if redis_url.startswith("redis://"):
                    url_parts = redis_url.replace("redis://", "").split(":")
                    if len(url_parts) >= 2:
                        host = url_parts[0]
                        port_db = ":".join(url_parts[1:])
                        if "/" not in port_db:
                            port_db = f"{port_db}/0"
                        redis_url_with_pass = f"redis://default:{settings.REDIS_PASSWORD}@{host}:{port_db}"
                        redis_client = _crear_cliente_redis_desde_url(redis_url_with_pass)
                        redis_client.ping()
                        logger.debug("Conexión a Redis exitosa con password")
                        return redis_client
        raise

    except Exception as conn_err:
        logger.error(f"❌ Error de conexión Redis: {type(conn_err).__name__}: {str(conn_err)[:100]}")
        raise


def _preparar_redis_url() -> str:
    """
    Prepara URL de Redis desde configuración.
    Retorna URL de Redis preparada.
    """
    from app.core.config import settings

    redis_url = settings.REDIS_URL

    # Manejar URLs de Render.com que pueden venir sin password
    if settings.REDIS_PASSWORD and "@" not in redis_url:
        redis_url = _construir_redis_url_con_password(redis_url, settings.REDIS_PASSWORD)
        logger.debug("Configurando Redis con password desde REDIS_PASSWORD")
    elif "@" not in redis_url:
        redis_url = _normalizar_redis_url(redis_url)
        logger.debug("Conectando a Redis sin autenticación")

    # Log de URL (sin mostrar password completo) - solo en debug
    if "@" in redis_url:
        safe_url = redis_url.split("@")[0].split(":")[0] + ":***@" + redis_url.split("@")[1]
        logger.debug(f"Conectando a Redis: {safe_url}")
    else:
        logger.debug(f"Conectando a Redis: {redis_url}")

    return redis_url


def _inicializar_redis_desde_url() -> Any:
    """
    Inicializa Redis usando REDIS_URL.
    Retorna cliente Redis.
    """
    from app.core.config import settings

    logger.debug("Usando REDIS_URL para conexión...")
    redis_url = _preparar_redis_url()
    logger.debug("Creando cliente Redis...")
    return _intentar_conexion_redis_con_autenticacion(redis_url)


def _inicializar_redis_desde_componentes() -> Any:
    """
    Inicializa Redis usando componentes individuales (HOST/PORT/DB).
    Retorna cliente Redis.
    """
    from app.core.config import settings

    logger.debug("Usando componentes individuales (REDIS_HOST/PORT/DB) para conexión...")
    logger.debug(f"Host: {settings.REDIS_HOST}, Port: {settings.REDIS_PORT}, DB: {settings.REDIS_DB}")

    redis_client = _crear_cliente_redis_desde_componentes()
    logger.debug("Cliente Redis creado")

    # Test de conexión
    redis_client.ping()
    logger.debug("Test de conexión a Redis exitoso")

    return redis_client


def _crear_clase_redis_cache(redis_client: Any) -> type:
    """
    Crea clase RedisCache con el cliente proporcionado.
    Retorna clase RedisCache.
    """
    import redis

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

    return RedisCache


def _log_error_redis_detallado(e: Exception) -> None:
    """
    Registra error detallado de inicialización de Redis.
    """
    from app.core.config import settings

    error_msg = str(e)
    error_type = type(e).__name__

    if "NOAUTH" in error_msg or "Authentication" in error_msg or "authentication" in error_msg.lower():
        logger.warning("⚠️ Redis requiere autenticación pero no se proporcionó password")
        logger.info("   Diagnóstico:")
        logger.info(f"   - REDIS_URL configurada: {'Sí' if settings.REDIS_URL else 'No'}")
        if settings.REDIS_URL:
            safe_url = settings.REDIS_URL.split("@")[0] if "@" in settings.REDIS_URL else settings.REDIS_URL
            logger.info(f"   - REDIS_URL: {safe_url}")
        logger.info(f"   - REDIS_PASSWORD configurada: {'Sí' if settings.REDIS_PASSWORD else 'No'}")
        logger.info("   Soluciones:")
        logger.info("   1. Agregar REDIS_PASSWORD en variables de entorno de Render")
        logger.info("   2. O usar URL completa: redis://default:password@host:port/db")
        logger.info("   3. Verificar en Render Dashboard > Redis > Internal Redis URL (incluye password)")
    elif "Connection refused" in error_msg or "Name or service not known" in error_msg or "timeout" in error_msg.lower():
        logger.warning(f"⚠️ No se pudo conectar a Redis: {error_type}")
        logger.info("   Diagnóstico:")
        logger.info(f"   - REDIS_URL: {settings.REDIS_URL or 'No configurada'}")
        logger.info(f"   - REDIS_HOST: {settings.REDIS_HOST}")
        logger.info(f"   - REDIS_PORT: {settings.REDIS_PORT}")
        logger.info("   Verificar:")
        logger.info("   1. Que Redis esté corriendo en Render")
        logger.info("   2. Que la URL sea correcta (copiar desde Render Dashboard)")
        logger.info("   3. Que el servicio Redis esté activo")
    else:
        logger.warning(f"⚠️ No se pudo conectar a Redis: {error_type}: {error_msg}")
        logger.info("   Diagnóstico:")
        logger.info(f"   - REDIS_URL: {settings.REDIS_URL or 'No configurada'}")
        logger.info(f"   - REDIS_PASSWORD: {'Configurada' if settings.REDIS_PASSWORD else 'No configurada'}")
        logger.info(f"   - Error completo: {error_msg}")

    logger.warning("   ⚠️ Usando MemoryCache como fallback - NO recomendado para producción con múltiples workers")
    logger.info("   💡 Para resolver: Verificar configuración de Redis en Render Dashboard")

    logger.info("=" * 80)
    logger.info("📋 RESUMEN DEL DIAGNÓSTICO:")
    logger.info("=" * 80)
    logger.info(
        f"   - Redis instalado: {'Sí' if 'redis' in str(e) or 'ImportError' not in str(type(e)) else 'No (ImportError)'}"
    )
    logger.info(f"   - REDIS_URL configurada: {'Sí' if settings.REDIS_URL else 'No'}")
    logger.info(f"   - REDIS_PASSWORD configurada: {'Sí' if settings.REDIS_PASSWORD else 'No'}")
    logger.info(f"   - Error final: {type(e).__name__}: {str(e)[:200]}")
    logger.info("=" * 80)


# Logs de diagnóstico más concisos - solo mostrar resumen en producción
try:
    logger.debug("🔍 Iniciando diagnóstico de Redis...")
    import redis

    logger.debug(f"✅ Módulo redis importado. Versión: {redis.__version__ if hasattr(redis, '__version__') else 'N/A'}")

    from app.core.config import settings

    logger.debug("✅ Settings importado")

    # Solo mostrar configuración detallada en modo debug
    logger.debug(
        f"Redis config - URL: {bool(settings.REDIS_URL)}, Host: {settings.REDIS_HOST}, Port: {settings.REDIS_PORT}, DB: {settings.REDIS_DB}"
    )

    # ✅ CONFIGURACIÓN DESDE VARIABLES DE ENTORNO
    # Prioridad: REDIS_URL > REDIS_HOST/REDIS_PORT/REDIS_DB
    if settings.REDIS_URL:
        redis_client = _inicializar_redis_desde_url()
    else:
        redis_client = _inicializar_redis_desde_componentes()

    # Crear clase RedisCache y asignar a cache_backend
    RedisCache = _crear_clase_redis_cache(redis_client)
    cache_backend = RedisCache(redis_client)

    if not _cache_logs_shown:
        logger.info("✅ Redis cache inicializado correctamente")
        _cache_logs_shown = True
    else:
        logger.debug("Redis cache inicializado")

except ImportError:
    # Logs concisos cuando Redis no está instalado (caso común)
    if not _cache_logs_shown:
        logger.warning("⚠️ Redis no instalado - Usando MemoryCache (no recomendado para producción con múltiples workers)")
        logger.info("💡 Para usar Redis: pip install 'redis>=5.0.0,<6.0.0'")
        _cache_logs_shown = True
    else:
        logger.debug("Redis no instalado - usando MemoryCache")
    # Inicializar MemoryCache como fallback
    if cache_backend is None:
        cache_backend = MemoryCache()
except Exception as e:
    logger.error("=" * 80)
    logger.error("❌ ERROR: NO SE PUDO INICIALIZAR REDIS")
    logger.error("=" * 80)
    logger.error(f"   - Tipo de error: {type(e).__name__}")
    logger.error(f"   - Mensaje: {str(e)}")
    logger.error(f"   - Args: {e.args if hasattr(e, 'args') else 'N/A'}")
    if not _cache_logs_shown:
        _log_error_redis_detallado(e)
        _cache_logs_shown = True
    # Inicializar MemoryCache como fallback si Redis falló
    if cache_backend is None:
        cache_backend = MemoryCache()


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
                    # ✅ MEJORA: Reducir verbosidad en producción - solo loggear en DEBUG
                    logger.debug(f"✅ Cache HIT: {cache_key}")
                    return cached_result

                # Ejecutar función
                # ✅ MEJORA: Loggear cache miss solo en INFO o superior (no DEBUG)
                logger.info(f"❌ Cache MISS: {cache_key} - Ejecutando función...")
                result = await func(*args, **kwargs)

                # Guardar en cache
                cache_saved = cache_backend.set(cache_key, result, ttl=ttl)
                if cache_saved:
                    # ✅ MEJORA: Reducir verbosidad - solo loggear en DEBUG
                    logger.debug(f"💾 Cache guardado: {cache_key} (TTL: {ttl}s)")
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
                        # ✅ MEJORA: Reducir verbosidad en producción - solo loggear en DEBUG
                        logger.debug(f"✅ Cache HIT: {cache_key}")
                        return cached_result

                    # Ejecutar función
                    # ✅ MEJORA: Loggear cache miss solo en INFO o superior (no DEBUG)
                    logger.info(f"❌ Cache MISS: {cache_key} - Ejecutando función...")
                    result = func(*args, **kwargs)

                    # Guardar en cache
                    try:
                        cache_saved = cache_backend.set(cache_key, result, ttl=ttl)
                        if cache_saved:
                            # ✅ MEJORA: Reducir verbosidad - solo loggear en DEBUG
                            logger.debug(f"💾 Cache guardado: {cache_key} (TTL: {ttl}s)")
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
    try:
        # Implementación para MemoryCache
        if isinstance(cache_backend, MemoryCache):
            keys_to_delete = [key for key in cache_backend._cache.keys() if pattern in key]
            for key in keys_to_delete:
                cache_backend.delete(key)
            logger.debug(f"✅ Invalidado {len(keys_to_delete)} entradas de cache con patrón: {pattern}")
        # ✅ Implementación para RedisCache
        elif hasattr(cache_backend, 'client'):
            # Redis soporta búsqueda por patrón con SCAN o KEYS
            try:
                # Usar SCAN para búsqueda eficiente (mejor que KEYS en producción)
                cursor = 0
                keys_to_delete = []
                while True:
                    cursor, keys = cache_backend.client.scan(cursor, match=f"*{pattern}*", count=100)
                    keys_to_delete.extend([k.decode() if isinstance(k, bytes) else k for k in keys])
                    if cursor == 0:
                        break
                
                # Eliminar todas las claves encontradas
                if keys_to_delete:
                    cache_backend.client.delete(*keys_to_delete)
                    logger.debug(f"✅ Invalidado {len(keys_to_delete)} entradas de cache en Redis con patrón: {pattern}")
                else:
                    logger.debug(f"ℹ️  No se encontraron claves de cache con patrón: {pattern}")
            except Exception as redis_error:
                # Fallback a KEYS si SCAN no está disponible (versiones antiguas de Redis)
                try:
                    keys_to_delete = cache_backend.client.keys(f"*{pattern}*")
                    if keys_to_delete:
                        cache_backend.client.delete(*keys_to_delete)
                        logger.debug(f"✅ Invalidado {len(keys_to_delete)} entradas de cache en Redis (usando KEYS) con patrón: {pattern}")
                except Exception as keys_error:
                    logger.warning(f"⚠️  Error invalidando cache en Redis: {keys_error}")
        else:
            logger.warning(f"⚠️  Invalidación por patrón no implementada para este backend: {type(cache_backend)}")
    except Exception as e:
        logger.warning(f"⚠️  Error en invalidate_cache: {e}")
