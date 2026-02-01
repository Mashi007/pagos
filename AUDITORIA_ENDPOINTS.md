# Auditoría integral de endpoints API v1

**Fecha:** 2026-02-01  
**Alcance:** Backend (FastAPI) vs Frontend (React/Vite) — rutas `/api/v1/*`.

---

## 1. Resumen ejecutivo

| Categoría | Backend | Frontend espera | Cubierto (stub/real) | Faltante |
|-----------|---------|----------------|----------------------|----------|
| Auth | 4 | 5 | 4 | 1 (logout, change-password) |
| Configuración | 2 | 2 + muchos AI | 2 | Toda rama `/configuracion/ai/*` |
| Pagos | 2 | 4+ (CRUD, kpis, stats) | 2 | CRUD pagos, list |
| Notificaciones | 1 | 1 + plantillas, listas | 1 | Plantillas, estadísticas por tipo |
| Dashboard | 21 | 21 | 21 | 0 (stubs añadidos) |
| KPIs | 1 | 1 | 1 | 0 (stub kpis/dashboard) |
| Otros módulos | 0 | ~15 módulos | 0 | clientes, usuarios, prestamos, etc. |

**Conclusión:** El backend actual expone solo **auth**, **whatsapp**, **configuracion** (general + logo), **pagos** (kpis + stats), **notificaciones** (resumen) y **dashboard** (14 rutas). El frontend espera además **más de 80 rutas** en otros módulos y varias rutas adicionales en dashboard y configuración AI.

---

## 2. Inventario backend (lo que existe hoy)

Prefijo global: `settings.API_V1_STR` = `/api/v1`.  
Rutas raíz sin prefijo: `/`, `/health` (GET/HEAD).

### 2.1 Auth `/api/v1/auth`

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/auth/status` | Diagnóstico auth configurado |
| POST | `/auth/login` | Login (JWT) |
| POST | `/auth/refresh` | Refresh token |
| GET | `/auth/me` | Usuario actual (requiere JWT) |

**No implementado en backend:**  
- `POST /auth/logout` (frontend llama en authService)  
- `POST /auth/change-password` (frontend llama en authService)

### 2.2 WhatsApp `/api/v1/whatsapp`

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/whatsapp/webhook` | Verificación webhook Meta |
| POST | `/whatsapp/webhook` | Eventos/incoming messages |

### 2.3 Configuración `/api/v1/configuracion`

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/configuracion/general` | Nombre app, logo_filename (stub) |
| GET | `/configuracion/logo/{filename}` | Sirve logo (404 si no hay archivo) |

**No implementado:**  
- `POST /configuracion/upload-logo`, `POST /configuracion/logo` (Configuracion.tsx)  
- Toda la rama **AI**: `/configuracion/ai/prompt`, `/configuracion/ai/prompt/variables`, `/configuracion/ai/configuracion`, `/configuracion/ai/documentos`, `/configuracion/ai/probar`, `/configuracion/ai/diccionario-semantico`, `/configuracion/ai/definiciones-campos`, `/configuracion/ai/tablas-campos`, `/configuracion/ai/chat`, `/configuracion/ai/chat/calificaciones`, etc.

### 2.4 Pagos `/api/v1/pagos`

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/pagos/kpis` | KPIs (stub: ceros) |
| GET | `/pagos/stats` | Stats por estado (stub: vacío) |

**No implementado:**  
- `GET /pagos/` (list paginado), `POST /pagos/`, `GET /pagos/{id}`, `PUT /pagos/{id}`, etc. (pagoService, PagosPage).

