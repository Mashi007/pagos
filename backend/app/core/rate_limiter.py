"""
Módulo de Rate Limiting usando slowapi
Protege la API contra abuso y ataques de fuerza bruta
"""

import logging

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.core.config import settings

logger = logging.getLogger(__name__)


# Función personalizada para obtener IP del cliente
# Considera proxies y headers X-Forwarded-For
def get_client_ip(request) -> str:
    """
    Obtener IP real del cliente considerando proxies
    """
    # Verificar header X-Forwarded-For (usado por proxies/load balancers)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # Tomar la primera IP (cliente original)
        client_ip = forwarded_for.split(",")[0].strip()
        logger.debug(f"IP desde X-Forwarded-For: {client_ip}")
        return client_ip

    # Verificar header X-Real-IP (usado por algunos proxies)
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        logger.debug(f"IP desde X-Real-IP: {real_ip}")
        return real_ip

    # Usar función por defecto de slowapi que maneja request.client
    return get_remote_address(request)


def _get_storage_uri() -> str:
    """
    Obtiene la URI de almacenamiento para rate limiting.
    Usa Redis si está configurado, sino usa memoria.
    """
    # Intentar usar Redis si está configurado
    if settings.REDIS_URL:
        logger.info(f"✅ Usando Redis para rate limiting: {settings.REDIS_URL[:20]}...")
        return settings.REDIS_URL
    elif settings.REDIS_HOST and settings.REDIS_HOST != "localhost":
        # Construir URL de Redis desde componentes
        redis_url = "redis://"
        if settings.REDIS_PASSWORD:
            redis_url += f":{settings.REDIS_PASSWORD}@"
        redis_url += f"{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}"
        logger.info(f"✅ Usando Redis para rate limiting: {redis_url[:20]}...")
        return redis_url
    else:
        # Usar memoria en desarrollo
        logger.warning(
            "⚠️ Redis no configurado. Usando memoria para rate limiting. "
            "En producción distribuida, configure REDIS_URL para rate limiting distribuido."
        )
        return "memory://"


# Inicializar limiter con función personalizada para obtener IP del cliente
limiter = Limiter(
    key_func=get_client_ip,
    default_limits=["1000/hour"],  # Límite general por defecto
    storage_uri=_get_storage_uri(),  # Usar Redis si está disponible, sino memoria
)


def get_rate_limiter() -> Limiter:
    """
    Obtener instancia del rate limiter
    """
    return limiter


def get_rate_limit_exceeded_handler():
    """
    Obtener manejador de excepciones de rate limit
    """
    return _rate_limit_exceeded_handler


# Límites predefinidos para diferentes tipos de endpoints
RATE_LIMITS = {
    "general": "60/minute",  # Límite general para la mayoría de endpoints
    "auth": "5/minute",  # Límite estricto para autenticación (protección fuerza bruta)
    "sensitive": "20/minute",  # Límite para endpoints sensibles
    "public": "100/minute",  # Límite más permisivo para endpoints públicos
    "strict": "10/minute",  # Límite muy estricto para operaciones críticas
}
