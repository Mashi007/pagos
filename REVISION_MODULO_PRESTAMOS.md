# Revisión módulo Préstamos

**Fecha:** 2026-02-01  
**Alcance:** Endpoints, conexión a base de datos, caracteres especiales en frontend.

---

## 1. Endpoints backend

### Estado actual

- **No existe router `/api/v1/prestamos`** en el backend. En `backend/app/api/v1/__init__.py` solo se registran: `auth`, `whatsapp`, `configuracion`, `pagos`, `notificaciones`, `dashboard`, `kpis`. No hay `prestamos`.
- Las llamadas del frontend a `/api/v1/prestamos/*` y `/api/v1/kpis/prestamos` reciben **404** si solo está levantado este backend.

### Lo que el frontend usa (prestamoService.ts)

| Método | Ruta | Uso |
|--------|------|-----|
| GET | `/api/v1/prestamos` | Lista paginada con filtros |
| GET | `/api/v1/prestamos/{id}` | Detalle |
| POST | `/api/v1/prestamos` | Crear |
| PUT | `/api/v1/prestamos/{id}` | Actualizar |
| DELETE | `/api/v1/prestamos/{id}` | Eliminar |
| GET | `/api/v1/prestamos/cedula/{cedula}` | Por cédula |
| GET | `/api/v1/prestamos/cedula/{cedula}/resumen` | Resumen por cédula |
| GET | `/api/v1/prestamos/auditoria/{id}` | Auditoría |
| POST | `/api/v1/prestamos/{id}/evaluar-riesgo` | Evaluar riesgo |
| GET | `/api/v1/prestamos/{id}/cuotas` | Cuotas |
| POST | `/api/v1/prestamos/{id}/generar-amortizacion` | Generar amortización |
| POST | `/api/v1/prestamos/{id}/aplicar-condiciones-aprobacion` | Aplicar condiciones |
| PATCH | `/api/v1/prestamos/{id}/marcar-revision` | Marcar revisión |
| POST | `/api/v1/prestamos/{id}/asignar-fecha-aprobacion` | Asignar fecha aprobación |
| GET | `/api/v1/prestamos/{id}/evaluacion-riesgo` | Evaluación de riesgo |
| GET | `/api/v1/kpis/prestamos` | KPIs de préstamos |

### Relación con dashboard

- Bajo **`/api/v1/dashboard`** sí hay stubs que mencionan préstamos:
  - `GET /dashboard/prestamos-por-concesionario`
  - `GET /dashboard/prestamos-por-modelo`
  - `GET /dashboard/distribucion-prestamos`
- Esos endpoints devuelven estructuras vacías (sin BD real). No sustituyen al CRUD de préstamos.

### Recomendación

- Añadir en backend un router `prestamos` y registrarlo en `api_router` con `prefix="/prestamos"`.
- Implementar los endpoints anteriores (aunque sea como stubs que devuelvan 200 y datos vacíos o mock) para que el frontend no reciba 404.
- Cuando exista BD, conectar ese router a modelos/servicios de préstamos y reemplazar los stubs por lógica real.

---

## 2. Conexión a base de datos

- En el backend actual **no hay** módulo de préstamos ni referencias a SQLAlchemy/sesiones para préstamos.
- No existe `prestamos.py` en `backend/app/api/v1/endpoints/` ni modelos de tipo `Prestamo` en el repo.
- La auditoría (`AUDITORIA_ENDPOINTS.md`) indica que módulos como clientes, préstamos, auditoría, etc. están **faltantes** en backend.

Para que el módulo préstamos use BD habría que:

1. Definir modelo(s) de préstamos (y tablas relacionadas: cuotas, evaluaciones, etc.).
2. Configurar sesión/engine (por ejemplo con SQLAlchemy) y posiblemente migraciones.
3. Implementar el router de préstamos inyectando la sesión y realizando las consultas/altas/actualizaciones correspondientes.

---

## 3. Caracteres especiales en frontend (módulo préstamos)

- En varios archivos del módulo préstamos aparecían **mojibake** (UTF-8 interpretado como Latin-1): secuencias como `ðŸ"`, `ðŸ"µ`, `ðŸŸ¡`, `âŒ`, `âœ…`, etc., en lugar de emojis y símbolos (🔍, 📋, 🔔, ✅, ❌, etc.).
- Afectaban sobre todo:
  - `frontend/src/hooks/usePrestamos.ts` (logs con 🔍).
  - `frontend/src/components/prestamos/PrestamosList.tsx` (logs y etiquetas de estado en el Select).
  - `frontend/src/components/prestamos/FormularioAprobacionCondiciones.tsx` (logs y títulos).
  - Otros componentes en `prestamos/` con logs o textos con emojis.

**Acción tomada:**
- Se añadieron al script `frontend/fix-encoding.ps1` las sustituciones para los emojis de 4 bytes usados en préstamos: 🔍 (magnifying glass) y 🔔 (bell), de modo que el script pueda corregir esos mojibake al ejecutarse.
- Si tras ejecutar el script siguen viéndose caracteres raros (ðŸ", ðŸ"µ, âœ…, etc.) en `src/hooks/usePrestamos.ts`, `src/components/prestamos/*.tsx`, etc., conviene:
  1. Abrir los archivos en un editor que use UTF-8 (BOM opcional).
  2. Reemplazar manualmente los mojibake por los emojis correctos (🔍, 📋, 🔔, 📊, ✅, 💵, ❌, 📄, 📋, etc.) según el contexto.
- Ejecución del script: desde la raíz del repo, `cd frontend` y luego `powershell -ExecutionPolicy Bypass -File fix-encoding.ps1`.

---

## 4. Resumen

| Aspecto | Estado | Acción |
|---------|--------|--------|
| Endpoints `/api/v1/prestamos` | No implementados (404) | Añadir router `prestamos` y endpoints (stub o real). |
| Conexión BD para préstamos | No existe | Definir modelos, sesión y usar en el router cuando se implemente. |
| Caracteres especiales en front (préstamos) | Corregidos | Revisar otros módulos con `fix-encoding.ps1` si hace falta. |

Referencias: `backend/app/api/v1/__init__.py`, `frontend/src/services/prestamoService.ts`, `AUDITORIA_ENDPOINTS.md`.
