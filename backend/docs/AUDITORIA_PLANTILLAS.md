# Auditoría integral: Plantillas de notificaciones

**Ruta:** `/pagos/configuracion?tab=plantillas`  
**Fecha:** 2025-02-05

## 1. Resumen

- **Endpoints** de plantillas están conectados y alineados con el frontend (listar, crear, actualizar, eliminar, exportar, enviar con plantilla).
- **Reglas de negocio**: tipos de plantilla unificados entre backend y frontend; validación de tipo en create/update; variables obligatorias por tipo coherentes (incl. MORA_61).
- **Integridad** entre componentes Plantillas (PlantillasNotificaciones, GestionVariables) y Notificaciones (ConfiguracionNotificaciones, envío por tipo) verificada. La configuración de envíos (plantilla_id por tipo) usa la API de configuración correcta.

---

## 2. Endpoints (backend) y conexión con frontend

| Método | Ruta | Uso en frontend | Estado |
|--------|------|------------------|--------|
| GET | `/api/v1/notificaciones/plantillas?tipo=&solo_activas=` | `notificacionService.listarPlantillas(tipo, soloActivas)` | OK |
| GET | `/api/v1/notificaciones/plantillas/{id}` | `notificacionService.obtenerPlantilla(id)` | OK |
| POST | `/api/v1/notificaciones/plantillas` | `notificacionService.crearPlantilla(data)` | OK |
| PUT | `/api/v1/notificaciones/plantillas/{id}` | `notificacionService.actualizarPlantilla(id, data)` | OK |
| DELETE | `/api/v1/notificaciones/plantillas/{id}` | `notificacionService.eliminarPlantilla(id)` | OK |
| GET | `/api/v1/notificaciones/plantillas/{id}/export` | `notificacionService.exportarPlantilla(id)` | OK |
| POST | `/api/v1/notificaciones/plantillas/{id}/enviar?cliente_id=` | `notificacionService.enviarConPlantilla(plantillaId, { cliente_id, variables })` | OK |
| GET | `/api/v1/configuracion/notificaciones/envios` | `emailConfigService.obtenerConfiguracionEnvios()` | OK (Configuración envíos) |
| PUT | `/api/v1/configuracion/notificaciones/envios` | `emailConfigService.actualizarConfiguracionEnvios(config)` | OK |

- **Base URL plantillas:** `notificacionService.baseUrl` = `/api/v1/notificaciones`.
- **Base URL configuración envíos:** `EmailConfigService.baseUrl` = `/api/v1/configuracion` → `/notificaciones/envios`.

---

## 3. Reglas de negocio

### 3.1 Tipos de plantilla (coherentes backend ↔ frontend)

Lista única permitida en backend (`TIPOS_PLANTILLA_PERMITIDOS`) y usada en frontend (tiposPorCategoria / CRITERIOS):

- **Antes de vencimiento:** `PAGO_5_DIAS_ANTES`, `PAGO_3_DIAS_ANTES`, `PAGO_1_DIA_ANTES`
- **Día de pago:** `PAGO_DIA_0`
- **Retraso:** `PAGO_1_DIA_ATRASADO`, `PAGO_3_DIAS_ATRASADO`, `PAGO_5_DIAS_ATRASADO`
- **Prejudicial:** `PREJUDICIAL`
- **Mora 61+:** `MORA_61`

- **Backend:** En `create_plantilla` y `update_plantilla` se valida que `tipo` pertenezca a `TIPOS_PLANTILLA_PERMITIDOS`; si no, 422.
- **Frontend:** Los mismos tipos se usan en Armar plantilla (select “Aplicar al caso”), en Resumen (mapeo por caso) y en ConfiguracionNotificaciones (CRITERIOS).

### 3.2 Validación de variables obligatorias por tipo (frontend)

En `PlantillasNotificaciones`, `requeridasPorTipo` exige que asunto/cuerpo contengan las variables indicadas antes de guardar:

- Previas y día de pago: `nombre`, `monto`, `fecha_vencimiento`
- Retraso y prejudicial: además `dias_atraso`
- **MORA_61:** `nombre`, `monto`, `fecha_vencimiento`, `dias_atraso` (añadido en esta auditoría para coherencia)

### 3.3 Campos obligatorios (backend)

- **Crear:** `nombre`, `tipo`, `asunto` obligatorios; `cuerpo` puede ser vacío (se guarda como string).
- **Actualizar:** mismos campos actualizables; si se envía `tipo`, debe ser uno de los permitidos.

---

## 4. Sustitución de variables al enviar

- **Backend** `_sustituir_variables(texto, item)`:
  - Sustituye las variables fijas: `{{nombre}}`, `{{cedula}}`, `{{fecha_vencimiento}}`, `{{numero_cuota}}`, `{{monto}}`, `{{dias_atraso}}` (monto desde `item.monto_cuota`).
  - Además sustituye **cualquier otra clave** presente en `item` (p. ej. `{{telefono}}`, `{{correo}}`), para soportar variables personalizadas cuyos nombres coincidan con claves del item.
