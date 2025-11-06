# 🔧 SOLUCIÓN: Índice No Se Está Usando

## ⚠️ PROBLEMA DETECTADO

El `EXPLAIN ANALYZE` muestra:
- **Seq Scan on prestamos** (escaneo secuencial)
- **NO está usando** `idx_prestamos_fecha_aprobacion_ym`

Aunque el índice existe, PostgreSQL no lo está usando.

---

## 🔍 POSIBLES CAUSAS

### 1. **PostgreSQL considera Seq Scan más rápido**
- Con pocos datos (36 filas), un Seq Scan puede ser más rápido
- PostgreSQL elige el plan más eficiente según estadísticas

### 2. **Estadísticas desactualizadas**
- Las estadísticas de la tabla pueden estar desactualizadas
- PostgreSQL no sabe que el índice es útil

### 3. **Índice funcional no reconocido**
- Los índices funcionales con EXTRACT pueden no ser reconocidos en todas las versiones

---

## ✅ SOLUCIONES

### SOLUCIÓN 1: Actualizar Estadísticas (Recomendado)

```sql
-- Actualizar estadísticas de la tabla
ANALYZE prestamos;

-- Verificar estadísticas
SELECT 
    schemaname,
    tablename,
    last_analyze,
    last_autoanalyze
FROM pg_stat_user_tables
WHERE tablename = 'prestamos';
```

Luego ejecutar de nuevo:
```sql
EXPLAIN ANALYZE 
SELECT 
    EXTRACT(YEAR FROM fecha_aprobacion),
    EXTRACT(MONTH FROM fecha_aprobacion),
    COUNT(*)
FROM prestamos
WHERE estado = 'APROBADO'
GROUP BY EXTRACT(YEAR FROM fecha_aprobacion), EXTRACT(MONTH FROM fecha_aprobacion);
```

---

### SOLUCIÓN 2: Verificar que el Índice Esté Correctamente Creado

```sql
-- Verificar definición del índice
SELECT 
    indexname,
    indexdef
FROM pg_indexes
WHERE indexname = 'idx_prestamos_fecha_aprobacion_ym';

-- Verificar que el índice esté activo
SELECT 
    indexrelid::regclass AS index_name,
    indisvalid,
    indisready,
    indislive
FROM pg_index
WHERE indexrelid = 'idx_prestamos_fecha_aprobacion_ym'::regclass;
```

**Resultado esperado:**
- `indisvalid = true` (índice válido)
- `indisready = true` (índice listo)
- `indislive = true` (índice activo)

---

### SOLUCIÓN 3: Forzar Uso del Índice (Solo para Pruebas)

```sql
-- Deshabilitar Seq Scan temporalmente (solo para pruebas)
SET enable_seqscan = OFF;

-- Ejecutar query
EXPLAIN ANALYZE 
SELECT 
    EXTRACT(YEAR FROM fecha_aprobacion),
    EXTRACT(MONTH FROM fecha_aprobacion),
    COUNT(*)
FROM prestamos
WHERE estado = 'APROBADO'
GROUP BY EXTRACT(YEAR FROM fecha_aprobacion), EXTRACT(MONTH FROM fecha_aprobacion);

-- Restaurar configuración
SET enable_seqscan = ON;
```

**⚠️ IMPORTANTE:** Esto es solo para verificar que el índice funciona. NO dejar `enable_seqscan = OFF` en producción.

---

### SOLUCIÓN 4: Verificar Tamaño de la Tabla

```sql
-- Ver tamaño de la tabla y número de filas
SELECT 
    pg_size_pretty(pg_total_relation_size('prestamos')) AS total_size,
    pg_size_pretty(pg_relation_size('prestamos')) AS table_size,
    pg_size_pretty(pg_total_relation_size('prestamos') - pg_relation_size('prestamos')) AS indexes_size,
    (SELECT COUNT(*) FROM prestamos) AS row_count,
    (SELECT COUNT(*) FROM prestamos WHERE estado = 'APROBADO') AS aprobados_count;
```

