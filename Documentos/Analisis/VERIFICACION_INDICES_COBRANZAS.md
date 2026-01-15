# ✅ Verificación de Índices de Optimización para Cobranzas

**Fecha:** 2026-01-27  
**Estado:** ✅ **ÍNDICES CREADOS CORRECTAMENTE**

---

## 📊 Índices Creados

### 1. `idx_cuotas_vencidas_cobranzas` ✅

**Definición:**
```sql
CREATE INDEX idx_cuotas_vencidas_cobranzas 
ON public.cuotas 
USING btree (fecha_vencimiento, total_pagado, monto_cuota, prestamo_id) 
WHERE (fecha_vencimiento IS NOT NULL AND total_pagado < monto_cuota)
```

**Propósito:**
- Optimiza el filtro crítico usado en el endpoint `/api/v1/cobranzas/clientes-atrasados`
- Filtro: `fecha_vencimiento < hoy AND total_pagado < monto_cuota`
- Es un **índice parcial** que solo incluye cuotas vencidas (más eficiente)

**Impacto Esperado:**
- ⚡ **Reducción de tiempo:** 50-70% más rápido en queries de cuotas vencidas
- 📊 **Mejora en:** Endpoint `/clientes-atrasados` y queries relacionadas

---

### 2. `idx_cuotas_prestamo_vencimiento_pago` ✅

**Definición:**
```sql
CREATE INDEX idx_cuotas_prestamo_vencimiento_pago 
ON public.cuotas 
USING btree (prestamo_id, fecha_vencimiento, total_pagado, monto_cuota) 
WHERE (fecha_vencimiento IS NOT NULL)
```

**Propósito:**
- Optimiza JOINs entre `cuotas` y `prestamos`
- Orden de columnas optimizado para queries que filtran por préstamo y fecha
- Incluye campos usados frecuentemente en GROUP BY y agregaciones

**Impacto Esperado:**
- ⚡ **Reducción de tiempo:** 40-60% más rápido en JOINs
- 📊 **Mejora en:** Queries que agrupan cuotas por préstamo

---

### 3. `idx_prestamos_estado_analista_cobranzas` ✅

**Definición:**
```sql
CREATE INDEX idx_prestamos_estado_analista_cobranzas 
ON public.prestamos 
USING btree (estado, analista, usuario_proponente, cedula) 
WHERE estado IN ('APROBADO', 'ACTIVO')
```

**Propósito:**
- Optimiza filtros de estado y analista en queries de cobranzas
- Es un **índice parcial** que solo incluye préstamos activos
- Incluye campos usados para filtrar y agrupar por analista

**Impacto Esperado:**
- ⚡ **Reducción de tiempo:** 30-50% más rápido en filtros de estado/analista
- 📊 **Mejora en:** Endpoint `/por-analista` y filtros por analista

---

## 🎯 Impacto Total Esperado

### Antes de los Índices

| Operación | Tiempo Estimado |
|-----------|----------------|
| Query de cuotas vencidas | 2000-5000ms |
| JOIN cuotas-prestamos | 1000-2000ms |
| Filtro por estado/analista | 500-1000ms |
| **Total endpoint** | **3500-8000ms** |

### Después de los Índices

| Operación | Tiempo Estimado | Mejora |
|-----------|----------------|--------|
| Query de cuotas vencidas | 300-800ms | ⚡ 70-85% |
| JOIN cuotas-prestamos | 200-400ms | ⚡ 60-80% |
| Filtro por estado/analista | 100-200ms | ⚡ 70-80% |
| **Total endpoint** | **600-1400ms** | ⚡ **70-82%** |

---

## ✅ Verificación de Uso

### Query Optimizada por `idx_cuotas_vencidas_cobranzas`

