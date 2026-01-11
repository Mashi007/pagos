#!/usr/bin/env python3
"""
Script para limpiar el cache del sistema sin desconfigurar servicios

Este script limpia todo el cache (Redis o MemoryCache) sin modificar
ninguna configuración de servicios.

Uso:
    python scripts/python/limpiar_cache.py

O desde PowerShell:
    python scripts\python\limpiar_cache.py
"""

import sys
import os
from pathlib import Path

# Agregar el directorio raíz del proyecto al path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Cambiar al directorio backend para importar módulos
backend_dir = project_root / "backend"
os.chdir(backend_dir)
sys.path.insert(0, str(backend_dir))

import logging
from app.core.cache import cache_backend, MemoryCache

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def limpiar_cache():
    """
    Limpia todo el cache del sistema sin modificar configuraciones.
    
    Returns:
        bool: True si se limpió exitosamente, False en caso contrario
    """
    try:
        # Determinar tipo de cache
        cache_type = "MemoryCache" if isinstance(cache_backend, MemoryCache) else "RedisCache"
        
        logger.info("=" * 80)
        logger.info("🧹 LIMPIEZA DE CACHE")
        logger.info("=" * 80)
        logger.info(f"Tipo de cache detectado: {cache_type}")
        
        # Información adicional para Redis
        if cache_type == "RedisCache" and hasattr(cache_backend, "client"):
            try:
                # Obtener información de Redis sin modificar nada
                info = cache_backend.client.info("keyspace")
                logger.info(f"Estado de Redis: Conectado")
                logger.info(f"Información de keyspace: {info}")
            except Exception as e:
                logger.warning(f"No se pudo obtener información de Redis: {e}")
        
        # Limpiar cache
        logger.info("Iniciando limpieza de cache...")
        resultado = cache_backend.clear()
        
        if resultado:
            logger.info("✅ Cache limpiado exitosamente")
            
            # Verificar que se limpió correctamente
            if cache_type == "RedisCache" and hasattr(cache_backend, "client"):
                try:
                    # Contar claves restantes (debería ser 0)
                    keys_count = cache_backend.client.dbsize()
                    logger.info(f"Claves restantes en Redis: {keys_count}")
                    if keys_count == 0:
                        logger.info("✅ Verificación: Cache completamente vacío")
                    else:
                        logger.warning(f"⚠️ Advertencia: Quedan {keys_count} claves en Redis")
                except Exception as e:
                    logger.warning(f"No se pudo verificar el estado de Redis: {e}")
            elif cache_type == "MemoryCache":
                cache_size = len(cache_backend._cache)
                logger.info(f"Entradas en MemoryCache: {cache_size}")
                if cache_size == 0:
                    logger.info("✅ Verificación: Cache completamente vacío")
            
            logger.info("=" * 80)
            logger.info("✅ LIMPIEZA COMPLETADA EXITOSAMENTE")
            logger.info("=" * 80)
            logger.info("")
            logger.info("📋 Notas importantes:")
            logger.info("   - No se modificó ninguna configuración de servicios")
            logger.info("   - El cache se regenerará automáticamente con las próximas solicitudes")
            logger.info("   - Los servicios siguen funcionando normalmente")
            logger.info("")
            
            return True
        else:
            logger.error("❌ Error: No se pudo limpiar el cache")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error al limpiar cache: {e}", exc_info=True)
        logger.error("")
        logger.error("⚠️ El cache puede no haberse limpiado completamente")
        logger.error("   Verifica los logs para más detalles")
        return False


if __name__ == "__main__":
    try:
        exito = limpiar_cache()
        sys.exit(0 if exito else 1)
    except KeyboardInterrupt:
        logger.warning("\n⚠️ Operación cancelada por el usuario")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Error fatal: {e}", exc_info=True)
        sys.exit(1)
