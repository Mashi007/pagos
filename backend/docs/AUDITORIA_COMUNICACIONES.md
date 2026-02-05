# Auditoría integral backend – Comunicaciones

**Alcance:** API usada por la sección [Comunicaciones](https://rapicredit.onrender.com/pagos/comunicaciones) (`/api/v1/comunicaciones`).  
**Archivo principal:** `app/api/v1/endpoints/comunicaciones.py`.  
**Fecha de referencia:** Febrero 2026.

---

## 1. Resumen ejecutivo

| Aspecto              | Estado   | Nota breve                                                                 |
|----------------------|----------|----------------------------------------------------------------------------|
| Autenticación        | ✅ Aceptable | Todos los endpoints exigen `get_current_user` (Bearer).                    |
| Autorización         | ⚠️ Revisar | No hay roles; cualquier usuario autenticado accede a todo el módulo.      |
| Validación de entrada| ⚠️ Deficiente | `crear_cliente_automatico` sin validar duplicados ni formato cédula/email. |
| Base de datos        | ❌ Crítico | N+1 y full table scan en `_cliente_id_por_telefono` (ver sección 5).       |
| Seguridad lógica     | ⚠️ Revisar | Envío WhatsApp en modo pruebas redirige destino; sin rate limit.          |
| Datos reales         | ✅ Aceptable | Listados y mensajes desde BD; stubs solo en email y “por responder”.       |

---

## 2. Autenticación y autorización

- **Autenticación:** El router declara `dependencies=[Depends(get_current_user)]`, por lo que todos los endpoints de comunicaciones exigen un Bearer token válido. Coherente con el resto de la API.
- **Autorización:** No se comprueba rol ni permisos. Cualquier usuario autenticado puede:
  - Listar todas las conversaciones y mensajes.
  - Enviar WhatsApp manual.
  - Crear clientes desde comunicaciones.
- **Recomendación:** Definir permisos por rol (por ejemplo solo “comunicaciones” o “admin”) para listar comunicaciones, enviar mensajes y crear clientes, según política de negocio.

---

## 3. Endpoints y flujos

| Método | Ruta | Uso | Observación |
|--------|------|-----|-------------|
| GET | `/comunicaciones` | Lista conversaciones (WhatsApp desde `conversacion_cobranza`). | Filtros: `tipo`, `cliente_id`; paginación. Email devuelve vacío (stub). |
| GET | `/comunicaciones/mensajes` | Historial de mensajes de una conversación por teléfono. | Query `telefono` obligatorio; `limit` 1–500 (default 200). |
| GET | `/comunicaciones/por-responder` | Comunicaciones que requieren respuesta. | Stub: siempre `[]`. |
| POST | `/comunicaciones/enviar-whatsapp` | Envío manual de mensaje WhatsApp. | Usa config WhatsApp; respeta `modo_pruebas` (redirige a `telefono_pruebas`). |
| POST | `/comunicaciones/crear-cliente-automatico` | Crear cliente desde una comunicación. | Sin validación de duplicados ni formato (ver sección 4). |

---

## 4. Seguridad y validación de entrada

### 4.1 `listar_comunicaciones`

- **Parámetros:** `page`, `per_page` (1–100), `tipo`, `cliente_id`, `requiere_respuesta`, `direccion`.
- **Riesgo:** Bajo. `cliente_id` es entero; no se usa en raw SQL. Filtro por cliente usa `db.get(Cliente, cliente_id)` y luego filtro por teléfono normalizado.
- **Observación:** Los filtros `requiere_respuesta` y `direccion` no se usan en la implementación actual (solo WhatsApp desde `conversacion_cobranza`).

### 4.2 `listar_mensajes_whatsapp`

- **Parámetros:** `telefono` (obligatorio), `limit` (1–500).
- **Riesgo:** Bajo. Teléfono se normaliza a dígitos (`_digits`); la consulta usa ORM (`.where(MensajeWhatsapp.telefono == phone)`), no concatenación SQL.
- **Observación:** Cualquier usuario autenticado puede ver el historial de cualquier número si lo conoce; considerar si debe restringirse por cliente o rol.

### 4.3 `enviar_whatsapp`

- **Validación:** Número mínimo 10 caracteres (tras strip); mensaje no vacío. Longitud de mensaje la acota `whatsapp_send` (4096).
- **Riesgo:** Sin rate limit por usuario/IP, el endpoint podría usarse para envío masivo o abuso. En modo pruebas el destino se sustituye por `telefono_pruebas` (correcto para no enviar a clientes reales).

### 4.4 `crear_cliente_automatico` (crítico)

- **Problemas:**
  1. **Duplicados:** No se comprueba si ya existe un cliente con la misma cédula (o cédula+nombres) ni email. En `clientes.py` el POST de creación sí valida y devuelve 409; aquí no.
  2. **Cédula:** Se acepta cualquier string; por defecto `"SIN-CEDULA"`. No se valida formato (E/J/V + dígitos) ni unicidad.
  3. **Email:** Por defecto `"noreply@ejemplo.com"`; no se valida formato ni duplicado.
  4. **Teléfono:** Por defecto `"+580000000000"`; no se valida formato.
  5. **Datos obligatorios en modelo:** `Cliente` exige `cedula`, `nombres`, `telefono`, `email`, `direccion`, `fecha_nacimiento`, `ocupacion`, `estado`, `usuario_registro`, `notas` no nulos. El endpoint rellena con valores por defecto; si el front envía vacíos, se persisten esos defaults (riesgo de datos basura y duplicados por cédula/email genéricos).

- **Recomendación:** Alinear con la lógica de `clientes.py`: normalizar cédula/nombres/email, comprobar duplicados (cedula+nombres y email si no vacío), devolver 409 con `existing_id` cuando aplique, y validar formatos (cédula, email, teléfono) antes de insertar.

---

## 5. Base de datos y rendimiento

### 5.1 N+1 y full table scan (crítico)

- En `listar_comunicaciones`, por **cada fila** de `ConversacionCobranza` se llama a `_cliente_id_por_telefono(db, row.telefono)`.
- `_cliente_id_por_telefono` hace **`db.query(Cliente).all()`** y recorre en Python todos los clientes para comparar teléfonos. Con N conversaciones y M clientes, el coste es O(N×M) y carga toda la tabla `clientes` N veces (o una vez por página, pero igualmente una full table scan por página).
- Además, si `cid` no es None, se hace **`db.get(Cliente, cid)`** por fila para obtener el nombre (otro acceso por conversación).

**Impacto:** En entornos con muchos clientes y conversaciones, el listado puede ser muy lento y consumir mucha memoria.

**Recomendación:**

- Sustituir la búsqueda por teléfono por una consulta SQL/ORM indexada:
  - Opción A: Añadir índice/columna normalizada de teléfono (solo dígitos) en `clientes` y filtrar por igualdad o sufijo con una sola query por lote (por ejemplo por lista de teléfonos de la página actual).
  - Opción B: Cargar en una sola query los `Cliente` cuyos teléfonos (normalizados) coincidan con los de las conversaciones de la página, y en memoria hacer el match por sufijo/lógica actual.
- Evitar `db.query(Cliente).all()` en un flujo que se ejecuta por cada fila (o por cada página).

### 5.2 Otras consultas

- **Conversaciones:** `q.count()` puede ser costoso en tablas grandes; considerar count aproximado o cache si el listado es muy usado.
- **Mensajes WhatsApp:** Query por `telefono` + `order_by` + `limit`; asumir índice en `telefono` (el modelo tiene `index=True`). Correcto.

### 5.3 Regla “datos reales desde BD”

- Listados y mensajes provienen de la BD; no hay stubs en esos flujos. Los únicos stubs son:
  - `tipo == "email"` → lista vacía.
  - `por-responder` → siempre vacío.
- Conforme con la regla del proyecto de no hardcodear datos demo en endpoints que deban reflejar información real.

---

## 6. Manejo de errores y transacciones

- **comunicaciones.py:** No hay `try/except` en los endpoints. Cualquier excepción no capturada (p. ej. de BD o de `send_whatsapp_text`) sube y FastAPI la convierte en 500. No se devuelven mensajes controlados para “configuración WhatsApp faltante” o “error al enviar”.
- **enviar_whatsapp:** Si `send_whatsapp_text` falla, se devuelve `success: false` con mensaje; si lanza excepción, 500.
- **crear_cliente_automatico:** Si la BD falla (constraint de unicidad, etc.), la excepción no se captura; el usuario vería 500 en lugar de 409 o 400 con mensaje claro.
- **Recomendación:** En `crear_cliente_automatico` capturar `IntegrityError` (y similares) y devolver 409/400 con detalle. En `enviar_whatsapp` considerar capturar errores de config o de envío y devolver 503/400 con mensaje controlado en lugar de 500.

---

## 7. Recomendaciones priorizadas

| Prioridad | Acción |
|-----------|--------|
| **P0** | Eliminar N+1 y full table scan en `listar_comunicaciones`: reemplazar `_cliente_id_por_telefono` por búsqueda indexada o por una/s pocas consultas por página (ver 5.1). |
| **P0** | En `crear_cliente_automatico`: validar duplicados (cédula+nombres y email) y devolver 409; validar formatos (cédula, email, teléfono); evitar valores por defecto que generen duplicados o datos inválidos. |
| **P1** | Capturar excepciones de BD en `crear_cliente_automatico` (IntegrityError, etc.) y devolver 4xx con mensaje claro. |
| **P1** | Definir permisos/roles para Comunicaciones (quién puede listar, enviar, crear clientes). |
| **P2** | Aplicar rate limit al endpoint `enviar-whatsapp` (por usuario o IP). |
| **P2** | Usar o documentar los filtros `requiere_respuesta` y `direccion` en el listado, o quitarlos de la API si no se usarán. |
| **P2** | Revisar si el historial de mensajes por teléfono debe restringirse (p. ej. solo números asociados al cliente del usuario o a su rol). |

---

## 8. Archivos y referencias

- **Endpoints:** `backend/app/api/v1/endpoints/comunicaciones.py`
- **Router:** `backend/app/api/v1/__init__.py` (prefix `/comunicaciones`, tag `comunicaciones`)
- **Modelos:** `ConversacionCobranza`, `Cliente`, `MensajeWhatsapp`
- **Envío WhatsApp:** `app.core.whatsapp_send.send_whatsapp_text`; guardado de mensaje: `app.services.whatsapp_service.guardar_mensaje_whatsapp`
- **Frontend:** `frontend/src/services/comunicacionesService.ts` (baseUrl `/api/v1/comunicaciones`); página Comunicaciones bajo ruta `/pagos/comunicaciones` en la app [RapiCredit](https://rapicredit.onrender.com/pagos/comunicaciones).