**Si la tabla es pequeña (< 10,000 filas):**
- PostgreSQL puede preferir Seq Scan porque es más rápido
- Esto es **normal y correcto**
- El índice será útil cuando la tabla crezca

---

### SOLUCIÓN 5: Verificar Configuración de PostgreSQL

```sql
-- Ver configuración relacionada con índices
SHOW random_page_cost;
SHOW seq_page_cost;
SHOW effective_cache_size;
SHOW work_mem;

-- Valores recomendados para producción:
-- random_page_cost = 1.1 (SSD) o 4.0 (HDD)
-- seq_page_cost = 1.0
-- effective_cache_size = 50% de RAM disponible
-- work_mem = 256MB (para queries complejas)
```

---

## 📊 ANÁLISIS DEL QUERY PLAN ACTUAL

### Lo que muestra:
- **Seq Scan**: Escanea toda la tabla
- **Filter**: `estado = 'APROBADO'` (36 filas)
- **HashAggregate**: Agrupa por año/mes
- **Tiempo total**: 2.338 ms (muy rápido)

### ¿Es un problema?
**Depende del tamaño de la tabla:**
- ✅ Si la tabla tiene < 10,000 filas: **Es normal** - Seq Scan es más rápido
- ⚠️ Si la tabla tiene > 100,000 filas: **Debería usar índice**

---

## 🎯 RECOMENDACIÓN

### Paso 1: Actualizar Estadísticas
```sql
ANALYZE prestamos;
ANALYZE cuotas;
ANALYZE pagos;
```

### Paso 2: Verificar Tamaño de Tabla
```sql
SELECT COUNT(*) FROM prestamos WHERE estado = 'APROBADO';
```

### Paso 3: Si la tabla es pequeña (< 10K filas)
✅ **No es un problema** - PostgreSQL está eligiendo el plan más eficiente
- El índice será útil cuando la tabla crezca
- El rendimiento actual es excelente (2.3ms)

### Paso 4: Si la tabla es grande (> 100K filas)
⚠️ **Necesita ajuste** - Ejecutar las soluciones 1-3

---

## ✅ VERIFICACIÓN FINAL

Después de ejecutar `ANALYZE`, verificar de nuevo:

```sql
EXPLAIN ANALYZE 
SELECT 
    EXTRACT(YEAR FROM fecha_aprobacion),
    EXTRACT(MONTH FROM fecha_aprobacion),
    COUNT(*)
FROM prestamos
WHERE estado = 'APROBADO'
GROUP BY EXTRACT(YEAR FROM fecha_aprobacion), EXTRACT(MONTH FROM fecha_aprobacion);
```

**Resultado esperado (si hay suficientes datos):**
```
Index Scan using idx_prestamos_fecha_aprobacion_ym on prestamos
```

**Si sigue mostrando Seq Scan:**
- Verificar tamaño de tabla
- Si es pequeña, es normal y correcto
- El índice se usará automáticamente cuando sea necesario

---

## 📝 NOTA IMPORTANTE

**PostgreSQL es inteligente** - Si el Seq Scan es más rápido que el Index Scan, elegirá el Seq Scan. Esto es **correcto** y **eficiente**.

El índice estará disponible y se usará automáticamente cuando:
- La tabla crezca
- El Seq Scan se vuelva más lento
- PostgreSQL determine que el índice es más eficiente

---

## 🎯 CONCLUSIÓN

1. ✅ **Ejecutar `ANALYZE prestamos`** para actualizar estadísticas
2. ✅ **Verificar tamaño de tabla** - Si es pequeña, Seq Scan es correcto
3. ✅ **Monitorear rendimiento** - El índice se usará cuando sea necesario
4. ✅ **No preocuparse** - 2.3ms es excelente rendimiento

