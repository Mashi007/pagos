# 🔧 Configuración de Redis en Render.com

## 📋 Formato de URL de Redis en Render

Render.com proporciona URLs de Redis en diferentes formatos:

### Formato 1: Con password en la URL (Recomendado)
```
redis://default:password@red-xxxxx:6379
```

### Formato 2: Sin password en la URL
```
redis://red-xxxxx:6379
```

### Formato 3: Con base de datos específica
```
redis://default:password@red-xxxxx:6379/0
```

---

## ✅ Verificación de tu Configuración Actual

Tu URL actual: `redis://red-d46dg4ripnbc73demdog:6379`

### Posibles Problemas:

1. **Falta el password:**
   - Si Render requiere password, debe estar en la URL
   - Formato: `redis://default:password@red-xxxxx:6379`

2. **Falta la base de datos:**
   - Por defecto usa `/0`, pero puede especificarse
   - Formato: `redis://red-xxxxx:6379/0`

3. **Usuario incorrecto:**
   - Render usa `default` como usuario
   - Formato: `redis://default:password@red-xxxxx:6379`

---

## 🔍 Cómo Obtener la URL Correcta en Render

1. **Ir a tu servicio Redis en Render Dashboard**
2. **Buscar "Internal Redis URL" o "Redis URL"**
3. **Copiar la URL completa** (debe incluir password si está configurado)

Ejemplo de URL completa de Render:
```
redis://default:AVNS_xxxxxxxxxxxx@red-d46dg4ripnbc73demdog:6379
```

---

## ⚙️ Configuración en Variables de Entorno

### Opción 1: URL Completa (Recomendado)

En Render Dashboard → Environment Variables:
```
REDIS_URL=redis://default:password@red-d46dg4ripnbc73demdog:6379
```

### Opción 2: Componentes Separados

Si prefieres componentes individuales:
```
REDIS_HOST=red-d46dg4ripnbc73demdog
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=tu_password_aqui
```

---

## 🧪 Verificación de la Conexión

### 1. Revisar Logs al Iniciar

**✅ Si Redis está funcionando:**
```
✅ Redis cache inicializado correctamente
```

**❌ Si hay error:**
```
⚠️ No se pudo conectar a Redis: ConnectionError: ...
   Usando MemoryCache como fallback
```

### 2. Errores Comunes

#### Error: "NOAUTH Authentication required"
**Causa:** Falta password en la URL
**Solución:** Agregar password a la URL:
```
redis://default:password@red-xxxxx:6379
```

#### Error: "Connection refused"
**Causa:** Redis no está corriendo o URL incorrecta
**Solución:** 
- Verificar que el servicio Redis esté activo en Render
- Verificar que la URL sea correcta

#### Error: "Name or service not known"
**Causa:** Host incorrecto
**Solución:** Verificar que el host sea `red-xxxxx` (no incluir `.onrender.com`)

---

## 🔧 Ajustes en el Código (si es necesario)

El código actual en `backend/app/core/cache.py` maneja:

1. ✅ URLs con password: `redis://:password@host:port`
2. ✅ URLs sin password: `redis://host:port`
3. ✅ URLs con base de datos: `redis://host:port/db`
4. ✅ Componentes separados: `REDIS_HOST`, `REDIS_PORT`, etc.

**Si Render proporciona una URL con formato especial**, el código debería manejarlo automáticamente.

---

## 📝 Checklist de Verificación

- [ ] URL de Redis copiada desde Render Dashboard
- [ ] URL incluye password si Render lo requiere
- [ ] Variable `REDIS_URL` configurada en Render
- [ ] Aplicación reiniciada después de configurar
- [ ] Logs muestran: "✅ Redis cache inicializado correctamente"
- [ ] No hay errores de conexión en logs

---

## 🚨 Si Sigue Sin Funcionar

### Paso 1: Verificar URL Completa
Asegúrate de copiar la URL completa desde Render, incluyendo:
- Usuario (`default`)
- Password (si existe)
- Host (`red-xxxxx`)
- Puerto (`6379`)

### Paso 2: Verificar en Render Dashboard
1. Ir a tu servicio Redis
2. Verificar que esté "Running"
3. Copiar "Internal Redis URL" (no External)

### Paso 3: Probar Conexión Manual
Si tienes acceso, puedes probar:
```bash
redis-cli -h red-d46dg4ripnbc73demdog -p 6379 -a password ping
```

### Paso 4: Revisar Logs Detallados
Buscar en los logs de la aplicación:
- Errores de conexión
- Timeouts
- Errores de autenticación

---

## 💡 Nota Importante

Render.com usa URLs **internas** para Redis. Estas URLs:
- ✅ Solo funcionan dentro de la red de Render
- ✅ No son accesibles desde fuera
- ✅ Son más seguras (no expuestas públicamente)

Si estás en desarrollo local, necesitarás:
- Una URL externa de Redis (si Render la proporciona)
- O usar Redis local: `redis://localhost:6379/0`

---

## 🔗 Referencias

- Documentación de Render Redis: https://render.com/docs/redis
- Configuración general: `backend/docs/CONFIGURACION_CACHE.md`
- Opciones de mejora: `backend/docs/OPCIONES_MEJORA_CACHE.md`