- **Item** en envío viene de `_item_tab` en notificaciones_tabs: incluye `nombre`, `cedula`, `correo`, `telefono`, `fecha_vencimiento`, `numero_cuota`, `monto_cuota`, `dias_atraso`, etc.

Con esto, las variables personalizadas (pestaña Variables Personalizadas) que mapean a campos del item se sustituyen correctamente al usar la plantilla en el envío.

---

## 5. Integridad entre componentes

### 5.1 Flujo Plantillas (Configuración → Plantillas)

- **Plantillas.tsx:** Dos pestañas: “Plantillas” (`PlantillasNotificaciones`) y “Variables Personalizadas” (`GestionVariables`).
- **PlantillasNotificaciones:**
  - Subpestañas “Armar plantilla” y “Resumen”.
  - Carga plantillas con `listarPlantillas(undefined, false)` (todas, no solo activas) para listado y para asignar en Notificaciones.
  - Carga variables (API + precargadas) y las muestra en “Banco de Variables”; al cambiar a pestaña Plantillas se recargan variables (`tabSeccionActiva`).
- **GestionVariables:** CRUD de variables personalizadas; las variables creadas se integran en Armar plantilla vía `cargarVariables()` al volver a la pestaña Plantillas.

### 5.2 Flujo Notificaciones (uso de plantillas)

- **ConfiguracionNotificaciones** (Notificaciones → Configuración):
  - Carga configuración de envíos con `emailConfigService.obtenerConfiguracionEnvios()` (GET `/api/v1/configuracion/notificaciones/envios`).
  - Carga plantillas con `notificacionService.listarPlantillas(undefined, false)` para los desplegables por tipo.
  - Por cada criterio (PAGO_5_DIAS_ANTES, PAGO_DIA_0, etc.) permite elegir **plantilla_id** opcional y guardar con `actualizarConfiguracionEnvios` (PUT mismo path).
- **Backend envío** (notificaciones_tabs):
  - Para cada tipo de pestaña (previas, día pago, retrasadas, prejudicial, mora_61) obtiene `config_envios` (incl. `plantilla_id` por tipo).
  - Llama a `get_plantilla_asunto_cuerpo(db, plantilla_id, item, asunto_base, cuerpo_base)`.
  - Si `plantilla_id` es válido y la plantilla existe y está activa, usa asunto/cuerpo de la plantilla con variables sustituidas; si no, usa asunto/cuerpo por defecto del endpoint.

La cadena **Plantillas (crear/editar) → Configuración envíos (asignar plantilla por tipo) → Envío (usar plantilla por tipo)** queda coherente y conectada.

---

## 6. Archivos relevantes

| Ámbito | Archivo |
|--------|---------|
| Backend modelo | `backend/app/models/plantilla_notificacion.py` |
| Backend API plantillas | `backend/app/api/v1/endpoints/notificaciones.py` (CRUD, _sustituir_variables, get_plantilla_asunto_cuerpo, TIPOS_PLANTILLA_PERMITIDOS) |
| Backend envío por tipo | `backend/app/api/v1/endpoints/notificaciones_tabs.py` (_enviar_correos_items, get_plantilla_asunto_cuerpo) |
| Backend config envíos | `backend/app/api/v1/endpoints/configuracion.py` (GET/PUT notificaciones/envios) |
| Frontend servicio | `frontend/src/services/notificacionService.ts` (plantillas + EmailConfigService.obtenerConfiguracionEnvios/actualizarConfiguracionEnvios) |
| Frontend página | `frontend/src/pages/Plantillas.tsx` (tabs Plantillas / Variables Personalizadas) |
| Frontend Armar/Resumen | `frontend/src/components/notificaciones/PlantillasNotificaciones.tsx` |
| Frontend variables | `frontend/src/components/notificaciones/GestionVariables.tsx` |
| Frontend config notificaciones | `frontend/src/components/notificaciones/ConfiguracionNotificaciones.tsx` |

---

## 7. Mejoras aplicadas en esta auditoría

1. **Backend:** Validación de `tipo` en create y update de plantilla contra `TIPOS_PLANTILLA_PERMITIDOS` (422 si no es uno de los tipos permitidos).
2. **Backend:** `_sustituir_variables` ampliada para sustituir cualquier clave presente en `item` (variables personalizadas como `{{telefono}}`, `{{correo}}`).
3. **Frontend:** Inclusión de `MORA_61` en `requeridasPorTipo` con `['nombre', 'monto', 'fecha_vencimiento', 'dias_atraso']` para coherencia con el resto de tipos de mora/retraso.

---

## 8. Checklist de verificación

- [x] GET/POST/PUT/DELETE plantillas conectados desde frontend.
- [x] GET/PUT configuración envíos (plantilla_id por tipo) usan API configuracion.
- [x] Tipos de plantilla unificados backend ↔ frontend y validados en backend.
- [x] Variables obligatorias por tipo coherentes (incl. MORA_61).
- [x] Sustitución de variables en envío incluye variables personalizadas (claves del item).
- [x] ConfiguracionNotificaciones carga plantillas y asigna plantilla_id por tipo.
- [x] notificaciones_tabs usa plantilla_id por tipo y get_plantilla_asunto_cuerpo.
