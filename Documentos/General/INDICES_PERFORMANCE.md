# 📊 Guía de Índices para Mejorar Performance

Este documento explica cómo crear y usar los índices recomendados para mejorar el rendimiento de las queries del dashboard.

## 🎯 Objetivo

Los índices funcionales mejoran significativamente las queries que usan `GROUP BY` con `EXTRACT(YEAR/MONTH)` en columnas de fecha, reduciendo el tiempo de respuesta de varios segundos a milisegundos.

## 📋 Índices Recomendados

### Prioridad ALTA (Impacto Crítico)

Estos índices mejoran los endpoints más lentos:

#### 1. `idx_pagos_staging_fecha_pago_funcional`
**Mejora:** `/api/v1/pagos/kpis`, `/api/v1/dashboard/cobranzas-mensuales`, `/api/v1/dashboard/evolucion-pagos`
**Impacto esperado:** Reducción de 2000-3000ms a 300-500ms

```sql
CREATE INDEX IF NOT EXISTS idx_pagos_staging_fecha_pago_funcional 
ON pagos_staging (
    EXTRACT(YEAR FROM fecha_pago::timestamp), 
    EXTRACT(MONTH FROM fecha_pago::timestamp)
)
WHERE fecha_pago IS NOT NULL 
  AND fecha_pago != '' 
  AND fecha_pago ~ '^\d{4}-\d{2}-\d{2}';
```

#### 2. `idx_cuotas_fecha_vencimiento_funcional`
**Mejora:** `/api/v1/dashboard/cobranzas-mensuales`, `/api/v1/dashboard/evolucion-morosidad`
**Impacto esperado:** Reducción de 1000-2000ms a 200-400ms

```sql
CREATE INDEX IF NOT EXISTS idx_cuotas_fecha_vencimiento_funcional 
ON cuotas (
    EXTRACT(YEAR FROM fecha_vencimiento), 
    EXTRACT(MONTH FROM fecha_vencimiento)
)
WHERE fecha_vencimiento IS NOT NULL;
```

#### 3. `idx_prestamos_fecha_registro_funcional`
**Mejora:** `/api/v1/dashboard/financiamiento-tendencia-mensual`, `/api/v1/dashboard/admin`
**Impacto esperado:** Reducción de 5000-10000ms a 500-1000ms

```sql
CREATE INDEX IF NOT EXISTS idx_prestamos_fecha_registro_funcional 
ON prestamos (
    EXTRACT(YEAR FROM fecha_registro), 
    EXTRACT(MONTH FROM fecha_registro)
)
WHERE fecha_registro IS NOT NULL
  AND estado = 'APROBADO';
```

### Prioridad MEDIA (Mejoras Importantes)

#### 4. `idx_pagos_fecha_pago_funcional`
**Mejora:** `/api/v1/dashboard/evolucion-general-mensual`

```sql
CREATE INDEX IF NOT EXISTS idx_pagos_fecha_pago_funcional 
ON pagos (
    EXTRACT(YEAR FROM fecha_pago), 
    EXTRACT(MONTH FROM fecha_pago)
)
WHERE fecha_pago IS NOT NULL
  AND activo = TRUE;
```

#### 5. Índices regulares para filtros frecuentes

```sql
-- Filtros por fecha
CREATE INDEX IF NOT EXISTS idx_pagos_staging_fecha_pago 
ON pagos_staging (fecha_pago::timestamp)
WHERE fecha_pago IS NOT NULL AND fecha_pago != '';

CREATE INDEX IF NOT EXISTS idx_cuotas_fecha_vencimiento 
ON cuotas (fecha_vencimiento);

CREATE INDEX IF NOT EXISTS idx_prestamos_fecha_registro 
ON prestamos (fecha_registro);

-- JOINs
CREATE INDEX IF NOT EXISTS idx_cuotas_prestamo_id 
ON cuotas (prestamo_id);

CREATE INDEX IF NOT EXISTS idx_prestamos_cedula 
ON prestamos (cedula);

-- Filtros por estado
CREATE INDEX IF NOT EXISTS idx_prestamos_estado 
ON prestamos (estado);

CREATE INDEX IF NOT EXISTS idx_cuotas_estado 
ON cuotas (estado);
```

## 🚀 Cómo Ejecutar

### Opción 1: Usar el Script Completo

```bash
# Conectarse a la base de datos y ejecutar:
psql -h HOST -U USER -d DATABASE -f backend/scripts/crear_indices_performance.sql
```

