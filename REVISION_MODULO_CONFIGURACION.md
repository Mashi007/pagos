# Revisión del Módulo Configuración

## 1. Endpoints y conexión a base de datos

### Backend (`backend/app/api/v1/endpoints/configuracion.py`)

| Método | Ruta | Estado | Descripción |
|--------|------|--------|-------------|
| GET | `/api/v1/configuracion/general` | ✅ Implementado | Configuración general (nombre_empresa, logo_filename, zona_horaria, idioma, moneda, etc.). Respuesta alineada con `ConfiguracionGeneral` del frontend. |
| PUT | `/api/v1/configuracion/general` | ✅ Implementado | Actualizar configuración general (stub en memoria hasta tener BD). Acepta `ConfiguracionGeneralUpdate`. |
| GET | `/api/v1/configuracion/logo/{filename}` | ✅ Implementado | Sirve el logo por nombre; filename saneado (evita path traversal). Requiere `LOGO_UPLOAD_DIR` para servir archivos. |
| POST | `/api/v1/configuracion/upload-logo` | ✅ Implementado | Subir logo (multipart, campo `logo`). Guarda en `LOGO_UPLOAD_DIR` si está configurado; devuelve `{ filename, url }`. |
| DELETE | `/api/v1/configuracion/logo` | ✅ Implementado | Eliminar logo actual; limpia `logo_filename` y borra archivo si existe. |

**Conexión a BD:** El módulo no usa base de datos aún. `config.py` define `DATABASE_URL` (obligatorio). Los endpoints usan un stub en memoria (`_config_stub`). Cuando exista BD, se debe:
- Inyectar `get_db` en los endpoints.
- Leer/escribir configuración general y `logo_filename` en tabla de configuración.

**Variables de entorno recomendadas:**
- `LOGO_UPLOAD_DIR`: ruta a carpeta donde guardar/servir logos (opcional).
- `API_BASE_URL`: base URL para construir la `url` en la respuesta de `upload-logo` (opcional).

---

## 2. Caracteres especiales en el frontend

- **Corregido en `Configuracion.tsx`:** "Último Backup" (antes "Ãšltimo"), "✅ Configurada" / "❌ No configurada" (emojis en Badge), y varios comentarios/logs con ✅.
- **Pendiente (opcional):** Algunos textos con emojis corruptos en "Formatos soportados" y "Tamaño máximo" pueden corregirse ejecutando `frontend/fix-encoding.ps1` o editando manualmente a 📋 y 📏.
- Asegurar que los archivos del frontend estén guardados en **UTF-8** para evitar nuevo mojibake.

---

## 3. Articulación con otros módulos

### Frontend → Backend (Configuración general y logo)

| Origen | Llama a | Estado |
|--------|---------|--------|
| `Configuracion.tsx` | `configuracionGeneralService.obtenerConfiguracionGeneral()` → GET `/configuracion/general` | ✅ |
| `Configuracion.tsx` | `configuracionGeneralService.actualizarConfiguracionGeneral()` → PUT `/configuracion/general` | ✅ |
| `Configuracion.tsx` | `fetch(…/upload-logo)` → POST `/configuracion/upload-logo` | ✅ |
| `Configuracion.tsx` | `fetch(…/logo)` → DELETE `/configuracion/logo` | ✅ |
| `Configuracion.tsx` / `Logo.tsx` | GET `/configuracion/logo/{filename}` | ✅ |

### Otros componentes que usan configuración

| Componente / Servicio | Endpoints que usa | Estado en backend |
|----------------------|--------------------|--------------------|
| `Logo.tsx` | GET `/configuracion/general`, GET `/configuracion/logo/{filename}` | ✅ Implementados |
| `ValidadoresConfig.tsx` | GET `/api/v1/validadores/configuracion-validadores`, POST `/configuracion/validadores/probar` | ❌ No implementados (router validadores no existe) |
| `AIConfig.tsx`, `ChatAI.tsx`, `RAGTab.tsx`, etc. | Toda la rama `/configuracion/ai/*` (configuracion, chat, documentos, prompt, etc.) | ❌ No implementados (ver `REVISION_MODULO_CHAT_AI.md`) |
| `configuracionService.ts` | `/validadores/configuracion-validadores`, `/configuracion/validadores/probar`, `/configuracion/sistema/completa`, `/configuracion/sistema/categoria/:categoria` | ❌ No implementados |

### Resumen de articulación

- **General + logo:** Completamente articulado: frontend y backend coinciden en rutas y formato (nombre_empresa, logo_filename, PUT general, upload-logo, DELETE logo).
- **Validadores:** El frontend llama a rutas que no existen en el backend; las pantallas de validadores fallarán hasta implementar un router de validadores o exponer esos endpoints bajo `/configuracion`.
- **AI (prompt, documentos, chat, calificaciones):** Sin implementar en backend; ver `REVISION_MODULO_CHAT_AI.md` y `AUDITORIA_ENDPOINTS.md`.

---

## 4. Cambios realizados en esta revisión

1. **Backend**
   - GET `/general`: respuesta con `nombre_empresa` (y resto de campos de `ConfiguracionGeneral`) en lugar de solo `nombre_app`.
   - Nuevo PUT `/general` con body Pydantic `ConfiguracionGeneralUpdate`.
   - Nuevo POST `/upload-logo` y DELETE `/logo` para subir y eliminar logo.
   - GET `/logo/{filename}`: sanitización de `filename` para evitar path traversal.

2. **Frontend**
   - Corrección de caracteres especiales en `Configuracion.tsx` (Último, ✅/❌ en Badge y comentarios).

3. **Documentación**
   - Este archivo: endpoints, BD, caracteres especiales y articulación con otros módulos.
