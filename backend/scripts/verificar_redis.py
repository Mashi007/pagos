#!/usr/bin/env python3
"""
Script para verificar la configuración y conexión de Redis
"""

import sys
import os
from pathlib import Path

# Agregar el directorio del proyecto al path
sys.path.insert(0, str(Path(__file__).parent.parent))

def verificar_redis():
    """Verificar configuración y conexión de Redis"""

    print("="*70)
    print("🔍 VERIFICACIÓN DE REDIS")
    print("="*70)

    # 1. Verificar variables de entorno
    print("\n1️⃣ VERIFICANDO VARIABLES DE ENTORNO...")
    print("-" * 70)

    from app.core.config import settings

    redis_url = os.getenv("REDIS_URL") or settings.REDIS_URL
    redis_host = os.getenv("REDIS_HOST") or settings.REDIS_HOST
    redis_port = os.getenv("REDIS_PORT") or settings.REDIS_PORT
    redis_db = os.getenv("REDIS_DB") or settings.REDIS_DB
    redis_password = os.getenv("REDIS_PASSWORD") or settings.REDIS_PASSWORD

    if redis_url:
        # Ocultar password si existe
        if "@" in redis_url:
            safe_url = redis_url.split("@")[0].split(":")[0] + ":***@" + redis_url.split("@")[1]
            print(f"✅ REDIS_URL configurado: {safe_url}")
        else:
            print(f"✅ REDIS_URL configurado: {redis_url}")
    else:
        print("⚠️  REDIS_URL no configurado")
        if redis_host:
            print(f"   Usando componentes: {redis_host}:{redis_port}/{redis_db}")

    if redis_password:
        print(f"✅ REDIS_PASSWORD configurado: *** (oculto)")
    else:
        print("ℹ️  REDIS_PASSWORD no configurado (puede ser normal si Redis no requiere autenticación)")

    # 2. Verificar instalación del cliente
    print("\n2️⃣ VERIFICANDO CLIENTE REDIS...")
    print("-" * 70)

    try:
        import redis
        print(f"✅ Cliente Redis instalado: versión {redis.__version__}")
    except ImportError:
        print("❌ Cliente Redis NO instalado")
        print("   Instalar con: pip install 'redis>=5.0.0,<6.0.0'")
        return 1

    # 3. Verificar backend de cache activo
    print("\n3️⃣ VERIFICANDO BACKEND DE CACHE...")
    print("-" * 70)

    try:
        from app.core.cache import cache_backend
        backend_type = type(cache_backend).__name__

        print(f"📦 Backend activo: {backend_type}")

        if backend_type == "RedisCache":
            print("✅ Redis está configurado y funcionando")

            # Obtener información adicional
            try:
                client = cache_backend.client
                info = client.info()

                print(f"\n📊 Información de Redis:")
                print(f"   - Versión: {info.get('redis_version', 'N/A')}")
                print(f"   - Memoria usada: {info.get('used_memory_human', 'N/A')}")
                print(f"   - Claves en cache: {client.dbsize()}")
                print(f"   - Uptime: {info.get('uptime_in_seconds', 0) // 3600} horas")
                print(f"   - Conexiones: {info.get('connected_clients', 'N/A')}")

            except Exception as e:
                print(f"   ⚠️  No se pudo obtener info adicional: {e}")

        elif backend_type == "MemoryCache":
            print("⚠️  MemoryCache está en uso (Redis no está conectado)")
            print("   - NO recomendado para producción")
            print("   - No funciona con múltiples workers")
        else:
            print(f"ℹ️  Usando {backend_type}")

    except Exception as e:
        print(f"❌ Error verificando backend: {e}")
        import traceback
        traceback.print_exc()
        return 1

    # 4. Test de conexión y operaciones
    print("\n4️⃣ TEST DE CONEXIÓN Y OPERACIONES...")
    print("-" * 70)

    try:
        from app.core.cache import cache_backend

        # Test de escritura
        test_key = "test_verificacion_redis"
        test_value = {"test": True, "timestamp": "2025-11-09", "verificacion": "ok"}

        print("   Probando escritura...")
        success_set = cache_backend.set(test_key, test_value, ttl=60)
        if success_set:
            print("   ✅ Escritura: OK")
        else:
            print("   ❌ Escritura: FALLÓ")
            return 1

        # Test de lectura
        print("   Probando lectura...")
        retrieved = cache_backend.get(test_key)
        if retrieved == test_value:
            print("   ✅ Lectura: OK")
        else:
            print("   ❌ Lectura: FALLÓ (valores no coinciden)")
            print(f"      Esperado: {test_value}")
            print(f"      Obtenido: {retrieved}")
            return 1

        # Test de eliminación
        print("   Probando eliminación...")
        success_delete = cache_backend.delete(test_key)
        if success_delete:
            print("   ✅ Eliminación: OK")
        else:
            print("   ⚠️  Eliminación: No se pudo eliminar (puede ser normal)")

        # Verificar que se eliminó
        retrieved_after = cache_backend.get(test_key)
        if retrieved_after is None:
            print("   ✅ Verificación: Clave eliminada correctamente")
        else:
            print("   ⚠️  Verificación: Clave aún existe (puede ser normal)")

    except Exception as e:
        print(f"   ❌ Error en tests: {e}")
        import traceback
        traceback.print_exc()
        return 1

    # 5. Resumen y recomendaciones
    print("\n5️⃣ RESUMEN Y RECOMENDACIONES...")
    print("-" * 70)

    try:
        from app.core.cache import cache_backend
        backend_type = type(cache_backend).__name__

        if backend_type == "RedisCache":
            print("✅ TODO CORRECTO")
            print("   - Redis está configurado y funcionando")
            print("   - Cache compartido entre workers")
            print("   - Óptimo para producción")
            return 0
        else:
            print("⚠️  ACCIONES RECOMENDADAS")
            print("   - Redis no está conectado")
            print("   - Usando MemoryCache como fallback")
            print("\n   Para activar Redis:")
            print("   1. Verificar que REDIS_URL esté configurado correctamente")
            print("   2. Verificar que Redis esté corriendo en Render")
            print("   3. Revisar logs de la aplicación para errores de conexión")
            return 0
    except Exception as e:
        print(f"❌ Error en resumen: {e}")
        return 1

def main():
    """Función principal"""
    try:
        resultado = verificar_redis()
        print("\n" + "="*70)
        if resultado == 0:
            print("✅ VERIFICACIÓN COMPLETADA")
        else:
            print("❌ VERIFICACIÓN FALLÓ - Revisar errores arriba")
        print("="*70)
        return resultado
    except Exception as e:
        print(f"\n❌ Error fatal: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
