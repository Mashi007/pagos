# 📊 Guía de Verificación de Índices

## Script de Verificación

Ejecutar el script completo para verificar todos los índices:

```bash
psql -U usuario -d pagos_db -f backend/scripts/verificar_uso_indices.sql
```

O ejecutar cada query individualmente en tu herramienta de base de datos.

---

## Qué Buscar en los Resultados

### ✅ Indicadores de Éxito (Índice en Uso)

1. **Index Only Scan** - **EXCELENTE**
   ```
   Index Only Scan using idx_pagos_fecha_pago_activo_monto
   Heap Fetches: 0
   ```
   - El índice contiene toda la información necesaria
   - No necesita leer la tabla física
   - Máxima eficiencia

2. **Index Scan** - **IDEAL**
   ```
   Index Scan using idx_cuotas_fecha_vencimiento_estado
   ```
   - PostgreSQL usa el índice para buscar
   - Luego lee solo las filas necesarias de la tabla
   - Muy eficiente

3. **Bitmap Index Scan** - **BUENO**
   ```
   Bitmap Index Scan using idx_prestamos_fecha_registro_estado
   ```
   - PostgreSQL usa el índice para crear un bitmap
   - Útil para múltiples condiciones
   - Eficiente para queries complejas

### ❌ Indicador de Problema (Índice NO se Usa)

**Seq Scan** - **MALO**
```
Seq Scan on pagos
```
- PostgreSQL está haciendo un scan completo de la tabla
- No está usando ningún índice
- Muy lento en tablas grandes

---

## Verificaciones por Índice

### 1. `idx_pagos_fecha_pago_activo_monto`

**Query de Prueba:**
```sql
EXPLAIN ANALYZE
SELECT
    EXTRACT(YEAR FROM fecha_pago)::integer as año,
    EXTRACT(MONTH FROM fecha_pago)::integer as mes,
    COUNT(*) as cantidad,
    COALESCE(SUM(monto_pagado), 0) as monto_total
FROM pagos
WHERE fecha_pago >= '2024-01-01'::date
  AND fecha_pago <= '2024-12-31'::date
  AND monto_pagado IS NOT NULL
  AND monto_pagado > 0
  AND activo = TRUE
GROUP BY
    EXTRACT(YEAR FROM fecha_pago),
    EXTRACT(MONTH FROM fecha_pago)
ORDER BY año, mes;
```

**Resultado Esperado:**
- ✅ `Index Only Scan using idx_pagos_fecha_pago_activo_monto`
- ✅ `Execution Time: < 1ms` (muy rápido)

**Si no se usa:**
- Verificar que `ANALYZE pagos` se ejecutó
- Verificar que el índice existe
- Verificar que los filtros coinciden con el índice

---

### 2. `idx_cuotas_fecha_vencimiento_estado`

**Query de Prueba:**
```sql
EXPLAIN ANALYZE
SELECT
    EXTRACT(YEAR FROM c.fecha_vencimiento)::int as año,
    EXTRACT(MONTH FROM c.fecha_vencimiento)::int as mes,
    COALESCE(SUM(c.monto_cuota), 0) as cobranzas
FROM cuotas c
INNER JOIN prestamos p ON c.prestamo_id = p.id
WHERE p.estado = 'APROBADO'
  AND c.fecha_vencimiento >= '2024-01-01'::date
  AND c.fecha_vencimiento <= '2024-12-31'::date
GROUP BY EXTRACT(YEAR FROM c.fecha_vencimiento), EXTRACT(MONTH FROM c.fecha_vencimiento)
ORDER BY año, mes;
```

**Resultado Esperado:**
- ✅ `Index Scan using idx_cuotas_fecha_vencimiento_estado`
- ✅ `Execution Time: < 5ms`

---

### 3. `idx_prestamos_fecha_registro_estado`

