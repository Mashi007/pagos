# Auditoría línea a línea: `/pagos/configuracion?tab=email`

**Alcance:** Flujo completo de la pantalla Configuración > Email (RapiCredit).  
**URL:** https://rapicredit.onrender.com/pagos/configuracion?tab=email  
**Fecha:** 2025-03-12

---

## 1. Enrutado y entrada a la pantalla

### 1.1 App.tsx (rutas)

- **Líneas 236-244:** `Route path="configuracion"` renderiza `<Configuracion />` dentro de `SimpleProtectedRoute requireAdmin={true}`.
- **Conclusión:** La ruta `/pagos/configuracion` (con basename `/pagos`) está protegida; solo usuarios admin acceden.

### 1.2 Configuracion.tsx (página principal)

| Líneas | Código | Auditoría |
|--------|--------|-----------|
| 57-58 | `useSearchParams()`, `tabToSeccion(searchParams.get('tab'))` | El estado inicial de la sección se deriva del query `?tab=`. |
| 33-51 | `tabToSeccion(tab)` | Mapeo `email` → `'emailConfig'`. Correcto. |
| 64-66 | `useEffect` con `[searchParams]` | Al cambiar `?tab=email` se actualiza `seccionActiva` a `'emailConfig'`. |
| 76 | `switch (seccionActiva)` | — |
| 81 | `case 'emailConfig': return <ConfigEmailTab />` | La pestaña Email renderiza `ConfigEmailTab`. |
| 54-55 | `SECTIONS_WITH_OWN_SAVE`, `SECTIONS_SELF_LOADING` | `emailConfig` está en ambas: tiene guardado propio y carga sus propios datos (no usa loading global). |
| 141 | `(!loading \|\| SECTIONS_SELF_LOADING.includes(seccionActiva)) && renderContenidoSeccion()` | En la pestaña Email no se muestra el spinner global "Cargando configuracion..."; el contenido se pinta de inmediato. Correcto. |

### 1.3 ConfigEmailTab.tsx

| Líneas | Código | Auditoría |
|--------|--------|-----------|
| 1-5 | Importa `EmailConfig` y retorna `<EmailConfig />` | Simple wrapper; toda la lógica y UI están en `EmailConfig.tsx`. |

### 1.4 configuracionSecciones.ts

| Líneas | Código | Auditoría |
|--------|--------|-----------|
| 47 | `{ id: 'emailConfig', nombre: 'Configuración Email', icono: Mail }` | La sección Email está bajo Herramientas; el id interno es `emailConfig`, coherente con `tab=email` vía `tabToSeccion`. |
| 66-67 | `NOMBRES_SECCION_ESPECIAL.emailConfig` | Título e icono para la cabecera cuando la sección activa es Email. |

---

## 2. EmailConfig.tsx – Componente principal (línea a línea)

### 2.1 Imports y tipos (1-31)

| Líneas | Auditoría |
|--------|-----------|
| 1-12 | Imports estándar (React, Lucide, Card, Button, Input, toast, validators, notificacionService, BASE_PATH). Correctos. |
| 14-30 | `EmailConfigData`: interface con smtp_*, from_*, imap_*, tickets_notify_emails, modo_pruebas, email_activo, etc. Cubre los campos que envía/recibe el backend. |

### 2.2 Estado inicial (34-77)

| Líneas | Código / Comportamiento | Auditoría |
|--------|-------------------------|-----------|
| 34-42 | Estado `config` con valores por defecto (smtp.gmail.com, 587, from_name RapiCredit, smtp_use_tls 'true') | Valores razonables para Gmail. |
| 45-47 | `mostrarPassword`, `guardando`, `probando` | UI y carga. |
| 49-56 | `modoPruebas`, `emailPruebas`, `emailActivo`, `emailPrincipalPrueba`, `emailCCPrueba`, `emailPruebaDestino`, `subjectPrueba`, `mensajePrueba`, `errorValidacion` | Coherentes con formulario y pruebas. |
| 59-68 | `vinculacionConfirmada`, `mensajeVinculacion`, `requiereAppPassword`, `estadoConfiguracion`, `setVerificandoEstado` | Estado de vinculación Gmail / App Password. |
| 71-77 | `enviosRecientes`, `cargandoEnvios`, `resultadoPrueba`, `emailEnviadoExitoso`, `mostrarPasswordImap`, `probandoImap`, `resultadoImap` | Envíos recientes y pruebas SMTP/IMAP. |

