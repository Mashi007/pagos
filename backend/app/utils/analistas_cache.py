"""
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session, relationship
from sqlalchemy import ForeignKey, Text, Numeric, JSON, Boolean, Enum
from fastapi import APIRouter, Depends, HTTPException, Query, status
Sistema de cache inteligente para analistas
Evita consultas repetidas a la base de datos
"""

logger = logging.getLogger(__name__)

# Constantes de configuración
DEFAULT_TTL_SECONDS = 300  # 5 minutos por defecto

class AnalistasCache:
    def __init__(self, ttl_seconds: int = DEFAULT_TTL_SECONDS):
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.ttl = ttl_seconds

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """Obtener datos del cache si no han expirado"""
        if key in self.cache:
            data = self.cache[key]
            if time.time() - data['timestamp'] < self.ttl:
                logger.info(f"Cache hit para key: {key}")
                return data['data']
            else:
                # Cache expirado, eliminar
                del self.cache[key]
                logger.info(f"Cache expirado para key: {key}")
        return None

    def set(self, key: str, data: Dict[str, Any]) -> None:
        """Guardar datos en el cache"""
        self.cache[key] = {
            'data': data,
            'timestamp': time.time()
        }
        logger.info(f"Datos guardados en cache para key: {key}")

    def clear(self) -> None:
        """Limpiar todo el cache"""
        self.cache.clear()
        logger.info("Cache limpiado completamente")

    def get_stats(self) -> Dict[str, Any]:
        """Obtener estadísticas del cache"""
        return {
            'total_keys': len(self.cache),
            'keys': list(self.cache.keys()),
            'ttl_seconds': self.ttl
        }

# Instancia global del cache
analistas_cache = AnalistasCache(ttl_seconds=DEFAULT_TTL_SECONDS)

def cache_analistas(key_func):
    """Decorator para cachear resultados de analistas"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Generar clave del cache basada en parámetros
            cache_key = key_func(*args, **kwargs)

            # Intentar obtener del cache
            cached_result = analistas_cache.get(cache_key)
            if cached_result is not None:
                return cached_result

            # Si no está en cache, ejecutar función y guardar resultado
            result = func(*args, **kwargs)
            analistas_cache.set(cache_key, result)
            return result

        wrapper.__name__ = func.__name__
        wrapper.__doc__ = func.__doc__
        return wrapper
    return decorator

def generate_cache_key(
    skip: int = 0, 
    limit: int = 100, 
    activo: Optional[bool] = None, 
    search: Optional[str] = None
) -> str:
    """
    Generar clave única para el cache basada en parámetros

    Args:
        skip: Número de registros a omitir
        limit: Límite de registros
        activo: Filtro de estado activo
        search: Término de búsqueda

    Returns:
        str: Clave única para el cache
    """
    return f"analistas_{skip}_{limit}_{activo}_{search or ''}"
