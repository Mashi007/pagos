# Reglas de negocio – Módulo Clientes

**Ruta:** `/pagos/clientes` (RapiCredit – Sistema de Préstamos y Cobranza)  
**Backend:** `backend/app/api/v1/endpoints/clientes.py`  
**Frontend:** `frontend/src/pages/Clientes.tsx`, `frontend/src/components/clientes/`

---

## 1. Datos y modelo

- **Tabla:** `public.clientes`.
- **Conexión:** Siempre datos reales desde BD (`get_db`); no se usan stubs ni datos demo.
- **Campos obligatorios en BD:** `id`, `cedula`, `nombres`, `telefono`, `email`, `direccion`, `fecha_nacimiento`, `ocupacion`, `estado`, `fecha_registro`, `fecha_actualizacion`, `usuario_registro`, `notas`.
- **Nota:** La tabla **no** tiene `total_financiamiento` ni `dias_mora`; esos conceptos viven en préstamos/cuotas.

---

## 2. Estados del cliente

- **Valores permitidos:** `ACTIVO`, `INACTIVO`, `MORA`, `FINALIZADO`.
- **Estado por defecto en alta:** `ACTIVO`.
- **Cambio de estado:** Solo vía `PATCH /api/v1/clientes/{cliente_id}/estado` con body `{ "estado": "ACTIVO" | "INACTIVO" | "MORA" | "FINALIZADO" }`. Cualquier otro valor devuelve 400.

---

## 3. Listado y filtros

- **Paginación:** `page` (≥ 1), `per_page` (1–100); por defecto 20 por página.
- **Búsqueda:** Parámetro `search` aplica `ILIKE` sobre **cédula**, **nombres**, **email** y **teléfono** (cualquier coincidencia parcial).
- **Filtro por estado:** Parámetro `estado` (opcional). Solo valores: `ACTIVO`, `INACTIVO`, `MORA`, `FINALIZADO`.
- **Orden:** Por `id` descendente (más recientes primero).
- **Respuesta:** `clientes[]`, `total`, `page`, `per_page`, `total_pages`.

---

## 4. Estadísticas (KPIs)

- **Endpoint:** `GET /api/v1/clientes/stats`.
- **Métricas:** `total`, `activos`, `inactivos`, `finalizados` (conteos por estado).
- **Regla:** Los conteos se calculan en tiempo real desde la tabla `clientes` (sin `MORA` como categoría separada en stats; en el listado sí existe el estado `MORA`).

---

## 5. Alta de cliente (crear)

- **Campos requeridos (backend):** `cedula`, `nombres`, `telefono`, `email`, `direccion`, `fecha_nacimiento`, `ocupacion`, `estado`, `usuario_registro`, `notas`.
- **Frontend – validaciones de formato:**
  - **Nombres:** 2–7 palabras (nombre y apellidos); se normalizan a Title Case.
  - **Cédula:** Formato válido (incluye letra si aplica); se normaliza con `formatCedula`.
  - **Teléfono:** Venezuela por defecto: exactamente 10 dígitos; se guarda como `+58XXXXXXXXXX`. Si >10 dígitos → `+589999999999`.
  - **Email:** Formato válido, sin comas/espacios; se guarda en minúsculas.
  - **Ocupación:** Máximo 2 palabras; Title Case.
  - **Dirección:** Estructurada (calle principal, transversal, descripción, parroquia, municipio, ciudad, estado); se persiste como JSON en el campo `direccion`.
  - **Fecha nacimiento:** Formato DD/MM/YYYY en UI; se envía YYYY-MM-DD al backend.
- **Valor especial “NN”:** Si el usuario escribe `nn` (cualquier caso) en campos opcionales, se trata como vacío (no se guarda el literal "nn").
- **Notas por defecto:** Si no se informa, se envía `"No hay observacion"`.
- **Usuario:** Se debe enviar `usuario_registro` (usuario que da de alta al cliente).

---

## 6. Duplicados (no permitido: misma cédula, nombre, email o teléfono)

- **Regla de negocio deseada:** No se permite crear un cliente con:
  - La misma **cédula** y el mismo **nombre completo** que otro cliente, ni
  - El mismo **email** que otro cliente (si el email está informado).
- **Estado actual:** El backend **no** valida explícitamente estos duplicados en `create_cliente`. El frontend está preparado para:
  - Errores **400 / 409 / 503** con `detail` que contenga referencias a “cedula” y “nombre” o “email”.
  - Mostrar mensaje amigable y opción “Abrir cliente existente” si el servidor devuelve un ID de cliente existente en el mensaje.