**Query de Prueba:**
```sql
EXPLAIN ANALYZE
SELECT
    EXTRACT(YEAR FROM fecha_registro)::integer as año,
    EXTRACT(MONTH FROM fecha_registro)::integer as mes,
    COUNT(*) as cantidad,
    COALESCE(SUM(total_financiamiento), 0) as monto_total
FROM prestamos
WHERE fecha_registro >= '2024-01-01'::date
  AND fecha_registro <= '2024-12-31'::date
  AND estado = 'APROBADO'
GROUP BY EXTRACT(YEAR FROM fecha_registro), EXTRACT(MONTH FROM fecha_registro)
ORDER BY año, mes;
```

**Resultado Esperado:**
- ✅ `Index Scan using idx_prestamos_fecha_registro_estado`
- ✅ `Execution Time: < 5ms`

---

### 4. `idx_pagos_prestamo_id_activo_fecha`

**Query de Prueba:**
```sql
EXPLAIN ANALYZE
SELECT COALESCE(SUM(p.monto_pagado), 0)
FROM pagos p
INNER JOIN prestamos pr ON p.prestamo_id = pr.id
WHERE p.fecha_pago >= '2024-01-01'::date
  AND p.fecha_pago <= '2024-12-31'::date
  AND p.monto_pagado IS NOT NULL
  AND p.monto_pagado > 0
  AND p.activo = TRUE
  AND pr.estado = 'APROBADO';
```

**Resultado Esperado:**
- ✅ `Index Scan using idx_pagos_prestamo_id_activo_fecha`
- ✅ `Execution Time: < 10ms`

---

### 5. `idx_cuotas_prestamo_estado_fecha_vencimiento`

**Query de Prueba:**
```sql
EXPLAIN ANALYZE
SELECT
    c.prestamo_id,
    COUNT(c.id) as cuotas_vencidas,
    SUM(c.monto_cuota) as total_adeudado
FROM cuotas c
INNER JOIN prestamos p ON c.prestamo_id = p.id
WHERE c.fecha_vencimiento < CURRENT_DATE
  AND c.estado != 'PAGADO'
  AND p.estado = 'APROBADO'
GROUP BY c.prestamo_id
LIMIT 20;
```

**Resultado Esperado:**
- ✅ `Index Scan using idx_cuotas_prestamo_estado_fecha_vencimiento`
- ✅ `Execution Time: < 50ms`

---

## Solución de Problemas

### Si un índice NO se está usando:

1. **Verificar que el índice existe:**
   ```sql
   SELECT indexname, indexdef
   FROM pg_indexes
   WHERE indexname = 'idx_nombre_indice';
   ```

2. **Actualizar estadísticas:**
   ```sql
   ANALYZE tabla_nombre;
   ```

3. **Verificar que los filtros coinciden:**
   - El índice debe incluir las columnas usadas en WHERE
   - Los filtros del índice (WHERE en CREATE INDEX) deben coincidir

4. **Verificar tamaño de la tabla:**
   - En tablas muy pequeñas (< 1000 filas), PostgreSQL puede preferir Seq Scan
   - Esto es normal y aceptable

5. **Forzar uso del índice (último recurso):**
   ```sql
   SET enable_seqscan = OFF;
   EXPLAIN ANALYZE ...;
   SET enable_seqscan = ON;
   ```
   ⚠️ Solo para pruebas, no usar en producción

---

## Métricas de Performance Esperadas

| Query | Execution Time Esperado | Tiempo Anterior |
|-------|------------------------|-----------------|
| Evolución de pagos | < 1ms | 2-5 segundos |
| Cobranzas mensuales | < 5ms | 3-6 segundos |
| Financiamiento tendencia | < 5ms | 2-4 segundos |
| Clientes atrasados | < 50ms | 348ms |
| JOINs pagos-prestamos | < 10ms | 430-519ms |

---

## Resumen

✅ **Índices creados:** 5/5 críticos
✅ **ANALYZE ejecutado:** Todas las tablas
✅ **Verificación:** Usar script `verificar_uso_indices.sql`
✅ **Performance esperada:** Mejora de 70-85% en endpoints

