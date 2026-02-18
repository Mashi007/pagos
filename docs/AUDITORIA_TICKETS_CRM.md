# Auditoría Integral - RapiCredit /pagos/crm/tickets

**Fecha:** 18 de febrero de 2025  
**URL objetivo:** https://rapicredit.onrender.com/pagos/crm/tickets  
**Alcance:** Conexión BD, coherencia backend-frontend, calidad de endpoints, flujo completo.

---

## 1. Resumen Ejecutivo

| Área | Estado | Observaciones |
|------|--------|---------------|
| **Conexión BD** | ✅ OK | `get_db` en todos los endpoints; tablas `tickets` y `clientes` |
| **Backend tickets** | ✅ OK | CRUD real, estadísticas, notificación por correo |
| **Frontend tickets** | ✅ OK | Integrado con API real; KPIs, filtros, timeline |
| **Coherencia API** | ⚠️ Menor | Endpoint inexistente; enlace cliente sin BASE_PATH |
| **Calidad endpoints** | ✅ OK | Paginación, filtros, fallback columnas BD |

---

## 2. Conexión a Base de Datos

### 2.1 Tablas utilizadas

| Tabla | Uso |
|-------|-----|
| `tickets` | CRUD tickets; `cliente_id`, `estado`, `prioridad`, `tipo`, `conversacion_whatsapp_id`, etc. |
| `clientes` | Datos del cliente asociado (`clienteData`, `cliente`) |

### 2.2 Engine y sesión

- Uso de `Depends(get_db)` en todos los endpoints.
- Fallback para BDs sin `fecha_creacion`/`fecha_actualizacion` en `tickets`.

---

## 3. Backend - Endpoints de Tickets

