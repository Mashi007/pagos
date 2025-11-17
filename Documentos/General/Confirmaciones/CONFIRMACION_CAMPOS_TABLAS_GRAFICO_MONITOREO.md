# 📊 Confirmación: Campos y Tablas del Gráfico "MONITOREO FINANCIERO"

## Fecha: 2025-11-05

---

## 📈 Gráfico: MONITOREO FINANCIERO

**Endpoint:** `/api/v1/dashboard/financiamiento-tendencia-mensual`

**Título:** `MONITOREO FINANCIERO` (actualizado)

---

## 📋 Líneas del Gráfico

### 1. **Total Financiamiento por Mes** (Línea Azul Claro con Área Rellena)

**Tabla:** `prestamos`

**Campo Principal:** `total_financiamiento`

**Campo de Agrupación:** `fecha_aprobacion`

**Filtros:**
- `estado = 'APROBADO'`
- `fecha_aprobacion >= fecha_inicio_query`
- `fecha_aprobacion <= fecha_fin_query`

**Query SQL:**
```sql
SELECT
    EXTRACT(YEAR FROM fecha_aprobacion)::integer as año,
    EXTRACT(MONTH FROM fecha_aprobacion)::integer as mes,
    COUNT(id) as cantidad,
    SUM(total_financiamiento) as monto_total
FROM prestamos
WHERE estado = 'APROBADO'
  AND fecha_aprobacion >= :fecha_inicio
  AND fecha_aprobacion <= :fecha_fin
GROUP BY
    EXTRACT(YEAR FROM fecha_aprobacion),
    EXTRACT(MONTH FROM fecha_aprobacion)
ORDER BY año, mes
```

**Código en Backend:**
```python
# Líneas 3326-3336 en dashboard.py
query_nuevos = (
    db.query(
        func.extract("year", Prestamo.fecha_aprobacion).label("año"),
        func.extract("month", Prestamo.fecha_aprobacion).label("mes"),
        func.count(Prestamo.id).label("cantidad"),
        func.sum(Prestamo.total_financiamiento).label("monto_total"),
    )
    .filter(*filtros_base)
    .group_by(func.extract("year", Prestamo.fecha_aprobacion), func.extract("month", Prestamo.fecha_aprobacion))
)
```

**Campo Usado en Gráfico:** `monto_total` (suma de `total_financiamiento`)

---

### 2. **Cuotas Programadas por Mes** (Línea Púrpura Punteada)

**✅ CONFIRMADO: SUMA EN DÓLARES** (NO cuenta cuotas)

**Tabla:** `cuotas`

**Campo Principal:** `monto_cuota` (SUMA de montos, no COUNT de cuotas)

**Campo de Agrupación:** `fecha_vencimiento`

**Tabla Relacionada:** `prestamos` (JOIN)

**Operación:** `SUM(monto_cuota)` - Suma los montos en dólares de todas las cuotas que vencen en cada mes

**Filtros:**
- `prestamos.estado = 'APROBADO'`
- `cuotas.fecha_vencimiento >= fecha_inicio_query`
- `cuotas.fecha_vencimiento <= fecha_fin_query`

**Query SQL:**
```sql
SELECT
    EXTRACT(YEAR FROM c.fecha_vencimiento)::integer as año,
    EXTRACT(MONTH FROM c.fecha_vencimiento)::integer as mes,
    SUM(c.monto_cuota) as total_cuotas_programadas  -- ✅ SUM, no COUNT
FROM cuotas c
INNER JOIN prestamos p ON c.prestamo_id = p.id
WHERE p.estado = 'APROBADO'
  AND c.fecha_vencimiento >= :fecha_inicio
  AND c.fecha_vencimiento <= :fecha_fin
GROUP BY
    EXTRACT(YEAR FROM c.fecha_vencimiento),
    EXTRACT(MONTH FROM c.fecha_vencimiento)
ORDER BY año, mes
```

**Código en Backend:**
```python
# Líneas 3368-3382 en dashboard.py
query_cuotas = (
    db.query(
        func.extract("year", Cuota.fecha_vencimiento).label("año"),
        func.extract("month", Cuota.fecha_vencimiento).label("mes"),
        func.sum(Cuota.monto_cuota).label("total_cuotas_programadas"),  # ✅ SUM, no COUNT
    )
    .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
    .filter(
        Prestamo.estado == "APROBADO",
        Cuota.fecha_vencimiento >= fecha_inicio_query,
        Cuota.fecha_vencimiento <= fecha_fin_query,
    )
    .group_by(func.extract("year", Cuota.fecha_vencimiento), func.extract("month", Cuota.fecha_vencimiento))
)
```

