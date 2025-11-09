#!/usr/bin/env python3
"""
Script simple para verificar el estado del cache
"""

import sys
from pathlib import Path

# Agregar el directorio del proyecto al path
sys.path.insert(0, str(Path(__file__).parent.parent))

def main():
    print("="*60)
    print("🔍 VERIFICACIÓN DE CACHE")
    print("="*60)
    
    try:
        # 1. Verificar tipo de backend
        from app.core.cache import cache_backend
        backend_type = type(cache_backend).__name__
        
        print(f"\n📦 Backend de cache: {backend_type}")
        
        if backend_type == "RedisCache":
            print("✅ Redis está configurado y funcionando")
            print("   - Cache compartido entre workers")
            print("   - Persistencia entre reinicios")
            print("   - Óptimo para producción")
            
            # Información adicional de Redis
            try:
                client = cache_backend.client
                info = client.info()
                print(f"\n📊 Información de Redis:")
                print(f"   - Versión: {info.get('redis_version', 'N/A')}")
                print(f"   - Memoria usada: {info.get('used_memory_human', 'N/A')}")
                print(f"   - Claves en cache: {client.dbsize()}")
                print(f"   - Uptime: {info.get('uptime_in_seconds', 0) // 3600}h")
            except Exception as e:
                print(f"   ⚠️  No se pudo obtener info adicional: {e}")
                
        elif backend_type == "MemoryCache":
            print("⚠️  MemoryCache está en uso")
            print("   - NO recomendado para producción")
            print("   - No funciona con múltiples workers")
            print("   - Se pierde al reiniciar")
            print("\n💡 Para usar Redis:")
            print("   1. Instalar: pip install 'redis>=5.0.0,<6.0.0'")
            print("   2. Configurar REDIS_URL o REDIS_HOST en variables de entorno")
            print("   3. Reiniciar la aplicación")
        else:
            print(f"ℹ️  Usando {backend_type}")
        
        # 2. Test básico de funcionamiento
        print("\n🧪 Test de funcionamiento...")
        test_key = "test_verificacion_cache"
        test_value = {"test": True, "timestamp": "2025-11-09"}
        
        # Guardar
        success_set = cache_backend.set(test_key, test_value, ttl=60)
        if success_set:
            print("   ✅ Escritura en cache: OK")
        else:
            print("   ❌ Escritura en cache: FALLÓ")
            return 1
        
        # Leer
        retrieved = cache_backend.get(test_key)
        if retrieved == test_value:
            print("   ✅ Lectura de cache: OK")
        else:
            print("   ❌ Lectura de cache: FALLÓ")
            return 1
        
        # Limpiar
        cache_backend.delete(test_key)
        print("   ✅ Eliminación de cache: OK")
        
        # 3. Verificar configuración
        print("\n⚙️  Configuración:")
        try:
            from app.core.config import settings
            
            if settings.REDIS_URL:
                # Ocultar password si existe
                redis_url = settings.REDIS_URL
                if "@" in redis_url:
                    parts = redis_url.split("@")
                    redis_url = f"redis://***@{parts[1]}"
                print(f"   - REDIS_URL: {redis_url}")
            else:
                print(f"   - REDIS_HOST: {settings.REDIS_HOST}")
                print(f"   - REDIS_PORT: {settings.REDIS_PORT}")
                print(f"   - REDIS_DB: {settings.REDIS_DB}")
                if settings.REDIS_PASSWORD:
                    print(f"   - REDIS_PASSWORD: *** (configurado)")
        except Exception as e:
            print(f"   ⚠️  Error obteniendo configuración: {e}")
        
        print("\n" + "="*60)
        if backend_type == "RedisCache":
            print("✅ TODO CORRECTO - Cache configurado óptimamente")
            return 0
        else:
            print("⚠️  ACCIONES RECOMENDADAS - Ver opciones arriba")
            return 0
            
    except Exception as e:
        print(f"\n❌ Error durante verificación: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())

