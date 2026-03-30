"""
Servicio de caché para endpoints costosos
Usa Redis (si disponible) o en-memory (fallback)
"""
import json
import logging
from typing import Any, Dict, Optional
from datetime import datetime, timedelta
from functools import wraps

logger = logging.getLogger(__name__)

# Intentar usar Redis
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None

# Caché en memoria (fallback)
MEMORY_CACHE: Dict[str, tuple] = {}  # {key: (value, expiry_time)}


class CacheService:
    """Servicio de caché con Redis fallback a memoria."""
    
    def __init__(self, redis_url: Optional[str] = None):
        self.redis_client = None
        self.use_redis = False
        
        if REDIS_AVAILABLE and redis_url:
            try:
                self.redis_client = redis.from_url(redis_url)
                self.redis_client.ping()
                self.use_redis = True
                logger.info("✅ Redis conectado para caché")
            except Exception as e:
                logger.warning("Redis no disponible, usando caché en memoria: %s", e)
                self.use_redis = False
    
    def get(self, key: str) -> Optional[Any]:
        """Obtiene valor del caché."""
        if self.use_redis and self.redis_client:
            try:
                value = self.redis_client.get(key)
                return json.loads(value) if value else None
            except Exception as e:
                logger.warning("Error leyendo Redis: %s", e)
                return None
        else:
            # Caché en memoria
            if key in MEMORY_CACHE:
                value, expiry = MEMORY_CACHE[key]
                if datetime.now() < expiry:
                    return value
                else:
                    del MEMORY_CACHE[key]
            return None
    
    def set(self, key: str, value: Any, ttl_seconds: int = 300) -> bool:
        """Guarda valor en caché con TTL."""
        try:
            if self.use_redis and self.redis_client:
                self.redis_client.setex(key, ttl_seconds, json.dumps(value))
                return True
            else:
                # Caché en memoria
                MEMORY_CACHE[key] = (value, datetime.now() + timedelta(seconds=ttl_seconds))
                return True
        except Exception as e:
            logger.warning("Error escribiendo caché: %s", e)
            return False
    
    def delete(self, key: str) -> bool:
        """Elimina clave del caché."""
        try:
            if self.use_redis and self.redis_client:
                self.redis_client.delete(key)
                return True
            else:
                MEMORY_CACHE.pop(key, None)
                return True
        except Exception as e:
            logger.warning("Error eliminando caché: %s", e)
            return False
    
    def clear_pattern(self, pattern: str) -> int:
        """Elimina todas las claves que coincidan con patrón."""
        try:
            if self.use_redis and self.redis_client:
                keys = self.redis_client.keys(pattern)
                if keys:
                    return self.redis_client.delete(*keys)
                return 0
            else:
                # En memoria, eliminar por prefijo
                keys_to_delete = [k for k in MEMORY_CACHE.keys() if pattern in k]
                for k in keys_to_delete:
                    del MEMORY_CACHE[k]
                return len(keys_to_delete)
        except Exception as e:
            logger.warning("Error limpiando caché: %s", e)
            return 0


# Instancia global
cache_service: Optional[CacheService] = None


def init_cache(redis_url: Optional[str] = None):
    """Inicializa el servicio de caché."""
    global cache_service
    cache_service = CacheService(redis_url)


def cached(ttl_seconds: int = 300, key_prefix: str = ""):
    """Decorador para cachear resultados de funciones."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if cache_service is None:
                return func(*args, **kwargs)
            
            # Generar clave de caché
            cache_key = f"{key_prefix}:{func.__name__}:{str(args)}:{str(kwargs)}"
            
            # Intentar obtener del caché
            cached_value = cache_service.get(cache_key)
            if cached_value is not None:
                logger.debug(f"✅ Caché hit: {cache_key}")
                return cached_value
            
            # Ejecutar función
            result = func(*args, **kwargs)
            
            # Guardar en caché
            cache_service.set(cache_key, result, ttl_seconds)
            logger.debug(f"💾 Caché set: {cache_key} (TTL: {ttl_seconds}s)")
            
            return result
        
        return wrapper
    return decorator
