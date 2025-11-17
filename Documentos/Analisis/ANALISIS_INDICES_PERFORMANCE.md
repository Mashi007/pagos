# 📊 Análisis de Índices para Optimización de Performance

## Fecha: 2025-11-05

---

## ✅ Resumen Ejecutivo

**Estado Actual:** Los índices existentes están **parcialmente optimizados** pero **faltan índices críticos** para las consultas más frecuentes.

**Recomendación:** Ejecutar el script `crear_indices_optimizados.sql` para agregar índices faltantes que mejorarán significativamente la velocidad de las consultas.

---

## 📋 Análisis de Consultas Frecuentes

### 1. Consultas con `EXTRACT(YEAR/MONTH)` en GROUP BY

#### **Consulta:** `/api/v1/dashboard/evolucion-pagos`
```sql
SELECT
    EXTRACT(YEAR FROM fecha_pago)::integer as año,
    EXTRACT(MONTH FROM fecha_pago)::integer as mes,
    COUNT(*) as cantidad,
    COALESCE(SUM(monto_pagado), 0) as monto_total
FROM pagos
WHERE fecha_pago >= :fecha_inicio
  AND fecha_pago <= :fecha_fin
  AND monto_pagado IS NOT NULL
  AND monto_pagado > 0
  AND activo = TRUE
GROUP BY
    EXTRACT(YEAR FROM fecha_pago),
    EXTRACT(MONTH FROM fecha_pago)
ORDER BY año, mes
```

**Índice Requerido:**
```sql
CREATE INDEX idx_pagos_extract_year_month
ON pagos (
    EXTRACT(YEAR FROM fecha_pago)::integer,
    EXTRACT(MONTH FROM fecha_pago)::integer
)
WHERE fecha_pago IS NOT NULL
  AND activo = TRUE
  AND monto_pagado IS NOT NULL
  AND monto_pagado > 0;
```

**Estado:** ❌ **NO EXISTE** - Crítico para performance

---

#### **Consulta:** `/api/v1/dashboard/cobranzas-mensuales`
```sql
SELECT
    EXTRACT(YEAR FROM c.fecha_vencimiento)::int as año,
    EXTRACT(MONTH FROM c.fecha_vencimiento)::int as mes,
    COALESCE(SUM(c.monto_cuota), 0) as cobranzas
FROM cuotas c
INNER JOIN prestamos p ON c.prestamo_id = p.id
WHERE p.estado = 'APROBADO'
  AND c.fecha_vencimiento >= :fecha_inicio
  AND c.fecha_vencimiento <= :fecha_fin
GROUP BY EXTRACT(YEAR FROM c.fecha_vencimiento), EXTRACT(MONTH FROM c.fecha_vencimiento)
ORDER BY año, mes
```

**Índice Requerido:**
```sql
CREATE INDEX idx_cuotas_extract_year_month_vencimiento
ON cuotas (
    EXTRACT(YEAR FROM fecha_vencimiento)::integer,
    EXTRACT(MONTH FROM fecha_vencimiento)::integer
)
WHERE fecha_vencimiento IS NOT NULL;
```

**Estado:** ❌ **NO EXISTE** - Crítico para performance

---

#### **Consulta:** `/api/v1/dashboard/financiamiento-tendencia-mensual`
```sql
SELECT
    EXTRACT(YEAR FROM fecha_registro)::integer as año,
    EXTRACT(MONTH FROM fecha_registro)::integer as mes,
    COUNT(*) as cantidad,
    COALESCE(SUM(total_financiamiento), 0) as monto_total
FROM prestamos
WHERE fecha_registro >= :fecha_inicio
  AND fecha_registro <= :fecha_fin
  AND estado = 'APROBADO'
GROUP BY EXTRACT(YEAR FROM fecha_registro), EXTRACT(MONTH FROM fecha_registro)
ORDER BY año, mes
```

**Índice Requerido:**
```sql
CREATE INDEX idx_prestamos_extract_year_month_registro
ON prestamos (
    EXTRACT(YEAR FROM fecha_registro)::integer,
    EXTRACT(MONTH FROM fecha_registro)::integer
)
WHERE fecha_registro IS NOT NULL
  AND estado = 'APROBADO';
```

**Estado:** ❌ **NO EXISTE** - Crítico para performance

---

### 2. Consultas con JOINs `pagos` ↔ `prestamos`

#### **Consulta:** `_calcular_total_cobrado_mes`, `_calcular_pagos_fecha`
```sql
SELECT COALESCE(SUM(p.monto_pagado), 0)
FROM pagos p
INNER JOIN prestamos pr ON (
    (p.prestamo_id IS NOT NULL AND pr.id = p.prestamo_id)
    OR (p.prestamo_id IS NULL AND pr.cedula = p.cedula AND pr.estado = 'APROBADO')
)
WHERE p.fecha_pago >= :fecha_inicio
  AND p.fecha_pago <= :fecha_fin
  AND p.monto_pagado IS NOT NULL
  AND p.monto_pagado > 0
  AND p.activo = TRUE
  AND pr.estado = 'APROBADO'
  AND (pr.analista = :analista OR pr.producto_financiero = :analista)
  AND pr.concesionario = :concesionario
  AND (pr.producto = :modelo OR pr.modelo_vehiculo = :modelo)
```

