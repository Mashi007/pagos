# Conexión Clientes ↔ Comunicaciones (WhatsApp y Email)

Verificación de que el módulo **Clientes** está conectado con **Comunicaciones** para realizar comunicaciones por WhatsApp o por email.

---

## 1. Flujo desde Clientes hacia Comunicaciones

| Origen | Acción | Destino |
|--------|--------|---------|
| **Tabla Clientes** (`/pagos/clientes`) | Botón "Comunicaciones" | Navega a `/comunicaciones?cliente_id={id}` |
| Misma fila | Enlace en **teléfono** | `/comunicaciones?cliente_id={id}&tipo=whatsapp` |
| Misma fila | Enlace en **email** | `/comunicaciones?cliente_id={id}&tipo=email` |

- **Frontend:** `ClientesList.tsx` (botón e iconos MessageSquare en teléfono/email).
- **Página:** `ComunicacionesPage` lee `cliente_id` de la URL y se lo pasa al componente `Comunicaciones`.
- **Servicio:** `comunicacionesService.listarComunicaciones(1, 100, undefined, clienteId)` → `GET /api/v1/comunicaciones?page=1&per_page=100&cliente_id={id}`.

**Conclusión:** La conexión desde la lista de clientes hacia la pantalla de comunicaciones (con `cliente_id`) está correctamente implementada.

---

## 2. Backend: uso de datos del cliente

### WhatsApp

- **Tabla cliente:** Se usa el campo `clientes.telefono` (ej. `+584241234567`).
- **Filtro por cliente:**  
  `GET /api/v1/comunicaciones?cliente_id=8334`:
  1. Obtiene el cliente por ID (`Cliente.id = 8334`).
  2. Toma `cliente.telefono`, lo normaliza a solo dígitos.
  3. Filtra `conversacion_cobranza` donde `telefono` coincida (exacto o últimos 10 dígitos).
  4. Devuelve esas conversaciones con `cliente_id` en cada ítem.

- **Vínculo de datos:**  
  `clientes.telefono` ↔ `conversacion_cobranza.telefono` ↔ `mensaje_whatsapp.telefono`.  
  El mismo número en la tabla de clientes identifica la conversación y los mensajes de WhatsApp.

- **Envío de mensaje:** En Comunicaciones se envía al número de la conversación (que puede ser el teléfono del cliente). Crear cliente desde Comunicaciones (`crear-cliente-automatico`) guarda `telefono` en `clientes` para futuras conversaciones.

**Conclusión:** La conexión Clientes ↔ Comunicaciones por **WhatsApp** está bien enlazada mediante el teléfono del cliente.

### Email

- **Tabla cliente:** El campo `clientes.email` existe y se usa en otros flujos (notificaciones, crear-cliente-automatico).
- **Listado de comunicaciones por email:**  
  Si se llama con `tipo=email`, el backend devuelve **lista vacía** (stub hasta integrar bandeja de entrada, p. ej. IMAP).
- **Envío de email:** La configuración y el envío de correos (p. ej. notificaciones) usan el email del cliente desde la tabla `clientes` en otros endpoints (notificaciones, plantillas).

**Conclusión:** La conexión para **email** está preparada (cliente tiene `email`, la UI pasa `cliente_id` y `tipo=email`), pero el **listado de hilos de email** por cliente aún no está implementado en backend (respuesta vacía cuando `tipo=email`).

---

## 3. Resumen

| Canal | Conexión Clientes ↔ Comunicaciones | Listado por cliente_id | Envío / uso del dato del cliente |
|-------|-------------------------------------|-------------------------|-----------------------------------|
| **WhatsApp** | Sí: `clientes.telefono` ↔ `conversacion_cobranza.telefono` | Sí (filtro por teléfono del cliente) | Sí (envío al número; crear cliente con teléfono) |
| **Email** | Sí: cliente tiene `email`; UI pasa `cliente_id` y `tipo=email` | No (stub: lista vacía hasta IMAP/bandeja) | Sí en otros flujos (notificaciones, crear cliente con email) |

---

## 4. Comprobar en la app

1. En **Clientes**, hacer clic en "Comunicaciones" de un cliente con **teléfono** → debe abrir Comunicaciones con `cliente_id` en la URL y, si existe conversación para ese número, mostrarla.
2. En **Clientes**, hacer clic en el icono de mensaje junto al **teléfono** → mismo flujo con `tipo=whatsapp`.
3. En **Clientes**, hacer clic en el icono de mensaje junto al **email** → abre Comunicaciones con `tipo=email`; el listado puede estar vacío hasta que exista listado real de correos en backend.

**Conclusión global:** Clientes está conectado con Comunicaciones de forma adecuada para **WhatsApp** (listado y envío por teléfono del cliente). Para **email**, la conexión de datos y navegación está lista; el listado de hilos de email por cliente queda pendiente de implementación en backend.
