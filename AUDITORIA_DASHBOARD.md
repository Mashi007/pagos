# Auditoría integral del flujo Dashboard (backend y frontend)

**Fecha:** 2025-02-02  
**Alcance:** Dashboard ejecutivo (DashboardMenu), endpoints `/api/v1/dashboard/*`, hooks y servicios relacionados.

---

## 1. Resumen ejecutivo

| Aspecto | Estado | Notas |
|---------|--------|--------|
| **Backend – datos reales** | ✅ Mayoría BD | KPIs, evolución, morosidad, concesionarios, modelos, rangos y composición morosidad usan BD. Algunos endpoints siguen stub. |
| **Frontend – flujo de datos** | ✅ Correcto | React Query por batches, filtros centralizados, manejo de errores. |
| **Seguridad** | ✅ OK | Dashboard protegido por `get_current_user`; frontend usa Bearer y apiClient. |
| **Consistencia API ↔ UI** | ⚠️ 2 bugs | Bandas usan `cantidad` en UI pero API devuelve `cantidad_prestamos`; período "día" (con tilde) no se traduce a fechas. |
| **Rendimiento** | ✅ Aceptable | Carga por prioridad, staleTime, timeouts extendidos en endpoints pesados. |

---

## 2. Backend

### 2.1 Estructura y rutas

- **Router:** `app/api/v1/endpoints/dashboard.py`
- **Prefijo:** `/api/v1/dashboard` (registrado en `app/api/v1/__init__.py`)
- **Protección:** `dependencies=[Depends(get_current_user)]` en el router; todos los endpoints exigen autenticación.

### 2.2 Endpoints utilizados por el Dashboard ejecutivo

| Endpoint | Origen datos | Uso en frontend |
|----------|--------------|------------------|
| `GET /opciones-filtros` | BD (vacío si no hay campos) | Selects Analista / Concesionario / Modelo |
| `GET /kpis-principales` | Cliente, Prestamo (BD) | 4 KPI cards (préstamos, créditos nuevos, cuotas programadas, morosidad) |
| `GET /admin` | Cuota (BD): cartera/cobrado/morosidad por mes | Gráfico “Evolución mensual” |
| `GET /morosidad-por-dia` | Cuota (BD) | Gráfico “Morosidad por día” |
| `GET /prestamos-por-concesionario` | Prestamo (BD) | Tablas por mes y acumulado concesionarios |
| `GET /prestamos-por-modelo` | Prestamo (BD) | Tablas por mes y acumulado modelos |
| `GET /financiamiento-por-rangos` | Prestamo (BD) | Gráfico “Distribución por bandas de $200 USD” |
| `GET /composicion-morosidad` | Cuota (BD) | Gráfico “Composición de morosidad” |
| `GET /cobranzas-semanales` | **Stub** (valores fijos) | No mostrado en DashboardMenu actual |
| `GET /morosidad-por-analista` | Cuota + Prestamo (BD) | Gráficos radar por analista |

### 2.3 Endpoints stub (sin BD real)

- `GET /cobranza-por-dia` → `{"dias": []}`
- `GET /cobranzas-mensuales` → `{"meses": []}`
- `GET /cobros-por-analista` → `{"analistas": []}`
- `GET /cobros-diarios` → `{"dias": []}`
- `GET /cuentas-cobrar-tendencias` → `{"tendencias": []}`
- `GET /distribucion-prestamos` → `{"distribucion": []}`
- `GET /metricas-acumuladas` → `{"metricas": []}`
- `GET /cobranza-fechas-especificas` → `{"dias": []}`
- `GET /evolucion-pagos` → datos demo desde `_ultimos_12_meses()`

### 2.4 Regla “datos reales”

- Se cumple en los endpoints que alimentan el Dashboard ejecutivo: usan `get_db`, consultas a `Cliente`, `Prestamo`, `Cuota`.
- Los stubs están documentados en el código y devuelven estructuras vacías o demo; conviene sustituirlos cuando existan tablas de pagos/cobranzas.

### 2.5 Parámetros de filtro

- **Query params comunes:** `fecha_inicio`, `fecha_fin`, `analista`, `concesionario`, `modelo`, `periodo`, `dias`, `meses`, `semanas`.
- El backend acepta fechas ISO (`YYYY-MM-DD`) y aplica rangos coherentes (p. ej. `_rango_y_anterior`, `_parse_fechas_concesionario`).

### 2.6 Compatibilidad BD

- Uso de `func.to_char`, `func.date_trunc` en `prestamos-por-concesionario` y `prestamos-por-modelo`: **PostgreSQL**. Si la BD fuera SQLite, habría que sustituir por expresiones equivalentes.

---

## 3. Frontend

### 3.1 Página principal

- **Componente:** `frontend/src/pages/DashboardMenu.tsx`
- **Ruta:** definida en `App.tsx` (ej. `/dashboard` según configuración).
- **Auth:** contenido bajo `SimpleProtectedRoute` + Layout; las llamadas API llevan Bearer (apiClient).

