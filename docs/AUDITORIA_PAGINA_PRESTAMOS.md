# Auditoría integral: /pagos/prestamos

**URL auditada:** https://rapicredit.onrender.com/pagos/prestamos  
**Alcance:** Backend (FastAPI), frontend (React/TypeScript), seguridad, datos reales BD, UX y consistencia API.  
**Fecha:** 2025-02-05.

---

## 1. Resumen ejecutivo

La página **Préstamos** está protegida por autenticación, usa datos reales desde la BD en los endpoints principales (listado, CRUD, stats, por cédula) y el flujo de listado + crear/editar/eliminar préstamo funciona. Se detectan **desalineaciones importantes** entre frontend y backend: varios servicios del frontend llaman a endpoints que **no existen** en el backend (cuotas, evaluación de riesgo, aprobación con condiciones, asignar fecha aprobación, auditoría por préstamo, etc.), filtros de búsqueda (cédula, fechas, requiere_revision) no implementados en el listado, y mejoras recomendables en seguridad, UX y código (logs en producción, encoding, borrado en cascada).

---

## 2. Arquitectura y flujo

| Capa | Detalle |
|------|--------|
| **Ruta frontend** | `path="prestamos"` en `App.tsx`; con `basename="/pagos"` la URL final es `/pagos/prestamos`. |
| **Protección** | `SimpleProtectedRoute`: exige usuario autenticado; no exige rol admin para ver préstamos. |
| **Backend** | Router en `app/api/v1/endpoints/prestamos.py` montado en `/api/v1/prestamos`; todos los endpoints usan `Depends(get_current_user)` y `Depends(get_db)`. |
| **Producción** | Front en Render; `server.js` hace proxy de `/api/*` a `API_BASE_URL`; en producción `API_URL` en front es `''` (rutas relativas). |

---

## 3. Backend (FastAPI)

### 3.1 Cumplimiento regla “datos reales”

- **Cumple:** Listado, stats, por cédula, resumen por cédula, GET/POST/PUT/DELETE por ID usan `get_db` y consultas a tablas `prestamos`, `clientes`, `cuotas`. No hay stubs ni datos demo en estos endpoints.