- **Recomendación:** Implementar en backend la validación antes de `db.add(row)` en `create_cliente` (y, si se desea, en `update_cliente` para email):
  - Misma cédula + mismos nombres → 409 con mensaje y `existing_id`.
  - Mismo email (no vacío) → 409 con mensaje y `existing_id`.

---

## 7. Edición de cliente (actualizar)

- **Endpoint:** `PUT /api/v1/clientes/{cliente_id}`.
- **Campos:** Todos opcionales en el schema `ClienteUpdate`; solo se actualizan los enviados (`model_dump(exclude_unset=True)`).
- **Regla:** No se puede actualizar un cliente inexistente (404 si `cliente_id` no existe).
- **Frontend:** En edición se envían solo los campos modificados; si no hay cambios, se muestra “No se detectaron cambios” y no se llama al backend.
- **Estados en edición:** En el formulario de edición solo se permiten `ACTIVO`, `INACTIVO`, `FINALIZADO` (el estado `MORA` se gestiona por el sistema/cobranzas, pero el backend acepta `MORA` vía PATCH estado).

---

## 8. Eliminación

- **Endpoint:** `DELETE /api/v1/clientes/{cliente_id}`.
- **Comportamiento:** Borrado físico (DELETE en BD). Respuesta 204 sin cuerpo.
- **Regla:** 404 si el cliente no existe.
- **Frontend:** Se pide confirmación antes de eliminar; tras el éxito se invalidan queries de clientes, stats, dashboard y KPIs.

---

## 9. Obtener un cliente por ID

- **Endpoint:** `GET /api/v1/clientes/{cliente_id}`.
- **Regla:** 404 si no existe. Respuesta con todos los campos del cliente según `ClienteResponse`.

---

## 10. Integración con otros módulos

- **Préstamos:** Un préstamo se asocia a un `cliente_id`; la cédula y nombres del préstamo pueden tomarse del cliente.
- **Comunicaciones / WhatsApp:** Se puede buscar cliente por teléfono (solo dígitos) para asociar conversaciones.
- **Notificaciones (previas, vencimiento, retraso, prejudicial, 61+ días):** Usan email y datos del cliente desde la tabla `clientes`.
- **Reportes:** PDF de cuotas pendientes por cliente por cédula: `GET /api/v1/reportes/cliente/{cedula}/pendientes.pdf`; el cliente debe existir (404 si no).
- **AI / dashboard:** Conteos y estadísticas usan la tabla `clientes` (p. ej. total clientes).

---

## 11. Búsqueda de clientes para otros flujos

- **Búsqueda para préstamos:** Por defecto `searchClientes` filtra solo clientes en estado **ACTIVO**; para incluir todos los estados se debe pasar `incluirTodosEstados: true`.
- **Clientes en mora:** Se obtienen con filtro `estado_financiero: 'MORA'` (si el backend lo soporta en el listado; el estado directo en la tabla es `estado = 'MORA'`).

---

## 12. Carga masiva e importación

- **Importar desde Excel:** Frontend llama a `POST /api/v1/carga-masiva/clientes` con archivo. Se esperan errores 400/409 por filas duplicadas (misma cédula+nombre o mismo email); el frontend muestra mensajes específicos por tipo de duplicado.
- **Exportación:** El servicio frontend tiene `exportarClientes` pero actualmente no está implementado en backend (lanza “Exportación de clientes no disponible”).

---

## Resumen de reglas críticas

| Regla | Descripción |
|-------|-------------|
| Datos reales | Todo el módulo usa BD real vía `get_db`; sin stubs. |
| Estados | Solo `ACTIVO`, `INACTIVO`, `MORA`, `FINALIZADO`. |
| Alta | Todos los campos obligatorios del schema; validaciones de formato en frontend (nombres 2–7 palabras, teléfono +58, email, dirección estructurada, etc.). |
| Duplicados | No permitido: misma cédula, mismo nombre, mismo email ni mismo teléfono. Validado en backend (409 con existing_id). Aplica a Nuevo Cliente y Carga masiva. Frontend muestra "Abrir cliente existente". |
| Edición | Solo campos enviados; sin cambios no se actualiza. |
| Eliminación | Borrado físico; confirmación en UI. |
| Listado | Paginado, búsqueda por cédula/nombres/email/teléfono, filtro por estado. |
| Integridad | Cliente referenciado por préstamos, comunicaciones, notificaciones y reportes; eliminar cliente puede impactar esos módulos si no hay restricciones FK o lógica de borrado. |

Si quieres, el siguiente paso puede ser proponer los cambios concretos en `clientes.py` para validar duplicados (cédula+nombres y email) y devolver 409 con `existing_id`.
