# 🚀 Opciones para Mejorar el Sistema de Cache

## 📊 Situación Actual

El sistema está usando **MemoryCache** (cache en memoria), que tiene las siguientes limitaciones:
- ❌ No funciona con múltiples workers (cada worker tiene su propio cache)
- ❌ Se pierde al reiniciar el servidor
- ❌ No comparte datos entre instancias
- ❌ Limitado por memoria RAM del proceso

---

## ✅ OPCIÓN 1: Redis (Recomendado para Producción)

### Ventajas:
- ✅ Cache compartido entre múltiples workers
- ✅ Persistencia opcional
- ✅ Alto rendimiento
- ✅ Escalable horizontalmente
- ✅ Soporte para TTL automático
- ✅ Operaciones avanzadas (pub/sub, streams, etc.)

### Implementación:

#### 1.1. Instalación Local (Desarrollo)

```bash
# Instalar Redis localmente
# Windows (usando WSL o Docker)
docker run -d -p 6379:6379 redis:7-alpine

# O instalar Redis nativo (Linux/Mac)
# Ubuntu/Debian:
sudo apt-get install redis-server

# macOS:
brew install redis
```

#### 1.2. Instalar Cliente Python

```bash
cd backend
pip install 'redis>=5.0.0,<6.0.0'
```

#### 1.3. Configurar Variables de Entorno

**Opción A: URL completa (Recomendado)**
```bash
REDIS_URL=redis://localhost:6379/0
```

**Opción B: Componentes individuales**
```bash
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=  # Opcional, dejar vacío si no hay password
```

#### 1.4. Para Producción (Render.com)

1. Crear servicio Redis en Render.com
2. Copiar la URL de conexión
3. Agregar como variable de entorno:
```bash
REDIS_URL=redis://default:password@redis-host:6379
```

### Verificación:
Al iniciar la aplicación, deberías ver:
```
✅ Redis cache inicializado correctamente
```

---

## ✅ OPCIÓN 2: Redis Cloud (Gratis hasta 30MB)

### Ventajas:
- ✅ Gratis para empezar
- ✅ Sin necesidad de servidor propio
- ✅ Gestión automática
- ✅ Escalable según necesidades

### Implementación:

1. Crear cuenta en [Redis Cloud](https://redis.com/try-free/)
2. Crear base de datos gratuita (30MB)
3. Copiar URL de conexión
4. Configurar variable de entorno:
```bash
REDIS_URL=redis://default:password@redis-12345.c1.us-east-1-1.ec2.cloud.redislabs.com:12345
```

---

## ✅ OPCIÓN 3: Upstash Redis (Serverless)

### Ventajas:
- ✅ Modelo serverless (pago por uso)
- ✅ Plan gratuito generoso
- ✅ Globalmente distribuido
- ✅ Sin gestión de servidores

### Implementación:

1. Crear cuenta en [Upstash](https://upstash.com/)
2. Crear base de datos Redis
3. Copiar URL REST o Redis
4. Configurar:
```bash
REDIS_URL=redis://default:password@usw1-xxx.upstash.io:6379
```

---

## ✅ OPCIÓN 4: FileCache (Mejora de MemoryCache)

### Ventajas:
- ✅ Persistencia entre reinicios
- ✅ No requiere servidor externo
- ✅ Funciona con múltiples workers (si comparten filesystem)
- ✅ Fácil de implementar

### Desventajas:
- ⚠️ Más lento que Redis
- ⚠️ Requiere filesystem compartido para múltiples workers
- ⚠️ No escalable horizontalmente

### Implementación:

Agregar al `backend/app/core/cache.py`:

```python
import os
import pickle
import hashlib
from pathlib import Path

class FileCache(CacheBackend):
    """Implementación de cache usando archivos"""

    def __init__(self, cache_dir: str = "/tmp/rapicredit_cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"✅ FileCache inicializado en: {cache_dir}")

    def _get_file_path(self, key: str) -> Path:
        """Obtener ruta del archivo para una clave"""
        # Usar hash para evitar caracteres especiales en nombres de archivo
        key_hash = hashlib.md5(key.encode()).hexdigest()
        return self.cache_dir / f"{key_hash}.cache"

    def get(self, key: str) -> Optional[Any]:
        """Obtener valor del cache"""
        try:
            file_path = self._get_file_path(key)
            if not file_path.exists():
                return None

            with open(file_path, 'rb') as f:
                data = pickle.load(f)
                value, expiry = data

                if expiry is None or expiry > time.time():
                    return value
                else:
                    # Expiró, eliminar archivo
                    file_path.unlink()
                    return None
        except Exception as e:
            logger.error(f"Error leyendo cache: {e}")
            return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Guardar valor en cache"""
        try:
            expiry = (time.time() + ttl) if ttl else None
            file_path = self._get_file_path(key)

            with open(file_path, 'wb') as f:
                pickle.dump((value, expiry), f)

            return True
        except Exception as e:
            logger.error(f"Error guardando cache: {e}")
            return False

    def delete(self, key: str) -> bool:
        """Eliminar valor del cache"""
        try:
            file_path = self._get_file_path(key)
            if file_path.exists():
                file_path.unlink()
                return True
            return False
        except Exception as e:
            logger.error(f"Error eliminando cache: {e}")
            return False

    def clear(self) -> bool:
        """Limpiar todo el cache"""
        try:
            for file in self.cache_dir.glob("*.cache"):
                file.unlink()
            return True
        except Exception as e:
            logger.error(f"Error limpiando cache: {e}")
            return False
```

Y modificar la inicialización en `cache.py`:

```python
# Intentar Redis primero, luego FileCache, luego MemoryCache
if redis_available:
    cache_backend = RedisCache(redis_client)
elif os.getenv("USE_FILE_CACHE", "false").lower() == "true":
    cache_backend = FileCache(os.getenv("CACHE_DIR", "/tmp/rapicredit_cache"))
else:
    cache_backend = MemoryCache()
```

---

## ✅ OPCIÓN 5: Cache Híbrido (Redis + MemoryCache)

### Ventajas:
- ✅ Redis para datos compartidos
- ✅ MemoryCache para datos locales (más rápido)
- ✅ Fallback automático si Redis falla

### Implementación:

Ya está implementado en el código actual. Solo necesitas configurar Redis.

---

## 📊 Comparación de Opciones

| Opción | Velocidad | Escalabilidad | Persistencia | Costo | Complejidad |
|--------|-----------|----------------|--------------|-------|-------------|
| **MemoryCache** | ⭐⭐⭐⭐⭐ | ❌ | ❌ | Gratis | ⭐ |
| **FileCache** | ⭐⭐⭐ | ⭐⭐ | ✅ | Gratis | ⭐⭐ |
| **Redis Local** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ✅ | Gratis | ⭐⭐⭐ |
| **Redis Cloud** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ✅ | Gratis/$$ | ⭐⭐⭐ |
| **Upstash** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ✅ | Gratis/$$ | ⭐⭐⭐ |

---

## 🎯 Recomendación por Escenario

### Desarrollo Local:
1. **Redis local** (Docker) - Más rápido y fácil
2. **FileCache** - Si no quieres instalar Redis

### Producción (Render.com):
1. **Redis Cloud** o **Upstash** - Gratis para empezar
2. **Redis en Render** - Si ya tienes servicio Redis

### Múltiples Workers:
- **Solo Redis** - MemoryCache no funciona

---

## 🚀 Pasos Rápidos para Implementar Redis

### Opción Rápida (Desarrollo):

```bash
# 1. Instalar Redis con Docker
docker run -d -p 6379:6379 --name redis-cache redis:7-alpine

# 2. Instalar cliente Python
cd backend
pip install 'redis>=5.0.0,<6.0.0'

# 3. Configurar variable de entorno
export REDIS_URL=redis://localhost:6379/0

# 4. Reiniciar aplicación
# Deberías ver: "✅ Redis cache inicializado correctamente"
```

### Opción Producción (Render.com):

1. Crear servicio Redis en Render
2. Copiar `REDIS_URL` de las variables de entorno
3. Agregar a variables de entorno de tu aplicación
4. Reiniciar aplicación

---

## 🔍 Verificación

Después de configurar Redis, verifica en los logs:

```bash
# Buscar en logs:
✅ Redis cache inicializado correctamente

# En lugar de:
⚠️ Usando MemoryCache - NO recomendado para producción
```

---

## 📝 Notas Adicionales

- El código ya está preparado para Redis, solo falta instalarlo y configurarlo
- MemoryCache seguirá funcionando como fallback si Redis no está disponible
- Los TTLs actuales son:
  - 5 minutos (300s): KPIs y dashboards
  - 10 minutos (600s): Datos históricos
- Puedes ajustar TTLs según necesidades en cada endpoint