### 2.3 Efectos y carga inicial (80-241)

| Líneas | Código | Auditoría |
|--------|--------|-----------|
| 81-85 | `useEffect(() => { cargarConfiguracion(); cargarEnviosRecientes(); verificarEstadoGoogle(); }, [])` | Al montar se cargan config, envíos y estado. Dependencias vacías: solo al montar. Correcto. |
| 87-138 | `verificarEstadoGoogle()` | Llama a `emailConfigService.verificarEstadoConfiguracionEmail()` (GET `/api/v1/configuracion/email/estado`). Actualiza vinculación, mensaje y si requiere App Password. Uso de `setVerificandoEstado` no visible en UI (estado no mostrado). Menor: se podría mostrar “Verificando…” si se desea. |
| 141-228 | `cargarConfiguracion()` | GET config; sincroniza `from_email` con `smtp_user` si está vacío; normaliza `smtp_use_tls` y `email_activo`; aplica defaults (imap_port 993, etc.); detecta contraseñas enmascaradas (`***`) y no pisa el estado local; carga `modoPruebas` y `emailPruebas`; sincroniza con `obtenerConfiguracionEnvios()` para modo_pruebas/emails. Lógica sólida. |
| 169 | `const apiSmtpMasked = (data.smtp_password === undefined \|\| data.smtp_password === '***')` | Correcto: no sobrescribir contraseña real con ***. |
| 176-179 | `serviceKeys` (email_activo_notificaciones, etc.) | Se rellenan por defecto 'true' si no vienen. Esos toggles están comentados en el JSX (líneas 458-479). |
| 203-219 | Sincronización con `notificaciones_envios` | Lee GET notificaciones/envios y unifica modo_pruebas y email_pruebas. try/catch silencioso: correcto para no bloquear la carga. |
| 230-241 | `cargarEnviosRecientes()` | `notificacionService.listarNotificaciones(1, 10)`. Muestra últimos 10 envíos. Correcto. |

### 2.4 Handlers y validación (244-357)

| Líneas | Código | Auditoría |
|--------|--------|-----------|
| 245-265 | `handleChange(campo, valor)` | Actualiza `config`; si `campo === 'smtp_user'` y from_email vacío o igual al smtp_user anterior, sincroniza `from_email`. Limpia `errorValidacion`. Correcto. |
| 268-324 | `puedeGuardar` (useMemo) | Requiere host, port, user, from_email; puerto 1-65535; para Gmail exige password y puerto 587 o 465; 587 exige TLS; en modo pruebas exige email de pruebas válido. Coherente con backend. |
| 327-363 | `obtenerCamposFaltantes()` | Duplica lógica de `puedeGuardar` en forma de lista para mensaje “Completa: …”. Podría extraerse a una función única que devuelva (puedeGuardar, faltantes) para evitar divergencias. |

### 2.5 Guardar (366-354)

