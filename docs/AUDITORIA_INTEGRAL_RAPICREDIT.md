# Auditoría Integral - RapiCredit /pagos/clientes

**Fecha:** 18 de febrero de 2025  
**URL objetivo:** https://rapicredit.onrender.com/pagos/clientes  
**Alcance:** Conexión BD, coherencia backend-frontend, calidad de endpoints, flujo completo.

---

## 1. Resumen Ejecutivo

| Área | Estado | Observaciones |
|------|--------|---------------|
| **Conexión BD** | ✅ OK | `get_db`, `pool_pre_ping`, health `/health/db` |
| **Backend clientes** | ✅ OK | CRUD real, Depends(get_db), sin stubs |
| **Frontend clientes** | ⚠️ Parcial | Funcional pero con endpoints inexistentes |
| **Coherencia API** | ❌ Inconsistencias | Filtros, endpoints legacy sin backend |
| **Calidad endpoints** | ⚠️ Mejorable | Filtros avanzados no implementados |

---

## 2. Conexión a Base de Datos

### 2.1 Configuración

- **Origen:** `DATABASE_URL` en `.env` o variables de entorno (Render).
- **Archivo:** `backend/app/core/config.py` → `Settings.DATABASE_URL`.
- **Driver:** PostgreSQL; se normaliza `postgres://` → `postgresql://` en `database.py`.

### 2.2 Engine y sesión

```python
# backend/app/core/database.py
engine = create_engine(_db_url, pool_pre_ping=True, pool_size=5, max_overflow=10)
SessionLocal = sessionmaker(..., expire_on_commit=False)
```

- `pool_pre_ping=True`: verifica conexión antes de usar.
- `expire_on_commit=False`: evita errores F405 en serialización.

### 2.3 Health check BD

| Endpoint | Método | Auth | Descripción |
|----------|--------|------|--------------|
| `/health` | GET | No | Estado básico |
| `/health/db` | GET | No | `SELECT 1` contra BD; 503 si falla |

**Recomendación:** Usar `GET /health/db` para validar conexión en Render o monitoreo.

---

## 3. Backend - Endpoints de Clientes

