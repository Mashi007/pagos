# 🔍 AUDITORÍA COMPLETA DEL PROXY

## 📋 CHECKLIST DE VERIFICACIÓN

### 1. ✅ LOGS DEL PROXY (Frontend - Render)

#### Verificar:
- [ ] `🔄 Proxy middleware ejecutándose` - ¿Se ejecuta el wrapper?
- [ ] `🔄 Path rewrite` - ¿Se ejecuta el pathRewrite?
- [ ] `➡️  [GET] Proxying hacia backend` - ¿Se ejecuta onProxyReq?
- [ ] `✅/❌ Proxy response` - ¿Se ejecuta onProxyRes?
- [ ] `❌ Error en proxy` - ¿Hay errores en onError?

#### Si NO aparece `onProxyReq`:
- El proxy NO está enviando la petición al backend
- Posibles causas:
  1. Error silencioso en pathRewrite
  2. El middleware no se está ejecutando completamente
  3. Hay un problema con la configuración de http-proxy-middleware

---

### 2. ✅ CONFIGURACIÓN DEL PROXY

#### Verificar en `frontend/server.js`:
- [ ] `API_URL` está configurado correctamente: `https://pagos-f2qf.onrender.com`
- [ ] `target: API_URL` apunta al backend correcto
- [ ] `changeOrigin: true` está configurado
- [ ] `pathRewrite` extrae correctamente el path sin query string
- [ ] El middleware se registra ANTES de `express.static`

---

### 3. ✅ LOGS DEL BACKEND (Backend - Render)

#### Verificar:
- [ ] ¿Llegan peticiones a `/api/v1/clientes?`
- [ ] ¿Qué status code devuelve? (200, 403, 404, 500)
- [ ] ¿Hay errores en los logs del backend?
- [ ] ¿El backend está activo y respondiendo?

#### Si NO llegan peticiones:
- El proxy NO está enviando las peticiones
- Revisar configuración del proxy

#### Si llegan pero devuelven 403:
- Problema de autenticación/autorización
- Verificar headers `Authorization`

#### Si llegan pero devuelven 404:
- Problema de ruta en el backend
- Verificar que el endpoint existe: `/api/v1/clientes`

---

### 4. ✅ HEADERS Y AUTENTICACIÓN

#### Verificar:
- [ ] ¿El header `Authorization` se está pasando?
- [ ] ¿El token es válido?
- [ ] ¿Los headers se copian correctamente en `onProxyReq`?

#### En los logs buscar:
```
Headers Authorization: PRESENTE
```

---

### 5. ✅ CONFIGURACIÓN DE RENDER

#### Variables de Entorno (Frontend):
- [ ] `VITE_API_BASE_URL=https://pagos-f2qf.onrender.com`
- [ ] `VITE_API_URL=https://pagos-f2qf.onrender.com` (opcional)
- [ ] `NODE_ENV=production` (opcional pero recomendado)

#### Verificar:
- [ ] Ambas variables apuntan a la URL pública del backend
- [ ] NO usar Service ID (`srv-...`), usar URL pública

---

### 6. ✅ PRUEBAS DIRECTAS

#### Probar backend directamente:
```bash
curl https://pagos-f2qf.onrender.com/api/v1/clientes?page=1&per_page=20
```
- Si funciona directamente → Problema está en el proxy
- Si no funciona → Problema está en el backend

#### Probar desde el navegador:
- Abrir: `https://rapicredit.onrender.com/api/v1/clientes?page=1&per_page=20`
- Debería redirigir al backend o mostrar error del proxy

---

## 🔧 SOLUCIONES POTENCIALES

### Si el proxy NO envía peticiones:

1. **Revisar orden de middlewares**: El proxy debe ir ANTES de `express.static`
2. **Verificar que no hay errores silenciosos**: Revisar logs de `onError`
3. **Probar sin pathRewrite**: Ver si el problema es el pathRewrite
4. **Verificar versión de http-proxy-middleware**: Puede haber incompatibilidad

### Si el backend NO recibe peticiones:

1. **Verificar URL del backend**: Confirmar que `https://pagos-f2qf.onrender.com` es correcta
2. **Verificar conectividad**: El frontend debe poder alcanzar el backend
3. **Verificar SSL/TLS**: Problemas de certificados

### Si hay 403/404:

1. **Verificar ruta en backend**: Debe ser exactamente `/api/v1/clientes`
2. **Verificar autenticación**: El token debe ser válido
3. **Verificar CORS**: El backend debe permitir el origin del frontend

---

## 📊 LOGS ESPERADOS (Si todo funciona)

```
📥 [GET] Petición API recibida: /api/v1/clientes
🔄 Proxy middleware ejecutándose para: GET /v1/clientes
🔄 Path rewrite:
   Path recibido (con query?): "/v1/clientes?page=1&per_page=20"
   Path sin query: "/v1/clientes"
   Path reescrito: "/api/v1/clientes"
➡️  [GET] Proxying hacia backend
   Target URL completa: https://pagos-f2qf.onrender.com/api/v1/clientes?page=1&per_page=20
✅ [GET] Proxy response: 200 para /api/v1/clientes?page=1&per_page=20
```

---

## 🚨 ACCIONES INMEDIATAS

Cuando lleguen los logs, buscar:
1. ✅ ¿Aparece `🔄 Proxy middleware ejecutándose`?
2. ✅ ¿Aparece `➡️  Proxying hacia backend`?
3. ❌ ¿Hay errores en los logs?
4. ❌ ¿El backend recibe las peticiones?

Si algún paso falla, aplicar la solución correspondiente del checklist.