### 2.5 Notificaciones `/api/v1/notificaciones`

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/notificaciones/estadisticas/resumen` | no_leidas, total (stub) |

**No implementado:**  
- Plantillas: `GET/POST /notificaciones/plantillas`, `GET/PUT/DELETE /plantillas/{id}`, export, enviar.  
- Listas: `notificaciones-previas`, `notificaciones-retrasadas`, `notificaciones-prejudicial`, `notificaciones-dia-pago` (frontend usa rutas con guión).

### 2.6 Dashboard `/api/v1/dashboard`

| Método | Ruta | Estado |
|--------|------|--------|
| GET | `/dashboard/opciones-filtros` | Stub |
| GET | `/dashboard/kpis-principales` | Stub |
| GET | `/dashboard/admin` | Stub |
| GET | `/dashboard/financiamiento-tendencia-mensual` | Stub |
| GET | `/dashboard/prestamos-por-concesionario` | Stub |
| GET | `/dashboard/prestamos-por-modelo` | Stub |
| GET | `/dashboard/financiamiento-por-rangos` | Stub |
| GET | `/dashboard/composicion-morosidad` | Stub |
| GET | `/dashboard/cobranza-fechas-especificas` | Stub |
| GET | `/dashboard/cobranzas-semanales` | Stub |
| GET | `/dashboard/morosidad-por-analista` | Stub |
| GET | `/dashboard/evolucion-morosidad` | Stub |
| GET | `/dashboard/evolucion-pagos` | Stub |
| GET | `/dashboard/cobranza-por-dia` | Stub |
| GET | `/dashboard/cobranzas-mensuales` | Stub |
| GET | `/dashboard/cobros-por-analista` | Stub |
| GET | `/dashboard/cobros-diarios` | Stub |
| GET | `/dashboard/cuentas-cobrar-tendencias` | Stub |
| GET | `/dashboard/distribucion-prestamos` | Stub |
| GET | `/dashboard/metricas-acumuladas` | Stub |

### 2.7 KPIs `/api/v1/kpis`

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/kpis/dashboard` | KPIs dashboard (stub; DashboardFinanciamiento, DashboardCuotas) |

---

## 3. Inventario frontend (rutas que el frontend usa)

Servicios y páginas que construyen URLs bajo `/api/v1/`.  
Solo se listan rutas únicas por path (sin duplicar por método cuando es obvio).

### 3.1 Auth

- `POST /api/v1/auth/login`  
- `POST /api/v1/auth/refresh`  
- `GET /api/v1/auth/me`  
- `POST /api/v1/auth/logout` (backend no existe)  
- `POST /api/v1/auth/change-password` (backend no existe)

### 3.2 Configuración

- `GET /api/v1/configuracion/general`  
- `GET /api/v1/configuracion/logo/{filename}`  
- `POST /api/v1/configuracion/upload-logo`, `POST /api/v1/configuracion/logo`  
- **AI:** prompt, prompt/variables, ai/configuracion, ai/documentos, ai/probar, ai/diccionario-semantico, ai/definiciones-campos, ai/tablas-campos, ai/chat, ai/chat/calificaciones, etc. (todos sin implementar en backend)

### 3.3 Pagos

- `GET /api/v1/pagos/kpis`, `GET /api/v1/pagos/stats` (existen)  
- `GET /api/v1/pagos/`, `POST /api/v1/pagos/`, `GET/PUT/DELETE /api/v1/pagos/{id}` (no existen)

### 3.4 Notificaciones

- `GET /api/v1/notificaciones/estadisticas/resumen` (existe)  
- `GET/POST /api/v1/notificaciones/plantillas`, `GET/PUT/DELETE /api/v1/notificaciones/plantillas/{id}`, export, enviar  
- `GET /api/v1/notificaciones-previas/`, `notificaciones-retrasadas/`, `notificaciones-prejudicial/`, `notificaciones-dia-pago/` (rutas con guión; no bajo `/notificaciones/`)

### 3.5 Dashboard

- Todos los listados en §2.6 más:  
  `cobranza-por-dia`, `cobranzas-mensuales`, `cobros-por-analista`, `cobros-diarios`, `cuentas-cobrar-tendencias`, `distribucion-prestamos`, `metricas-acumuladas`.

### 3.6 KPIs (rutas distintas a dashboard)

- `GET /api/v1/kpis/dashboard` (DashboardFinanciamiento, DashboardCuotas) — **stub añadido** en `backend/app/api/v1/endpoints/kpis.py`.

### 3.7 Usuarios

- `GET/POST /api/v1/usuarios/`, `GET/PUT/DELETE /api/v1/usuarios/{id}`, `POST /api/v1/usuarios/{id}/activate`, `POST /api/v1/usuarios/{id}/deactivate`, `GET /api/v1/usuarios/verificar-admin` — **no existe módulo en backend**.

### 3.8 Validadores

- `POST /api/v1/validadores/validar-campo`, `GET /api/v1/validadores/configuracion`, `configuracion-validadores`, `ejemplos-correccion`, `formatear-tiempo-real`, `detectar-errores-masivo` — **no existe en backend**.

### 3.9 Scheduler