| Líneas | Código | Auditoría |
|--------|--------|-----------|
| 367-372 | Limpieza de espacios en contraseñas; no enviar si es vacía o '***' | Buen practice. |
| 375-388 | `configCompleta` con todos los campos (imap_*, tickets_notify_emails, modo_pruebas, email_activo) | Payload completo para PUT. Correcto. |
| 390 | `emailConfigService.actualizarConfiguracionEmail(configCompleta)` | PUT `/api/v1/configuracion/email/configuracion`. Timeout 60s en servicio. Correcto. |
| 393-399 | Después de guardar, sincroniza con notificaciones/envios (modo_pruebas, email_pruebas, emails_pruebas) vía GET + PUT | Mantiene consistencia entre Email y Notificaciones. |
| 402-414 | Actualiza estado de vinculación desde respuesta (vinculacion_confirmada, mensaje_vinculacion, requiere_app_password); toasts según resultado | Backend actualmente no devuelve vinculación real (siempre false en configuracion_email.py 187-192). Los estados se sobrescriben después con `verificarEstadoGoogle()`. |
| 417-418 | Aviso si la contraseña no se actualizó (***) | UX correcta. |
| 420 | `cargarConfiguracion()` | Refresca formulario tras guardar. |
| 424-437 | Tras `verificarEstadoGoogle()`, restaura estado de vinculación/App Password según lo que devolvió el guardado si `requiereAppPasswordAntes` o `vinculacionAntes` | Evita que la verificación posterior pise el resultado del guardado. Correcto. |
| 338-353 | catch: setErrorValidacion, toast.error, reset de vinculación | Errores 400 del backend se muestran. Correcto. |

### 2.6 Probar email (357-416)

| Líneas | Código | Auditoría |
|--------|--------|-----------|
| 359-372 | En modo pruebas exige Correo Principal y valida email; en producción valida emailPruebaDestino si se usa | Coherente con el formulario. |
| 375-382 | Llama a `probarConfiguracionEmail(..., subjectPrueba, mensajePrueba, emailCC)` | POST `/api/v1/configuracion/email/probar` con email_destino, subject, mensaje, email_cc. Correcto. |
| 386-410 | Si success=false muestra toast y puede marcar requiereAppPassword; si mensaje incluye 'enviado' marca éxito y vinculación | Detección de errores de credenciales y mensajes de éxito consistente. |
| 411-415 | catch: toast y posible requiereAppPassword | Correcto. |

### 2.7 Envío manual y UI (419-861)

| Líneas | Código | Auditoría |
|--------|--------|-----------|
| 421 | `esGmail = config.smtp_host?.toLowerCase().includes('gmail.com')` | Usado para mostrar bloques específicos de Gmail (estado vinculación, App Password). |
| 424-447 | `handleEnvioManual()` | Solo en modo pruebas; valida emailPruebas; envía correo de prueba con asunto/mensaje fijos. Correcto. |
| 455-479 | Toggle “Servicio de Email” (Activo/Inactivo) | `emailActivo` se envía en configCompleta como 'true'/'false'. Correcto. |
| 458 | Comentario en texto: “El sistema NO enviará…” | Hay un carácter raro antes de “El”: `` (U+008F). Debería ser espacio o “El”. |
| 481-531 | Bloques de estado Gmail (verde/amarillo/rojo según vinculación y requiereAppPassword) | Condiciones anidadas correctas; enlaces a myaccount.google.com/security y apppasswords. |
| 534-657 | Campos SMTP (host, port, user, password, from_email, from_name, TLS) e IMAP (host, port, user, password, SSL) | Labels y placeholders claros; contraseñas enmascaradas; aviso sobre ***. |
| 639-657 | Botón “Probar conexión IMAP” y mensaje de resultado | Llama a `probarConfiguracionImap` con la config del formulario; traduce errores de credenciales a mensaje amigable. Correcto. |
| 660-688 | Sección “Notificación automática de tickets (CRM)” y `tickets_notify_emails` | Descripción y placeholder correctos; usa BASE_PATH para enlace a /crm/tickets. |
| 691-732 | Ambiente (Producción / Pruebas), email de pruebas, Correo Principal y CC (solo en modo pruebas) | Coherente con backend. |
| 735-752 | Error de validación (errorValidacion) y botón Guardar deshabilitado si !puedeGuardar | Mensaje “Completa: …” con obtenerCamposFaltantes(). |
| 756-776 | Envío manual destacado (solo modo pruebas y emailPruebas definido) | Correcto. |
| 777-828 | Sección “Envío de Email de Prueba” (destino, asunto, mensaje, botón) | En producción avisa que el envío es real; en pruebas avisa que va a Principal/CC. Correcto. |
| 831-858 | Resultado de prueba (resultadoPrueba) con estilo verde/rojo | Correcto. |
| 862-864 | Card “Verificación de Envíos Recientes” | listarNotificaciones(1, 10); botón Actualizar. Correcto. |

