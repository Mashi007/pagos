# Auditoría integral: KPIs de préstamos no se actualizan

**Fecha:** 2026-03-08  
**Página afectada:** `/pagos/prestamos` (KPIs: Financiamiento mensual, Préstamos mensual, Promedio mensual, Por cobrar mensual)  
**Endpoint:** `GET /api/v1/prestamos/stats`

---

## 1. Flujo revisado

| Capa | Componente | Detalle |
|------|------------|---------|
| Frontend | `PrestamosKPIs.tsx` | Usa `usePrestamosKPIs({})` sin mes/año → mes y año = actual del navegador |
| Frontend | `prestamoService.getKPIs()` | Llama `GET /api/v1/prestamos/stats?mes=X&anio=Y` (X = 1–12, Y = año actual) |
| Backend | `get_prestamos_stats()` | Filtra por `Cliente.estado == "ACTIVO"`, fecha ref = COALESCE(fecha_aprobacion, fecha_registro), y **estado del préstamo** |
| BD | `prestamos.estado` | Valores válidos: DRAFT, EN_REVISION, EVALUADO, APROBADO, RECHAZADO, **DESEMBOLSADO** |

---

## 2. Causa raíz identificada

**Problema:** El endpoint `/prestamos/stats` filtraba solo `Prestamo.estado == "APROBADO"`.

En el flujo real de la aplicación:

- **Aprobar manual** (`POST /prestamos/{id}/aprobar-manual`) → deja el préstamo en **DESEMBOLSADO**.
- **Asignar fecha de aprobación** (`POST /prestamos/{id}/asignar-fecha-aprobacion`) → deja el préstamo en **DESEMBOLSADO**.

Por tanto, casi todos los préstamos “aprobados” en BD están en estado **DESEMBOLSADO**. Al contar solo **APROBADO**, los KPIs (total, total_financiamiento, promedio_monto) quedaban en **0**.

**Por cobrar (mensual)** sí se veía porque esa métrica no dependía del estado del préstamo de la misma forma en la consulta de cuotas (o ya incluía préstamos con cuotas, típicamente desembolsados).

---

## 3. Cambios realizados

### 3.1 Backend (`backend/app/api/v1/endpoints/prestamos.py`)

- **Estados considerados “aprobados” para KPIs:** se consideran **APROBADO** y **DESEMBOLSADO**.
- Se introdujo `_estados_aprobados_kpi = ("APROBADO", "DESEMBOLSADO")` y se reemplazó:
  - `Prestamo.estado == "APROBADO"` → `Prestamo.estado.in_(_estados_aprobados_kpi)`
- Afecta a:
  - Consulta base para **total**, **total_financiamiento** y **promedio_monto**.
  - Consulta por estado (**por_estado**).
  - Consulta de **cartera_vigente** (por cobrar mensual).

### 3.2 Fecha de referencia (ya corregido previamente)

- Se usa `cast(func.coalesce(Prestamo.fecha_aprobacion, Prestamo.fecha_registro), Date)` con rango `inicio_mes`–`fin_mes` (sin conversión de zona horaria), para que “aprobados en el mes” coincida con la fecha en BD.

### 3.3 Frontend (invalidación de caché, ya aplicado antes)

- Al aprobar o asignar fecha de aprobación se invalida `['prestamos']`, de modo que los KPIs se recalculan al volver a la página o al refetch.
- `usePrestamosKPIs` con `staleTime: 0` para que tras invalidar se refresquen los datos.

---

## 4. Verificación recomendada

1. **Backend:** Tras desplegar, llamar por ejemplo:
   - `GET /api/v1/prestamos/stats?mes=3&anio=2026`
   - Comprobar que `total`, `total_financiamiento` y `promedio_monto` reflejan préstamos con estado APROBADO o DESEMBOLSADO y fecha de aprobación/registro en marzo 2026.
2. **BD (opcional):**
   ```sql
   SELECT estado, COUNT(*), SUM(total_financiamiento)
   FROM prestamos p
   JOIN clientes c ON p.cliente_id = c.id
   WHERE c.estado = 'ACTIVO'
     AND p.estado IN ('APROBADO', 'DESEMBOLSADO')
     AND (COALESCE(p.fecha_aprobacion, p.fecha_registro))::date BETWEEN '2026-03-01' AND '2026-03-31'
   GROUP BY estado;
   ```
3. **Frontend:** En `/pagos/prestamos`, comprobar que los cuatro KPIs se actualizan según el mes y que, tras aprobar o asignar fecha, los valores se refrescan (recargar o volver a la pestaña si hace falta).

---

## 5. Resumen

| Antes | Después |
|-------|---------|
| Solo `Prestamo.estado == "APROBADO"` | `Prestamo.estado.in_(("APROBADO", "DESEMBOLSADO"))` |
| Préstamos desembolsados no contaban | Préstamos desembolsados entran en total, financiamiento y promedio |
| KPIs en 0 en la práctica | KPIs reflejan aprobados + desembolsados del mes |

La causa de que los KPIs “no se actualizaran” era que **no incluían el estado DESEMBOLSADO**, que es el estado en el que quedan los préstamos tras la aprobación/desembolso en esta aplicación.