### 3.1 Rutas disponibles

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/api/v1/clientes` | Listado paginado (search, estado) |
| GET | `/api/v1/clientes/stats` | Estadísticas (total, activos, inactivos, finalizados) |
| GET | `/api/v1/clientes/casos-a-revisar` | Clientes con placeholders (Z999999999, etc.) |
| GET | `/api/v1/clientes/{id}` | Cliente por ID |
| POST | `/api/v1/clientes` | Crear cliente |
| PUT | `/api/v1/clientes/{id}` | Actualizar cliente |
| PATCH | `/api/v1/clientes/{id}/estado` | Cambiar estado |
| DELETE | `/api/v1/clientes/{id}` | Eliminar cliente |
| POST | `/api/v1/clientes/check-cedulas` | Verificar cédulas existentes |
| POST | `/api/v1/clientes/actualizar-lote` | Actualización en lote |

### 3.2 Filtros soportados (GET /clientes)

| Parámetro | Tipo | Descripción |
|-----------|------|-------------|
| `page` | int | Página (default 1) |
| `per_page` | int | Por página (1-100, default 20) |
| `search` | string | Búsqueda en cédula, nombres, email, teléfono |
| `estado` | string | ACTIVO, INACTIVO, MORA, FINALIZADO |

### 3.3 Calidad del backend

- ✅ Uso de `Depends(get_db)` en todos los endpoints.
- ✅ Datos reales desde tabla `clientes`.
- ✅ Validación de duplicados (cédula, nombres, email).
- ✅ Manejo de errores (ProgrammingError, OperationalError).
- ⚠️ No soporta filtros: `cedula`, `email`, `telefono`, `ocupacion`, `usuario_registro`, `fecha_desde`, `fecha_hasta` (el frontend los envía pero se ignoran).

---

## 4. Frontend - Servicio de Clientes

### 4.1 Endpoints que SÍ existen en backend

| Método frontend | Endpoint backend | Estado |
|-----------------|-----------------|--------|
| `getClientes` | GET /clientes | ✅ |
| `getCliente` | GET /clientes/{id} | ✅ |
| `createCliente` | POST /clientes | ✅ |
| `updateCliente` | PUT /clientes/{id} | ✅ |
| `deleteCliente` | DELETE /clientes/{id} | ✅ |
| `getStats` | GET /clientes/stats | ✅ |
| `cambiarEstado` | PATCH /clientes/{id}/estado | ✅ |
| `checkCedulas` | POST /clientes/check-cedulas | ✅ |
| `getCasosARevisar` | GET /clientes/casos-a-revisar | ✅ |
| `actualizarClientesLote` | POST /clientes/actualizar-lote | ✅ |

### 4.2 Endpoints que NO existen en backend

| Método frontend | Endpoint llamado | Impacto |
|-----------------|------------------|---------|
| `getClientesEnMora` | GET /clientes?estado_financiero=MORA | ❌ Backend usa `estado`, no `estado_financiero` |
| `getEstadisticasEmbudo` | GET /clientes/embudo/estadisticas | ❌ 404 |
| `getClientesConProblemasValidacion` | GET /clientes/con-problemas-validacion | ❌ 404 (existe `/casos-a-revisar`) |
| `exportarValoresPorDefecto` | GET /clientes/valores-por-defecto/exportar | ❌ 404 |
| `getHistorialPagos` | GET /clientes/{id}/pagos | ❌ 404 |
| `getTablaAmortizacion` | GET /clientes/{id}/amortizacion | ❌ 404 |
| `validateCedula` | POST /clientes/validate-cedula | ❌ 404 |
| `getEstadisticasCliente` | GET /clientes/{id}/estadisticas | ❌ 404 |
| `importarClientes` | POST /api/v1/carga-masiva/clientes | ❌ 404 (no existe router carga-masiva) |

---

## 5. Inconsistencias Críticas

### 5.1 Filtros frontend vs backend

El frontend (`ClientesList.tsx`) ofrece filtros que el backend no usa:

- `cedula`, `email`, `telefono`, `ocupacion`, `usuario_registro`, `fecha_desde`, `fecha_hasta`

El backend solo usa `search` (búsqueda global) y `estado`. Los demás parámetros se envían pero se ignoran.

### 5.2 `estado_financiero` vs `estado`

- Frontend: `ClienteFilters.estado_financiero` (usado en `getClientesEnMora`).
- Backend: solo `estado` (ACTIVO, INACTIVO, MORA, FINALIZADO).

**Corrección:** Usar `estado: 'MORA'` en lugar de `estado_financiero: 'MORA'`.

### 5.3 `deleteCliente` – tipo de ID

- `clienteService.deleteCliente(id: string)` recibe string.
- `ClientesList.tsx` pasa `clienteSeleccionado.id` (number). Funciona por coerción en la URL, pero conviene usar `String(clienteSeleccionado.id)` para consistencia.

---

## 6. Arquitectura de Despliegue

### 6.1 Render

- **Frontend:** `rapicredit-frontend` (o `pagos-frontend`) – Node/Express, base `/pagos`.
- **Backend:** `pagos-backend` – FastAPI/Gunicorn.
- **Proxy:** Express hace proxy de `/api/*` hacia `API_BASE_URL` (backend).

### 6.2 Variables de entorno

| Variable | Uso |
|----------|-----|
| `API_BASE_URL` | URL del backend para proxy (runtime) |
| `VITE_API_URL` | URL API (build-time, frontend) |
| `DATABASE_URL` | Conexión PostgreSQL (backend) |
| `SECRET_KEY` | JWT (backend) |

En producción, el frontend usa `API_URL = ''` (rutas relativas) y el proxy reenvía `/api/*` al backend.

---

## 7. Recomendaciones

### 7.1 Prioridad alta

1. **Alinear `getClientesEnMora`:** Usar `estado: 'MORA'` en lugar de `estado_financiero`.
2. **Eliminar o adaptar endpoints inexistentes:**  
   - `getEstadisticasEmbudo`: implementar en backend o eliminar del frontend.  
   - `getClientesConProblemasValidacion`: redirigir a `getCasosARevisar`.  
   - `exportarValoresPorDefecto`: implementar o quitar.  
   - `getHistorialPagos`, `getTablaAmortizacion`, `validateCedula`, `getEstadisticasCliente`: implementar o eliminar llamadas.
3. **Carga masiva:** Crear endpoint `POST /api/v1/carga-masiva/clientes` o deshabilitar `importarClientes` en el frontend.

### 7.2 Prioridad media

4. **Filtros avanzados:** Implementar en backend `cedula`, `email`, `telefono`, `ocupacion`, `usuario_registro`, `fecha_desde`, `fecha_hasta` o simplificar la UI para usar solo `search` y `estado`.
5. **Quitar logs de depuración:** Eliminar `console.log` en `clienteService.ts` y `ClientesList.tsx` en producción.
6. **Mock data:** Eliminar `mockClientes` en `ClientesList.tsx` (ya no se usa con datos reales).

### 7.3 Prioridad baja

7. **Health check:** Configurar Render para usar `GET /health/db` si se quiere validar BD en el health check.
8. **CORS:** Verificar que `https://rapicredit.onrender.com` esté en `CORS_ORIGINS`.

---

## 8. Checklist de Verificación

- [ ] `GET /health/db` responde 200 con `"database": "connected"`.
- [ ] `GET /api/v1/clientes` devuelve datos reales (requiere auth).
- [ ] La página `/pagos/clientes` carga sin errores 404 en consola.
- [ ] Crear, editar y eliminar cliente funcionan correctamente.
- [ ] Filtro por estado (ACTIVO, INACTIVO, etc.) funciona.
- [ ] Búsqueda por texto (search) funciona.
- [ ] KPIs de clientes (total, activos, inactivos, finalizados) se actualizan.

---

## 9. Referencias

- `backend/app/core/database.py` – Conexión BD.
- `backend/app/core/config.py` – Configuración.
- `backend/app/api/v1/endpoints/clientes.py` – Endpoints clientes.
- `frontend/src/services/clienteService.ts` – Servicio frontend.
- `frontend/src/hooks/useClientes.ts` – Hooks React Query.
- `frontend/src/components/clientes/ClientesList.tsx` – Listado UI.
- Regla de workspace: `.cursor/rules/datos-reales-bd.mdc`.
