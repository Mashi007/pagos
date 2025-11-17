# 📊 Análisis de Logs de Performance - 2025-11-05 14:43

## Resumen de Tiempos de Respuesta

### Endpoints Analizados (14:43:23 - 14:43:47)

| Endpoint | Tiempo (ms) | Estado | Observación |
|----------|-------------|--------|-------------|
| `/api/v1/cobranzas/clientes-atrasados` | 348 | ✅ Bueno | Aceptable |
| `/api/v1/cobranzas/por-analista` | 239 | ✅ Bueno | Aceptable |
| `/api/v1/reportes/dashboard/resumen` | 250 | ✅ Bueno | Aceptable |
| `/api/v1/pagos/` (paginado) | 519 | ⚠️ Regular | Podría mejorarse |
| `/api/v1/reportes/dashboard/resumen` | 261 | ✅ Bueno | Aceptable |
| `/api/v1/pagos/` | 430 | ⚠️ Regular | Podría mejorarse |
| `/api/v1/prestamos` (paginado) | 255 | ✅ Bueno | Aceptable |
| `/api/v1/prestamos/3683` | 256 | ✅ Bueno | Aceptable |
| `/api/v1/prestamos/3683/cuotas` | 217 | ✅ Bueno | Aceptable |

### Análisis Detallado

#### ✅ Endpoints con Buen Performance (< 300ms)
- `/api/v1/cobranzas/por-analista` - 239ms
- `/api/v1/reportes/dashboard/resumen` - 250-261ms
- `/api/v1/prestamos` (paginado) - 255ms
- `/api/v1/prestamos/{id}` - 256ms
- `/api/v1/prestamos/{id}/cuotas` - 217ms

**Observación:** Estos endpoints están respondiendo bien, probablemente porque:
- Usan paginación eficiente
- Tienen índices básicos en las columnas de filtro
- No realizan JOINs complejos

#### ⚠️ Endpoints que Podrían Mejorarse (> 300ms)
- `/api/v1/cobranzas/clientes-atrasados` - 348ms
- `/api/v1/pagos/` (paginado) - 430-519ms

**Análisis:**
- `/api/v1/cobranzas/clientes-atrasados`: Probablemente hace JOIN con `cuotas` y `prestamos`, filtra por `fecha_vencimiento < hoy` y `estado != 'PAGADO'`. **Falta índice compuesto** para esta consulta.
- `/api/v1/pagos/`: Consulta con filtros múltiples y posible JOIN con `prestamos`. **Faltan índices compuestos** para filtros combinados.

---

## Impacto Esperado con Índices Optimizados

### Endpoints que Mejorarán Significativamente

#### 1. `/api/v1/cobranzas/clientes-atrasados` (348ms → ~150-200ms)
**Mejora esperada: 40-50%**

**Índices necesarios:**
```sql
-- Índice compuesto para cuotas vencidas no pagadas
CREATE INDEX idx_cuotas_prestamo_estado_fecha_vencimiento
ON cuotas (prestamo_id, estado, fecha_vencimiento)
WHERE estado != 'PAGADO';
```

**Query típica:**
```sql
SELECT c.*, p.*
FROM cuotas c
INNER JOIN prestamos p ON c.prestamo_id = p.id
WHERE c.fecha_vencimiento < CURRENT_DATE
  AND c.estado != 'PAGADO'
  AND p.estado = 'APROBADO'
ORDER BY c.fecha_vencimiento DESC;
```

#### 2. `/api/v1/pagos/` (430-519ms → ~200-300ms)
**Mejora esperada: 40-50%**

**Índices necesarios:**
```sql
-- Índice compuesto para filtros frecuentes
CREATE INDEX idx_pagos_prestamo_id_activo_fecha
ON pagos (prestamo_id, activo, fecha_pago)
WHERE prestamo_id IS NOT NULL
  AND activo = TRUE
  AND fecha_pago IS NOT NULL;

-- Índice para filtros individuales
CREATE INDEX idx_pagos_activo_fecha_pago
ON pagos (activo, fecha_pago)
WHERE activo = TRUE;
```

