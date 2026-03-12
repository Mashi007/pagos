# Auditoría total: Configuración > Email (`/pagos/configuracion?tab=email`)

**URL:** https://rapicredit.onrender.com/pagos/configuracion?tab=email  
**Alcance:** Endpoints usados por la pestaña, definición de rutas, procesos reales vs stubs/falsos.  
**Fecha:** 2025-03-12

---

## 1. Inventario de endpoints

La pestaña Email utiliza los siguientes endpoints (todos bajo `/api/v1/`, con auth salvo que se indique lo contrario).

| Método | Ruta completa | Uso en la pestaña Email |
|--------|----------------|-------------------------|
| GET | `/api/v1/configuracion/email/configuracion` | Cargar formulario (SMTP, IMAP, toggles, modo prueba). |
| PUT | `/api/v1/configuracion/email/configuracion` | Guardar configuración. |
| GET | `/api/v1/configuracion/email/estado` | Estado “configurada” y mensajes para la UI (vinculación, App Password). |
| POST | `/api/v1/configuracion/email/probar` | Enviar email de prueba (SMTP real). |
| POST | `/api/v1/configuracion/email/probar-imap` | Probar conexión IMAP (conexión real). |
| GET | `/api/v1/configuracion/notificaciones/envios` | Sincronizar modo_pruebas y email_pruebas con Notificaciones. |
| PUT | `/api/v1/configuracion/notificaciones/envios` | Tras guardar Email, actualizar modo_pruebas/emails en notificaciones. |
| GET | `/api/v1/notificaciones?page=1&per_page=10` | “Verificación de Envíos Reales”: listado de envíos recientes. |

Rutas de configuración están protegidas por `get_current_user` (router en `configuracion.py` con `dependencies=[Depends(get_current_user)]`). El sub-router de email se monta en `configuracion.router` con `prefix="/email"`, por tanto las rutas de email requieren autenticación.

---

## 2. Definición de rutas (backend)

| Ruta | Definición | Conclusión |
|------|------------|------------|
| `/api/v1/configuracion` | `api_router.include_router(configuracion.router, prefix="/configuracion")` en `__init__.py`. | Correcto. |
| `/configuracion/email/*` | `router.include_router(configuracion_email.router, prefix="/email")` en `configuracion.py`. | Correcto. |
| GET `/configuracion` | No existe en configuracion_email; el recurso es `/email/configuracion`. | Correcto (front llama a `email/configuracion`). |
| GET/PUT `/email/configuracion` | `@router.get("/configuracion")`, `@router.put("/configuracion")` en `configuracion_email.py`. | Bien definidos. |
| GET `/email/estado` | `@router.get("/estado")`. | Bien definido. |
| POST `/email/probar` | `@router.post("/probar")`. | Bien definido. |
| POST `/email/probar-imap` | `@router.post("/probar-imap")`. | Bien definido. |
| GET/PUT `/notificaciones/envios` | `@router.get("/notificaciones/envios")`, `@router.put("/notificaciones/envios")` en `configuracion.py`. | Bien definidos. |
| GET `/notificaciones` (lista) | `@router.get("")` en `notificaciones.py` (router con prefix `/notificaciones`). | Bien definido. |

No hay rutas duplicadas ni conflictos. La base URL del frontend (`/api/v1/configuracion` para EmailConfigService) coincide con el prefijo del API.

---

## 3. Procesos reales vs stubs / falsos

### 3.1 GET `/api/v1/configuracion/email/configuracion`

- **Proceso:** Carga desde BD (`_load_email_config_from_db`: tabla `configuracion`, clave `email_config`), fusiona con stub en memoria y con `.env` (`_sync_stub_from_settings`). Devuelve copia del stub con contraseñas enmascaradas (`***`).
- **Conclusión:** Proceso real. Lectura desde BD; contraseñas no se exponen.

### 3.2 PUT `/api/v1/configuracion/email/configuracion`

- **Proceso:** Recibe body, actualiza stub (ignora contraseña si viene `***`), valida con `validar_config_email_para_guardar`, actualiza holder en memoria (`update_from_api`), persiste en BD (`_persist_email_config`: tabla `configuracion`, clave `email_config`). Campos sensibles se encriptan antes de guardar.
- **Conclusión:** Proceso real. Validación, persistencia en BD y encriptación correctas.

### 3.3 GET `/api/v1/configuracion/email/estado`

- **Proceso:** Lee de BD y stub; calcula `configurada` (host + user + password presentes); construye `problemas[]` y mensaje. **No** abre conexión SMTP. Siempre devuelve `conexion_smtp: { success: False, message: "Usa 'Enviar Email de Prueba'..." }` (o `null` si no configurada).
- **Conclusión:** Proceso real para “datos completos / problemas”. La “conexión SMTP” es intencionadamente falsa (no se hace prueba SMTP aquí); la verificación real es con POST `/probar`. Documentar en UI que el estado de “vinculación” se confirma enviando un correo de prueba.

