# Diagnóstico: Gráficos del Dashboard → Endpoint → Base de datos

Cada bloque visual del dashboard (KPIs, gráficos) está conectado a un endpoint del backend y, a través de él, a la **misma base de datos PostgreSQL** configurada en `DATABASE_URL` (inyectada vía `get_db()` en todos los endpoints).

---

## Resumen

| # | Bloque en pantalla | Endpoint | Tablas BD | Conectado |
|---|--------------------|----------|-----------|-----------|
| 0 | Opciones de filtros (dropdowns) | `GET /api/v1/dashboard/opciones-filtros` | **prestamos** | ✅ |
| 1 | KPIs principales (4 tarjetas) | `GET /api/v1/dashboard/kpis-principales` | **clientes**, **prestamos**, **cuotas** | ✅ |
| 2 | Evolución mensual (barras + línea) | `GET /api/v1/dashboard/admin` | **cuotas** | ✅ |
| 3 | Morosidad por día (barras) | `GET /api/v1/dashboard/morosidad-por-dia` | **cuotas** | ✅ |
| 4 | Monto programado por día (7 días) | `GET /api/v1/dashboard/monto-programado-proxima-semana` | **cuotas** | ✅ |
| 5 | Distribución por bandas de $200 USD | `GET /api/v1/dashboard/financiamiento-por-rangos` | **prestamos** | ✅ |
| 6 | Préstamos aprobados por modelo | `GET /api/v1/dashboard/prestamos-por-modelo` | **prestamos** | ✅ |
| 7 | Composición de morosidad (USD) | `GET /api/v1/dashboard/composicion-morosidad` | **cuotas** | ✅ |
| 8 | Cantidad de préstamos en mora por rango | Mismo endpoint que #7 | **cuotas** | ✅ |
| 9 | Cobranzas semanales (planificado vs real) | `GET /api/v1/dashboard/cobranzas-semanales` | **cuotas** | ✅ |
| 10 | Morosidad por analista (radar + barras) | `GET /api/v1/dashboard/morosidad-por-analista` | **cuotas** + **prestamos** (JOIN) | ✅ |

**Todos los gráficos están conectados a un endpoint y a la BD real.** No hay stubs en los datos que muestra esta página.

---

## Detalle por bloque

### 0. Opciones de filtros (Analista, Concesionario, Modelo)

- **Frontend:** `queryKey: ['opciones-filtros']` → `apiClient.get('/api/v1/dashboard/opciones-filtros')`
- **Endpoint:** `GET /api/v1/dashboard/opciones-filtros` → `get_opciones_filtros(db)`
- **BD:** Una sola base de datos (PostgreSQL vía `get_db`).
- **Tablas:**
  - **prestamos**: `SELECT DISTINCT analista`, `SELECT DISTINCT concesionario`, `SELECT DISTINCT modelo_vehiculo` (solo valores no nulos).

---

### 1. KPIs principales (4 tarjetas: Total préstamos, Créditos nuevos, Cuotas programadas, Morosidad total)

- **Frontend:** `queryKey: ['kpis-principales-menu', periodo, filtros]` → `GET /api/v1/dashboard/kpis-principales?…`
- **Endpoint:** `GET /api/v1/dashboard/kpis-principales` → `get_kpis_principales(...)` → `_compute_kpis_principales(db, ...)`
- **BD:** Misma PostgreSQL.
- **Tablas:**
  - **clientes**: conteo total, conteo por estado (ACTIVO, INACTIVO, FINALIZADO).
  - **prestamos**: conteo por período/filtros, suma `total_financiamiento` (período actual y anterior para variación).
  - **cuotas**: morosidad (cuotas vencidas sin pagar, join prestamos para filtros), cuotas programadas del mes, cantidad de cuotas pagadas (para %).

---

### 2. Evolución mensual (Cartera, Cobrado, Morosidad por mes)

- **Frontend:** `queryKey: ['dashboard-menu', periodoEvolucion, filtros]` → `GET /api/v1/dashboard/admin?…`
- **Endpoint:** `GET /api/v1/dashboard/admin` → `get_dashboard_admin(...)` → `_compute_dashboard_admin(db, fecha_inicio, fecha_fin)`
- **BD:** Misma PostgreSQL.
- **Tablas:**
  - **cuotas**: por cada mes del rango, suma `monto` con `fecha_vencimiento` en el mes (cartera); misma condición + `fecha_pago IS NOT NULL` (cobrado). Morosidad = cartera - cobrado.  
  No usa tabla **prestamos** en esta vista (no filtra por analista/concesionario/modelo en admin).

---

### 3. Morosidad por día

- **Frontend:** `queryKey: ['morosidad-por-dia', ...]` → `GET /api/v1/dashboard/morosidad-por-dia?dias=…&fecha_inicio=…&fecha_fin=…`
- **Endpoint:** `GET /api/v1/dashboard/morosidad-por-dia` → `get_morosidad_por_dia(...)` → `_compute_morosidad_por_dia(db, ...)`
- **BD:** Misma PostgreSQL.
- **Tablas:**
  - **cuotas**: por cada día del rango, cartera del día (suma `monto` donde `fecha_vencimiento = d`) y cobrado (suma `monto` donde `fecha_pago` cae en ese día). Morosidad = cartera - cobrado.

---

### 4. Monto programado por día (hoy hasta 7 días)

