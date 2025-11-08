# 📋 Confirmación de Datos - Tarjeta de Financiamiento

## 🎯 Resumen
Este documento confirma de dónde se obtienen los datos para la tarjeta "FINANCIAMIENTO" que muestra:
1. **Monto de Financiamiento**
2. **Cartera Recobrada** (porcentaje)
3. **Morosidad** (porcentaje)

---

## 📊 1. MONTO DE FINANCIAMIENTO

### Frontend
- **Variable:** `datosDashboard?.financieros?.ingresosCapital`
- **Endpoint:** `GET /api/v1/dashboard/admin`
- **Ubicación código:** `frontend/src/pages/DashboardMenu.tsx` línea 603

### Backend
- **Endpoint:** `GET /api/v1/dashboard/admin`
- **Ubicación código:** `backend/app/api/v1/endpoints/dashboard.py` línea 1709
- **Variable backend:** `ingresos_capital`
- **Cálculo:** `ingresos_capital = total_financiamiento_operaciones`

### Tabla y Campos
- **Tabla:** `prestamos`
- **Campo:** `prestamos.total_financiamiento`
- **Query SQL:**
```sql
SELECT SUM(prestamos.total_financiamiento)
FROM prestamos
WHERE prestamos.estado = 'APROBADO'
```
- **Ubicación código backend:** `backend/app/api/v1/endpoints/dashboard.py` líneas 1611-1622

### Filtros Aplicados
- ✅ Aplica filtros automáticos mediante `FiltrosDashboard.aplicar_filtros_prestamo()`:
  - `analista` (filtra por `prestamos.analista` o `prestamos.producto_financiero`)
  - `concesionario` (filtra por `prestamos.concesionario`)
  - `modelo` (filtra por `prestamos.producto` o `prestamos.modelo_vehiculo`)
  - `fecha_inicio` / `fecha_fin` (filtra por `prestamos.fecha_aprobacion`)

---

## 💰 2. CARTERA RECOBRADA (Porcentaje)

### Frontend
- **Variable:** `datosDashboard?.financieros?.totalCobrado`
- **Endpoint:** `GET /api/v1/dashboard/admin`
- **Ubicación código:** `frontend/src/pages/DashboardMenu.tsx` líneas 612-620
- **Cálculo porcentaje:** `(totalCobrado / ingresosCapital) * 100`

### Backend
- **Endpoint:** `GET /api/v1/dashboard/admin`
- **Ubicación código:** `backend/app/api/v1/endpoints/dashboard.py` línea 1707
- **Variable backend:** `total_cobrado_periodo`
- **Función helper:** `_calcular_total_cobrado_mes()`
- **Ubicación función:** `backend/app/api/v1/endpoints/dashboard.py` líneas 118-184

### Tabla y Campos
- **Tabla principal:** `pagos`
- **Campos usados:**
  - `pagos.monto_pagado`
  - `pagos.fecha_pago`
  - `pagos.activo`
  - `pagos.prestamo_id` (opcional, para JOIN)
  - `pagos.cedula` (opcional, para JOIN)

### Query SQL (con filtros)
```sql
SELECT COALESCE(SUM(p.monto_pagado), 0)
FROM pagos p
INNER JOIN prestamos pr ON (
    (p.prestamo_id IS NOT NULL AND pr.id = p.prestamo_id)
    OR (p.prestamo_id IS NULL AND pr.cedula = p.cedula AND pr.estado = 'APROBADO')
)
WHERE p.fecha_pago >= :primer_dia
  AND p.fecha_pago <= :ultimo_dia
  AND p.monto_pagado IS NOT NULL
  AND p.monto_pagado > 0
  AND p.activo = TRUE
  AND pr.estado = 'APROBADO'
```

### Query SQL (sin filtros)
```sql
SELECT COALESCE(SUM(monto_pagado), 0)
FROM pagos
WHERE fecha_pago >= :primer_dia
  AND fecha_pago <= :ultimo_dia
  AND monto_pagado IS NOT NULL
  AND monto_pagado > 0
  AND activo = TRUE
```

### Filtros Aplicados
- ✅ Filtra por rango de fechas del mes actual (`primer_dia` a `ultimo_dia`)
- ✅ Si hay filtros de analista/concesionario/modelo, hace JOIN con `prestamos` y aplica filtros:
  - `analista` (filtra por `prestamos.analista` o `prestamos.producto_financiero`)
  - `concesionario` (filtra por `prestamos.concesionario`)
  - `modelo` (filtra por `prestamos.producto` o `prestamos.modelo_vehiculo`)

### Nota Importante
- **Periodo:** Calcula el total cobrado del **mes actual** (desde el primer día hasta el último día del mes)
- **Ubicación código backend:** `backend/app/api/v1/endpoints/dashboard.py` líneas 1276-1285

---

## ⚠️ 3. MOROSIDAD (Porcentaje)

### Frontend
- **Variable:** `kpisPrincipales.total_morosidad_usd?.valor_actual`
- **Endpoint:** `GET /api/v1/dashboard/kpis-principales`
- **Ubicación código:** `frontend/src/pages/DashboardMenu.tsx` líneas 627-636
- **Cálculo porcentaje:** `(morosidadTotal / ingresosCapital) * 100`

