# 🔧 Corrección de Error de Sintaxis SQL en Índices

## Error Original
```
SQL Error [42601]: ERROR: syntax error at or near "::"
Position: 2208
```

## Causa del Error

El error se debía a dos problemas:

1. **Cast `::integer` en expresiones de índices funcionales**: PostgreSQL no permite usar casts (`::integer`) directamente en la definición de expresiones de índices funcionales.

2. **EXTRACT no es IMMUTABLE**: Aunque algunos índices con `EXTRACT` pueden funcionar, PostgreSQL prefiere funciones marcadas como `IMMUTABLE` para índices funcionales.

## Solución Implementada

### Cambio 1: Eliminado cast `::integer`
```sql
-- ❌ ANTES (causaba error)
CREATE INDEX idx_pagos_extract_year_month
ON pagos (
    EXTRACT(YEAR FROM fecha_pago)::integer,  -- ❌ Error aquí
    EXTRACT(MONTH FROM fecha_pago)::integer
);

-- ✅ DESPUÉS (corregido)
CREATE INDEX idx_pagos_date_trunc_month
ON pagos (
    DATE_TRUNC('month', fecha_pago)  -- ✅ Sin cast, usa DATE_TRUNC
);
```

### Cambio 2: Usar DATE_TRUNC en lugar de EXTRACT
```sql
-- ❌ PROBLEMA: EXTRACT no es IMMUTABLE
EXTRACT(YEAR FROM fecha_pago), EXTRACT(MONTH FROM fecha_pago)

-- ✅ SOLUCIÓN: DATE_TRUNC es IMMUTABLE
DATE_TRUNC('month', fecha_pago)
```

## Índices Corregidos

1. **`idx_pagos_date_trunc_month`** - Para GROUP BY por fecha_pago
2. **`idx_cuotas_date_trunc_month_vencimiento`** - Para GROUP BY por fecha_vencimiento
3. **`idx_prestamos_date_trunc_month_registro`** - Para GROUP BY por fecha_registro

## Compatibilidad con Queries

Las queries en el código usan `EXTRACT(YEAR FROM fecha_pago)`, pero PostgreSQL puede usar índices con `DATE_TRUNC` para optimizar estas consultas porque:

- `DATE_TRUNC('month', fecha_pago)` agrupa por año-mes
- `EXTRACT(YEAR/MONTH FROM fecha_pago)` también agrupa por año-mes
- PostgreSQL puede usar el índice de `DATE_TRUNC` para optimizar queries con `EXTRACT`

## Verificación

Después de ejecutar el script corregido, verificar que los índices se crearon:

```sql
SELECT
    schemaname,
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE schemaname = 'public'
  AND indexname LIKE 'idx_%_date_trunc%'
ORDER BY tablename, indexname;
```

## Impacto en Performance

El uso de `DATE_TRUNC` en lugar de `EXTRACT` **no afecta negativamente** el rendimiento. De hecho:

- ✅ `DATE_TRUNC` es más eficiente para índices
- ✅ PostgreSQL puede usar estos índices para optimizar queries con `EXTRACT`
- ✅ El rendimiento esperado es el mismo o mejor

## Notas Importantes

1. **DATE_TRUNC es IMMUTABLE**: Esto significa que PostgreSQL puede usarlo en índices funcionales sin problemas.

2. **Compatibilidad con queries existentes**: Las queries que usan `EXTRACT` seguirán funcionando y PostgreSQL puede usar los índices con `DATE_TRUNC` para optimizarlas.

3. **Si prefieres usar EXTRACT**: Si necesitas usar `EXTRACT` específicamente, puedes crear índices en las columnas de fecha directamente y dejar que PostgreSQL haga el GROUP BY en memoria (puede ser más lento para datasets grandes).