### 2.8 Detalles menores

| Línea | Hallazgo |
|-------|----------|
| 268 | Typo en comentario: “CONDICIóN” (í minúscula). |
| 458 | Carácter U+008F en el texto “El sistema NO enviará…”. |
| 456 | Comentario HTML “Banners de estado” y bloque comentado (459-479) con “Email por servicio”: código muerto; se podría eliminar o descomentar si se quiere la feature. |

---

## 3. Backend: configuracion_email.py (línea a línea)

### 3.1 Cabecera y stub (1-58)

| Líneas | Código | Auditoría |
|--------|--------|-----------|
| 1-15 | Docstring: GET/PUT config, GET estado, POST probar, POST probar-imap; persistencia en tabla configuracion; encriptación de campos sensibles | Documentación clara. |
| 16-30 | Imports (json, logging, FastAPI, Pydantic, SQLAlchemy, config, get_db, update_from_api, Configuracion, validar_config_email_para_guardar) | Correctos. |
| 32 | `CLAVE_EMAIL_CONFIG = "email_config"` | Clave única en tabla configuracion. Correcto. |
| 35-58 | `_email_config_stub`: diccionario con todos los campos por defecto | Stub en memoria; se fusiona con BD en _load_email_config_from_db y _sync_stub_from_settings. Correcto. |

### 3.2 Carga y persistencia (61-117)

| Líneas | Código | Auditoría |
|--------|--------|-----------|
| 61-69 | `_sync_stub_from_settings()` | Si smtp_user está vacío, rellena desde settings (SMTP_HOST, SMTP_PORT, SMTP_USER, etc.). Permite usar .env sin pasar por la UI. |
| 72-97 | `_load_email_config_from_db(db)` | db.get(Configuracion, CLAVE_EMAIL_CONFIG); parsea JSON; aplica valores; para campos *_encriptado usa _decrypt_value_safe y rellena el stub. No expone contraseñas. Correcto. |
| 100-116 | `_persist_email_config(db)` | prepare_for_db_storage (encripta smtp_password, imap_password); json.dumps; upsert en Configuracion; commit. rollback en excepción. Correcto. |

### 3.3 GET /configuracion (120-130)

| Líneas | Código | Auditoría |
|--------|--------|-----------|
| 121-130 | Carga desde BD, sync desde settings, copia del stub, enmascara smtp_password e imap_password con "***", return | No expone secretos. Correcto. |

### 3.4 PUT /configuracion (134-196)

| Líneas | Código | Auditoría |
|--------|--------|-----------|
| 134-157 | `EmailConfigUpdate`: todos los campos Optional; incluye email_activo_* y tickets_notify_emails | Coherente con frontend. |
| 160-165 | `_is_password_masked(v)` | True si v es None, no string, vacío o "***". No sobrescribe contraseña real. Correcto. |
| 167-196 | Carga BD; model_dump(exclude_none=True); actualiza stub (salta contraseñas enmascaradas); validar_config_email_para_guardar; si no valido HTTP 400; update_from_api; _persist_email_config; respuesta con message, vinculacion_confirmada=False, requiere_app_password=False; si password_skipped añade password_not_updated y mensaje | Validación en backend; persistencia en BD; holder actualizado. La respuesta no devuelve vinculación real (siempre false); el frontend depende de GET /estado y de la respuesta de POST /probar para eso. Aceptable. |

### 3.5 GET /estado (199-227)

| Líneas | Código | Auditoría |
|--------|--------|-----------|
| 200-227 | Carga BD y settings; configurada = host+user+password presentes; problemas[] con mensajes; mensaje_estado; conexion_smtp siempre success: false con mensaje “Usa Enviar Email de Prueba…” | No hace prueba SMTP real; solo comprueba que haya datos. El frontend usa esto para “Datos completos” vs “Falta…”. Para verificación real el usuario debe usar “Enviar Email de Prueba”. Correcto. |

