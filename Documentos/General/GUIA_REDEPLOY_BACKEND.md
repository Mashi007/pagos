# 🚀 GUÍA PASO A PASO: Forzar Redeploy del Backend en Render

## 📋 Objetivo

Forzar que el backend en Render se actualice con el código más reciente que tiene `@router.get("/")` en lugar de `@router.get("")`.

---

## ✅ PASO 1: Abrir Render Dashboard

1. Ve a: **https://dashboard.render.com**
2. **Inicia sesión** con tu cuenta

---

## ✅ PASO 2: Localizar el Servicio Backend

1. En el dashboard, busca el servicio llamado: **`pagos-backend`**
2. Haz **clic** en el servicio

---

## ✅ PASO 3: Verificar el Último Deploy

1. En la página del servicio, ve a la pestaña **"Events"** (o "Deploys")
2. Revisa el **último commit** desplegado
3. Debe mostrar algo como:
   ```
   Commit: 87101da6 (o más reciente)
   Message: docs: Documentar solución causa raíz...
   ```

**Si el commit es anterior a `1d02ac32`**, necesitas forzar el redeploy.

---

## ✅ PASO 4: Forzar Nuevo Deploy

### Opción A: Desde la Página Principal del Servicio

1. En la parte superior de la página, busca el botón **"Manual Deploy"**
2. Haz **clic** en **"Manual Deploy"**
3. Selecciona **"Deploy latest commit"**
4. Confirma el deploy

### Opción B: Desde el Menú de Acciones

1. En la página del servicio, busca el menú **"..."** (tres puntos)
2. Selecciona **"Manual Deploy"** → **"Deploy latest commit"**
3. Confirma

---

## ✅ PASO 5: Monitorear el Deploy

1. Ve a la pestaña **"Events"** o **"Logs"**
2. Observa el progreso del deploy:
   - ✅ **Build**: Instalando dependencias
   - ✅ **Release**: Ejecutando `alembic upgrade heads` (migraciones)
   - ✅ **Deploy**: Iniciando el servidor

**Tiempo estimado**: 5-10 minutos

---

## ✅ PASO 6: Verificar que el Deploy Fue Exitoso

### 6.1: Revisar Logs del Backend

En la pestaña **"Logs"**, busca estas líneas:

```
✅ Todos los routers registrados correctamente
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:10000
```

### 6.2: Verificar Health Check

Prueba en el navegador o con curl:

```bash
GET https://pagos-f2qf.onrender.com/api/v1/health/render
```

**Debe responder**: `{"status": "healthy", "service": "pagos-api"}`

---

## ✅ PASO 7: Verificar que los Endpoints Funcionan

### 7.1: Probar Endpoint de Analistas

**⚠️ IMPORTANTE**: Este endpoint requiere autenticación, pero podemos verificar si devuelve 401 (autenticación requerida) en lugar de 404 (no encontrado).

Prueba desde el frontend:
1. Abre: https://rapicredit.onrender.com/analistas
2. Inicia sesión si es necesario
3. Debe cargar los analistas

### 7.2: Verificar en los Logs del Backend

Cuando hagas una petición, en los logs del backend deberías ver:

```
✅ Listando X analistas de Y totales (página 1/Z)
```

**Si ves este log**: ✅ El endpoint está funcionando correctamente

**Si ves 404**: ❌ El backend aún no tiene los cambios (ver siguiente sección)

---

## 🔍 PASO 8: Si Persiste el 404

### 8.1: Verificar Código Desplegado

El problema puede ser que Render está usando código en caché. Intenta:

1. En Render Dashboard → `pagos-backend`
2. Ve a **"Settings"**
3. Busca **"Clear build cache"** o **"Force rebuild"**
4. Haz clic en **"Manual Deploy"** nuevamente

### 8.2: Verificar Variables de Entorno

Asegúrate de que estas variables estén configuradas:

- `DATABASE_URL`: (debe estar conectada a la base de datos)
- `LOG_LEVEL`: `INFO`
- `ENVIRONMENT`: `production`

### 8.3: Verificar que el Commit Incluye el Cambio

En los logs del deploy, verifica que el commit incluye:

```bash
# Debe mostrar algo como:
Building from commit: 87101da6
```

Y ese commit debe incluir el cambio de `@router.get("")` a `@router.get("/")`.

---

## ✅ PASO 9: Verificar desde el Frontend

Una vez que el backend se haya desplegado correctamente:

1. Abre: https://rapicredit.onrender.com
2. Inicia sesión
3. Ve a **"Analistas"**, **"Concesionarios"** y **"Modelos"**
4. Deben cargar los datos correctamente

---

## 📊 Verificación Final

### ✅ Deploy Exitoso Si:

- ✅ Logs muestran: `✅ Todos los routers registrados correctamente`
- ✅ Health check responde: `{"status": "healthy"}`
- ✅ Frontend puede cargar Analistas, Concesionarios y Modelos
- ✅ No hay errores 404 en la consola del navegador

### ❌ Si Aún Hay Problemas:

1. **Revisa los logs del proxy** (frontend) para ver la URL exacta que se intenta
2. **Revisa los logs del backend** para ver si recibe la petición
3. **Verifica autenticación**: El token puede no estar llegando correctamente

---

## 🆘 Soporte Adicional

Si después de seguir estos pasos el problema persiste:

1. **Captura los logs del backend** cuando hagas una petición a `/api/v1/analistas`
2. **Captura los logs del frontend** (proxy) cuando hagas la misma petición
3. **Comparte ambos logs** para diagnóstico adicional

---

**Última actualización**: 2025-11-01

