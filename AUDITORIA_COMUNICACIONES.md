# Auditoría integral: Comunicaciones

**URL auditada:** https://rapicredit.onrender.com/pagos/comunicaciones  
**Fecha:** 2025-02-02  
**Alcance:** Rutas frontend, endpoints backend, parámetros y conexión a APIs para integrar servicios (WhatsApp, Email, AI, Informe pagos).

---

## 1. Rutas frontend

| Ruta (pathname) | Componente | Protegida | Notas |
|-----------------|-------------|-----------|--------|
| `/comunicaciones` | `ComunicacionesPage` | Sí (`SimpleProtectedRoute`) | Ruta bajo `basename=/pagos` → URL final `/pagos/comunicaciones`. |
| `/comunicaciones?cliente_id=N` | Idem | Sí | Misma página con filtro por cliente (query). |
| `/comunicaciones?tipo=whatsapp\|email` | Idem | Sí | Filtro por tipo (usado desde ClientesList). |
| `/configuracion?tab=whatsapp` | Configuracion (tab WhatsApp) | Sí | Enlace desde Comunicaciones para configurar WhatsApp. |
| `/configuracion?tab=email` | Configuracion (tab Email) | Sí | Enlace desde Comunicaciones para configurar Email. |
| `/configuracion?tab=ai` | Configuracion (tab AI) | Sí | Enlace desde Comunicaciones para configurar AI. |
| `/configuracion?tab=informe-pagos` | Configuracion (tab Informe pagos) | Sí | Enlace desde Comunicaciones para Drive, Sheets, OCR. |

**Conclusión:** Las rutas están claras y definidas. La página Comunicaciones enlaza correctamente a Configuración por pestaña.

---

## 2. Endpoints backend usados por Comunicaciones

### 2.1 API Comunicaciones (`/api/v1/comunicaciones`)

| Método | Ruta | Parámetros query/body | Respuesta | Estado |
|--------|------|------------------------|-----------|--------|
| GET | `/api/v1/comunicaciones` o `/api/v1/comunicaciones/` | `page`, `per_page`, `tipo`, `cliente_id`, `requiere_respuesta`, `direccion` | `{ comunicaciones: [], paginacion }` | **Stub:** devuelve lista vacía; pensado para tabla comunicaciones o integración Meta/IMAP. |
| GET | `/api/v1/comunicaciones/por-responder` | `page`, `per_page` | `{ comunicaciones: [], paginacion }` | **Stub:** lista vacía hasta tener datos reales. |
| POST | `/api/v1/comunicaciones/crear-cliente-automatico` | Body: `CrearClienteAutomaticoRequest` (telefono, email, nombres, cedula, direccion, notas) | `{ success, cliente }` | **Real:** persiste en tabla `clientes`; usado al crear cliente desde comunicación. |

**Parámetros listar_comunicaciones:**

- `page` (int, ≥1), `per_page` (int, 1–100)
- Opcionales: `tipo`, `cliente_id`, `requiere_respuesta`, `direccion`

**Conclusión:** Los endpoints existen, tienen parámetros claros y autenticación (`get_current_user`). El listado y por-responder son stub hasta tener fuente de datos (tabla comunicaciones o webhook Meta/IMAP).

---

### 2.2 Configuración WhatsApp (Comunicaciones usa solo lectura)

| Método | Ruta | Uso en Comunicaciones |
|--------|------|------------------------|
| GET | `/api/v1/configuracion/whatsapp/configuracion` | ComunicacionesPage: `whatsappConfigService.obtenerConfiguracionWhatsApp()` para mostrar si WhatsApp está configurado. |

La configuración se edita en Configuración > WhatsApp; Comunicaciones solo lee para mostrar estado (configurada/no configurada).

---

### 2.3 Configuración Email, AI e Informe pagos

Comunicaciones no llama directamente a estos endpoints; redirige a Configuración por tab:

- **Email:** `GET/PUT /api/v1/configuracion/email/configuracion`, `POST /api/v1/configuracion/email/probar`, etc.
- **AI:** bajo `/api/v1/configuracion/ai/...`
- **Informe pagos:** `GET/PUT /api/v1/configuracion/informe-pagos/configuracion`

Todos están montados en el router de configuración y requieren auth.

---

## 3. Servicios frontend y conexión a APIs