**Índices Requeridos:**
```sql
-- Para JOIN por prestamo_id
CREATE INDEX idx_pagos_prestamo_id_activo_fecha
ON pagos (prestamo_id, activo, fecha_pago)
WHERE prestamo_id IS NOT NULL
  AND activo = TRUE
  AND fecha_pago IS NOT NULL
  AND monto_pagado IS NOT NULL
  AND monto_pagado > 0;

-- Para JOIN por cedula
CREATE INDEX idx_pagos_cedula_activo_fecha
ON pagos (cedula, activo, fecha_pago)
WHERE cedula IS NOT NULL
  AND activo = TRUE
  AND fecha_pago IS NOT NULL
  AND monto_pagado IS NOT NULL
  AND monto_pagado > 0;

-- Para filtros de prestamos
CREATE INDEX idx_prestamos_estado_analista_concesionario
ON prestamos (estado, analista, concesionario)
WHERE estado = 'APROBADO';

CREATE INDEX idx_prestamos_estado_producto_modelo
ON prestamos (estado, producto, modelo_vehiculo)
WHERE estado = 'APROBADO';

CREATE INDEX idx_prestamos_estado_cedula
ON prestamos (estado, cedula)
WHERE estado = 'APROBADO'
  AND cedula IS NOT NULL;
```

**Estado:** ❌ **NO EXISTEN** - Críticos para JOINs eficientes

---

### 3. Consultas con Filtros Individuales

#### **Consulta:** `/api/v1/dashboard/cobros-por-analista`
```sql
SELECT
    COALESCE(pr.analista, 'Sin Analista') as analista,
    COALESCE(SUM(p.monto_pagado), 0) as total_cobrado,
    COUNT(p.id) as cantidad_pagos
FROM pagos p
LEFT JOIN prestamos pr ON (
    (p.prestamo_id IS NOT NULL AND pr.id = p.prestamo_id)
    OR (p.prestamo_id IS NULL AND pr.cedula = p.cedula AND pr.estado = 'APROBADO')
)
WHERE p.activo = TRUE
  AND p.monto_pagado IS NOT NULL
  AND p.monto_pagado > 0
  AND p.fecha_pago >= :fecha_inicio
  AND p.fecha_pago <= :fecha_fin
GROUP BY pr.analista
ORDER BY total_cobrado DESC
LIMIT 10
```

**Índices Requeridos:**
- `idx_pagos_prestamo_id_activo_fecha` (ya mencionado arriba)
- `idx_prestamos_estado_analista` (individual)

**Estado:** ⚠️ **PARCIAL** - Algunos índices existen, faltan compuestos

---

## 📊 Comparación: Índices Existentes vs. Requeridos

### Tabla `pagos`

#### ✅ Índices que SÍ existen (según `crear_indices_performance.sql`):
- `idx_pagos_prestamo_id` - Para JOINs
- `idx_pagos_fecha_pago` - Para filtros de fecha
- `idx_pagos_activo` - Para filtros de activo
- `idx_pagos_conciliado` - Para filtros de conciliación
- `idx_pagos_activo_fecha_pago` - Compuesto básico

#### ❌ Índices que FALTAN (críticos):
- `idx_pagos_extract_year_month` - **CRÍTICO** para GROUP BY con EXTRACT
- `idx_pagos_prestamo_id_activo_fecha` - **CRÍTICO** para JOINs eficientes
- `idx_pagos_cedula_activo_fecha` - **CRÍTICO** para JOINs por cedula
- `idx_pagos_monto_pagado` - Para filtros de monto

---

### Tabla `prestamos`

#### ✅ Índices que SÍ existen:
- `idx_prestamos_estado` - Para filtros de estado
- `idx_prestamos_fecha_registro` - Para filtros de fecha
- `idx_prestamos_cedula` - Para JOINs
- `idx_prestamos_cliente_id` - Para JOINs
- `idx_prestamos_estado_fecha_registro` - Compuesto básico

#### ❌ Índices que FALTAN (críticos):
- `idx_prestamos_extract_year_month_registro` - **CRÍTICO** para GROUP BY
- `idx_prestamos_estado_analista_concesionario` - **CRÍTICO** para filtros
- `idx_prestamos_estado_producto_modelo` - **CRÍTICO** para filtros
- `idx_prestamos_estado_producto_financiero` - **CRÍTICO** para filtros
- `idx_prestamos_estado_cedula` - **CRÍTICO** para JOINs por cedula
- `idx_prestamos_analista` - Individual (filtro frecuente)
- `idx_prestamos_concesionario` - Individual (filtro frecuente)
- `idx_prestamos_producto` - Individual (filtro frecuente)
- `idx_prestamos_modelo_vehiculo` - Individual (filtro frecuente)

