# 🚀 Guía para Crear Índices en Render

Esta guía te ayudará a crear los índices críticos de performance en el entorno de producción (Render) para mejorar significativamente los tiempos de respuesta del dashboard.

## 📋 Prerrequisitos

1. Acceso al servicio de backend en Render
2. Acceso a la base de datos PostgreSQL
3. Conocer la URL del backend (ej: `https://pagos-f2qf.onrender.com`)

---

## 🎯 Opción 1: Usar el Endpoint API (Recomendado)

### Paso 1: Verificar índices actuales

```bash
curl -X GET "https://pagos-f2qf.onrender.com/api/v1/database/indexes" \
  -H "Authorization: Bearer TU_TOKEN_JWT"
```

**Respuesta esperada:**
```json
{
  "status": "error",
  "total_found": 0,
  "total_missing": 13,
  "missing_indexes": [
    "notificaciones.idx_notificaciones_estado",
    "notificaciones.idx_notificaciones_tipo",
    ...
  ]
}
```

### Paso 2: Crear los índices faltantes

```bash
curl -X POST "https://pagos-f2qf.onrender.com/api/v1/database/indexes/create" \
  -H "Authorization: Bearer TU_TOKEN_JWT" \
  -H "Content-Type: application/json"
```

**Respuesta esperada:**
```json
{
  "status": "success",
  "created": [
    "notificaciones.idx_notificaciones_estado",
    "notificaciones.idx_notificaciones_tipo",
    ...
  ],
  "skipped": [],
  "errors": []
}
```

### Paso 3: Verificar que se crearon correctamente

```bash
curl -X GET "https://pagos-f2qf.onrender.com/api/v1/database/indexes" \
  -H "Authorization: Bearer TU_TOKEN_JWT"
```

**Respuesta esperada:**
```json
{
  "status": "success",
  "total_found": 13,
  "total_missing": 0,
  "message": "✅ Todos los índices críticos están presentes"
}
```

### Paso 4: Monitorear rendimiento después de crear índices

```bash
curl -X GET "https://pagos-f2qf.onrender.com/api/v1/database/indexes/performance" \
  -H "Authorization: Bearer TU_TOKEN_JWT"
```

**Respuesta esperada:**
```json
{
  "status": "success",
  "endpoints": {
    "financiamiento_tendencia_mensual": {
      "response_time_ms": 450.23,
      "expected_max_ms": 2000,
      "status": "fast",
      "improvement": "✅ Mejora detectada"
    },
    ...
  },
  "summary": {
    "total_tested": 4,
    "fast_endpoints": 4,
    "slow_endpoints": 0,
    "improvement_detected": true
  }
}
```

---

## 🎯 Opción 2: Usar Render Web Shell (Alternativa)

Si prefieres ejecutar el script manualmente:

### Paso 1: Abrir Render Web Shell

1. Ve a tu dashboard de Render
2. Selecciona el servicio `pagos-backend`
3. Haz clic en "Shell" en el menú lateral

### Paso 2: Navegar al directorio del backend

```bash
cd backend
```

### Paso 3: Ejecutar el script de creación de índices

```bash
python scripts/crear_indices_manual.py
```

**Salida esperada:**
```
================================================================================
🚀 CREANDO ÍNDICES CRÍTICOS DE PERFORMANCE
================================================================================

✅ Índice 'idx_notificaciones_estado' creado en tabla 'notificaciones'
✅ Índice 'idx_notificaciones_tipo' creado en tabla 'notificaciones'
...
✅ Índice funcional 'idx_cuotas_extract_year_month' creado en tabla 'cuotas'

📊 Actualizando estadísticas de tablas...
✅ ANALYZE ejecutado en 'notificaciones'
✅ ANALYZE ejecutado en 'cuotas'
...

================================================================================
📊 RESUMEN
================================================================================
✅ Índices creados: 13
ℹ️ Índices ya existentes: 0
```

---

## 📊 Verificación Post-Creación

### 1. Verificar índices creados