### 3.2 Endpoints existentes

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/` o `` | Listado paginado (page, per_page, cliente_id, estado, analista, concesionario) |
| GET | `/stats` | Total y conteo por estado |
| GET | `/cedula/{cedula}` | Préstamos del cliente por cédula |
| GET | `/cedula/{cedula}/resumen` | Resumen saldo/mora por cédula |
| GET | `/{prestamo_id}` | Detalle de un préstamo |
| POST | `` | Crear préstamo (valida cliente_id) |
| PUT | `/{prestamo_id}` | Actualizar préstamo |
| DELETE | `/{prestamo_id}` | Eliminar préstamo |

### 3.3 Filtros del listado

El listado **solo** acepta:

- `page`, `per_page`
- `cliente_id`, `estado`, `analista`, `concesionario`

**No** acepta: `cedula`, `search`, `fecha_inicio`, `fecha_fin`, `requiere_revision`. El frontend envía estos parámetros pero el backend los ignora.

### 3.4 Endpoints que el frontend usa y no existen

El `prestamoService` y los hooks llaman a:

| Llamada frontend | Ruta API | Estado backend |
|------------------|----------|----------------|
| `getAuditoria(prestamoId)` | GET `/api/v1/prestamos/auditoria/{id}` | No existe (auditoría está en `/api/v1/auditoria` con filtros, no por préstamo) |
| `getCuotasPrestamo(prestamoId)` | GET `/api/v1/prestamos/{id}/cuotas` | No existe |
| `generarAmortizacion(prestamoId)` | POST `/api/v1/prestamos/{id}/generar-amortizacion` | No existe |
| `aplicarCondicionesAprobacion(prestamoId, condiciones)` | POST `/api/v1/prestamos/{id}/aplicar-condiciones-aprobacion` | No existe |
| `evaluarRiesgo(prestamoId, datos)` | POST `/api/v1/prestamos/{id}/evaluar-riesgo` | No existe |
| `marcarRevision(prestamoId, requiereRevision)` | PATCH `/api/v1/prestamos/{id}/marcar-revision` | No existe |
| `asignarFechaAprobacion(prestamoId, fecha)` | POST `/api/v1/prestamos/{id}/asignar-fecha-aprobacion` | No existe |
| `getEvaluacionRiesgo(prestamoId)` | GET `/api/v1/prestamos/{id}/evaluacion-riesgo` | No existe |
| `searchPrestamos(query)` | GET `/api/v1/prestamos?search=...` | Backend no tiene param `search` |

Al usar “Evaluar riesgo”, “Aprobar crédito”, “Asignar fecha aprobación”, “Ver auditoría” del préstamo, etc., las peticiones devolverán **404** o error.

### 3.5 Seguridad y consistencia

- **Autenticación:** Todos los endpoints de préstamos exigen `get_current_user` (Bearer). Correcto.
- **Autorización:** No hay control por rol en el backend para préstamos (no se distingue admin vs operativo en los endpoints). El frontend oculta acciones según `usePermissions()` (ej. eliminar, evaluar riesgo solo admin).
- **Validación:** Crear préstamo valida que `cliente_id` exista y rellena cedula/nombres desde `Cliente`. Actualizar valida `cliente_id` si se envía.
- **Eliminación:** `delete_prestamo` hace `db.delete(row)` sin borrar antes cuotas. Si la FK `cuotas.prestamo_id` no tiene `ON DELETE CASCADE`, puede fallar por restricción o dejar cuotas huérfanas. Recomendación: comprobar FK en BD y, si no hay CASCADE, borrar cuotas antes o rechazar borrado si existen cuotas.

### 3.6 Modelo y schemas

- Modelo `Prestamo` alineado con tabla `prestamos` (incluye campos ML, requiere_revision, etc.).
- `PrestamoCreate` / `PrestamoUpdate` / `PrestamoResponse` / `PrestamoListResponse` coherentes con el modelo. En listado se hace join con `Cliente` para nombres y cédula; número de cuotas se obtiene de la tabla `cuotas` cuando hay registros.

---

## 4. Frontend (React / TypeScript)

### 4.1 Página y componentes

- **`Prestamos.tsx`:** Envuelve la vista con título, card “Novedades” y `PrestamosList`.
- **`PrestamosList`:** Listado con KPIs (`PrestamosKPIs`), filtros (búsqueda, cédula, estado, fechas, analista, concesionario, modelo), tabla paginada, acciones (ver, editar, evaluar riesgo, aprobar, asignar fecha aprobación, eliminar) según permisos y estado.
- Formularios/modos: `CrearPrestamoForm`, `EvaluacionRiesgoForm`, `PrestamoDetalleModal`, `FormularioAprobacionCondiciones`, `AsignarFechaAprobacionModal`.

### 4.2 Datos y API

- Listado: `usePrestamos(filters, page)` → `prestamoService.getPrestamos()`. El servicio adapta la respuesta del backend (`prestamos`, `total`, `page`, `per_page`, `total_pages`) a `{ data, total, page, per_page, total_pages }`. Correcto para el contrato actual del listado.
- Filtros: Se envían `search`, `cedula`, `estado`, `analista`, `concesionario`, `modelo`, `fecha_inicio`, `fecha_fin`, `requiere_revision`. Solo estado, analista y concesionario tienen efecto en backend; el resto no filtra.
- Búsqueda por cédula: El placeholder dice “Buscar por cédula…” pero el listado usa el mismo endpoint sin param `cedula` en backend; para filtrar por cédula habría que añadir el param en backend o resolver `cliente_id` desde cédula y usar `cliente_id`.

### 4.3 UX y robustez

- Estados de carga y error en la tabla; mensaje cuando `total > 0` pero `data` vacío (posible inconsistencia de formato).
- Bloque de debug en desarrollo (data, isLoading, error) y `<details>` con JSON; recomendable no dejar logs sensibles en producción.
- `handleRefresh` invalida y re-fetch de queries de préstamos; correcto.
- Eliminación con `window.confirm`; funcional pero se podría sustituir por un modal de confirmación más accesible.

### 4.4 Inconsistencias y mejoras

- **Toasts:** `usePrestamos` usa `toast` de `react-hot-toast`; `PrestamosList` y `CrearPrestamoForm` usan `sonner`. Conviene unificar una sola librería.
- **Logs en producción:** `prestamoService.getPrestamosByCedula` y `usePrestamos` tienen `console.log`; en producción es mejor usar el logger condicionado por entorno o eliminarlos.
- **Encoding:** En `PrestamosList.tsx` hay caracteres corruptos (ej. “ðŸ"”, “âš ï¸”) donde deberían ir emojis (🔍, ⚠️). Recomendación: guardar el archivo en UTF-8 y reemplazar por texto o emojis correctos.
- **Filtro requiere_revision:** Se lee de `searchParams` y se pone en `filters`, pero el backend no filtra por ello; la intención de “préstamos que requieren revisión” no se aplica en el listado.

---

## 5. Seguridad (resumen)

| Aspecto | Estado |
|---------|--------|
| Autenticación en API | Correcta (Bearer, decode_token, usuario desde BD o admin env) |
| Protección de ruta /prestamos | Correcta (SimpleProtectedRoute) |
| Roles en backend para préstamos | No diferenciados (el front limita acciones por rol) |
| Eliminación de préstamo con cuotas | Riesgo de error o huérfanos si no hay CASCADE |
| Headers de seguridad (server.js) | CSP, X-Frame-Options, etc. configurados |

---

## 6. Recomendaciones prioritarias

### Alta prioridad

1. **Implementar o alinear endpoints usados por la UI:**  
   Añadir en el backend (o en otro router) los endpoints que el frontend ya usa: cuotas por préstamo, generar amortización, aplicar condiciones de aprobación, evaluar riesgo, marcar revisión, asignar fecha de aprobación, evaluación de riesgo. O bien desactivar/ocultar en la UI las acciones que dependen de ellos hasta que existan.

2. **Filtros de listado:**  
   En `listar_prestamos` soportar al menos:
   - `cedula` (filtrar por cédula del cliente, vía join con `clientes`).
   - Opcional: `fecha_inicio` / `fecha_fin` sobre `fecha_registro` o `fecha_creacion`.
   - Opcional: `requiere_revision` si se quiere el filtro “requiere revisión”.

3. **Eliminación de préstamos:**  
   Verificar en BD si `cuotas.prestamo_id` tiene `ON DELETE CASCADE`. Si no, o borrar cuotas antes de borrar el préstamo en el endpoint, o rechazar el delete cuando existan cuotas y documentar el comportamiento.

### Media prioridad

4. **Unificar toasts** en una sola librería (p. ej. sonner) en toda la app.
5. **Quitar o condicionar** `console.log` en servicios y hooks de préstamos para producción.
6. **Corregir encoding** en `PrestamosList.tsx` (UTF-8 y reemplazo de caracteres corruptos).
7. **Auditoría por préstamo:** Si se quiere “auditoría de un préstamo”, añadir en backend algo como `GET /auditoria?prestamo_id={id}` o `GET /prestamos/{id}/auditoria` y que el servicio de préstamos llame a esa ruta.

### Baja prioridad

8. **Búsqueda general:** Si se mantiene “Buscar por cédula”, implementar param `cedula` (o `search` por cédula) en el listado; si se quiere búsqueda por más campos, definir contrato y añadirlo en backend y frontend.
9. **Confirmación de eliminación:** Sustituir `window.confirm` por un modal accesible.
10. **KPIs de préstamos:** `getKPIs` en frontend devuelve solo `totalPrestamos` desde `/prestamos/stats`; los demás (totalFinanciamiento, promedioMonto, totalCarteraVigente) están en 0. Si el dashboard o la página los necesitan, ampliar `/prestamos/stats` o un endpoint específico de KPIs con datos reales.

---

## 7. Verificación rápida en entorno

- **Listado:** `GET /api/v1/prestamos?page=1&per_page=20` (con Bearer).
- **Filtros:** Probar `estado`, `analista`, `concesionario`; comprobar que `cedula`/`fecha_inicio`/`fecha_fin` no cambian el resultado hasta que se implementen.
- **Crear:** POST con `cliente_id`, `total_financiamiento`, etc.; comprobar 201 y que el préstamo aparece en el listado.
- **Eliminar:** Borrar un préstamo sin cuotas; si tiene cuotas, comprobar el comportamiento actual (error o CASCADE).

---

## 8. Conclusión

La página **/pagos/prestamos** cumple la regla de datos reales en los flujos principales (listado, CRUD, stats, resumen por cédula) y está protegida por autenticación. La auditoría muestra **desajustes claros** entre la UI (evaluación de riesgo, aprobación con condiciones, cuotas, auditoría por préstamo, filtros por cédula/fechas) y la API actual. Priorizar la implementación o alineación de los endpoints que la UI ya utiliza y la ampliación de filtros en el listado mejorará de forma directa la funcionalidad y la experiencia en https://rapicredit.onrender.com/pagos/prestamos.
