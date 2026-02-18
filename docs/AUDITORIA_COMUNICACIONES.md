# Auditoría Integral - RapiCredit /pagos/comunicaciones

**Fecha:** 18 de febrero de 2025  
**URL objetivo:** https://rapicredit.onrender.com/pagos/comunicaciones  
**Alcance:** Conexión BD, coherencia backend-frontend, calidad de endpoints, flujo completo.

---

## 1. Resumen Ejecutivo

| Área | Estado | Observaciones |
|------|--------|---------------|
| **Conexión BD** | ✅ OK | `get_db` en todos los endpoints; tablas `conversacion_cobranza`, `mensaje_whatsapp`, `clientes` |
| **Backend comunicaciones** | ✅ OK | Datos reales desde BD; WhatsApp operativo; Email stub |
| **Frontend comunicaciones** | ✅ OK | Integrado con API real; flujo completo |
| **Coherencia API** | ⚠️ Menor | `cliente_id` no se pasa al listar cuando viene por URL |
| **Calidad endpoints** | ✅ OK | Paginación, filtros, rate limit, validaciones |

---

## 2. Conexión a Base de Datos

### 2.1 Tablas utilizadas

| Tabla | Uso |
|-------|-----|
| `conversacion_cobranza` | Conversaciones WhatsApp (webhook cobranza); `telefono`, `cedula`, `nombre_cliente`, `estado` |
| `mensaje_whatsapp` | Historial de mensajes (INBOUND/OUTBOUND) por conversación |
| `clientes` | Vinculación teléfono → cliente_id; `crear-cliente-automatico` |

### 2.2 Engine y sesión

- Uso de `Depends(get_db)` en todos los endpoints.
- Índices por teléfono para evitar N+1 en el listado.

---

## 3. Backend - Endpoints de Comunicaciones

### 3.1 Rutas disponibles

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/api/v1/comunicaciones` | Listado paginado (tipo, cliente_id, requiere_respuesta, direccion) |
| GET | `/api/v1/comunicaciones/mensajes` | Historial WhatsApp por teléfono (query: `telefono`, `limit`) |
| GET | `/api/v1/comunicaciones/por-responder` | Stub: devuelve vacío |
| POST | `/api/v1/comunicaciones/enviar-whatsapp` | Enviar mensaje manual; rate limit 10/min |
| POST | `/api/v1/comunicaciones/crear-cliente-automatico` | Crear cliente desde comunicación |

### 3.2 Filtros soportados (GET /comunicaciones)

| Parámetro | Tipo | Descripción |
|-----------|------|-------------|
| `page` | int | Página (default 1) |
| `per_page` | int | Por página (1-100, default 20) |
| `tipo` | string | `whatsapp` o `email`; si `email` → lista vacía (stub) |
| `cliente_id` | int | Filtrar por cliente (mismo teléfono) |
| `requiere_respuesta` | bool | No implementado en filtro SQL |
| `direccion` | string | No implementado en filtro SQL |

### 3.3 Calidad del backend

- ✅ Datos reales desde `conversacion_cobranza` y `mensaje_whatsapp`.
- ✅ Vinculación cliente por teléfono y cédula.
- ✅ Rate limit en envío WhatsApp (10/min por usuario).
- ✅ Validación de duplicados en `crear-cliente-automatico`.
- ⚠️ `requiere_respuesta` y `direccion` se aceptan pero no se aplican en filtro SQL.
- ⚠️ `por-responder` es stub (siempre vacío).

---

## 4. Frontend - Servicio y Componente

### 4.1 Endpoints que SÍ existen y se usan

| Método frontend | Endpoint backend | Estado |
|-----------------|-----------------|--------|
| `listarComunicaciones` | GET /comunicaciones | ✅ |
| `listarMensajesWhatsApp` | GET /comunicaciones/mensajes | ✅ |
| `enviarWhatsApp` | POST /comunicaciones/enviar-whatsapp | ✅ |
| `crearClienteAutomatico` | POST /comunicaciones/crear-cliente-automatico | ✅ |

### 4.2 Endpoints que NO se usan en el flujo principal

| Método frontend | Endpoint backend | Uso |
|-----------------|-----------------|-----|
| `obtenerComunicacionesPorResponder` | GET /comunicaciones/por-responder | No se usa en `Comunicaciones.tsx` |

### 4.3 Integración con Tickets

- `ticketsService.getTickets({ cliente_id })` → GET `/api/v1/tickets?cliente_id=X` ✅
- `ticketsService.createTicket` → POST `/api/v1/tickets` ✅
- `ticketsService.updateTicket` → PATCH `/api/v1/tickets/{id}` ✅

---

## 5. Inconsistencias y Observaciones

### 5.1 Filtro `cliente_id` no se pasa al listar

Cuando el usuario abre desde Clientes: `/pagos/comunicaciones?cliente_id=123`:

- El frontend llama `listarComunicaciones(1, 100, undefined, undefined)` → **no pasa `cliente_id`**.
- El backend devuelve todas las conversaciones.
- El frontend añade placeholders para el cliente si no está en la lista. Esto funciona pero es menos eficiente.

**Recomendación:** Pasar `clienteId` al listar cuando viene por URL para filtrar en el backend y reducir carga.

### 5.2 `mockNombresClientes` como fallback

- Usado en `Comunicaciones.tsx` línea 189: `nombre = mockNombresClientes[comm.cliente_id] || \`Cliente #${comm.cliente_id}\``
- El backend ya devuelve `nombre_contacto` desde `clientes.nombres` cuando hay match.
- El mock solo sirve cuando el backend no devuelve nombre (p. ej. cliente eliminado o datos incompletos). Es un fallback razonable.

