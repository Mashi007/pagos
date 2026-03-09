# Auditoría integral: KPIs de préstamos no se actualizan

**Fecha:** 2026-03-08  
**Página afectada:** `/pagos/prestamos` (KPIs: Financiamiento mensual, Préstamos mensual, Promedio mensual, Por cobrar mensual)  
**Endpoint:** `GET /api/v1/prestamos/stats`

---

## 1. Flujo revisado

| Capa | Componente | Detalle |
|------|------------|---------|
| Frontend | `PrestamosKPIs.tsx` | Selector mes/año; usa `usePrestamosKPIs({ mes, anio })` |
| Frontend | `prestamoService.getKPIs()` | Llama `GET /api/v1/prestamos/stats?mes=X&anio=Y` (X = 1–12, Y = año) |
| Backend | `get_prestamos_stats()` | Filtra por `Cliente.estado == "ACTIVO"`, `Prestamo.estado IN ('APROBADO','DESEMBOLSADO')`, fecha_ref en el mes |
| BD | `prestamos.estado` | Valores válidos: DRAFT, EN_REVISION, EVALUADO, APROBADO, RECHAZADO, DESEMBOLSADO |

---

## 2. Causa raíz identificada

**Problema:** El endpoint `/prestamos/stats` filtraba solo `Prestamo.estado == "APROBADO"`. Tras aprobar o desembolsar, el préstamo queda en **DESEMBOLSADO**, por lo que no contaba y los KPIs salían en 0.

**Solución aplicada:** Incluir `Prestamo.estado.in_(("APROBADO", "DESEMBOLSADO"))` en todas las consultas del stats.

---

## 3. Cambios realizados

### 3.1 Backend (`prestamos.py`)

- `_estados_aprobados_kpi = ("APROBADO", "DESEMBOLSADO")` en consulta base, por_estado y cartera_vigente.
- Fecha de referencia: `cast(func.coalesce(Prestamo.fecha_aprobacion, Prestamo.fecha_registro), Date)` entre inicio_mes y fin_mes.

### 3.2 Frontend

- Selector de **mes** y **año** en la sección KPIs para elegir el mes a consultar.
- Invalidación de caché `['prestamos']` al aprobar o asignar fecha de aprobación.
- `usePrestamosKPIs` con `staleTime: 0` y filtros `mes`, `anio` en la queryKey para refetch al cambiar mes/año.

---

## 4. Si los KPIs siguen sin actualizarse

### 4.1 Checklist

| # | Punto | Cómo comprobar |
|---|--------|-----------------|
| 1 | **Mes consultado** | Usar el selector mes/año y elegir el mes donde hay aprobaciones (ej. Febrero 2026). Si está en Marzo y no hay aprobaciones en marzo, los KPIs en 0 son correctos. |
| 2 | **URL y parámetros** | En la pestaña Red (F12), la petición debe ser `GET /api/v1/prestamos/stats?mes=2&anio=2026`. El parámetro es `anio` (sin tilde). |
| 3 | **Backend desplegado** | En Render (o tu host) debe estar desplegada la versión con DESEMBOLSADO y la lógica de fecha con `cast(..., Date)`. Si el backend es antiguo, los valores pueden seguir en 0. |
| 4 | **Clientes ACTIVO** | Solo entran préstamos cuyo cliente tiene `clientes.estado = 'ACTIVO'`. Si los aprobados están con clientes INACTIVO/FINALIZADO, ese mes puede devolver 0. |
| 5 | **Error en la petición** | Si la llamada a `/prestamos/stats` falla (red, 401, 500), el front muestra 0. Revisar consola del navegador (F12) y registro de errores del servicio. |
| 6 | **Caché** | Al cambiar mes o año, la queryKey de React Query cambia y se hace nueva petición. Si no ves cambio, hacer F5 o comprobar que los selectores actualizan el estado. |

### 4.2 Flujo de datos

```
PrestamosKPIs (mesSel, anioSel)
  → usePrestamosKPIs({ mes: mesSel, anio: anioSel, ... })
  → queryKey: ['prestamos', 'kpis', { mes, anio, ... }]
  → prestamoService.getKPIs(filters)
  → GET /api/v1/prestamos/stats?mes=2&anio=2026
  → get_prestamos_stats(mes=2, anio=2026)
  → WHERE cliente.estado='ACTIVO' AND prestamo.estado IN ('APROBADO','DESEMBOLSADO')
        AND (COALESCE(fecha_aprobacion,fecha_registro))::date BETWEEN '2026-02-01' AND '2026-02-29'
  → Response: { total, total_financiamiento, promedio_monto, cartera_vigente, mes, anio }
  → UI: totalFinanciamiento, totalPrestamos, promedioMonto, totalCarteraVigente
```

### 4.3 Robustez

- **Selector mes/año:** Permite consultar cualquier mes; por defecto es el mes actual.
- **Log de error:** En `prestamoService.getKPIs`, si la petición falla se registra en consola para diagnóstico.
- **Invalidación:** Al aprobar o asignar fecha de aprobación se invalida la caché de préstamos para que los KPIs se refresquen.