### Backend
- **Endpoint:** `GET /api/v1/dashboard/kpis-principales`
- **Ubicación código:** `backend/app/api/v1/endpoints/dashboard.py` línea 2243
- **Variable backend:** `morosidad_actual`
- **Función helper:** `_calcular_morosidad()`
- **Ubicación función:** `backend/app/api/v1/endpoints/dashboard.py` líneas 215-330

### Tablas y Campos
- **Tablas:** `cuotas`, `prestamos`, `pagos`
- **Campos usados:**
  - `cuotas.monto_cuota`
  - `cuotas.fecha_vencimiento`
  - `cuotas.prestamo_id`
  - `prestamos.id`
  - `prestamos.estado`
  - `prestamos.fecha_aprobacion`
  - `prestamos.analista`
  - `prestamos.producto_financiero`
  - `prestamos.concesionario`
  - `prestamos.producto`
  - `prestamos.modelo_vehiculo`
  - `pagos.monto_pagado`
  - `pagos.fecha_pago`
  - `pagos.activo`
  - `pagos.prestamo_id`
  - `pagos.cedula`

### Lógica de Cálculo
La morosidad se calcula como **morosidad acumulada** desde enero 2024 hasta la fecha actual:

1. **Morosidad mensual** = `MAX(0, Monto Programado del mes - Monto Pagado del mes)`
2. **Morosidad acumulada** = Suma de todas las morosidades mensuales desde 2024-01-01 hasta la fecha

### Query SQL (simplificado)
```sql
WITH meses AS (
    SELECT
        EXTRACT(YEAR FROM c.fecha_vencimiento)::integer as año,
        EXTRACT(MONTH FROM c.fecha_vencimiento)::integer as mes,
        COALESCE(SUM(c.monto_cuota), 0) as monto_programado
    FROM cuotas c
    INNER JOIN prestamos p ON c.prestamo_id = p.id
    WHERE p.estado = 'APROBADO'
      AND c.fecha_vencimiento >= :fecha_inicio_calculo
      AND c.fecha_vencimiento <= :fecha_limite
    GROUP BY EXTRACT(YEAR FROM c.fecha_vencimiento), EXTRACT(MONTH FROM c.fecha_vencimiento)
),
pagos_por_mes AS (
    SELECT
        EXTRACT(YEAR FROM pa.fecha_pago)::integer as año,
        EXTRACT(MONTH FROM pa.fecha_pago)::integer as mes,
        COALESCE(SUM(pa.monto_pagado), 0) as monto_pagado
    FROM pagos pa
    LEFT JOIN prestamos pr ON (...)
    WHERE pa.activo = TRUE
      AND pa.monto_pagado IS NOT NULL
      AND pa.monto_pagado > 0
      AND pa.fecha_pago >= :fecha_inicio_calculo
      AND pa.fecha_pago <= :fecha_limite
    GROUP BY EXTRACT(YEAR FROM pa.fecha_pago), EXTRACT(MONTH FROM pa.fecha_pago)
)
SELECT COALESCE(SUM(GREATEST(0, m.monto_programado - COALESCE(p.monto_pagado, 0))), 0) as morosidad_acumulada
FROM meses m
LEFT JOIN pagos_por_mes p ON m.año = p.año AND m.mes = p.mes
```

### Filtros Aplicados
- ✅ Aplica filtros automáticos mediante condiciones en WHERE:
  - `analista` (filtra por `prestamos.analista` o `prestamos.producto_financiero`)
  - `concesionario` (filtra por `prestamos.concesionario`)
  - `modelo` (filtra por `prestamos.producto` o `prestamos.modelo_vehiculo`)
  - `fecha_inicio` / `fecha_fin` (filtra por `prestamos.fecha_aprobacion`)

### Nota Importante
- **Fecha inicio cálculo:** 2024-01-01 (o `fecha_inicio` si es más reciente)
- **Fecha límite:** Fecha actual (o `fecha_fin` si está definida)
- **Ubicación código backend:** `backend/app/api/v1/endpoints/dashboard.py` líneas 2126-2133

---

## ✅ Resumen de Endpoints

| Métrica | Endpoint | Tabla Principal | Campo Principal |
|---------|----------|----------------|-----------------|
| **Monto de Financiamiento** | `/api/v1/dashboard/admin` | `prestamos` | `total_financiamiento` |
| **Cartera Recobrada** | `/api/v1/dashboard/admin` | `pagos` | `monto_pagado` |
| **Morosidad** | `/api/v1/dashboard/kpis-principales` | `cuotas`, `pagos` | `monto_cuota`, `monto_pagado` |

---

## 🔍 Verificación de Datos Reales

Todos los datos provienen de **tablas reales** de la base de datos:
- ✅ `prestamos` - Tabla de préstamos aprobados
- ✅ `pagos` - Tabla de pagos registrados
- ✅ `cuotas` - Tabla de cuotas programadas

**No hay datos mock o hardcodeados** - Todo se calcula desde la base de datos en tiempo real.

---

## 📝 Notas Adicionales

1. **Cartera Recobrada:** El porcentaje se calcula en el frontend como `(totalCobrado / ingresosCapital) * 100`
2. **Morosidad:** El porcentaje se calcula en el frontend como `(morosidadTotal / ingresosCapital) * 100`
3. **Filtros:** Todos los endpoints respetan los filtros aplicados en el dashboard (analista, concesionario, modelo, fechas)
4. **Cache:** Ambos endpoints tienen cache de 5 minutos (`@cache_result(ttl=300)`)