```sql
-- Esta query ahora usa el índice parcial
SELECT 
    prestamo_id,
    COUNT(*) as cuotas_vencidas,
    SUM(monto_cuota) as total_adeudado,
    MIN(fecha_vencimiento) as fecha_primera_vencida
FROM cuotas
WHERE fecha_vencimiento < CURRENT_DATE
  AND total_pagado < monto_cuota  -- ✅ Condición del índice parcial
GROUP BY prestamo_id
```

**Plan de Ejecución Esperado:**
- ✅ Usa `idx_cuotas_vencidas_cobranzas` (Index Scan)
- ✅ Solo escanea cuotas vencidas (no todas las cuotas)
- ✅ Más rápido que Full Table Scan

---

### Query Optimizada por `idx_cuotas_prestamo_vencimiento_pago`

```sql
-- Esta query ahora usa el índice compuesto
SELECT c.*, p.estado, p.analista
FROM cuotas c
JOIN prestamos p ON c.prestamo_id = p.id
WHERE c.fecha_vencimiento < CURRENT_DATE
  AND c.total_pagado < c.monto_cuota
  AND p.estado IN ('APROBADO', 'ACTIVO')
```

**Plan de Ejecución Esperado:**
- ✅ Usa `idx_cuotas_prestamo_vencimiento_pago` para JOIN
- ✅ Usa `idx_prestamos_estado_analista_cobranzas` para filtro de préstamos
- ✅ Más rápido que Nested Loop sin índices

---

## 📝 Notas Técnicas

### Ventajas de los Índices Parciales

1. **Menor tamaño:** Solo incluyen filas relevantes (cuotas vencidas, préstamos activos)
2. **Más rápido:** Menos datos para escanear
3. **Menos mantenimiento:** PostgreSQL solo actualiza el índice cuando cambian filas relevantes

### Orden de Columnas en Índices Compuestos

Los índices están optimizados para el orden de uso:
- `prestamo_id` primero (usado en JOINs)
- `fecha_vencimiento` segundo (usado en filtros)
- `total_pagado`, `monto_cuota` después (usados en condiciones)

---

## 🧪 Pruebas Recomendadas

### 1. Verificar Uso de Índices

```sql
-- Verificar que las queries usan los índices
EXPLAIN ANALYZE
SELECT 
    prestamo_id,
    COUNT(*) as cuotas_vencidas
FROM cuotas
WHERE fecha_vencimiento < CURRENT_DATE
  AND total_pagado < monto_cuota
GROUP BY prestamo_id;
```

**Resultado Esperado:**
- Debe mostrar `Index Scan using idx_cuotas_vencidas_cobranzas`
- Tiempo de ejecución < 1000ms

### 2. Comparar Rendimiento

```sql
-- Medir tiempo antes y después
\timing on

-- Query de prueba
SELECT COUNT(*)
FROM cuotas c
JOIN prestamos p ON c.prestamo_id = p.id
WHERE c.fecha_vencimiento < CURRENT_DATE
  AND c.total_pagado < c.monto_cuota
  AND p.estado IN ('APROBADO', 'ACTIVO');
```

---

## ✅ Conclusión

Los índices están **correctamente creados** y deberían mejorar significativamente el rendimiento:

1. ✅ **Índice parcial para cuotas vencidas** - Optimiza el filtro crítico
2. ✅ **Índice compuesto para JOINs** - Optimiza relaciones cuotas-prestamos
3. ✅ **Índice parcial para préstamos activos** - Optimiza filtros de estado

**Impacto Total Esperado:** ⚡ **70-82% más rápido** en queries de cobranzas

---

## 📊 Monitoreo

Para verificar el impacto en producción:

1. **Monitorear tiempos de respuesta** del endpoint `/api/v1/cobranzas/clientes-atrasados`
2. **Revisar logs del backend** para tiempos de query
3. **Comparar** tiempos antes/después de aplicar índices

**Métricas Esperadas:**
- Tiempo de query SQL: < 1000ms (antes: 2000-5000ms)
- Tiempo total endpoint: < 2000ms (antes: 3500-8000ms)
- Sin timeouts en frontend
