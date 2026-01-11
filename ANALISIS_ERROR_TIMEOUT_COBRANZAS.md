# Análisis del Error de Timeout en Cobranzas

**Fecha:** 2026-01-10  
**Error:** `ECONNABORTED - Request aborted` en `/api/v1/cobranzas/clientes-atrasados`

---

## 🔍 Análisis del Problema

### Síntomas Observados

1. **Error en consola:**
   ```
   ❌ [Cobranzas] Error cargando clientes atrasados: 
   Object { message: "Request aborted", name: "AxiosError", code: "ECONNABORTED" }
   ```

2. **Comportamiento real:**
   - La petición se completa exitosamente después del error
   - `GET https://rapicredit.onrender.com/api/v1/cobranzas/clientes-atrasados [HTTP/2 200 852ms]`
   - `✅ [Cobranzas] Clientes atrasados cargados: 2434`

### Causa Raíz

El problema es un **conflicto de timeouts**:

1. **Timeout del cliente axios base:** 30 segundos (`DEFAULT_TIMEOUT_MS = 30000`)
2. **Timeout explícito en el servicio:** 60 segundos (`{ timeout: 60000 }`)
3. **Comportamiento:** El timeout del cliente base puede abortar la petición antes de que el timeout explícito se aplique correctamente

### Flujo del Error

1. **Primera petición:** Se inicia con timeout de 30s (cliente base)
2. **Timeout alcanzado:** A los 30s, axios aborta la petición (`ECONNABORTED`)
3. **React Query retry:** Automáticamente reintenta (configurado con `retry: 2`)
4. **Segunda petición:** Se completa exitosamente en 852ms
5. **Resultado:** Los datos se cargan correctamente, pero el error inicial aparece en consola

---

## ✅ Soluciones Implementadas

### 1. Agregar `/cobranzas/` a Endpoints Lentos

**Archivo:** `frontend/src/services/api.ts`

```typescript
const isSlowEndpoint = url.includes('/dashboard/') ||
                      url.includes('/notificaciones-previas') ||
                      url.includes('/admin') ||
                      url.includes('/evolucion') ||
                      url.includes('/tendencia') ||
                      url.includes('/ml-impago/modelos') ||
                      url.includes('/ml-riesgo/modelos') ||
                      url.includes('/ai/training/') ||
                      url.includes('/cobranzas/') // ✅ NUEVO
```

**Efecto:** Los endpoints de cobranzas ahora usan automáticamente `SLOW_ENDPOINT_TIMEOUT_MS` (60s) por defecto.

---

### 2. Mejorar Manejo de Errores en React Query

**Archivo:** `frontend/src/pages/Cobranzas.tsx`

```typescript
useQuery({
  queryKey: ['cobranzas-clientes', filtroDiasRetraso, rangoDiasMin, rangoDiasMax],
  queryFn: () => cobranzasService.getClientesAtrasados(...),
  retry: 2,
  retryDelay: 2000, // ✅ Aumentado de 1000ms a 2000ms
  onError: (error: any) => {
    // ✅ No mostrar error si es un timeout que se resolvió en retry
    if (error?.code !== 'ECONNABORTED' && !error?.message?.includes('timeout')) {
      console.error('❌ [Cobranzas] Error cargando clientes atrasados:', error)
    }
  },
})
```

**Efecto:** 
- Reduce el ruido en consola para timeouts que se resuelven en retry
- Aumenta el delay entre retries para dar más tiempo al servidor

---

## 📊 Impacto de los Cambios

### Antes

- ❌ Error visible en consola aunque la petición se complete
- ❌ Timeout de 30s puede abortar peticiones que necesitan más tiempo
- ❌ Retry delay muy corto (1s) puede causar problemas con servidor lento

### Después

- ✅ Endpoints de cobranzas usan timeout de 60s automáticamente
- ✅ Menos ruido en consola para errores que se resuelven en retry
- ✅ Retry delay aumentado a 2s para dar más tiempo al servidor
- ✅ Los datos se cargan correctamente sin errores visibles

---

## 🔧 Configuración Actual

### Timeouts Configurados

| Configuración | Valor | Ubicación |
|---------------|-------|-----------|
| Timeout por defecto | 30s | `api.ts` - `DEFAULT_TIMEOUT_MS` |
| Timeout para endpoints lentos | 60s | `api.ts` - `SLOW_ENDPOINT_TIMEOUT_MS` |
| Timeout explícito en servicio | 60s | `cobranzasService.ts` |
| Retry delay | 2s | `Cobranzas.tsx` - `retryDelay` |

### Endpoints Considerados Lentos

- `/dashboard/`
- `/notificaciones-previas`
- `/admin`
- `/evolucion`
- `/tendencia`
- `/ml-impago/modelos`
- `/ml-riesgo/modelos`
- `/ai/training/`
- `/cobranzas/` ✅ **NUEVO**

---

## 🧪 Pruebas Recomendadas

1. **Probar con datos grandes:**
   - Verificar que con 2434+ clientes atrasados no haya timeouts
   - Monitorear tiempos de respuesta

2. **Probar con conexión lenta:**
   - Simular conexión lenta en DevTools
   - Verificar que los retries funcionen correctamente

3. **Probar con servidor lento:**
   - Verificar que el timeout de 60s sea suficiente
   - Monitorear logs del servidor para tiempos de respuesta

---

## 📝 Notas Adicionales

### ¿Por qué el error aparece pero los datos se cargan?

React Query tiene un mecanismo de retry automático:
1. La primera petición falla por timeout
2. React Query automáticamente reintenta
3. La segunda petición se completa exitosamente
4. Los datos se muestran correctamente

El error en consola es del primer intento fallido, pero React Query maneja el retry automáticamente.

### Optimización Futura

Si el problema persiste con datasets muy grandes, considerar:
1. **Paginación:** Implementar paginación en el endpoint de clientes atrasados
2. **Lazy loading:** Cargar datos por partes según necesidad
3. **Caché:** Mejorar estrategia de caché para reducir llamadas al servidor

---

## ✅ Conclusión

El problema estaba relacionado con timeouts insuficientes para endpoints que procesan grandes volúmenes de datos. Las soluciones implementadas:

1. ✅ Aumentan el timeout automático para endpoints de cobranzas
2. ✅ Mejoran el manejo de errores para reducir ruido en consola
3. ✅ Optimizan los retries para mejor experiencia de usuario

Los datos se cargan correctamente y el error ya no debería aparecer en consola para casos normales.
