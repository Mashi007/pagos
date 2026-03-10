# Revisión integral: endpoints, tablas, BD (Pagos / RapiCredit)

**URL revisada:** https://rapicredit.onrender.com/pagos/pagos  
**Fecha:** 2025-03-09

---

## 1. Relación URL ↔ Backend

| Capa | Detalle |
|------|--------|
| **Frontend (SPA)** | Base path `/pagos/` (Vite `base: '/pagos/'`, `server.js` FRONTEND_BASE). La ruta interna es `/pagos` (path relativo al basename), URL completa: `https://rapicredit.onrender.com/pagos/pagos`. |
| **API consumida** | En producción el frontend usa `API_URL = ''` (rutas relativas). Las peticiones van a `/api/v1/...` sobre el mismo origen. |
| **Proxy (server.js)** | Las peticiones a `/api/*` se reenvían al backend vía `API_BASE_URL` (variable en Render). Sin `API_BASE_URL` las llamadas a la API fallan. |
| **Backend (FastAPI)** | Prefijo global `API_V1_STR = "/api/v1"` en `backend/app/main.py`. Routers se montan con ese prefijo en `backend/app/api/v1/__init__.py`. |

**Conclusión:** La pantalla **Pagos** (`/pagos/pagos`) llama a **GET /api/v1/pagos** (listado paginado). Ese endpoint lee datos reales de la tabla `pagos` y, si se filtra por analista, hace JOIN con `prestamos`.

---

## 2. Endpoints relevantes para Pagos, Préstamos y Clientes

Rutas completas: **`/api/v1`** + prefijo + path del router.

### 2.1 Pagos (pantalla /pagos/pagos)

| Método | Ruta completa | Descripción |
|--------|----------------|-------------|
| GET | `/api/v1/pagos` | Listado paginado (filtros: cedula, estado, fecha_desde/hasta, analista, conciliado, sin_prestamo). **Datos: tabla `pagos`**. Si hay filtro `analista`, JOIN con `prestamos`. |
| GET | `/api/v1/pagos/ultimos` | Últimos pagos por cédula (resumen). Usa `pagos` + JOIN `prestamos` → `clientes` y `cuotas` para mora. |
| GET | `/api/v1/pagos/{pago_id}` | Detalle de un pago. |
| POST | `/api/v1/pagos` | Crear pago. |
| PUT | `/api/v1/pagos/{pago_id}` | Actualizar pago. |
| DELETE | `/api/v1/pagos/{pago_id}` | Eliminar pago. |
| GET | `/api/v1/pagos/kpis` | KPIs de pagos (conteos, montos). JOIN pagos + préstamos + clientes/cuotas. |
| GET | `/api/v1/pagos/stats` | Estadísticas. Igual, datos reales con JOINs. |
| POST | `/api/v1/pagos/{pago_id}/aplicar-cuotas` | Aplicar pago a cuotas (tablas `cuotas`, `cuota_pagos`). |
| POST | `/api/v1/pagos/upload` | Carga masiva Excel. |
| POST | `/api/v1/pagos/conciliacion/upload` | Carga conciliación. |

**Pagos con errores (Revisar Pagos):**

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET/POST/etc. | `/api/v1/pagos/con-errores` | CRUD sobre tabla `pagos_con_error`. El router está registrado **antes** que `/pagos` para que `/pagos/con-errores` no se interprete como `GET /pagos/{pago_id}`. |

### 2.2 Préstamos

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/api/v1/prestamos` | Listado (JOIN con `clientes` para nombres/cédula). |
| GET | `/api/v1/prestamos/stats` | Estadísticas. |
| GET | `/api/v1/prestamos/cedula/{cedula}` | Por cédula. |
| GET | `/api/v1/prestamos/{prestamo_id}` | Detalle. |
| GET | `/api/v1/prestamos/{prestamo_id}/cuotas` | Cuotas del préstamo. |
| POST/PUT/DELETE | `/api/v1/prestamos` y `/{id}` | CRUD. |
| POST | `/api/v1/prestamos/upload-excel` | Carga masiva. |

### 2.3 Clientes

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/api/v1/clientes` | Listado paginado desde tabla `clientes`. |
| GET | `/api/v1/clientes/stats` | Estadísticas. |
| GET | `/api/v1/clientes/estados` | Estados (tabla `estados_cliente`). |
| POST | `/api/v1/clientes/actualizar-lote` | Actualización en lote. |

### 2.4 Dashboard, reportes, notificaciones

- **Dashboard/KPIs:** `/api/v1/kpis/*`, `/api/v1/dashboard/*` — usan préstamos, clientes, cuotas, pagos (JOINs).
- **Reportes:** `/api/v1/reportes/*` (cartera, pagos, morosidad, financiero, asesores, productos, por cédula, contable, conciliación) — todos con datos reales y JOINs entre prestamos, clientes, cuotas, pagos.
- **Notificaciones:** `/api/v1/notificaciones/*` — clientes retrasados y envíos; usan cuotas → préstamos → clientes.

---

## 3. Tablas y concatenación (JOINs)

### 3.1 Modelos principales

