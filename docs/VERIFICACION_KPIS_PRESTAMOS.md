# Verificación de mecánica de cálculo - KPIs de Préstamos

**Endpoint:** `GET /api/v1/prestamos/stats`  
**Página:** `/pagos/prestamos`  
**Fecha verificación:** 2026-02-19

---

## 1. Flujo de datos

```
PrestamosKPIs (sin props)
  → usePrestamosKPIs({})
  → prestamoService.getKPIs(filters)
  → GET /api/v1/prestamos/stats?mes=2&año=2026
  → get_prestamos_stats() en prestamos.py
```

**Parámetros por defecto:** `mes` y `año` = mes/año actual (febrero 2026).

---

## 2. Lógica de cálculo (backend)

### 2.1 Filtro base

- **Tablas:** `prestamos` JOIN `clientes`
- **Condiciones:**
  - `clientes.estado = 'ACTIVO'`
  - `prestamos.estado = 'APROBADO'`
  - `fecha_ref` entre inicio y fin del mes
- **fecha_ref:** `COALESCE(DATE(fecha_aprobacion), DATE(fecha_registro))`

### 2.2 KPIs calculados

| KPI | Fórmula | Descripción |
|-----|---------|-------------|
| **total** (Préstamos mensual) | `COUNT(*)` del subquery filtrado | Cantidad de préstamos aprobados en el mes |
| **total_financiamiento** | `SUM(total_financiamiento)` del subquery | Suma de montos aprobados en el mes |
| **promedio_monto** | `total_financiamiento / total` (si total > 0) | Promedio por préstamo |
| **cartera_vigente** (Por cobrar) | `SUM(cuotas.monto)` donde `fecha_vencimiento` en mes y `fecha_pago IS NULL` | Cuotas vencidas en el mes no cobradas |

### 2.3 Corrección aplicada (bug SQLAlchemy)

**Problema:** `func.sum(Prestamo.total_financiamiento)` con `select_from(q_base.subquery())` sumaba toda la tabla `prestamos` en lugar de solo las filas del subquery.

**Solución:** Usar la columna del subquery explícitamente:

```python
subq = q_base.subquery()
total_fin = db.scalar(select(func.coalesce(func.sum(subq.c.total_financiamiento), 0)).select_from(subq)) or 0
```

---

## 3. Verificación con SQL (Febrero 2026)

```sql
WITH prestamos_mes AS (
  SELECT p.id, p.total_financiamiento,
         COALESCE(DATE(p.fecha_aprobacion), DATE(p.fecha_registro)) AS fecha_ref
  FROM prestamos p
  JOIN clientes c ON p.cliente_id = c.id
  WHERE c.estado = 'ACTIVO'
    AND p.estado = 'APROBADO'
    AND COALESCE(DATE(p.fecha_aprobacion), DATE(p.fecha_registro)) >= '2026-02-01'
    AND COALESCE(DATE(p.fecha_aprobacion), DATE(p.fecha_registro)) <= '2026-02-28'
)
SELECT
  COUNT(*) AS total_prestamos,
  COALESCE(SUM(total_financiamiento), 0) AS total_financiamiento,
  CASE WHEN COUNT(*) > 0 THEN COALESCE(SUM(total_financiamiento), 0) / COUNT(*) ELSE 0 END AS promedio_monto
FROM prestamos_mes;
```

**Resultado esperado (Feb 2026):** total=1, total_financiamiento=850.21, promedio_monto=850.21

---

## 4. Mapeo frontend → backend

| Frontend (prestamoService) | Backend (prestamos.py) |
|---------------------------|------------------------|
| `totalFinanciamiento` | `total_financiamiento` |
| `totalPrestamos` | `total` |
| `promedioMonto` | `promedio_monto` |
| `totalCarteraVigente` | `cartera_vigente` |
| `mes`, `año` | `mes`, `año` |

---

## 5. Valores correctos vs bug (antes del fix)

| Escenario | total | total_financiamiento | promedio_monto |
|-----------|-------|----------------------|----------------|
| **Feb 2025** (50 préstamos) | 50 | 72,540.00 | 1,450.80 |
| **Feb 2026** (1 préstamo) | 1 | 850.21 | 850.21 |
| **Bug (antes fix)** | 1* | 6,877,426.21** | 6,877,426.21 |

\* El count sí filtraba por mes (correcto).  
\** El sum sumaba toda la tabla (4,668 préstamos = $6.8M).

---

## 6. Despliegue

Tras desplegar el fix en Render, los KPIs deben mostrar los valores correctos según el mes seleccionado. Si la pantalla sigue mostrando $6,877,426.21, verificar que el backend desplegado incluya el cambio en `prestamos.py` (uso de `subq.c.total_financiamiento`).
