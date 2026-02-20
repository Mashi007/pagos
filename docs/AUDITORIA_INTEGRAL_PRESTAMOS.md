# Auditoría integral: /pagos/prestamos

**Fecha:** 20 de febrero de 2025  
**URL:** https://rapicredit.onrender.com/pagos/prestamos  
**Alcance:** Endpoints, conexión, eficiencia de código, conexión a BD

---

## 1. Resumen ejecutivo

| Área | Estado | Observaciones |
|------|--------|---------------|
| **Endpoints** | ✅ OK | CRUD completo, stats, cuotas, auditoría, aprobación manual |
| **Conexión frontend↔backend** | ✅ OK | Proxy `/api` → `API_BASE_URL`; rutas relativas en producción |
| **Conexión BD** | ✅ OK | `Depends(get_db)` en todos los endpoints; sin stubs |
| **Eficiencia backend** | ⚠️ Mejorable | Consultas batcheadas; posibles optimizaciones |
| **Eficiencia frontend** | ⚠️ Mejorable | `staleTime: 0` genera refetch frecuente |

---

## 2. Endpoints verificados

### 2.1 Listado y CRUD

| Método | Ruta | Uso BD | Descripción |
|--------|------|--------|-------------|
| GET | `/api/v1/prestamos` | ✅ `get_db` | Listado paginado con filtros (cliente_id, estado, analista, concesionario, cedula, search, modelo, requiere_revision, fecha_inicio/fin) |
| GET | `/api/v1/prestamos/{id}` | ✅ `get_db` | Detalle de préstamo (join con Cliente) |
| POST | `/api/v1/prestamos` | ✅ `get_db` | Crear préstamo |
| PUT | `/api/v1/prestamos/{id}` | ✅ `get_db` | Actualizar préstamo |
| DELETE | `/api/v1/prestamos/{id}` | ✅ `get_db` | Eliminar préstamo (solo Admin) |

### 2.2 Estadísticas y búsqueda

| Método | Ruta | Uso BD | Descripción |
|--------|------|--------|-------------|
| GET | `/api/v1/prestamos/stats` | ✅ `get_db` | KPIs mensuales (total_financiamiento, total, cartera_vigente, por_estado) |
| GET | `/api/v1/prestamos/cedula/{cedula}` | ✅ `get_db` | Préstamos por cédula |
| GET | `/api/v1/prestamos/cedula/{cedula}/resumen` | ✅ `get_db` | Resumen (saldo, mora) por cédula |

### 2.3 Cuotas y auditoría

| Método | Ruta | Uso BD | Descripción |
|--------|------|--------|-------------|
| GET | `/api/v1/prestamos/{id}/cuotas` | ✅ `get_db` | Tabla de amortización con info de pago |
| GET | `/api/v1/prestamos/{id}/auditoria` | ✅ `get_db` | Historial de auditoría del préstamo |

### 2.4 Aprobación y riesgo

| Método | Ruta | Uso BD | Descripción |
|--------|------|--------|-------------|
| POST | `/api/v1/prestamos/{id}/evaluar-riesgo` | ✅ `get_db` | Evaluar riesgo ML/manual |
| POST | `/api/v1/prestamos/{id}/aprobar-manual` | ✅ `get_db` | Aprobación manual con condiciones |
| POST | `/api/v1/prestamos/{id}/aplicar-condiciones-aprobacion` | ✅ `get_db` | Aplicar condiciones |
| POST | `/api/v1/prestamos/{id}/asignar-fecha-aprobacion` | ✅ `get_db` | Asignar fecha y recalcular amortización |
| PATCH | `/api/v1/prestamos/{id}/marcar-revision` | ✅ `get_db` | Marcar requiere_revision |
| GET | `/api/v1/prestamos/{id}/evaluacion-riesgo` | ✅ `get_db` | Obtener evaluación de riesgo |
| POST | `/api/v1/prestamos/{id}/generar-amortizacion` | ✅ `get_db` | Generar tabla de amortización |

### 2.5 Exportación

| Método | Ruta | Uso BD | Descripción |
|--------|------|--------|-------------|
| GET | `/api/v1/prestamos/{id}/amortizacion/excel` | ✅ `get_db` | Descargar Excel |
| GET | `/api/v1/prestamos/{id}/amortizacion/pdf` | ✅ `get_db` | Descargar PDF |

**Conclusión:** Todos los endpoints de préstamos usan `Depends(get_db)` y consultan datos reales. No hay stubs ni datos demo.

---

## 3. Conexión frontend ↔ backend

### 3.1 Configuración

- **Producción:** `env.API_URL = ''` (rutas relativas).
- **Proxy:** `server.js` reenvía `/api/*` a `API_BASE_URL` (variable de entorno en Render).
- **Origen:** Las peticiones van a `https://rapicredit.onrender.com/api/v1/prestamos` (mismo origen que la SPA).

### 3.2 apiClient (frontend)

- **Timeout:** 30 s por defecto; 60 s para endpoints lentos.
- **Interceptores:** Token JWT, refresh automático, manejo de 401.
- **Base URL:** `env.API_URL` (vacío en prod → rutas relativas).

### 3.3 Servicio prestamoService

- `baseUrl = '/api/v1/prestamos'`
- Usa `apiClient.get/post/put/delete` y `buildUrl` para query params.
- Mapea correctamente `body.prestamos` y `body.total` del backend.

