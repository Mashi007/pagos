#!/usr/bin/env python3
"""
Script para configurar y verificar Redis cache
"""

import os
import sys
from pathlib import Path

# Agregar el directorio del proyecto al path
sys.path.insert(0, str(Path(__file__).parent.parent))

def check_redis_installation():
    """Verificar si Redis está instalado"""
    try:
        import redis
        print("✅ Cliente Redis instalado")
        print(f"   Versión: {redis.__version__}")
        return True
    except ImportError:
        print("❌ Cliente Redis NO instalado")
        print("   Instalar con: pip install 'redis>=5.0.0,<6.0.0'")
        return False

def check_redis_connection():
    """Verificar conexión a Redis"""
    try:
        import redis
        from app.core.config import settings

        # Intentar conectar
        if settings.REDIS_URL:
            client = redis.from_url(settings.REDIS_URL, decode_responses=False)
            print(f"✅ Configurado REDIS_URL: {settings.REDIS_URL.split('@')[1] if '@' in settings.REDIS_URL else settings.REDIS_URL}")
        else:
            client = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                db=settings.REDIS_DB,
                password=settings.REDIS_PASSWORD,
                decode_responses=False,
            )
            print(f"✅ Configurado Redis: {settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}")

        # Test de conexión
        client.ping()
        print("✅ Conexión a Redis exitosa")

        # Información adicional
        info = client.info()
        print(f"   Versión Redis: {info.get('redis_version', 'N/A')}")
        print(f"   Memoria usada: {info.get('used_memory_human', 'N/A')}")
        print(f"   Claves: {client.dbsize()}")

        return True
    except ImportError:
        print("❌ Cliente Redis no instalado")
        return False
    except Exception as e:
        print(f"❌ Error conectando a Redis: {e}")
        print("\n💡 Opciones:")
        print("   1. Verificar que Redis esté corriendo")
        print("   2. Verificar variables de entorno (REDIS_URL, REDIS_HOST, etc.)")
        print("   3. Para desarrollo local: docker run -d -p 6379:6379 redis:7-alpine")
        return False

def check_cache_backend():
    """Verificar qué backend de cache está en uso"""
    try:
        from app.core.cache import cache_backend

        backend_type = type(cache_backend).__name__
        print(f"\n📦 Backend de cache actual: {backend_type}")

        if backend_type == "RedisCache":
            print("✅ Usando Redis (óptimo para producción)")
        elif backend_type == "MemoryCache":
            print("⚠️  Usando MemoryCache (NO recomendado para producción)")
            print("   - No funciona con múltiples workers")
            print("   - Se pierde al reiniciar")
        else:
            print(f"ℹ️  Usando {backend_type}")

        # Test básico
        test_key = "test_cache_verification"
        test_value = {"test": True, "timestamp": "2025-11-09"}

        cache_backend.set(test_key, test_value, ttl=60)
        retrieved = cache_backend.get(test_key)

        if retrieved == test_value:
            print("✅ Test de cache exitoso")
            cache_backend.delete(test_key)
        else:
            print("⚠️  Test de cache falló")

        return True
    except Exception as e:
        print(f"❌ Error verificando cache: {e}")
        return False

def print_recommendations():
    """Imprimir recomendaciones según el estado actual"""
    print("\n" + "="*60)
    print("📋 RECOMENDACIONES")
    print("="*60)

    try:
        from app.core.cache import cache_backend
        backend_type = type(cache_backend).__name__

        if backend_type == "MemoryCache":
            print("\n🚀 Para mejorar el cache:")
            print("\n1. INSTALAR REDIS (Recomendado):")
            print("   pip install 'redis>=5.0.0,<6.0.0'")
            print("\n2. CONFIGURAR REDIS:")
            print("   # Opción A: URL completa")
            print("   export REDIS_URL=redis://localhost:6379/0")
            print("\n   # Opción B: Componentes")
            print("   export REDIS_HOST=localhost")
            print("   export REDIS_PORT=6379")
            print("\n3. INICIAR REDIS (si no está corriendo):")
            print("   docker run -d -p 6379:6379 --name redis-cache redis:7-alpine")
            print("\n4. REINICIAR LA APLICACIÓN")
            print("\n📖 Ver más opciones en: backend/docs/OPCIONES_MEJORA_CACHE.md")
        else:
            print("\n✅ Cache configurado correctamente")
            print("   No se requieren cambios adicionales")
    except Exception as e:
        print(f"⚠️  Error obteniendo recomendaciones: {e}")

def main():
    """Función principal"""
    print("="*60)
    print("🔍 VERIFICACIÓN DE CACHE")
    print("="*60)

    print("\n1. Verificando instalación de Redis...")
    redis_installed = check_redis_installation()

    print("\n2. Verificando conexión a Redis...")
    redis_connected = check_redis_connection()

    print("\n3. Verificando backend de cache...")
    cache_ok = check_cache_backend()

    print_recommendations()

    print("\n" + "="*60)
    if redis_installed and redis_connected and cache_ok:
        print("✅ TODO CORRECTO - Cache configurado óptimamente")
        return 0
    else:
        print("⚠️  ACCIONES REQUERIDAS - Ver recomendaciones arriba")
        return 1

if __name__ == "__main__":
    sys.exit(main())