### Opción 2: Ejecutar en DBeaver

1. Abrir DBeaver
2. Conectarse a la base de datos
3. Abrir el archivo `backend/scripts/crear_indices_performance.sql`
4. Ejecutar el script completo (Ctrl+Enter)

### Opción 3: Ejecutar Índices Individuales

Si solo quieres crear índices específicos, copia y ejecuta las queries individuales.

## ⏱️ Tiempo de Ejecución

- **Tablas pequeñas (< 100K registros):** 1-5 minutos
- **Tablas medianas (100K - 1M registros):** 5-15 minutos
- **Tablas grandes (> 1M registros):** 15-60 minutos

**Recomendación:** Ejecutar durante horarios de bajo tráfico.

## ✅ Verificación

### Verificar que los índices se crearon:

```sql
SELECT 
    schemaname,
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE schemaname = 'public'
  AND indexname LIKE 'idx_%'
ORDER BY tablename, indexname;
```

### Verificar uso de índices en una query:

```sql
EXPLAIN ANALYZE
SELECT 
    EXTRACT(YEAR FROM fecha_pago::timestamp)::int as año,
    EXTRACT(MONTH FROM fecha_pago::timestamp)::int as mes,
    COALESCE(SUM(monto_pagado::numeric), 0) as pagos
FROM pagos_staging
WHERE fecha_pago IS NOT NULL
  AND fecha_pago != ''
  AND fecha_pago ~ '^\d{4}-\d{2}-\d{2}'
  AND fecha_pago::timestamp >= '2025-01-01'
  AND fecha_pago::timestamp <= '2025-12-31'
GROUP BY EXTRACT(YEAR FROM fecha_pago::timestamp), EXTRACT(MONTH FROM fecha_pago::timestamp);
```

**Buscar en el resultado:** `Index Scan using idx_pagos_staging_fecha_pago_funcional`

### Actualizar estadísticas después de crear índices:

```sql
ANALYZE pagos_staging;
ANALYZE cuotas;
ANALYZE prestamos;
ANALYZE pagos;
ANALYZE clientes;
```

## 📊 Impacto Esperado

Después de crear los índices, los tiempos de respuesta deberían mejorar:

| Endpoint | Antes | Después | Mejora |
|----------|-------|---------|-------|
| `/api/v1/pagos/kpis` | 2860ms | 800-1000ms | ~70% |
| `/api/v1/dashboard/cobranzas-mensuales` | 27-39s | 3-5s | ~85% |
| `/api/v1/dashboard/evolucion-pagos` | 30s | 2-3s | ~90% |
| `/api/v1/dashboard/financiamiento-tendencia-mensual` | 5.5s | 1-2s | ~70% |
| `/api/v1/dashboard/evolucion-morosidad` | 5.7s | 1-2s | ~70% |

## ⚠️ Consideraciones

1. **Espacio en disco:** Los índices ocupan espacio adicional (estimado: 10-20% del tamaño de las tablas)

2. **Tiempo de creación:** Los índices funcionales pueden tardar varios minutos en tablas grandes

3. **Mantenimiento:** PostgreSQL actualiza los índices automáticamente, pero es recomendable ejecutar `ANALYZE` periódicamente

4. **Monitoreo:** Después de crear los índices, monitorear el rendimiento para verificar que están siendo usados

## 🔍 Troubleshooting

### Si los índices no se están usando:

1. **Verificar que existen:**
   ```sql
   SELECT indexname FROM pg_indexes WHERE tablename = 'pagos_staging';
   ```

2. **Verificar estadísticas:**
   ```sql
   SELECT relname, n_tup_ins, n_tup_upd, last_analyze 
   FROM pg_stat_user_tables 
   WHERE relname = 'pagos_staging';
   ```

3. **Forzar actualización de estadísticas:**
   ```sql
   ANALYZE pagos_staging;
   ```

4. **Verificar configuración de PostgreSQL:**
   ```sql
   SHOW enable_seqscan;  -- Debe ser 'on'
   SHOW random_page_cost; -- Debe ser 4.0 o menor
   ```

## 📝 Script de Verificación

Usar el script `backend/scripts/verificar_indices_bd.py` para verificar qué índices faltan:

```bash
python backend/scripts/verificar_indices_bd.py
```

Este script mostrará:
- Índices existentes
- Índices faltantes recomendados
- Prioridad de cada índice
- Estadísticas de cada tabla

---

**Última actualización:** 2025-11-04