**Recomendación:** Verificar en Render que `API_BASE_URL` apunte al backend (ej. `https://pagos-xxx.onrender.com` si el backend está en un servicio separado, o la URL interna si comparten servicio).

---

## 4. Conexión a base de datos

### 4.1 Configuración

- **Origen:** `app/core/config.py` → `settings.DATABASE_URL`.
- **Engine:** `app/core/database.py`:
  - `pool_pre_ping=True` (verifica conexión antes de usar).
  - `pool_size=5`, `max_overflow=10`.
  - `postgres://` se reemplaza por `postgresql://` para compatibilidad.

### 4.2 Health check BD

- **Endpoint:** `GET /health/db` (en el backend FastAPI, no en Express).
- **Comportamiento:** Ejecuta `SELECT 1` contra el engine; devuelve `{"status":"healthy","database":"connected"}` o 503 si falla.
- **Nota:** En Render, si frontend y backend están en el mismo servicio, `/health/db` no está expuesto en la ruta pública. El health check de Render usa `/health` del `server.js` (Express), que no comprueba la BD. Para validar BD en producción, usar la URL directa del backend (si existe) o un endpoint interno.

### 4.3 Uso en endpoints

Todos los endpoints de `prestamos.py` declaran `db: Session = Depends(get_db)`. La sesión se cierra al finalizar el request (`yield` en `get_db`).

---

## 5. Eficiencia del código

### 5.1 Backend

**Puntos positivos:**

1. **Sin N+1 en listado:** El listado hace:
   - 1 query principal (Prestamo + Cliente con JOIN).
   - 1 query de conteo (COUNT).
   - 1 query batch para cuotas por préstamo (`Cuota.prestamo_id.in_(prestamo_ids)`).
   - 1 query batch para estados de revisión manual.
   - Total: 4 queries por request, sin bucles por fila.

2. **Paginación:** `offset` y `limit` aplicados en la query principal.

3. **Índices:** El modelo `Prestamo` tiene índices en `cliente_id`, `estado`, `concesionario`, `modelo_vehiculo`.

**Posibles mejoras:**

1. **Count en tablas grandes:** El `count_q` recorre toda la tabla filtrada. Para tablas muy grandes, considerar estimación o cache del total.
2. **Stats:** `get_prestamos_stats` ejecuta varias consultas (total, por_estado, total_fin, cartera_vigente). Podrían unificarse en una sola con subconsultas si el rendimiento lo requiere.

### 5.2 Frontend

**Puntos positivos:**

1. **React Query:** Cache por `queryKey` (filtros, página, perPage).
2. **Queries paralelas:** `PrestamosList` carga en paralelo: préstamos, concesionarios, analistas, modelos.
3. **Invalidación:** Tras crear/actualizar/eliminar se invalidan `prestamos`, `revision-manual`, `kpis`, `dashboard`.

**Posibles mejoras:**

1. **staleTime en usePrestamos:** Actualmente `staleTime: 0` implica refetch en cada mount y `refetchOnWindowFocus`. Para listados que no cambian tan a menudo, aumentar a 1–2 minutos reduce peticiones.
2. **Cache en server.js:** Los endpoints `/api/v1/concesionarios`, `/api/v1/analistas`, `/api/v1/modelos-vehiculos` ya tienen `Cache-Control: max-age=300` en el proxy. Los préstamos usan `no-cache` (correcto para datos dinámicos).

---

## 6. Checklist de verificación

| Verificación | Estado |
|--------------|--------|
| Endpoints usan `Depends(get_db)` | ✅ |
| No hay stubs ni datos demo | ✅ |
| Paginación en listado | ✅ |
| Filtros aplicados en backend | ✅ |
| JOIN con Cliente para nombres/cedula | ✅ |
| Conteo de cuotas por batch (no N+1) | ✅ |
| Frontend usa apiClient con rutas relativas | ✅ |
| Proxy /api configurado en server.js | ✅ |
| DATABASE_URL desde .env/config | ✅ |
| pool_pre_ping en engine | ✅ |

---

## 7. Recomendaciones prioritarias

1. **Validar API_BASE_URL en Render:** Confirmar que el proxy apunta al backend correcto.
2. **Ajustar staleTime en usePrestamos:** Probar `staleTime: 60_000` (1 min) para reducir refetches sin perder frescura.
3. **Health BD en producción:** Si se necesita monitorear la BD, exponer `/health/db` en una ruta que Render pueda consultar (por ejemplo, en el mismo servicio que el backend o vía proxy).
4. **Mantener documentación:** Actualizar `ENDPOINTS_COMPLETO.md` o similar si se añaden nuevos endpoints de préstamos.

---

## 8. Archivos revisados

| Archivo | Propósito |
|---------|-----------|
| `backend/app/api/v1/endpoints/prestamos.py` | Endpoints de préstamos |
| `backend/app/core/database.py` | Conexión y sesión BD |
| `backend/app/core/config.py` | Configuración (DATABASE_URL) |
| `backend/app/models/prestamo.py` | Modelo Prestamo |
| `backend/app/schemas/prestamo.py` | Schemas Pydantic |
| `frontend/src/services/prestamoService.ts` | Servicio API préstamos |
| `frontend/src/services/api.ts` | apiClient, interceptores |
| `frontend/src/hooks/usePrestamos.ts` | Hooks React Query |
| `frontend/src/components/prestamos/PrestamosList.tsx` | Listado y filtros |
| `frontend/server.js` | Proxy /api, health, estáticos |
| `frontend/src/config/env.ts` | API_URL, BASE_PATH |