### 5.3 Email: stub hasta integración IMAP

- Backend: si `tipo=email` → lista vacía.
- Frontend: muestra conversaciones de email solo cuando se abre desde Clientes con un cliente que tiene email (placeholder añadido en el frontend).
- No hay comunicaciones de email reales hasta integración IMAP.

### 5.4 Envío de email

- En `handleEnviarMensaje`: si `tipo === 'email'` → `toast.info('Envío de email en desarrollo')`.
- No hay endpoint de envío de email en comunicaciones.

---

## 6. Flujo de Datos

### 6.1 WhatsApp

1. **Webhook** recibe mensajes → guarda en `conversacion_cobranza` y `mensaje_whatsapp`.
2. **GET /comunicaciones** → lista conversaciones desde `conversacion_cobranza` y vincula con `clientes`.
3. **GET /comunicaciones/mensajes?telefono=+58...** → historial desde `mensaje_whatsapp`.
4. **POST /comunicaciones/enviar-whatsapp** → envía vía Meta API y guarda en `mensaje_whatsapp`.

### 6.2 Crear cliente desde comunicación

**POST /comunicaciones/crear-cliente-automatico**:

- Valida duplicados (cédula, nombres, email).
- Crea cliente en BD.
- Usado cuando la conversación es de un contacto sin `cliente_id`.

---

## 7. Recomendaciones

### 7.1 Prioridad media

1. **Pasar `cliente_id` al listar:** Cuando `clienteId` viene por URL, llamar `listarComunicaciones(1, 100, undefined, clienteId)` para filtrar en backend.
2. **Implementar o eliminar `por-responder`:** Si se usa en el futuro, implementar con datos reales; si no, eliminar del servicio.

### 7.2 Prioridad baja

3. **Filtros `requiere_respuesta` y `direccion`:** Implementar en backend o eliminar de la UI si no se usan.
4. **Integración IMAP:** Para comunicaciones de email reales.

---

## 8. Checklist de Verificación

- [ ] `GET /api/v1/comunicaciones` devuelve conversaciones reales (requiere auth).
- [ ] La página `/pagos/comunicaciones` carga sin errores.
- [ ] Al seleccionar una conversación WhatsApp, se cargan los mensajes.
- [ ] Enviar mensaje WhatsApp funciona (modo manual).
- [ ] Crear cliente desde conversación sin cliente vinculado funciona.
- [ ] Tickets del cliente se cargan y se pueden crear/actualizar.
- [ ] Abrir desde Clientes (`?cliente_id=X`) muestra la conversación del cliente al inicio.

---

## 9. Referencias

- `backend/app/api/v1/endpoints/comunicaciones.py` – Endpoints.
- `backend/app/models/conversacion_cobranza.py` – Modelo conversaciones.
- `backend/app/models/mensaje_whatsapp.py` – Modelo mensajes.
- `frontend/src/services/comunicacionesService.ts` – Servicio.
- `frontend/src/components/comunicaciones/Comunicaciones.tsx` – Componente principal.
- `frontend/src/services/ticketsService.ts` – Tickets.
- `docs/CONEXION_CLIENTES_COMUNICACIONES.md` – Documentación cliente-comunicaciones.
