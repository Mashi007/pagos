# 🔍 Diagnóstico: Error de Conexión

## 📋 Descripción del Problema

Error de conexión mostrado en el frontend con el mensaje:
- **Título**: "Connection Error"
- **Mensaje**: "Connection failed. If the problem persists, please check your internet connection or VPN"
- **Request ID**: Se muestra un identificador único para cada solicitud fallida

## 🔎 Análisis del Código

### 1. Configuración del Proxy (Frontend)

**Archivo**: `frontend/server.js`

El proxy está configurado para redirigir todas las peticiones `/api/*` hacia el backend:

```javascript
const API_URL = process.env.API_BASE_URL || process.env.VITE_API_BASE_URL || process.env.VITE_API_URL || 'http://localhost:8000';
```

**Verificaciones necesarias**:
- ✅ Variable `API_BASE_URL` debe estar configurada en Render (runtime)
- ✅ Variable `VITE_API_URL` debe estar configurada para el build
- ⚠️ El proxy solo funciona si `API_URL` está configurado correctamente

### 2. Configuración de Variables de Entorno

**Archivo**: `render.yaml` y `frontend/render.yaml`

Variables configuradas:
```yaml
envVars:
  - key: VITE_API_URL
    value: https://pagos-f2qf.onrender.com
  - key: API_BASE_URL
    value: https://pagos-f2qf.onrender.com
```

**Estado**: ✅ Configuradas correctamente

### 3. Manejo de Errores en el Frontend

**Archivo**: `frontend/src/services/api.ts`

El código maneja diferentes tipos de errores de conexión:

```typescript
// Errores de red
if (
  errorCode === 'ERR_NETWORK' ||
  errorCode === 'ECONNREFUSED' ||
  errorMessage.includes('Connection refused') ||
  errorMessage.includes('NS_ERROR_CONNECTION_REFUSED')
) {
  console.warn('⚠️ Servidor no disponible temporalmente. Esto es normal durante reinicios.')
  return
}
```

### 4. Configuración CORS (Backend)

**Archivo**: `backend/app/core/config.py`

CORS está configurado para permitir:
- Producción: `https://rapicredit.onrender.com`
- Desarrollo: `http://localhost:3000`, `http://localhost:5173`, `https://rapicredit.onrender.com`

**⚠️ Posible problema**: Si el frontend está en una URL diferente a `https://rapicredit.onrender.com`, CORS bloqueará las peticiones.

## 🐛 Posibles Causas

### 1. Backend No Disponible
- El backend está caído o reiniciando
- El backend está en modo "sleep" (plan gratuito de Render)
- Problemas de red entre frontend y backend

### 2. Configuración Incorrecta del Proxy
- Variable `API_BASE_URL` no está configurada en Render
- El proxy no está interceptando las peticiones correctamente
- El path rewrite no está funcionando

### 3. Problemas de CORS
- El frontend está en una URL no permitida por CORS
- Headers de CORS no están configurados correctamente

### 4. Problemas de Red
- VPN bloqueando conexiones
- Firewall bloqueando peticiones
- Problemas de DNS

### 5. Timeout
- El backend tarda demasiado en responder
- Timeout configurado muy corto (30 segundos por defecto)

## ✅ Soluciones Recomendadas

### Solución 1: Verificar Estado del Backend

1. Verificar que el backend esté funcionando:
   ```bash
   curl https://pagos-f2qf.onrender.com/api/v1/health/render
   ```

2. Verificar logs del backend en Render:
   - Ir a Render Dashboard
   - Seleccionar el servicio `pagos-backend`
   - Revisar logs recientes

### Solución 2: Verificar Variables de Entorno

1. En Render Dashboard, verificar que las siguientes variables estén configuradas:
   - `API_BASE_URL=https://pagos-f2qf.onrender.com`
   - `VITE_API_URL=https://pagos-f2qf.onrender.com`

2. Si faltan, agregarlas y hacer redeploy del frontend

### Solución 3: Verificar CORS

1. Verificar la URL del frontend en Render
2. Si es diferente a `https://rapicredit.onrender.com`, agregarla a `CORS_ORIGINS` en el backend:
   ```python
   # En backend/app/core/config.py
   # O mediante variable de entorno CORS_ORIGINS
   ```

### Solución 4: Mejorar Manejo de Errores

Agregar más información de diagnóstico en los errores de conexión:

```typescript
// En frontend/src/services/api.ts
private handleError(error: unknown) {
  // ... código existente ...
  
  // Agregar más detalles para debugging
  if (error.request) {
    console.error('❌ Error de conexión:', {
      url: error.config?.url,
      method: error.config?.method,
      baseURL: API_BASE_URL,
      code: error.code,
      message: error.message
    })
  }
}
```

### Solución 5: Agregar Health Check

Verificar que el health check del backend funcione:

```bash
# Verificar health check
curl https://pagos-f2qf.onrender.com/api/v1/health/render

# Verificar health check del frontend
curl https://rapicredit.onrender.com/health
```

## 🔧 Mejoras Implementadas

### 1. Mejorar Logging de Errores

Agregar más información de diagnóstico cuando ocurre un error de conexión para facilitar el debugging.

### 2. Verificar Configuración CORS

Asegurar que el frontend esté incluido en los orígenes permitidos de CORS.

### 3. Agregar Retry Logic

Implementar lógica de reintento para errores temporales de conexión.

## 📝 Checklist de Verificación

- [ ] Backend está funcionando (`/api/v1/health/render` responde)
- [ ] Variables de entorno `API_BASE_URL` y `VITE_API_URL` están configuradas
- [ ] El proxy está interceptando peticiones `/api/*`
- [ ] CORS permite la URL del frontend
- [ ] No hay problemas de red/VPN
- [ ] Los logs del backend no muestran errores críticos
- [ ] El frontend puede hacer peticiones al backend directamente (sin proxy)

## 🚨 Acciones Inmediatas

1. **Verificar estado del backend**: Comprobar que el servicio esté activo en Render
2. **Revisar logs**: Verificar logs del backend y frontend en Render
3. **Verificar variables de entorno**: Confirmar que todas las variables estén configuradas
4. **Probar conexión directa**: Intentar hacer una petición directa al backend desde el navegador
5. **Verificar CORS**: Asegurar que el frontend esté en la lista de orígenes permitidos

## 📚 Referencias

- [Documentación del Proxy](Documentos/Auditorias/AUDITORIA_PROXY.md)
- [Configuración de Variables](Documentos/General/Verificaciones/VALIDACION_CONFIGURACION.md)
- [Solución de Problemas CORS](Documentos/General/Soluciones/SOLUCION_ECONNRESET.md)