### 3.4 POST `/api/v1/configuracion/email/probar`

- **Proceso:** Carga config desde BD, obtiene SMTP con `get_smtp_config()`, valida destino y formato, llama a `send_email(..., respetar_destinos_manuales=True)`. `send_email` usa `smtplib`: conexión SMTP real (SSL o STARTTLS), login y envío.
- **Conclusión:** Proceso real. Envío de correo de prueba real por SMTP.

### 3.5 POST `/api/v1/configuracion/email/probar-imap`

- **Proceso:** Usa config del body o de BD, llama a `test_imap_connection()` en `email.py`: `imaplib.IMAP4_SSL` o `IMAP4` + STARTTLS, `server.login()`, `server.list()` para carpetas, cierre de sesión.
- **Conclusión:** Proceso real. Conexión IMAP real al servidor.

### 3.6 GET `/api/v1/configuracion/notificaciones/envios`

- **Proceso:** Lee de BD: `db.get(Configuracion, CLAVE_NOTIFICACIONES_ENVIOS)`, parsea JSON, devuelve el objeto. Si no hay fila o no es JSON válido, devuelve `{}`.
- **Conclusión:** Proceso real. Datos desde BD (tabla `configuracion`, clave `notificaciones_envios`).

### 3.7 PUT `/api/v1/configuracion/notificaciones/envios`

- **Proceso:** Recibe dict, hace `json.dumps`, upsert en tabla `configuracion` (clave `notificaciones_envios`), commit.
- **Conclusión:** Proceso real. Persistencia en BD.

### 3.8 GET `/api/v1/notificaciones` (listado para “Envíos recientes”)

- **Proceso:** En `notificaciones.py`, `get_notificaciones_lista` devuelve siempre `items=[], total=0, total_pages=0`. No consulta la tabla `envios_notificacion`. Comentario en código: “Sin tabla de notificaciones en BD se devuelve lista vacía”.
- **Conclusión:** Proceso falso/stub. La tabla `envios_notificacion` existe y se escribe desde las pestañas de notificaciones al enviar correos, pero este endpoint no está conectado a ella. La card “Verificación de Envíos Reales” siempre muestra “No hay envíos recientes” aunque haya registros en BD.

---

## 4. Validación y seguridad

| Aspecto | Estado |
|---------|--------|
| Validación al guardar | `validar_config_email_para_guardar`: SMTP obligatorio (host, user, from_email, puerto 587/465 para Gmail), formato email, modo pruebas + email_pruebas, IMAP opcional, `tickets_notify_emails` si existe. |
| Contraseñas | No se devuelven en GET; en PUT no se sobrescribe si el cliente envía `***`. En BD se guardan encriptadas (campos `*_encriptado`). |
| Auth | Todas las rutas de configuración requieren `get_current_user`. |
| Inyección / formato | Validación de emails y puertos; body validado por Pydantic donde aplica. |

---

## 5. Resumen y recomendaciones

### Endpoints bien definidos y procesos reales

- GET/PUT `configuracion/email/configuracion`: lectura/escritura real en BD, encriptación de sensibles.
- GET `configuracion/email/estado`: datos reales; “conexión SMTP” es solo mensaje (no prueba SMTP).
- POST `configuracion/email/probar`: envío SMTP real.
- POST `configuracion/email/probar-imap`: conexión IMAP real.
- GET/PUT `configuracion/notificaciones/envios`: lectura/escritura real en BD.

### Proceso falso detectado

- **GET `/api/v1/notificaciones` (listado):** Siempre devuelve lista vacía. No usa la tabla `envios_notificacion`, que sí se alimenta al enviar desde las pestañas de notificaciones. La card “Verificación de Envíos Reales” en la pestaña Email nunca muestra envíos reales.

**Recomendación:** Implementar en `get_notificaciones_lista` la lectura desde `envios_notificacion` (paginada), mapeando al menos `id`, `fecha_envio`, `exito` → `estado` (ej. ENVIADA/FALLIDA), `error_mensaje`. El modelo no tiene campo “asunto”; se puede dejar asunto opcional o derivado de `tipo_tab` para no romper la UI actual.

### Documentación sugerida

- En la UI de “Estado” o ayuda, aclarar que “Configuración correcta” / “Datos completos” se confirman realmente con “Enviar Email de Prueba”, ya que GET estado no hace prueba SMTP.

---

*Auditoría realizada sobre el código del repositorio; no se inspeccionó el sitio desplegado en vivo.*