### 3.6 POST /probar (231-315)

| Líneas | Código | Auditoría |
|--------|--------|-----------|
| 231-246 | ProbarEmailRequest (email_destino, email_cc, subject, mensaje); _destino_prueba prioriza payload.email_destino, luego modo_pruebas + email_pruebas | Coherente con frontend. |
| 249-315 | _load_email_config_from_db; sync_from_db(); get_smtp_config(); valida host y user; valida password; destino con _destino_prueba; valida que destino tenga @ y dominio con al menos 2 caracteres en TLD; subject/body por defecto; reemplazo de {{LOGO_URL}}; send_email(..., respetar_destinos_manuales=True); return success/mensaje/email_destino | Envío real; validaciones adecuadas; logging. Correcto. |

### 3.7 POST /probar-imap (317-384)

| Líneas | Código | Auditoría |
|--------|--------|-----------|
| 317-324 | ProbarImapRequest con imap_* opcionales | Si el body trae host, user y password, se usa; si no, se usa la config de BD. |
| 326-384 | Si payload completo, cfg desde payload; si no, _load_email_config_from_db y cfg = stub; valida imap_host, imap_user, imap_password (no ***); test_imap_connection real; return success, mensaje, carpetas_encontradas si ok | Prueba IMAP real. Correcto. |

---

## 4. Servicio frontend: notificacionService.ts (EmailConfigService)

| Líneas | Método | Auditoría |
|--------|--------|-----------|
| 369 | baseUrl = '/api/v1/configuracion' | Correcto (relativo al proxy/base del frontend). |
| 371-373 | obtenerConfiguracionEmail() → GET email/configuracion | Correcto. |
| 375-388 | actualizarConfiguracionEmail(config) → PUT email/configuracion, timeout 60000 | Correcto. |
| 390-396 | probarConfiguracionEmail(...) → POST email/probar con email_destino, subject, mensaje, email_cc | Body en params; backend espera ProbarEmailRequest. Correcto. |
| 400-406 | obtenerConfiguracionEnvios() → GET notificaciones/envios | Correcto. |
| 404-406 | actualizarConfiguracionEnvios(config) → PUT notificaciones/envios | Correcto. |
| 408-418 | verificarEstadoConfiguracionEmail() → GET email/estado | Tipo de retorno incluye conexion_smtp; el backend no devuelve success real en conexion_smtp (solo mensaje). Tipo algo optimista pero funcional. |
| 420-433 | probarConfiguracionImap(imapConfig) → POST email/probar-imap, timeout 60000 | Correcto. |

---

## 5. Validación backend: email_config_validacion.py

| Líneas | Código | Auditoría |
|--------|--------|-----------|
| 14-21 | SMTP_PUERTOS_PERMITIDOS (587, 465), IMAP (993, 143), EMAIL_REGEX | Estándar Gmail. |
| 24-31 | _validar_formato_email | Longitud máx 254; regex. Correcto. |
| 34-51 | validar_emails_lista (tickets_notify_emails) | Split por coma; valida cada uno; devuelve (ok, validos) o (False, errores). Correcto. |
| 54-121 | validar_config_email_para_guardar | Obligatorios: smtp_host, smtp_user, from_email (y formato); puerto SMTP numérico y para Gmail 587/465; modo_pruebas → email_pruebas obligatorio y válido; tickets_notify_emails si existe; IMAP opcional con puerto y formato usuario. Devuelve (True, []) o (False, errores). Usado en PUT antes de persistir. Correcto. |

---

## 6. email_config_holder.py (resumen)