- **Frontend:** `queryKey: ['monto-programado-proxima-semana']` → `GET /api/v1/dashboard/monto-programado-proxima-semana`
- **Endpoint:** `GET /api/v1/dashboard/monto-programado-proxima-semana` → `get_monto_programado_proxima_semana(db)`
- **BD:** Misma PostgreSQL.
- **Tablas:**
  - **cuotas**: por cada día de hoy a hoy+7, `SUM(monto)` donde `fecha_vencimiento = d` (solo cuotas con vencimiento ese día).

---

### 5. Distribución por bandas de $200 USD (barras horizontales)

- **Frontend:** `queryKey: ['financiamiento-rangos', ...]` → `GET /api/v1/dashboard/financiamiento-por-rangos?…`
- **Endpoint:** `GET /api/v1/dashboard/financiamiento-por-rangos` → `_compute_financiamiento_por_rangos(db, ...)`
- **BD:** Misma PostgreSQL.
- **Tablas:**
  - **prestamos**: cuenta de préstamos con `estado = 'APROBADO'` y `total_financiamiento` en cada banda ($0–200, $200–400, …, más de $1,400). Opcionalmente filtrado por analista, concesionario, modelo.

---

### 6. Préstamos aprobados por modelo de vehículo (barras %)

- **Frontend:** `queryKey: ['prestamos-por-modelo', ...]` → `GET /api/v1/dashboard/prestamos-por-modelo?…`
- **Endpoint:** `GET /api/v1/dashboard/prestamos-por-modelo` → `get_prestamos_por_modelo(...)` (usa `_parse_fechas_concesionario` y consultas directas a Prestamo)
- **BD:** Misma PostgreSQL.
- **Tablas:**
  - **prestamos**: agrupación por `modelo_vehiculo` (por_mes en el período y acumulado desde el inicio), `estado = 'APROBADO'`.

---

### 7 y 8. Composición de morosidad (USD) y Cantidad de préstamos en mora por rango de días

- **Frontend:** `queryKey: ['composicion-morosidad', ...]` → `GET /api/v1/dashboard/composicion-morosidad?…`
- **Endpoint:** `GET /api/v1/dashboard/composicion-morosidad` → `_compute_composicion_morosidad(db, ...)`
- **BD:** Misma PostgreSQL.
- **Tablas:**
  - **cuotas**: cuotas con `fecha_pago IS NULL` y días de atraso (`current_date - fecha_vencimiento`) en bandas 1–30, 31–60, 61–90, 90+ días. Se devuelve monto, cantidad de cuotas y cantidad de préstamos (`COUNT(DISTINCT prestamo_id)`).  
  Nota: el endpoint recibe analista/concesionario/modelo pero la función `_compute_composicion_morosidad` actual **no** los aplica en el WHERE (solo usa **cuotas**).

---

### 9. Cobranzas semanales (planificado vs real)

- **Frontend:** `queryKey: ['cobranzas-semanales', ...]` → `GET /api/v1/dashboard/cobranzas-semanales?…&semanas=12`
- **Endpoint:** `GET /api/v1/dashboard/cobranzas-semanales` → `_compute_cobranzas_semanales(db, ...)`
- **BD:** Misma PostgreSQL.
- **Tablas:**
  - **cuotas**: por cada semana hacia atrás, cuenta y suma de cuotas con `fecha_pago` en esa semana (`pagos_reales`, `monto_reales`). `cobranzas_planificadas` se devuelve en 0 (sin tabla de planificación).

---

### 10. Morosidad por analista (radar “Cuotas vencidas” + barras “Dólares vencidos”)

- **Frontend:** `queryKey: ['morosidad-analista', ...]` → `GET /api/v1/dashboard/morosidad-por-analista?…`
- **Endpoint:** `GET /api/v1/dashboard/morosidad-por-analista` → `_compute_morosidad_por_analista(db, ...)`
- **BD:** Misma PostgreSQL.
- **Tablas:**
  - **cuotas** + **prestamos**: `Cuota JOIN Prestamo ON cuota.prestamo_id = prestamo.id`, filtro `Prestamo.estado = 'APROBADO'`, cuotas con `fecha_pago IS NULL` y `fecha_vencimiento < hoy`. Agrupado por `Prestamo.analista`, con opcional filtro por analista/concesionario/modelo.

---

## Conexión de la BD

- **Configuración:** `app/core/config.py` → `settings.DATABASE_URL` (por defecto desde `.env` o variables de entorno).
- **Uso en dashboard:** Todos los endpoints del dashboard usan `Depends(get_db)`; `get_db()` está definido en `app/core/database.py` y devuelve una sesión de SQLAlchemy sobre el `engine` creado con `settings.DATABASE_URL` (PostgreSQL).
- **Conclusión:** Hay una sola BD (PostgreSQL) para toda la app; todos los gráficos del dashboard leen de esa BD a través de los endpoints indicados.

---

## Resumen por tabla

| Tabla      | Usada en bloques |
|-----------|-------------------|
| **clientes** | 1 (KPIs: total clientes, por estado) |
| **prestamos** | 0 (opciones filtros), 1 (KPIs), 5 (bandas), 6 (por modelo), 10 (morosidad por analista, JOIN con cuotas) |
| **cuotas** | 1 (KPIs), 2 (evolución), 3 (morosidad por día), 4 (monto programado), 7 y 8 (composición morosidad), 9 (cobranzas semanales), 10 (morosidad por analista, JOIN con prestamos) |

Este documento refleja el estado del código en `backend/app/api/v1/endpoints/dashboard.py` y `frontend/src/pages/DashboardMenu.tsx`.