**Campo Usado en Gráfico:** `total_cuotas_programadas` (suma en dólares de `monto_cuota`)

**⚠️ IMPORTANTE:** Esta línea **SUMA** los montos en dólares de todas las cuotas programadas que vencen en cada mes, **NO cuenta** el número de cuotas. Es el total monetario de pagos programados para ese mes.

---

### 3. **Monto Pagado por Mes** (Línea Verde)

**Tabla:** `pagos`

**Campo Principal:** `monto_pagado`

**Campo de Agrupación:** `fecha_pago`

**Tabla Relacionada:** `prestamos` (LEFT JOIN opcional, solo si hay filtros)

**Filtros:**
- `fecha_pago >= fecha_inicio`
- `fecha_pago <= fecha_fin`
- `monto_pagado IS NOT NULL`
- `monto_pagado > 0`
- `activo = TRUE`
- Si hay filtros: `prestamos.estado = 'APROBADO'`

**Query SQL (Sin Filtros):**
```sql
SELECT
    EXTRACT(YEAR FROM fecha_pago)::integer as año,
    EXTRACT(MONTH FROM fecha_pago)::integer as mes,
    COALESCE(SUM(monto_pagado), 0) as total_pagado
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

**Query SQL (Con Filtros - JOIN con prestamos):**
```sql
SELECT
    EXTRACT(YEAR FROM p.fecha_pago)::integer as año,
    EXTRACT(MONTH FROM p.fecha_pago)::integer as mes,
    COALESCE(SUM(p.monto_pagado), 0) as total_pagado
FROM pagos p
LEFT JOIN prestamos pr ON (
    (p.prestamo_id IS NOT NULL AND pr.id = p.prestamo_id)
    OR (p.prestamo_id IS NULL AND pr.cedula = p.cedula AND pr.estado = 'APROBADO')
)
WHERE p.fecha_pago >= :fecha_inicio
  AND p.fecha_pago <= :fecha_fin
  AND p.monto_pagado IS NOT NULL
  AND p.monto_pagado > 0
  AND p.activo = TRUE
  AND pr.estado = 'APROBADO'
  [Filtros adicionales: analista, concesionario, modelo]
GROUP BY
    EXTRACT(YEAR FROM p.fecha_pago),
    EXTRACT(MONTH FROM p.fecha_pago)
ORDER BY año, mes
```

**Código en Backend:**
```python
# Líneas 3463-3480 en dashboard.py (sin filtros)
query_pagos_sql = text(
    """
    SELECT
        EXTRACT(YEAR FROM fecha_pago)::integer as año,
        EXTRACT(MONTH FROM fecha_pago)::integer as mes,
        COALESCE(SUM(monto_pagado), 0) as total_pagado
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
    """
)
```

**Campo Usado en Gráfico:** `total_pagado` (suma de `monto_pagado`)

---

### 4. **Morosidad por Mes** (Línea Roja Rayada)

**Tabla:** `cuotas`

**Campo Principal:** `monto_cuota`

**Campo de Agrupación:** Mes calculado (último día de cada mes)

**Tabla Relacionada:** `prestamos` (JOIN)

**Filtros:**
- `prestamos.estado = 'APROBADO'`
- `cuotas.fecha_vencimiento <= ultimo_dia_mes` (acumulativo hasta el final del mes)
- `cuotas.estado != 'PAGADO'`

**Query SQL Optimizada:**
```sql
WITH meses AS (
    SELECT
        generate_series(
            DATE_TRUNC('month', :fecha_inicio::date),
            DATE_TRUNC('month', :fecha_fin::date),
            '1 month'::interval
        )::date as fecha_mes
),
meses_completos AS (
    SELECT
        EXTRACT(YEAR FROM fecha_mes)::int as año,
        EXTRACT(MONTH FROM fecha_mes)::int as mes,
        (fecha_mes + INTERVAL '1 month - 1 day')::date as ultimo_dia_mes
    FROM meses
)
SELECT
    m.año,
    m.mes,
    COALESCE(SUM(c.monto_cuota), 0) as morosidad