| Servicio | baseUrl | Llamadas desde Comunicaciones |
|----------|---------|-------------------------------|
| `comunicacionesService` | `/api/v1/comunicaciones` | `listarComunicaciones(page, perPage, tipo?, clienteId?, requiereRespuesta?, direccion?)`, `obtenerComunicacionesPorResponder(page, perPage)`, `crearClienteAutomatico(request)`. |
| `whatsappConfigService` (notificacionService) | `/api/v1/configuracion` | `obtenerConfiguracionWhatsApp()` → GET `/whatsapp/configuracion`. |

El cliente HTTP usa `env.API_URL` (en producción vacío → rutas relativas; proxy en server sirve `/api/*` al backend). Token JWT se envía en `Authorization: Bearer <token>`.

**Conclusión:** Parámetros y rutas del frontend coinciden con los endpoints del backend. Conexión a APIs está centralizada en `apiClient` y servicios.

---

## 4. Integración con otros módulos

- **Clientes:** Enlaces desde ClientesList a `/comunicaciones?cliente_id=N` y `?tipo=email|whatsapp`; creación de cliente desde Comunicaciones vía `crear-cliente-automatico`.
- **Tickets:** Comunicaciones usa `ticketsService` y `userService` para listar usuarios y crear/actualizar tickets asociados a conversaciones.
- **WhatsApp (flujo cobranza):** El webhook y la lógica de cobranza (cédula → confirmación → foto → Drive/OCR/informe) viven en `whatsapp.py` y `whatsapp_service.py`; los datos se guardan en `pagos_whatsapp`, `conversacion_cobranza` y `pagos_informes`. La página Comunicaciones no lista esos registros como “comunicaciones” unificadas; el listado unificado sigue siendo stub.

---

## 5. Resumen de estado

| Aspecto | Estado | Notas |
|--------|--------|--------|
| Rutas frontend | OK | `/comunicaciones` y enlaces a configuración por tab definidos. |
| Endpoints comunicaciones | OK (parcial) | GET listado y por-responder son stub; POST crear-cliente-automatico real. |
| Parámetros y contratos | OK | Query y body alineados entre frontend y backend. |
| Conexión API (auth, baseUrl) | OK | JWT y rutas relativas/proxy correctos. |
| Config WhatsApp/Email/AI/Informe | OK | Endpoints existentes; Comunicaciones enlaza a Configuración. |
| Datos reales en listado | Pendiente | Requiere tabla comunicaciones o almacenar mensajes entrantes (Meta/IMAP) y exponerlos en GET comunicaciones. |

---

## 6. Recomendaciones

1. **Listado con datos reales:** Cuando exista tabla `comunicaciones` (o se persistan mensajes de Meta/IMAP), implementar en `listar_comunicaciones` la consulta a BD con filtros `tipo`, `cliente_id`, `requiere_respuesta`, `direccion` y paginación, y devolver el mismo formato `ComunicacionUnificada` que espera el frontend.
2. **Por-responder:** Implementar `obtener_comunicaciones_por_responder` con filtro `requiere_respuesta=True` sobre la misma fuente de datos.
3. **Documentación API:** Los endpoints están en FastAPI; conviene revisar que `tags=["comunicaciones"]` y descripciones en docstrings sigan al día para Swagger/OpenAPI.
4. **Informe pagos:** La configuración (Drive, Sheets, OCR, horarios 6:00, 13:00, 16:30 America/Caracas) y el envío de informes por email ya están integrados; Comunicaciones solo necesita el enlace a `configuracion?tab=informe-pagos`, que ya existe.

---

## 7. Checklist rápida para integración de servicios

- [x] Rutas frontend claras y definidas.
- [x] Endpoints comunicaciones registrados bajo `/api/v1/comunicaciones`.
- [x] Parámetros de listado y crear-cliente documentados y usados correctamente.
- [x] Auth en todos los endpoints de comunicaciones y configuración.
- [x] Frontend usa servicios con baseUrl y buildUrl correctos.
- [x] Enlaces a configuración WhatsApp, Email, AI e Informe pagos desde Comunicaciones.
- [ ] Listado de comunicaciones con datos reales (cuando exista fuente de datos).
- [ ] Por-responder con datos reales (idem).

Esta auditoría confirma que la página Comunicaciones tiene rutas claras, endpoints definidos, parámetros alineados y conexión a APIs lista para integrar servicios; el único punto pendiente es alimentar el listado (y por-responder) con datos reales cuando se disponga de almacenamiento de mensajes (Meta/IMAP o tabla comunicaciones).
