# 📊 ANÁLISIS DE LOGS: Índices Críticos de Performance

## 🎯 Objetivo

Verificar que la migración de índices críticos se ejecutó correctamente y medir el impacto en los tiempos de respuesta.

---

## ✅ PASO 1: Verificar Deploy en Render Dashboard

1. **Ir a**: https://dashboard.render.com
2. **Seleccionar servicio**: `pagos-backend`
3. **Verificar Events/Deploys**:
   - Debe mostrar commit: `32c75508` o más reciente
   - Mensaje: "feat: Agregar índices críticos de performance..."

---

## ✅ PASO 2: Analizar Logs del Release Command

En la pestaña **"Logs"** del servicio, busca durante la fase **"Release"**:

### ✅ Logs Esperados (ÉXITO):

```
🚀 Iniciando migración de índices críticos de performance...
✅ Índice 'idx_notificaciones_estado' creado en tabla 'notificaciones'
✅ Índice 'idx_notificaciones_leida' creado en tabla 'notificaciones'
✅ Índice 'idx_pagos_staging_fecha_timestamp' creado en tabla 'pagos_staging'
✅ Índice 'idx_pagos_staging_monto_numeric' creado en tabla 'pagos_staging'
✅ Índice 'idx_cuotas_vencimiento_estado' creado en tabla 'cuotas'
✅ Índice 'idx_cuotas_prestamo_id' creado en tabla 'cuotas'
✅ Índice 'idx_prestamos_estado' creado en tabla 'prestamos'
✅ Índice 'idx_prestamos_cedula' creado en tabla 'prestamos'

📊 Actualizando estadísticas de tablas...
✅ ANALYZE ejecutado en 'notificaciones'
✅ ANALYZE ejecutado en 'pagos_staging'
✅ ANALYZE ejecutado en 'cuotas'
✅ ANALYZE ejecutado en 'prestamos'

✅ Migración de índices críticos completada
📈 Impacto esperado: Reducción de timeouts de 57s a <500ms (114x mejora)
```

### ⚠️ Logs de Advertencia (Aceptables):

Si ves estos mensajes, es normal (significa que el índice ya existía o la columna no existe aún):

```
ℹ️ Índice 'idx_xxx' ya existe, omitiendo...
ℹ️ Columna 'xxx' no existe en 'xxx', omitiendo...
```

### ❌ Logs de Error (PROBLEMA):

```
⚠️ Advertencia: No se pudo crear índice 'idx_xxx': [error]
❌ Error ejecutando migración: [error]
```

**Si ves errores**, revisar:
- Permisos de la base de datos
- Conexión a PostgreSQL
- Sintaxis SQL

---

## ✅ PASO 3: Verificar Logs del Servidor

Después del deploy, en los logs del servidor, busca:

### ✅ Logs Esperados (ÉXITO):

```
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:10000
✅ Todos los routers registrados correctamente
```

### ⚠️ Verificar Cache:

Si el endpoint de notificaciones está usando cache, deberías ver en logs (si está habilitado logging de cache):

```
Cache hit para notificaciones/estadisticas/resumen
```

O en el primer request:

```
Cache miss para notificaciones/estadisticas/resumen
```

---

## ✅ PASO 4: Probar Endpoints y Medir Performance

### Opción A: Usar Script Automático

```bash
cd backend
python scripts/analizar_logs_performance.py
```

### Opción B: Probar Manualmente

#### 4.1: Endpoint Crítico (Notificaciones)

```bash
# Hacer 3 requests y medir tiempos
time curl -X GET "https://pagos-f2qf.onrender.com/api/v1/notificaciones/estadisticas/resumen" \
  -H "Authorization: Bearer [TOKEN]"
```

**Objetivo**: <500ms (vs 57s anterior = 114x mejora)

#### 4.2: Health Check

```bash
curl -X GET "https://pagos-f2qf.onrender.com/api/v1/health/render"
```

**Esperado**: `{"status": "healthy", "service": "pagos-api"}`

---

## 📊 MÉTRICAS DE ÉXITO

### ✅ ÉXITO COMPLETO:

- ✅ Todos los índices se crearon correctamente
- ✅ Endpoint `/api/v1/notificaciones/estadisticas/resumen` responde en **<500ms**
- ✅ Sin timeouts (>30s)
- ✅ Cache funcionando (segundos requests <100ms)

### ⚠️ ÉXITO PARCIAL:

- ✅ Índices creados
- ⚠️ Endpoint responde en **<2s** (mejora significativa pero no óptima)
- ⚠️ Algunos timeouts ocasionales

### ❌ PROBLEMA:

- ❌ Índices no se crearon
- ❌ Endpoint aún responde en **>10s**
- ❌ Timeouts frecuentes

---

## 🔍 ANÁLISIS AVANZADO: Verificar Índices en PostgreSQL

Si tienes acceso a la base de datos:

```sql
-- Verificar que los índices existen
SELECT
    schemaname,
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE tablename IN ('notificaciones', 'pagos_staging', 'cuotas', 'prestamos')
  AND indexname LIKE 'idx_%'
ORDER BY tablename, indexname;
```

**Debes ver 8 índices**:
- `idx_notificaciones_estado`
- `idx_notificaciones_leida`
- `idx_pagos_staging_fecha_timestamp`
- `idx_pagos_staging_monto_numeric`
- `idx_cuotas_vencimiento_estado`
- `idx_cuotas_prestamo_id`
- `idx_prestamos_estado`
- `idx_prestamos_cedula`

---

## 📈 COMPARACIÓN: Antes vs Después

### Antes (Sin Índices):

```
Endpoint: /api/v1/notificaciones/estadisticas/resumen
Tiempo promedio: 57,000ms (57 segundos)
Status: TIMEOUT frecuente
Queries: 5 COUNT separadas
```

### Después (Con Índices + Optimización):

```
Endpoint: /api/v1/notificaciones/estadisticas/resumen
Tiempo promedio objetivo: <500ms
Status: 200 OK
Queries: 1 GROUP BY (optimizada)
Cache: 5 minutos
```

**Mejora esperada**: **114x más rápido** (57s → <500ms)

---

## 🔧 TROUBLESHOOTING

### Problema 1: Índices no se crearon

**Causa**: Error en la migración o permisos

**Solución**:
1. Revisar logs completos del release command
2. Verificar permisos de la base de datos
3. Ejecutar migración manualmente si es necesario

### Problema 2: Tiempos aún altos (>5s)

**Causas posibles**:
- Índices no se están usando (verificar EXPLAIN ANALYZE)
- Cache no está funcionando
- Problema de red/conexión

**Solución**:
1. Verificar que los índices existen en PostgreSQL
2. Verificar que el query planner está usando los índices
3. Verificar configuración de Redis/cache

### Problema 3: Cache no funciona

**Causa**: Redis no está disponible o mal configurado

**Solución**:
1. Verificar que Redis está corriendo
2. Verificar variables de entorno de Redis
3. El sistema tiene fallback a MemoryCache si Redis falla

---

## 📝 PRÓXIMOS PASOS DESPUÉS DEL ANÁLISIS

1. ✅ Documentar tiempos reales de respuesta
2. ✅ Monitorear durante 24-48 horas
3. ✅ Verificar que no hay regresiones en otros endpoints
4. ✅ Si es exitoso, aplicar optimizaciones similares a otros endpoints críticos

---

## 📞 CONTACTO

Si encuentras problemas durante el análisis, revisar:
- Logs completos en Render Dashboard
- Estado de la base de datos
- Variables de entorno