- `GET /api/v1/scheduler/tareas`, `POST /api/v1/scheduler/ejecutar-manual` — **no existe en backend**.

### 3.10 Reportes

- `GET /api/v1/reportes/diferencias-abonos`, `PUT .../diferencias-abonos/{prestamoId}/ajustar`, `PUT .../actualizar-valor-imagen`, `GET .../cliente/{cedula}/pendientes.pdf` — **no existe en backend**.

### 3.11 Otros servicios (baseUrl en frontend)

- `/api/v1/clientes` (CRUD + carga-masiva/clientes)  
- `/api/v1/prestamos`, `/api/v1/kpis/prestamos`  
- `/api/v1/auditoria`  
- `/api/v1/tickets`  
- `/api/v1/cobranzas`  
- `/api/v1/conversaciones-whatsapp`  
- `/api/v1/concesionarios`  
- `/api/v1/comunicaciones`  
- `/api/v1/amortizacion` (cuotaService)  
- `/api/v1/modelos-vehiculos`  
- `/api/v1/analistas`  
- `/api/v1/ai/training` (recolectar-automatico, analizar-calidad), `/api/v1/configuracion/ai/tablas-campos`  

Ninguno de estos módulos está implementado en el backend actual.

---

## 4. Matriz de cobertura (resumen)

| Módulo | Rutas backend | Rutas frontend (únicas) | Cobertura |
|--------|----------------|-------------------------|-----------|
| auth | 4 | 5 | Parcial (falta logout, change-password) |
| whatsapp | 2 | 0 (solo webhook externo) | OK |
| configuracion | 2 | 2 + ~25 AI | Parcial (solo general + logo) |
| pagos | 2 | 6+ | Parcial (solo kpis, stats) |
| notificaciones | 1 | 1 + plantillas + 4 listas | Parcial (solo resumen) |
| dashboard | 21 | 21 | Completo (stubs) |
| kpis | 1 | 1 (kpis/dashboard) | Stub |
| usuarios | 0 | ~8 | Faltante |
| validadores | 0 | ~6 | Faltante |
| scheduler | 0 | 2 | Faltante |
| reportes | 0 | 4+ | Faltante |
| clientes | 0 | múltiples | Faltante |
| prestamos | 0 | múltiples | Faltante |
| auditoria | 0 | 1+ | Faltante |
| tickets, cobranzas, conversaciones-whatsapp, concesionarios, comunicaciones, amortizacion, modelos-vehiculos, analistas, ai/training | 0 | múltiples | Faltante |

---

## 5. Recomendaciones

1. **Corto plazo (evitar 404 en pantallas ya usadas)** — **Hecho**  
   - Añadidos en backend los **7 endpoints de dashboard** como stubs: `cobranza-por-dia`, `cobranzas-mensuales`, `cobros-por-analista`, `cobros-diarios`, `cuentas-cobrar-tendencias`, `distribucion-prestamos`, `metricas-acumuladas`.  
   - Añadido stub `GET /api/v1/kpis/dashboard` en `endpoints/kpis.py` (DashboardFinanciamiento, DashboardCuotas).

2. **Auth**  
   - Implementar `POST /auth/logout` (invalidar refresh token o solo respuesta 200) y `POST /auth/change-password` (validar JWT + body con contraseña actual/nueva).

3. **Configuración**  
   - Implementar `upload-logo` y `POST /configuracion/logo` cuando se requiera subir logo.  
   - La rama `/configuracion/ai/*` es un módulo grande; priorizar por pantallas (ej. prompt, configuracion, documentos) si se usa.

4. **Pagos / Notificaciones**  
   - Cuando exista BD y lógica de negocio: CRUD pagos, list paginado; plantillas y listas de notificaciones según diseño.

5. **Resto de módulos**  
   - Planificar por fases (usuarios, validadores, scheduler, reportes, clientes, prestamos, auditoria, etc.) según prioridad de producto y recursos.

---

## 6. Referencia rápida: archivos clave

- **Backend routers:** `backend/app/api/v1/__init__.py`, `backend/app/api/v1/endpoints/*.py`.  
- **Frontend servicios:** `frontend/src/services/*.ts` (baseUrl y llamadas directas).  
- **Frontend páginas:** `frontend/src/pages/*.tsx`, `frontend/src/components/**/*.tsx` (llamadas a `/api/v1/...`).
