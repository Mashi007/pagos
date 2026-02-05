# Endpoints de configuración: Backend ↔ Frontend

Resumen de endpoints bajo `/api/v1/configuracion` y su articulación con el frontend.

---

## 1. Configuración general y logo

| Método | Ruta backend (prefijo `/api/v1/configuracion`) | Frontend | Estado |
|--------|------------------------------------------------|----------|--------|
| GET | `/general` | `configuracionGeneralService.obtenerConfiguracionGeneral()` → `/general` | ✅ Activo |
| PUT | `/general` | `configuracionGeneralService.actualizarConfiguracionGeneral()` → `/general` | ✅ Activo |
| GET | `/logo/{filename}` | `Configuracion.tsx`, `Logo.tsx` → `/logo/{filename}` | ✅ Activo |
| POST | `/upload-logo` | `Configuracion.tsx` → `/upload-logo` | ✅ Activo |
| DELETE | `/logo` | `Configuracion.tsx` → `/logo` | ✅ Activo |

**Frontend:** `frontend/src/services/configuracionGeneralService.ts`, `Configuracion.tsx`, `Logo.tsx`.

---

## 2. Configuración Email (SMTP / IMAP)

| Método | Ruta backend | Frontend | Estado |
|--------|--------------|----------|--------|
| GET | `/email/configuracion` | `EmailConfigService.obtenerConfiguracionEmail()` | ✅ Activo |
| PUT | `/email/configuracion` | `EmailConfigService.actualizarConfiguracionEmail()` | ✅ Activo |
| GET | `/email/estado` | `verificarEstadoConfiguracionEmail()` | ✅ Activo |
| POST | `/email/probar` | `probarConfiguracionEmail()` | ✅ Activo |
| POST | `/email/probar-imap` | `probarConfiguracionImap()` | ✅ Activo |

**Frontend:** `frontend/src/services/notificacionService.ts` (EmailConfigService).

---

## 3. Configuración WhatsApp

| Método | Ruta backend | Frontend | Estado |
|--------|--------------|----------|--------|
| GET | `/whatsapp/configuracion` | `WhatsAppConfigService.obtenerConfiguracionWhatsApp()` | ✅ Activo |
| PUT | `/whatsapp/configuracion` | `actualizarConfiguracionWhatsApp()` | ✅ Activo |

**Frontend:** `frontend/src/services/notificacionService.ts` (WhatsAppConfigService).

---

## 4. Configuración de envíos (notificaciones)

| Método | Ruta backend | Frontend | Estado |
|--------|--------------|----------|--------|
| GET | `/notificaciones/envios` | `obtenerConfiguracionEnvios()` | ✅ Stub añadido |
| PUT | `/notificaciones/envios` | `actualizarConfiguracionEnvios()` | ✅ Stub añadido |

**Frontend:** `frontend/src/services/notificacionService.ts`.

---

## 5. Validadores (bajo configuración)

| Método | Ruta backend | Frontend | Estado |
|--------|--------------|----------|--------|
| GET | `/api/v1/validadores/configuracion-validadores` | `configuracionService.obtenerValidadores()` | ✅ Activo (router validadores) |
| POST | `/configuracion/validadores/probar` | `configuracionService.probarValidadores()` | ✅ Stub añadido |

**Frontend:** `frontend/src/services/configuracionService.ts`. La configuración de validadores se obtiene de `/api/v1/validadores/`, la prueba se llama a `/api/v1/configuracion/validadores/probar`.

---

## 6. Sistema (configuración completa / por categoría)

| Método | Ruta backend | Frontend | Estado |
|--------|--------------|----------|--------|
| GET | `/configuracion/sistema/completa` | `obtenerConfiguracionCompleta()` | ✅ Stub añadido |
| GET | `/configuracion/sistema/categoria/{categoria}` | `obtenerConfiguracionCategoria()` | ✅ Stub añadido |

**Frontend:** `frontend/src/services/configuracionService.ts`.

---

## 7. Configuración AI (OpenRouter)

| Método | Ruta backend | Frontend | Estado |
|--------|--------------|----------|--------|
| GET | `/ai/configuracion` | AIConfig, ChatAI, EntrenamientoMejorado | ✅ Activo |
| PUT | `/ai/configuracion` | AIConfig, EntrenamientoMejorado | ✅ Activo |
| POST | `/ai/chat` | ChatAI | ✅ Activo |
| POST | `/ai/probar` | AIConfig | ✅ Activo |
| GET | `/ai/documentos` | AIConfig, RAGTab | ✅ Activo (stub: lista vacía) |

**Frontend:** `AIConfig.tsx`, `ChatAI.tsx`, `EntrenamientoMejorado.tsx`, `RAGTab.tsx`, etc.

Rutas AI que el frontend llama y **no existen** en backend (devuelven 404 si se usan):

- `POST /ai/documentos` (subir documento)
- `POST /ai/documentos/{id}/procesar`
- `PUT /ai/documentos/{id}`, `DELETE /ai/documentos/{id}`, `PATCH /ai/documentos/{id}/activar`
- `POST /ai/chat/calificar`
- `GET /ai/chat/calificaciones`, `POST /ai/chat/calificaciones/{id}/procesar`
- `GET /ai/definiciones-campos`, `POST/PUT/DELETE /ai/definiciones-campos`, sincronizar
- `GET /ai/diccionario-semantico`, categorías, procesar
- `GET /ai/tablas-campos`

**Implementadas:** `GET /ai/prompt`, `PUT /ai/prompt`, `GET /ai/prompt/variables`, `POST /ai/prompt/variables`, `PUT /ai/prompt/variables/{id}`, `DELETE /ai/prompt/variables/{id}` (persistencia en tabla `configuracion`; el prompt personalizado se usa en el chat cuando está configurado).

Estas rutas restantes se pueden implementar más adelante o añadir como stubs si se necesitan para que la UI no falle.

---

## Resumen

- **Configuración general, logo, email, WhatsApp:** configurados y activos; articulados back ↔ front.
- **Notificaciones/envios, validadores/probar, sistema/completa y sistema/categoria:** stubs añadidos en backend para evitar 404 en las pantallas de configuración.
- **AI:** config, chat, probar, listado de documentos y **prompt** (GET/PUT prompt + variables CRUD) están activos; el resto de rutas AI (documentos CRUD, calificaciones, definiciones, diccionario, tablas-campos) no están implementadas en backend.

**Archivos backend:**  
`app/api/v1/endpoints/configuracion.py` (general, logo, notificaciones/envios, validadores/probar, sistema).  
Sub-routers: `configuracion_ai.py`, `configuracion_email.py`, `configuracion_whatsapp.py`.  
Router principal: `app/api/v1/__init__.py` → `configuracion.router` con `prefix="/configuracion"`.