```bash
# Usando el endpoint
curl -X GET "https://pagos-f2qf.onrender.com/api/v1/database/indexes" \
  -H "Authorization: Bearer TU_TOKEN_JWT"
```

### 2. Monitorear rendimiento

```bash
# Verificar tiempos de respuesta de endpoints críticos
curl -X GET "https://pagos-f2qf.onrender.com/api/v1/database/indexes/performance" \
  -H "Authorization: Bearer TU_TOKEN_JWT"
```

### 3. Verificar logs del backend

Revisa los logs de Render para confirmar que:
- ✅ No hay errores de sintaxis SQL
- ✅ Los índices se crearon correctamente
- ✅ Los tiempos de respuesta mejoraron

**Ejemplo de log esperado:**
```
✅ Índice 'idx_cuotas_vencimiento_estado' creado en tabla 'cuotas'
✅ ANALYZE ejecutado en 'cuotas'
📊 [dashboard/financiamiento-tendencia] Query completada en 450ms (antes: 25000ms)
```

---

## 🎯 Índices que se Crearán

### Notificaciones (3 índices)
- `idx_notificaciones_estado`
- `idx_notificaciones_tipo`
- `idx_notificaciones_fecha_creacion`

### Cuotas (3 índices)
- `idx_cuotas_vencimiento_estado` (compuesto parcial)
- `idx_cuotas_prestamo_id`
- `idx_cuotas_extract_year_month` (funcional para GROUP BY)

### Préstamos (2 índices)
- `idx_prestamos_estado`
- `idx_prestamos_cedula`

### Pagos (1 índice)
- `ix_pagos_fecha_registro`

### Pagos Staging (4 índices funcionales)
- `idx_pagos_staging_fecha_timestamp`
- `idx_pagos_staging_monto_numeric`
- `idx_pagos_staging_extract_year`
- `idx_pagos_staging_extract_year_month`

**Total: 13 índices críticos**

---

## ⚠️ Solución de Problemas

### Error: "Not authenticated"
- **Causa**: El endpoint requiere autenticación
- **Solución**: Incluir el header `Authorization: Bearer TU_TOKEN_JWT`

### Error: "syntax error at or near"
- **Causa**: Error de sintaxis SQL (ya corregido en el código)
- **Solución**: Verificar que el código esté actualizado con la corrección del error SQL

### Error: "current transaction is aborted"
- **Causa**: Transacción abortada por error previo
- **Solución**: El código ya incluye rollback preventivo, pero si persiste, ejecutar nuevamente

### Los índices no se crean
- **Causa**: Puede ser que las columnas no existan o haya un problema de permisos
- **Solución**: 
  1. Verificar que las tablas existan
  2. Verificar permisos de la base de datos
  3. Revisar logs para ver errores específicos

---

## 📈 Impacto Esperado

Después de crear los índices, deberías ver:

- ✅ **Reducción de tiempos de respuesta**: De 17-31 segundos a <2 segundos
- ✅ **Mejora en queries de GROUP BY**: De 25+ segundos a <500ms
- ✅ **Mejora en filtros de fecha**: De 5+ segundos a <200ms
- ✅ **Mejora en estadísticas de notificaciones**: De 57 segundos a <500ms

---

## 🔄 Monitoreo Continuo

Después de crear los índices, monitorea regularmente:

1. **Tiempos de respuesta del dashboard**: Deberían estar consistentemente <2s
2. **Logs de errores**: No deberían aparecer errores de transacción abortada
3. **Uso de cache**: Verificar que el cache esté funcionando correctamente

**Endpoint de monitoreo:**
```bash
curl -X GET "https://pagos-f2qf.onrender.com/api/v1/database/indexes/performance" \
  -H "Authorization: Bearer TU_TOKEN_JWT"
```

---

## ✅ Checklist Final

- [ ] Índices creados (verificar con `/api/v1/database/indexes`)
- [ ] Rendimiento mejorado (verificar con `/api/v1/database/indexes/performance`)
- [ ] No hay errores SQL en logs
- [ ] Tiempos de respuesta del dashboard <2s
- [ ] Cache funcionando correctamente

---

**Última actualización**: 2025-11-06