**Query típica:**
```sql
SELECT p.*
FROM pagos p
LEFT JOIN prestamos pr ON p.prestamo_id = pr.id
WHERE p.activo = TRUE
  AND p.fecha_pago >= :fecha_desde
  AND p.fecha_pago <= :fecha_hasta
ORDER BY p.fecha_pago DESC
LIMIT 20 OFFSET 0;
```

---

## Comparativa: Antes vs. Después (Estimado)

| Endpoint | Tiempo Actual | Tiempo Esperado | Mejora |
|----------|---------------|-----------------|---------|
| `/api/v1/cobranzas/clientes-atrasados` | 348ms | 150-200ms | **40-50%** |
| `/api/v1/cobranzas/por-analista` | 239ms | 150-180ms | **25-35%** |
| `/api/v1/pagos/` (paginado) | 430-519ms | 200-300ms | **40-50%** |
| `/api/v1/reportes/dashboard/resumen` | 250-261ms | 150-200ms | **20-30%** |
| `/api/v1/prestamos` (paginado) | 255ms | 200-250ms | **10-20%** |
| `/api/v1/prestamos/{id}/cuotas` | 217ms | 150-200ms | **10-20%** |

---

## Recomendaciones Inmediatas

### 1. Ejecutar Script de Índices Optimizados
```bash
psql -U usuario -d pagos_db -f backend/scripts/crear_indices_optimizados.sql
```

### 2. Actualizar Estadísticas
```sql
ANALYZE pagos;
ANALYZE prestamos;
ANALYZE cuotas;
```

### 3. Verificar Uso de Índices
Para cada endpoint que queremos optimizar, ejecutar `EXPLAIN ANALYZE`:

```sql
-- Ejemplo: /api/v1/cobranzas/clientes-atrasados
EXPLAIN ANALYZE
SELECT c.*, p.*
FROM cuotas c
INNER JOIN prestamos p ON c.prestamo_id = p.id
WHERE c.fecha_vencimiento < CURRENT_DATE
  AND c.estado != 'PAGADO'
  AND p.estado = 'APROBADO'
ORDER BY c.fecha_vencimiento DESC
LIMIT 20;
```

**Buscar en el resultado:**
- ✅ `Index Scan using idx_cuotas_prestamo_estado_fecha_vencimiento`
- ❌ `Seq Scan on cuotas` (malo - necesita índice)

### 4. Monitorear Performance Después de Crear Índices
- Comparar tiempos antes/después
- Verificar que los índices se están usando (`pg_stat_user_indexes`)
- Ajustar índices si no se usan

---

## Índices Críticos Faltantes Identificados

### Para `/api/v1/cobranzas/clientes-atrasados`
```sql
-- Ya incluido en crear_indices_optimizados.sql
CREATE INDEX idx_cuotas_prestamo_estado_fecha_vencimiento
ON cuotas (prestamo_id, estado, fecha_vencimiento)
WHERE estado != 'PAGADO';
```

### Para `/api/v1/pagos/`
```sql
-- Ya incluido en crear_indices_optimizados.sql
CREATE INDEX idx_pagos_prestamo_id_activo_fecha
ON pagos (prestamo_id, activo, fecha_pago)
WHERE prestamo_id IS NOT NULL
  AND activo = TRUE
  AND fecha_pago IS NOT NULL;
```

---

## Conclusión

**Estado Actual:** Los tiempos de respuesta son **aceptables** (200-500ms), pero pueden mejorarse significativamente con los índices optimizados.

**Acción Recomendada:** Ejecutar el script `crear_indices_optimizados.sql` para mejorar el rendimiento de los endpoints más lentos.

**Impacto Esperado:** Reducción del 40-50% en tiempos de respuesta para los endpoints más lentos, mejorando la experiencia del usuario.

