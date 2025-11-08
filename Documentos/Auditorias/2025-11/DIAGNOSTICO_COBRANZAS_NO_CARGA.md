# 🔍 Diagnóstico: Módulo Cobranzas No Carga Datos

**Fecha:** 2025-11-XX  
**Problema:** El módulo de cobranzas no carga datos, muestra "Network Error"  
**Prioridad:** 🔴 CRÍTICA

---

## 📋 Síntomas Reportados

1. **Error en consola del navegador:**
   ```
   Error cargando dashboard: 
   Object { message: "Network Error", name: "AxiosError", code: "ERR_NETWORK", ... }
   ```

2. **Error de carga de módulo:**
   ```
   TypeError: error loading dynamically imported module: 
   https://rapicredit.onrender.com/assets/Cobranzas-CCoATXe_.js
   ```

3. **El módulo no muestra datos:**
   - Los KPIs no se cargan
   - Las tablas están vacías
   - Los gráficos no se renderizan

---

## 🔍 Análisis del Problema

### 1. ✅ Verificación de Backend

**Router registrado correctamente:**
```python
# backend/app/main.py:288
app.include_router(cobranzas.router, prefix="/api/v1/cobranzas", tags=["cobranzas"])
```

**Endpoints disponibles:**
- ✅ `/api/v1/cobranzas/health`
- ✅ `/api/v1/cobranzas/resumen`
- ✅ `/api/v1/cobranzas/clientes-atrasados`
- ✅ `/api/v1/cobranzas/por-analista`
- ✅ `/api/v1/cobranzas/montos-por-mes`

### 2. ✅ Verificación de Frontend

**Servicio configurado correctamente:**
```typescript
// frontend/src/services/cobranzasService.ts
private baseUrl = '/api/v1/cobranzas'
```

**Componente con manejo de errores:**
```typescript
// frontend/src/pages/Cobranzas.tsx
const { 
  data: resumen, 
  isLoading: cargandoResumen, 
  isError: errorResumen,
  error: errorResumenDetalle,
  refetch: refetchResumen
} = useQuery({
  queryKey: ['cobranzas-resumen'],
  queryFn: () => cobranzasService.getResumen(),
  retry: 2,
  retryDelay: 1000,
})
```

### 3. ⚠️ Posibles Causas

#### A. Error de Red (Network Error)

**Causas posibles:**
1. **Backend no está corriendo**
   - El servidor no está activo
   - El puerto está bloqueado
   - El servicio se cayó

2. **URL base incorrecta**
   - La variable de entorno `API_URL` no está configurada
   - La URL apunta a un servidor incorrecto
   - Problema con proxy o CORS

3. **Timeout de conexión**
   - El servidor tarda demasiado en responder
   - Timeout configurado muy bajo (30 segundos por defecto)
   - Problemas de red o latencia

#### B. Error de Carga de Módulo Dinámico

**Causa:**
- El archivo JavaScript del módulo no se puede cargar
- Problema con el build de producción
- Ruta incorrecta del archivo compilado

#### C. Problema de Autenticación

**Causa:**
- Token de autenticación expirado
- Token no se está enviando correctamente
- Usuario no tiene permisos

---

## 🔧 Soluciones Propuestas

### Solución 1: Verificar Backend

**Pasos:**
1. Verificar que el backend esté corriendo:
   ```bash
   # Verificar logs del backend
   tail -f backend/logs/app.log
   
   # Verificar que el puerto esté escuchando
   netstat -an | grep 8000  # o el puerto configurado
   ```

2. Probar endpoint directamente:
   ```bash
   curl -X GET "http://localhost:8000/api/v1/cobranzas/health" \
     -H "Authorization: Bearer YOUR_TOKEN"
   ```

3. Verificar logs del backend para errores:
   ```bash
   # Buscar errores relacionados con cobranzas
   grep -i "cobranzas\|error" backend/logs/app.log
   ```

### Solución 2: Verificar Configuración de Frontend

**Pasos:**
1. Verificar variable de entorno:
   ```typescript
   // frontend/src/config/env.ts
   console.log('API_URL:', env.API_URL)
   ```

2. Verificar que la URL base sea correcta:
   - En desarrollo: `http://localhost:8000`
   - En producción: `https://rapicredit.onrender.com`

3. Verificar configuración de CORS en backend:
   ```python
   # backend/app/core/config.py
   CORS_ORIGINS = [
       "http://localhost:5173",  # Desarrollo
       "https://rapicredit.onrender.com",  # Producción
   ]
   ```

### Solución 3: Aumentar Timeout

**Modificar timeout en apiClient:**
```typescript
// frontend/src/services/api.ts
const SLOW_ENDPOINT_TIMEOUT_MS = 120000 // Aumentar a 2 minutos

// O específicamente para cobranzas
async getResumen(): Promise<ResumenCobranzas> {
  return await apiClient.get(`${this.baseUrl}/resumen`, { 
    timeout: 120000 
  })
}
```

### Solución 4: Verificar Autenticación