### 3.1 Rutas disponibles

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/api/v1/tickets` | Listado paginado (cliente_id, estado, prioridad, tipo) + estadísticas |
| GET | `/api/v1/tickets/{id}` | Ticket por ID con datos de cliente |
| POST | `/api/v1/tickets` | Crear ticket; notifica por correo |
| PUT | `/api/v1/tickets/{id}` | Actualizar ticket (solo estado, prioridad, asignado, escalado, fecha_limite, archivos) |

### 3.2 Filtros soportados (GET /tickets)

| Parámetro | Tipo | Descripción |
|-----------|------|-------------|
| `page` | int | Página (default 1) |
| `per_page` | int | Por página (1-100, default 20) |
| `cliente_id` | int | Filtrar por cliente |
| `estado` | string | abierto, en_proceso, resuelto, cerrado |
| `prioridad` | string | baja, media, urgente |
| `tipo` | string | consulta, incidencia, solicitud, reclamo, contacto |

### 3.3 Estadísticas (KPIs)

El backend devuelve `estadisticas` con: `total`, `abiertos`, `en_proceso`, `resueltos`, `cerrados`.

### 3.4 Calidad del backend

- ✅ Datos reales desde tabla `tickets`.
- ✅ Vinculación con `clientes` para `clienteData`.
- ✅ Notificación por correo al crear/actualizar (`TICKETS_NOTIFY_EMAIL`).
- ✅ Fallback si la BD no tiene `fecha_creacion`/`fecha_actualizacion`.
- ⚠️ `titulo` y `descripcion` no se pueden actualizar (solo en creación).

---

## 4. Frontend - Servicio y Página

### 4.1 Endpoints que SÍ existen y se usan

| Método frontend | Endpoint backend | Estado |
|-----------------|-----------------|--------|
| `getTickets` | GET /tickets | ✅ |
| `getTicket` | GET /tickets/{id} | ✅ |
| `createTicket` | POST /tickets | ✅ |
| `updateTicket` | PUT /tickets/{id} | ✅ |

### 4.2 Endpoints que NO existen en backend

| Método frontend | Endpoint llamado | Uso |
|-----------------|------------------|-----|
| `getTicketsByConversacion` | GET /tickets/conversacion/{id} | No se usa en ningún componente (código muerto) |

---

## 5. Inconsistencias y Observaciones

### 5.1 Modal Editar: título y descripción editables pero no se actualizan

- El modal de edición permite cambiar título y descripción.
- `handleActualizarTicket` solo envía: `estado`, `prioridad`, `asignado_a`, `fecha_limite`.
- El backend `TicketUpdate` no incluye `titulo` ni `descripcion`.
- **Efecto:** Los cambios en título/descripción se pierden al guardar.

**Recomendación:** Deshabilitar o marcar como solo lectura título y descripción en el modal de edición, o documentar que no se pueden editar.

### 5.2 Enlace "Ver cliente completo"

- Código: `window.open(\`/clientes/${ticket.clienteId}\`, '_blank')`
- Con la app en `/pagos`, la ruta correcta sería `/pagos/clientes/{id}`.
- `/clientes/123` puede no resolver bien según la configuración del servidor.

**Recomendación:** Usar `window.open(\`${BASE_PATH}/clientes/${ticket.clienteId}\`, '_blank')` o un `Link` de React Router.

### 5.3 Navegación a Comunicaciones

- `handleVerConversacion` navega a `/comunicaciones?conversacion_id=${conversacionId}`.
- `conversacionId` = `ticket.conversacion_whatsapp_id` (id de `conversacion_cobranza`).
- La página Comunicaciones usa `conversacionIdFromUrl` para seleccionar la conversación.
- **Estado:** Coherente; el flujo funciona correctamente.

### 5.4 `getTicketsByConversacion`

- Definido en el servicio pero no usado.
- El endpoint `/tickets/conversacion/{id}` no existe en el backend.
- **Recomendación:** Eliminar del servicio o implementar el endpoint si se va a usar.

### 5.5 `clienteData.apellidos`

- El frontend `Ticket.clienteData` incluye `apellidos`.
- El backend `ClienteDataTicket` solo tiene `nombres` (nombre completo).
- No hay conflicto; `apellidos` puede quedar `undefined` en el frontend.

---

## 6. Flujo de Datos

### 6.1 Listado

1. `getTickets({ page, per_page, estado, prioridad })` → GET `/api/v1/tickets`.
2. Backend consulta `tickets` con filtros y carga `clientes` para `clienteData`.
3. Devuelve `tickets`, `paginacion`, `estadisticas`.

### 6.2 Crear ticket

1. Usuario selecciona cliente (búsqueda con `useSearchClientes`).
2. `createTicket` → POST `/api/v1/tickets`.
3. Backend crea fila y envía notificación por correo.

### 6.3 Actualizar ticket

1. Usuario edita estado, prioridad, asignado, fecha límite.
2. `updateTicket` → PUT `/api/v1/tickets/{id}`.
3. Backend actualiza y notifica por correo.

### 6.4 Vinculación con Comunicaciones

- Al crear ticket desde Comunicaciones se envía `conversacion_whatsapp_id`.
- En Tickets, el botón "WhatsApp" navega a Comunicaciones con ese id para abrir la conversación.

---

## 7. Recomendaciones

### 7.1 Prioridad media

1. **Modal Editar:** Deshabilitar o marcar como solo lectura título y descripción.
2. **Enlace cliente:** Usar `BASE_PATH` en `window.open` para el enlace "Ver cliente completo".

### 7.2 Prioridad baja

3. **`getTicketsByConversacion`:** Eliminar del servicio o implementar el endpoint en backend si se necesita.
4. **Filtro búsqueda local:** El filtro por texto (`searchTerm`) se aplica en el frontend sobre la página actual. Para búsqueda global, habría que añadir un parámetro `search` en el backend.

---

## 8. Checklist de Verificación

- [ ] `GET /api/v1/tickets` devuelve tickets reales (requiere auth).
- [ ] La página `/pagos/crm/tickets` carga sin errores.
- [ ] Crear ticket con cliente asociado funciona.
- [ ] Actualizar ticket (estado, prioridad, fecha límite) funciona.
- [ ] KPIs (Total, Abiertos, En Proceso, Resueltos, Cerrados) se actualizan.
- [ ] Filtros por estado y prioridad funcionan.
- [ ] Botón "WhatsApp" navega a Comunicaciones y selecciona la conversación correcta.
- [ ] Alertas de tickets vencidos y próximos a vencer se muestran correctamente.

---

## 9. Referencias

- `backend/app/api/v1/endpoints/tickets.py` – Endpoints.
- `backend/app/models/ticket.py` – Modelo.
- `backend/app/schemas/ticket.py` – Schemas.
- `frontend/src/services/ticketsService.ts` – Servicio.
- `frontend/src/pages/TicketsAtencion.tsx` – Página principal.
- `frontend/src/components/comunicaciones/Comunicaciones.tsx` – Creación de tickets desde comunicaciones.