| Funcionalidad | Auditoría |
|---------------|-----------|
| sync_from_db() | Carga desde tabla configuracion, desencripta campos sensibles, update_from_api. Usado por get_smtp_config y por send_email. Correcto. |
| get_smtp_config() | Llama sync_from_db(); devuelve config SMTP; si no hay smtp_user en _current usa settings. Correcto. |
| update_from_api(data) | Llamado desde PUT después de persistir; actualiza _current con los campos conocidos. Correcto. |
| prepare_for_db_storage | Encripta smtp_password e imap_password; guarda en *_encriptado; pone valor en claro a None. Usado en _persist_email_config. Correcto. |
| get_modo_pruebas_email() | Prioridad notificaciones_envios luego email_config; devuelve (modo, list_of_emails). Correcto. |
| get_email_activo(), get_email_activo_servicio() | Master y por-servicio; sync_from_db antes. Los toggles por servicio están comentados en frontend pero el backend y holder los soportan. Correcto. |

---

## 7. Resumen de hallazgos

### 7.1 Correcto y coherente

- Ruta `/pagos/configuracion?tab=email` → `emailConfig` → `ConfigEmailTab` → `EmailConfig`.
- Protección admin en la ruta de configuración.
- GET/PUT config, GET estado, POST probar, POST probar-imap usan BD y, donde aplica, encriptación y enmascaramiento.
- Validación en frontend (puedeGuardar) y en backend (validar_config_email_para_guardar).
- Sincronización from_email/smtp_user y modo_pruebas/email_pruebas con notificaciones/envios.
- Contraseñas no se sobrescriben con ***; aviso al usuario cuando la contraseña no se actualizó.
- Prueba SMTP e IMAP reales en backend; timeouts 60s en frontend para PUT y probar-imap.

### 7.2 Mejoras menores (no bloqueantes)

1. **EmailConfig.tsx ~458:** Corregido: carácter U+008F en el texto “El sistema NO enviará…”.
2. **EmailConfig.tsx ~268:** Corregido: typo “CONDICIóN” en comentario.
3. **EmailConfig.tsx:** Unificar lógica de “puede guardar” y “campos faltantes” en una sola función para evitar que puedan divergir (pendiente).
4. **Configuracion.tsx:** Si se desea feedback de “Verificando estado…”, usar el estado `verificandoEstado` en `verificarEstadoGoogle()` (actualmente se setea pero no se muestra en UI) (pendiente).

### 7.3 Código comentado

- **EmailConfig.tsx 458-479:** Bloque “Email por servicio” (toggles por tipo de notificación) está comentado. Si no se va a usar, eliminar; si se va a activar, descomentar y asegurar que los `serviceKeys` se persistan y muestren correctamente.

### 7.4 GET /estado

- No realiza prueba SMTP real; solo comprueba que existan host, user y password. La “vinculación” real se confirma con “Enviar Email de Prueba” o tras guardar (el frontend luego llama a GET /estado y verificarEstadoGoogle). Documentado en auditoría; comportamiento aceptable.

---

## 8. Flujo de datos resumido

```
Usuario abre /pagos/configuracion?tab=email
  → Configuracion (tab=email → seccionActiva=emailConfig)
  → ConfigEmailTab → EmailConfig

Al montar EmailConfig:
  → GET /api/v1/configuracion/email/configuracion  (cargar formulario)
  → GET /api/v1/configuracion/notificaciones/envios (sincronizar modo_pruebas/email_pruebas)
  → GET /api/v1/configuracion/email/estado         (estado vinculación / mensajes)
  → listarNotificaciones(1,10)                     (envíos recientes)

Al guardar:
  → PUT /api/v1/configuracion/email/configuracion (body: configCompleta)
  → Backend: validar_config_email_para_guardar → update_from_api → _persist_email_config (BD)
  → Frontend: PUT notificaciones/envios (modo_pruebas, email_pruebas)
  → cargarConfiguracion() + verificarEstadoGoogle() (GET estado)

Al “Enviar Email de Prueba”:
  → POST /api/v1/configuracion/email/probar (email_destino, subject, mensaje, email_cc)
  → Backend: get_smtp_config() → send_email(...)

Al “Probar conexión IMAP”:
  → POST /api/v1/configuracion/email/probar-imap (imap_* del formulario o BD)
```

---

*Auditoría realizada sobre el código del repositorio en la ruta indicada; no se inspeccionó el sitio desplegado en vivo.*