FROM meses_completos m
LEFT JOIN cuotas c ON c.fecha_vencimiento <= m.ultimo_dia_mes AND c.estado != 'PAGADO'
LEFT JOIN prestamos p ON c.prestamo_id = p.id AND p.estado = 'APROBADO'
GROUP BY m.año, m.mes
ORDER BY m.año, m.mes
```

**Query SQL Fallback (por mes):**
```sql
SELECT
    COALESCE(SUM(c.monto_cuota), 0) as morosidad
FROM cuotas c
INNER JOIN prestamos p ON c.prestamo_id = p.id
WHERE p.estado = 'APROBADO'
  AND c.fecha_vencimiento <= :ultimo_dia_mes
  AND c.estado != 'PAGADO'
```

**Código en Backend:**
```python
# Líneas 3592-3629 en dashboard.py (query optimizada)
query_morosidad_sql = text(
    f"""
    WITH meses AS (...)
    SELECT
        m.año,
        m.mes,
        COALESCE(SUM(c.monto_cuota), 0) as morosidad
    FROM meses_completos m
    LEFT JOIN cuotas c ON c.fecha_vencimiento <= m.ultimo_dia_mes AND c.estado != 'PAGADO'
    LEFT JOIN prestamos p ON c.prestamo_id = p.id AND p.estado = 'APROBADO'
    GROUP BY m.año, m.mes
    """
)
```

**Campo Usado en Gráfico:** `morosidad` (suma acumulativa de `monto_cuota` de cuotas vencidas no pagadas)

**Nota Importante:** La morosidad es **acumulativa**, es decir, suma todas las cuotas vencidas hasta el final de cada mes, no solo las que vencen en ese mes.

---

## 📊 Resumen de Tablas y Campos

| Línea | Tabla Principal | Campo Monto | Campo Fecha | Filtros Principales |
|-------|----------------|-------------|-------------|---------------------|
| **Total Financiamiento** | `prestamos` | `total_financiamiento` | `fecha_aprobacion` | `estado = 'APROBADO'` |
| **Cuotas Programadas** | `cuotas` | `monto_cuota` (SUM) | `fecha_vencimiento` | `prestamos.estado = 'APROBADO'` |
| **Monto Pagado** | `pagos` | `monto_pagado` | `fecha_pago` | `activo = TRUE`, `monto_pagado > 0` |
| **Morosidad** | `cuotas` | `monto_cuota` | `fecha_vencimiento <= ultimo_dia_mes` | `estado != 'PAGADO'`, `prestamos.estado = 'APROBADO'` |

---

## ✅ Confirmación

### Cambios Realizados:

1. ✅ **Título actualizado** en `frontend/src/pages/DashboardMenu.tsx`:
   - **Antes:** `"Financiamiento Aprobado por Mes (Último Año)"`
   - **Después:** `"MONITOREO FINANCIERO"`

2. ✅ **Confirmación de campos y tablas** documentada en este archivo

---

## 📝 Notas Técnicas

### Consideraciones Especiales:

1. **Total Financiamiento**: Usa `fecha_aprobacion` en lugar de `fecha_registro` (nota temporal en código)
2. **Monto Pagado**: Puede hacer JOIN con `prestamos` solo si hay filtros de analista/concesionario/modelo
3. **Morosidad**: Es acumulativa (suma todas las cuotas vencidas hasta el final del mes), no solo las que vencen en ese mes
4. **Todas las queries**: Agrupan por `EXTRACT(YEAR FROM fecha)` y `EXTRACT(MONTH FROM fecha)`

---

## 🔍 Verificación

Para verificar que los datos son correctos:

1. **Total Financiamiento**: Debe coincidir con la suma de `total_financiamiento` de préstamos aprobados por mes
2. **Cuotas Programadas**: Debe coincidir con la suma de `monto_cuota` de cuotas que vencen en cada mes
3. **Monto Pagado**: Debe coincidir con la suma de `monto_pagado` de pagos activos por mes
4. **Morosidad**: Debe ser la suma acumulativa de todas las cuotas vencidas no pagadas hasta el final de cada mes

---

**Estado:** ✅ Confirmado y documentado