**Agregar logging para debug:**
```typescript
// frontend/src/services/cobranzasService.ts
async getResumen(): Promise<ResumenCobranzas> {
  try {
    console.log('🔍 [Cobranzas] Llamando a:', `${this.baseUrl}/resumen`)
    const result = await apiClient.get(`${this.baseUrl}/resumen`)
    console.log('✅ [Cobranzas] Respuesta recibida:', result)
    return result
  } catch (error) {
    console.error('❌ [Cobranzas] Error:', error)
    throw error
  }
}
```

### Solución 5: Verificar Build de Producción

**Si el error es de carga de módulo dinámico:**
1. Verificar que el build se haya completado correctamente
2. Verificar que los archivos estáticos estén en el servidor
3. Verificar rutas de assets en configuración de Vite

---

## 🧪 Pruebas de Diagnóstico

### Test 1: Healthcheck del Módulo

```bash
# Desde el navegador (consola)
fetch('/api/v1/cobranzas/health', {
  headers: {
    'Authorization': `Bearer ${localStorage.getItem('access_token')}`
  }
})
.then(r => r.json())
.then(console.log)
.catch(console.error)
```

### Test 2: Verificar Conexión

```bash
# Desde terminal
curl -X GET "https://rapicredit.onrender.com/api/v1/cobranzas/health" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -v
```

### Test 3: Verificar en Red del Navegador

1. Abrir DevTools → Network
2. Filtrar por "cobranzas"
3. Intentar cargar el módulo
4. Verificar:
   - ¿Se hace la petición?
   - ¿Qué código de estado devuelve?
   - ¿Hay errores de CORS?
   - ¿Cuánto tarda la respuesta?

---

## 📝 Checklist de Verificación

- [ ] Backend está corriendo y accesible
- [ ] Endpoint `/api/v1/cobranzas/health` responde correctamente
- [ ] Variable `API_URL` está configurada correctamente
- [ ] CORS está configurado correctamente
- [ ] Token de autenticación es válido
- [ ] Timeout es suficiente para las queries
- [ ] No hay errores en la consola del navegador
- [ ] No hay errores en los logs del backend
- [ ] El build de producción está completo
- [ ] Los archivos estáticos están disponibles

---

## 🚨 Acciones Inmediatas

### Prioridad 1: Verificar Backend

1. **Verificar que el backend esté corriendo:**
   ```bash
   # En el servidor
   ps aux | grep uvicorn
   # O
   systemctl status backend-service
   ```

2. **Verificar logs del backend:**
   ```bash
   tail -f /var/log/backend/app.log | grep -i "cobranzas\|error"
   ```

3. **Probar endpoint directamente:**
   ```bash
   curl http://localhost:8000/api/v1/cobranzas/health
   ```

### Prioridad 2: Verificar Frontend

1. **Abrir consola del navegador y verificar:**
   - Errores de red
   - Errores de JavaScript
   - Estado de las peticiones

2. **Verificar configuración:**
   ```typescript
   // En consola del navegador
   console.log('API_URL:', import.meta.env.VITE_API_URL)
   ```

3. **Probar petición manual:**
   ```javascript
   // En consola del navegador
   fetch('/api/v1/cobranzas/resumen', {
     headers: {
       'Authorization': `Bearer ${localStorage.getItem('access_token')}`
     }
   })
   .then(r => r.json())
   .then(console.log)
   ```

### Prioridad 3: Aumentar Logging

Agregar logging detallado para identificar el problema exacto:

```typescript
// frontend/src/services/cobranzasService.ts
async getResumen(): Promise<ResumenCobranzas> {
  const url = `${this.baseUrl}/resumen`
  console.log('🔍 [Cobranzas] Iniciando petición a:', url)
  console.log('🔍 [Cobranzas] Base URL:', this.baseUrl)
  
  try {
    const startTime = Date.now()
    const result = await apiClient.get(url)
    const duration = Date.now() - startTime
    console.log(`✅ [Cobranzas] Respuesta recibida en ${duration}ms:`, result)
    return result
  } catch (error: any) {
    console.error('❌ [Cobranzas] Error completo:', {
      message: error.message,
      code: error.code,
      response: error.response,
      config: error.config
    })
    throw error
  }
}
```

---

## 📊 Información de Debug

### Headers de Petición Esperados

```
GET /api/v1/cobranzas/resumen HTTP/1.1
Host: rapicredit.onrender.com
Authorization: Bearer <token>
Content-Type: application/json
```

### Respuesta Esperada

```json
{
  "total_cuotas_vencidas": 0,
  "monto_total_adeudado": 0.0,
  "clientes_atrasados": 0
}
```

### Códigos de Error Posibles

- **401 Unauthorized:** Token expirado o inválido
- **403 Forbidden:** Usuario sin permisos
- **404 Not Found:** Endpoint no existe
- **500 Internal Server Error:** Error en el servidor
- **503 Service Unavailable:** Servicio no disponible
- **ERR_NETWORK:** Error de conexión (servidor no responde)

---

## 🔄 Próximos Pasos

1. **Ejecutar pruebas de diagnóstico** (Test 1, 2, 3)
2. **Revisar logs del backend** para errores específicos
3. **Verificar configuración de red** (CORS, proxy, firewall)
4. **Aumentar timeout** si las queries son lentas
5. **Agregar logging detallado** para identificar el problema exacto

---

**Última actualización:** 2025-11-XX  
**Estado:** 🔴 En investigación

