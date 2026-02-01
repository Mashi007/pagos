# Revisión: Conexión frontend ↔ base de datos en Dashboard

**Fecha:** 2026-02-01  
**Alcance:** Cadena Frontend → API → Base de datos para el dashboard.

---

## 1. Conclusión breve

- **Frontend → API:** La conexión es **correcta**. El frontend llama a los endpoints del dashboard mediante `apiClient` y la URL base está bien configurada (relativa en producción con proxy, o `VITE_API_URL` en desarrollo).
- **API (backend) → Base de datos:** **No hay conexión**. Los endpoints del dashboard son **stubs**: devuelven datos fijos (listas vacías, ceros) y **no usan base de datos**. El backend no tiene capa de acceso a datos implementada para el dashboard.

---

## 2. Frontend → API (conexión adecuada)

### Configuración

- **URL base:** `frontend/src/config/env.ts` define `env.API_URL`:
  - **Producción:** `API_URL = ''` → peticiones relativas (ej. `/api/v1/dashboard/...`). El servidor Node (`server.js`) hace proxy de `/api/*` al backend (ej. `https://pagos-f2qf.onrender.com`).
  - **Desarrollo:** `API_URL = import.meta.env.VITE_API_URL` o vacío; si está vacío, se usan rutas relativas y el proxy de Vite/Node.
- **Cliente HTTP:** `frontend/src/services/api.ts` crea Axios con `baseURL: env.API_URL`, interceptores para JWT (login, refresh, 401) y timeouts. Las rutas se llaman con prefijo `/api/v1/...`.

### Uso en el dashboard

- **DashboardMenu.tsx** y demás páginas/modales del dashboard usan `apiClient.get('/api/v1/dashboard/opciones-filtros')`, `apiClient.get('/api/v1/dashboard/kpis-principales')`, etc., y `apiClient.get('/api/v1/kpis/dashboard')`.
- Las URLs y métodos coinciden con los endpoints definidos en el backend. No hay llamadas directas a base de datos desde el frontend (correcto en una SPA).

**Conclusión:** La conexión del frontend con la API del dashboard es adecuada.

---

## 3. Backend (API) → Base de datos (no implementada)

### Estado actual del backend

- **`backend/app/api/v1/endpoints/dashboard.py`** y **`kpis.py`**:  
  Solo devuelven diccionarios/listas estáticas (stubs). No importan `db`, `Session`, `get_db` ni modelos. No hay consultas SQL ni ORM.
- **`backend/app/db/__init__.py`** y **`backend/app/models/__init__.py`**:  
  Están vacíos (solo docstrings). No hay sesión de BD, engine ni modelos definidos.
- **Búsqueda en el backend:** No aparece uso de `get_db`, `Session`, `session.query`, `select()` ni `from_statement` en ningún `.py`. La aplicación no usa una capa de acceso a datos para el dashboard (ni para otros módulos que dependan de BD).

### Configuración

- **`backend/app/core/config.py`** exige `DATABASE_URL` (PostgreSQL). La app está preparada para tener BD, pero ningún endpoint del dashboard la utiliza todavía.

**Conclusión:** No hay conexión del backend del dashboard con la base de datos. Los datos que ve el frontend son stubs (ceros y listas vacías).

---

## 4. Qué haría falta para una conexión adecuada con BD en el dashboard

Para que el dashboard muestre datos reales desde la base de datos:

1. **Implementar la capa de datos en el backend**
   - Crear engine y sesión (p. ej. con SQLAlchemy) en `app/db/` usando `DATABASE_URL`.
   - Definir modelos (tablas) en `app/models/` que reflejen préstamos, pagos, cobranzas, analistas, concesionarios, etc., según el diseño del negocio.
   - Exponer una dependencia `get_db()` (o similar) para inyectar la sesión en los endpoints.

2. **Conectar los endpoints del dashboard con la BD**
   - En cada endpoint de `dashboard.py` y `kpis.py` que deba devolver datos reales:
     - Recibir la sesión (p. ej. `db: Session = Depends(get_db)`).
     - Ejecutar consultas (ORM o SQL) según filtros (`fecha_inicio`, `fecha_fin`, `analista`, etc.).
     - Devolver la misma estructura de respuesta que espera el frontend (para no cambiar el frontend).

3. **Mantener el frontend como está**
   - No es necesario cambiar la conexión frontend → API; solo que el backend pase de stubs a respuestas generadas desde la BD.

---

## 5. Resumen

| Eslabón | Estado | Nota |
|--------|--------|------|
| Frontend → API (dashboard) | Adecuado | URL base, apiClient, rutas y métodos correctos. |
| API (dashboard) → Base de datos | No implementado | Endpoints son stubs; no hay sesión ni consultas a BD. |
| Conexión “frontend con base de datos” para el dashboard | Indirecta y incompleta | El frontend está bien conectado a la API; la API aún no está conectada a la BD. |

Para tener una conexión adecuada del frontend con la base de datos en el dashboard, hay que implementar en el backend la capa de acceso a datos y que los endpoints del dashboard (y kpis) lean y devuelvan datos reales desde la BD.
