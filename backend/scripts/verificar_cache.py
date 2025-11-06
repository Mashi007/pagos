#!/usr/bin/env python3
"""
Script para verificar el estado del sistema de cache
"""
import sys
import os

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.cache import cache_backend, MemoryCache
from app.core.config import settings
import time

def verificar_cache():
    """Verifica el estado del cache"""
    print("=" * 80)
    print("🔍 VERIFICACIÓN DEL SISTEMA DE CACHE")
    print("=" * 80)
    print()
    
    # 1. Tipo de cache
    cache_type = "MemoryCache" if isinstance(cache_backend, MemoryCache) else "RedisCache"
    print(f"📦 Tipo de cache: {cache_type}")
    print()
    
    # 2. Configuración
    print("⚙️  Configuración:")
    print(f"   REDIS_URL: {'✅ Configurada' if settings.REDIS_URL else '❌ No configurada'}")
    if settings.REDIS_URL:
        # Mostrar solo los primeros y últimos caracteres por seguridad
        url_display = settings.REDIS_URL[:20] + "..." + settings.REDIS_URL[-10:] if len(settings.REDIS_URL) > 30 else settings.REDIS_URL
        print(f"   REDIS_URL valor: {url_display}")
    print(f"   REDIS_HOST: {settings.REDIS_HOST}")
    print(f"   REDIS_PORT: {settings.REDIS_PORT}")
    print(f"   REDIS_DB: {settings.REDIS_DB}")
    print(f"   REDIS_PASSWORD: {'✅ Configurada' if settings.REDIS_PASSWORD else '❌ No configurada'}")
    print(f"   REDIS_SOCKET_TIMEOUT: {settings.REDIS_SOCKET_TIMEOUT}s")
    print()
    
    # 3. Pruebas de operatividad
    print("🧪 Pruebas de operatividad:")
    test_key = "test_cache_verification"
    test_value = {"test": True, "timestamp": time.time()}
    
    # Prueba de escritura
    try:
        write_success = cache_backend.set(test_key, test_value, ttl=10)
        if write_success:
            print("   ✅ Escritura: OK")
        else:
            print("   ❌ Escritura: FALLÓ")
    except Exception as e:
        print(f"   ❌ Escritura: ERROR - {e}")
    
    # Prueba de lectura
    try:
        read_value = cache_backend.get(test_key)
        if read_value and read_value.get("test") is True:
            print("   ✅ Lectura: OK")
        else:
            print("   ❌ Lectura: FALLÓ - Valor no encontrado o incorrecto")
    except Exception as e:
        print(f"   ❌ Lectura: ERROR - {e}")
    
    # Prueba de eliminación
    try:
        delete_success = cache_backend.delete(test_key)
        if delete_success:
            print("   ✅ Eliminación: OK")
        else:
            print("   ❌ Eliminación: FALLÓ")
    except Exception as e:
        print(f"   ❌ Eliminación: ERROR - {e}")
    
    print()
    
    # 4. Verificar conexión Redis (si aplica)
    if cache_type == "RedisCache":
        print("🔗 Verificación de conexión Redis:")
        try:
            if hasattr(cache_backend, 'client'):
                cache_backend.client.ping()
                print("   ✅ Redis responde al PING")
            else:
                print("   ⚠️  No se puede verificar conexión (cliente no disponible)")
        except Exception as e:
            print(f"   ❌ Redis NO responde: {e}")
        print()
    
    # 5. Advertencias
    print("⚠️  Advertencias:")
    warnings = []
    if cache_type == "MemoryCache":
        warnings.append("   ⚠️  Usando MemoryCache - NO recomendado para producción con múltiples workers")
        warnings.append("   ⚠️  El cache no se comparte entre workers, puede causar inconsistencias")
    if not settings.REDIS_URL and cache_type == "MemoryCache":
        warnings.append("   ⚠️  REDIS_URL no configurada - usando fallback MemoryCache")
    
    if warnings:
        for warning in warnings:
            print(warning)
    else:
        print("   ✅ No hay advertencias")
    
    print()
    print("=" * 80)
    
    # 6. Resumen
    print("📊 RESUMEN:")
    if cache_type == "RedisCache":
        print("   ✅ Cache Redis configurado correctamente")
    else:
        print("   ⚠️  Cache en memoria (MemoryCache) - considerar configurar Redis para producción")
    print()
    
    # 7. Recomendaciones
    if cache_type == "MemoryCache":
        print("💡 RECOMENDACIONES:")
        print("   1. Configurar Redis en Render:")
        print("      - Crear un servicio Redis en Render")
        print("      - Agregar variable de entorno REDIS_URL en el servicio backend")
        print("   2. Verificar que el paquete redis esté instalado:")
        print("      pip install redis==5.0.1")
        print()

if __name__ == "__main__":
    verificar_cache()