| Modelo | Tabla | Relación FK |
|--------|--------|-------------|
| **Cliente** | `clientes` | — |
| **Prestamo** | `prestamos` | `cliente_id` → `clientes.id` |
| **Pago** | `pagos` | `prestamo_id` → `prestamos.id` (SET NULL) |
| **Cuota** | `cuotas` | `prestamo_id` → `prestamos.id`, `pago_id` → `pagos.id` (SET NULL), `cliente_id` → `clientes.id` |
| **CuotaPago** | `cuota_pagos` | `cuota_id` → `cuotas.id`, `pago_id` → `pagos.id` (CASCADE) — tabla de aplicación pago↔cuota (N:N con monto y orden). |

Definiciones: `backend/app/models/` (cliente.py, prestamo.py, pago.py, cuota.py, cuota_pago.py).

### 3.2 Dónde se “concatenan” tablas (JOINs)

- **Listado GET /api/v1/pagos**
  - Base: solo tabla `pagos` (select Pago, filtros sobre columnas de Pago).
  - Si se envía filtro `analista`: se hace `JOIN prestamos` (`Pago.prestamo_id == Prestamo.id`) y `WHERE Prestamo.analista = ...`. No se devuelven columnas de Prestamo/Cliente en el listado; solo se usan para filtrar.
- **GET /pagos/ultimos**
  - Pagos + para cada cédula: préstamos del cliente (Prestamo + Cliente) y cuotas en mora (Cuota).
- **GET /pagos/kpis y /pagos/stats**
  - JOINs entre Pago, Prestamo, Cliente, Cuota según la métrica.
- **Préstamos (listado, stats, por cédula)**
  - Prestamo JOIN Cliente (nombre, cédula).
- **Dashboard, reportes, notificaciones**
  - Combinaciones de Cuota, Prestamo, Cliente, Pago según el endpoint.

En el código no se usan `relationship()` de SQLAlchemy en estos modelos de negocio; los JOINs se hacen explícitos en las consultas (select/join/where).

---

## 4. Acceso a la base de datos

### 4.1 Configuración

- **Engine y sesión:** `backend/app/core/database.py`.
  - `DATABASE_URL` desde `app/core/config.py` (env `.env` o variables de entorno).
  - `engine` con `pool_pre_ping`, pool size 10, max_overflow 20, pool_recycle 1800.
  - `SessionLocal` con `expire_on_commit=False`.
  - Zona horaria por conexión: `America/Caracas`.

### 4.2 Inyección en endpoints

- **Dependencia:** `get_db()` en `database.py`: genera una sesión por request y la cierra en un `finally`.
- **Uso:** En los endpoints que tocan BD se usa `db: Session = Depends(get_db)`.
- **Pagos:** `listar_pagos`, `get_ultimos_pagos`, `get_pago`, crear/actualizar/eliminar, KPIs, stats, aplicar-cuotas, upload, etc. usan `Depends(get_db)` y consultas sobre `Pago`, `Prestamo`, `Cliente`, `Cuota`, `CuotaPago` según corresponda.

No hay stubs en estos endpoints; los datos salen de la BD configurada. El health check de BD es **GET /api/v1/health/db** (o bajo el prefijo que monte el router de health).

---

## 5. Verificaciones recomendadas para https://rapicredit.onrender.com/pagos/pagos

1. **Variable en Render (servidor frontend):** `API_BASE_URL` debe apuntar al backend (ej. `https://pagos-backend-ov5f.onrender.com` o la URL del servicio backend en Render). Sin ella, las peticiones a `/api/v1/pagos` devuelven 404 o no llegan al backend.
2. **CORS en el backend:** Si en algún momento el frontend llamara al backend por URL absoluta (otro dominio), el backend debe incluir en CORS el origen `https://rapicredit.onrender.com` (en el proyecto está en la lista por defecto en `config.py`).
3. **Orden de routers:** En `api/v1/__init__.py`, el router de `pagos_con_errores` está antes que el de `pagos`, de modo que `GET /api/v1/pagos/con-errores` no se capture como `GET /api/v1/pagos/{pago_id}`. Correcto.
4. **Listado de pagos:** Solo devuelve columnas de la tabla `pagos` (y `cuotas_atrasadas` calculado cuando aplica). Si la UI necesitara nombre de cliente o datos del préstamo en cada fila, habría que ampliar el endpoint (p. ej. JOIN con Cliente/Prestamo y devolver campos extra) o hacer llamadas adicionales por fila (menos eficiente).

---

## 6. Resumen

- **Endpoints:** La pantalla `/pagos/pagos` usa sobre todo **GET /api/v1/pagos** (listado) y el resto de operaciones CRUD/KPIs/stats sobre el mismo prefijo `/api/v1/pagos`. Préstamos y clientes se sirven en `/api/v1/prestamos` y `/api/v1/clientes`.
- **Tablas:** `pagos`, `prestamos`, `clientes`, `cuotas`, `cuota_pagos` están relacionadas por FKs; la “concatenación” se hace con JOINs en las consultas, no con relationships en los modelos.
- **Acceso BD:** Todos los endpoints relevantes usan `get_db` y consultas reales; no hay respuestas stub para esta funcionalidad.
- **Producción:** Para que https://rapicredit.onrender.com/pagos/pagos funcione, el proxy del frontend debe tener configurado `API_BASE_URL` hacia el backend y la BD del backend debe ser la correcta vía `DATABASE_URL`.