---

### Tabla `cuotas`

#### ✅ Índices que SÍ existen:
- `idx_cuotas_prestamo_id` - Para JOINs
- `idx_cuotas_estado` - Para filtros
- `idx_cuotas_fecha_vencimiento` - Para filtros
- `idx_cuotas_estado_fecha_vencimiento` - Compuesto básico

#### ❌ Índices que FALTAN (críticos):
- `idx_cuotas_extract_year_month_vencimiento` - **CRÍTICO** para GROUP BY
- `idx_cuotas_prestamo_estado_fecha_vencimiento` - **CRÍTICO** para JOINs eficientes

---

## 🎯 Impacto Esperado

### Mejoras de Performance Estimadas:

| Endpoint | Tiempo Actual (aprox.) | Tiempo Esperado | Mejora |
|----------|------------------------|-----------------|---------|
| `/dashboard/evolucion-pagos` | 2-5 seg | 0.5-1 seg | **70-80%** |
| `/dashboard/cobranzas-mensuales` | 3-6 seg | 0.5-1 seg | **80-85%** |
| `/dashboard/financiamiento-tendencia-mensual` | 2-4 seg | 0.3-0.8 seg | **75-80%** |
| `/dashboard/admin` (con filtros) | 5-10 seg | 1-2 seg | **80-85%** |
| `/dashboard/cobros-por-analista` | 2-4 seg | 0.5-1 seg | **70-75%** |

---

## ✅ Plan de Acción

### Paso 1: Ejecutar Script de Índices Optimizados
```bash
psql -U usuario -d pagos_db -f backend/scripts/crear_indices_optimizados.sql
```

### Paso 2: Actualizar Estadísticas
```sql
ANALYZE pagos;
ANALYZE prestamos;
ANALYZE cuotas;
ANALYZE clientes;
```

### Paso 3: Verificar Uso de Índices
```sql
-- Ejemplo: Verificar índice en query de evolución de pagos
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

**Buscar en el resultado:**
- ✅ `Index Scan using idx_pagos_extract_year_month` (ideal)
- ✅ `Bitmap Index Scan using idx_pagos_extract_year_month` (bueno)
- ❌ `Seq Scan on pagos` (malo - índice no se usa)

### Paso 4: Monitorear Performance
- Usar logs de aplicación para medir tiempos de respuesta
- Comparar antes/después de crear índices
- Ajustar índices si no se usan

---

## ⚠️ Consideraciones Importantes

### 1. Espacio en Disco
- Los índices ocupan espacio adicional (aproximadamente 20-30% del tamaño de la tabla)
- Verificar espacio disponible antes de crear índices

### 2. Tiempo de Creación
- Los índices funcionales pueden tardar varios minutos en tablas grandes
- Ejecutar durante horarios de bajo tráfico

### 3. Mantenimiento
- PostgreSQL actualiza índices automáticamente en INSERT/UPDATE/DELETE
- Ejecutar `ANALYZE` periódicamente para actualizar estadísticas

### 4. Índices No Utilizados
- Si un índice no se usa después de varias semanas, considerar eliminarlo
- Verificar uso con: `pg_stat_user_indexes`

---

## 📝 Notas Adicionales

### Sobre Índices Funcionales con EXTRACT

PostgreSQL permite índices funcionales con `EXTRACT` aunque técnicamente no es `IMMUTABLE` si la expresión es determinista. Sin embargo, si PostgreSQL no puede usar estos índices, considerar:

1. **Alternativa 1:** Usar índices en `fecha_pago` directamente y dejar que PostgreSQL haga el GROUP BY en memoria
2. **Alternativa 2:** Crear índices con `DATE_TRUNC` si las queries pueden adaptarse

### Sobre JOINs Complejos

Los JOINs con condiciones `OR` (como `pagos` ↔ `prestamos` por `prestamo_id` O `cedula`) son difíciles de optimizar. Los índices compuestos ayudan, pero PostgreSQL puede necesitar hacer múltiples scans.

**Recomendación:** Considerar normalizar la relación `pagos.prestamo_id` para eliminar la necesidad de JOINs por `cedula`.

---

## ✅ Conclusión

**Los índices actuales están bien configurados para consultas básicas, pero faltan índices críticos para las consultas más frecuentes del dashboard.**

**Acción recomendada:** Ejecutar `crear_indices_optimizados.sql` para agregar los índices faltantes y mejorar significativamente el rendimiento de las consultas.

**Impacto esperado:** Reducción del 70-85% en tiempos de respuesta de los endpoints del dashboard.