### 3.2 Flujo de datos

1. **Filtros:** estado local `filtros` + `periodo`; `useDashboardFiltros(filtros)` expone `construirFiltrosObject(periodo)` y `construirParams(periodo)` para armar query params y fechas.
2. **Carga:** React Query en “batches”:
   - Batch 1: `opciones-filtros`, `kpis-principales`
   - Batch 2: `dashboard/admin` (evolución)
   - Batch 3: `morosidad-por-dia`, `prestamos-por-concesionario`, `prestamos-por-modelo`
   - Batch 4: `financiamiento-por-rangos`, `composicion-morosidad`, `cobranzas-semanales`, `morosidad-por-analista`
3. **QueryKeys:** incluyen `periodo` y `JSON.stringify(filtros)` para refetch al cambiar filtros/período.
4. **Refresh manual:** `handleRefresh` invalida y refetch de las queries del dashboard.

### 3.3 Períodos

- Valores en UI: `ultimos_12_meses`, `día`, `semana`, `mes`, `año`.
- Cálculo de fechas: `useDashboardFiltros` → `calcularFechasPorPeriodo(periodo)`.  
- **Bug:** En el `Select` se usa el valor `día` (con tilde), pero en `calcularFechasPorPeriodo` el `switch` solo tiene `case 'dia'` (sin tilde). Al elegir “Hoy” se cae en `default` y se usan fechas de “Este mes”. **Corrección:** aceptar también `'día'` (p. ej. `case 'día':` delegando a la misma lógica que `'dia'`).

### 3.4 Gráfico “Distribución por bandas de $200 USD”

- **Backend:** `GET /financiamiento-por-rangos` devuelve `rangos[]` con `categoria`, `cantidad_prestamos`, `monto_total`, `porcentaje_cantidad`, `porcentaje_monto`.
- **Frontend:** `datosBandas200` mapea `rangos` y añade `categoriaFormateada`, pero el `Bar` usa `dataKey="cantidad"` y las celdas usan `d.cantidad`. En la API no existe `cantidad`, solo `cantidad_prestamos`. **Efecto:** las barras salen vacías. **Corrección:** en el mapeo de `datosBandas200` incluir `cantidad: r.cantidad_prestamos` (o usar `dataKey="cantidad_prestamos"` en Bar/Cells).

### 3.5 Manejo de errores

- Errores críticos (`errorOpcionesFiltros`, `errorKPIs`): banner amarillo “Algunos datos no se pudieron cargar…”.
- Error en KPIs: card roja con mensaje.
- Error en financiamiento por rangos: catch con fallback a `{ rangos: [], total_prestamos: 0, total_monto: 0 }` para errores no 5xx/red; 5xx/red se relanzan para React Query.
- Timeouts: 60s en `dashboard/admin` y `financiamiento-por-rangos`.

### 3.6 UX

- Aviso cuando no hay datos (préstamos/cuotas) y gráficos vacíos.
- Badge “Datos de ejemplo” cuando `evolucion_origen === 'demo'` (en el código actual la evolución viene de BD, así que no se muestra).
- Selector de período por gráfico (cada card puede usar período general o propio).
- Loading skeletons en KPIs y en gráficos.

---

## 4. Hallazgos y acciones

### 4.1 Bugs corregidos en esta auditoría

1. **Bandas $200:** El gráfico espera `cantidad` y la API devuelve `cantidad_prestamos`. Se corrige mapeando `cantidad: r.cantidad_prestamos` en `datosBandas200` (o usando `cantidad_prestamos` en el Bar).
2. **Período “Hoy”:** El valor `día` (con tilde) no tiene `case` en `calcularFechasPorPeriodo`. Se añade `case 'día':` con la misma lógica que `'dia'`.

### 4.2 Recomendaciones

- **Backend:** Sustituir stubs de cobranza/evolución de pagos cuando existan tablas de pagos/cobranzas; documentar en OpenAPI qué endpoints son stub.
- **BD:** Si se usa SQLite, revisar `to_char`/`date_trunc` en concesionarios/modelos y usar equivalentes (p. ej. `strftime`).
- **Frontend:** Unificar valor de período “día” en toda la app (solo `día` o solo `dia`) para evitar desajustes.
- **Tipado:** Alinear tipos TypeScript de respuestas del dashboard con los DTOs/schemas del backend para evitar desajustes como `cantidad` vs `cantidad_prestamos`.

---

## 5. Checklist de verificación

- [x] Dashboard requiere autenticación (backend y frontend).
- [x] KPIs y gráficos principales usan datos reales de BD.
- [x] Filtros (período, analista, concesionario, modelo) se envían correctamente en las peticiones.
- [x] Errores y timeouts manejados sin romper la página.
- [x] Gráfico de bandas usa el campo correcto de la API (`cantidad_prestamos` → `cantidad` en UI).
- [x] Período “Hoy” (`día`) calcula fechas del día actual.
- [ ] Endpoints stub documentados o sustituidos por implementaciones con BD (seguimiento futuro).
