# Recomendaciones para asegurar el éxito del módulo Cobros (reporte de pago público e integración con Pagos)

**Objetivo:** Tras investigación del código, configuración y flujos, estas recomendaciones buscan maximizar la confiabilidad, la experiencia del cliente y la operación del módulo en producción.

---

## 1. Configuración y despliegue

### 1.1 Variables de entorno obligatorias

| Variable | Uso | Riesgo si falta |
|---------|-----|------------------|
| `GEMINI_API_KEY` | Comparación formulario vs imagen (100% → aprobado automático) | Todos los reportes van a **en_revision**; no hay fallo visible para el cliente, pero aumenta carga manual. |
| `DATABASE_URL` | Persistencia de reportes, clientes, préstamos | El reporte falla con error 500. |
| SMTP (`SMTP_HOST`, `SMTP_USER`, `SMTP_PASSWORD`, etc.) o configuración en **Configuración > Email** | Envío de recibo al aprobar y de correo al rechazar | Recibo/PDF se genera y guarda en BD, pero el cliente **no recibe el correo**; no hay notificación de fallo al operador. |

**Recomendación:**  
- Documentar en un checklist de despliegue (o en `.env.example` comentado) que el módulo Cobros requiere: `GEMINI_API_KEY`, BD y SMTP.  
  → **Implementado:** ver `docs/CHECKLIST_DESPLIEGUE_COBROS.md`.  
- En **health**: añadir un endpoint opcional `GET /api/v1/health/cobros` que verifique: BD accesible, `GEMINI_API_KEY` configurado (sin llamar a la API), y SMTP con credenciales no vacías. No exponer secretos.  
  → **Implementado:** `GET /api/v1/health/cobros` retorna `db_ok`, `gemini_configured`, `smtp_configured` (sin exponer secretos).

### 1.2 Gemini (cuotas y reintentos)

- El código ya usa reintentos ante 429 (rate limit) y devuelve `coincide_exacto: false` si Gemini no está configurado o falla.  
- **Recomendación:** En producción, configurar `GEMINI_API_KEY` desde el primer día. Si se usa plan gratuito, tener en cuenta límites de RPM; ante muchos reportes simultáneos, los excedentes irán a revisión manual (comportamiento seguro).  
- Opcional: registrar en logs o métricas cuántos reportes entran por “Gemini no configurado” o “error Gemini” para detectar problemas de configuración o cuota.

---

## 2. Correo electrónico

### 2.1 Fallo silencioso del envío

Hoy, si `send_email()` falla (SMTP mal configurado, red, etc.), el reporte se guarda como aprobado y el PDF se persiste en BD, pero el cliente no recibe el recibo y el backend no notifica al operador.

**Recomendación:**  
- Tras `send_email()` en `cobros_publico.py` (aprobado) y en `cobros.py` (aprobar/rechazar), comprobar el retorno `(ok, error_msg)`.  
- Si `ok` es False:  
  - **Aprobado (público):** mantener el estado aprobado y el PDF en BD; registrar en log con nivel ERROR e incluir `referencia_interna` y `error_msg`; opcionalmente guardar un flag o comentario en el registro (ej. `correo_enviado: false`) para que en Cobros admin se vea que hay que reenviar.  
  - **Aprobar/Rechazar (admin):** además de log, devolver en la respuesta del endpoint un aviso tipo `"mensaje": "Pago aprobado/rechazado, pero el correo no pudo enviarse. Reenvíe el recibo desde el detalle."` para que el usuario sepa que debe reenviar.  
- Opcional: cola de reintentos para envío de correo (segunda fase).

### 2.2 Modo pruebas

Si en **Configuración > Email** o notificaciones está activo el “modo pruebas”, los correos se redirigen al correo de pruebas.  
**Recomendación:** Comprobar en staging que el modo pruebas esté desactivado (o que el correo de pruebas sea el adecuado) antes de dar por válido el envío al cliente en producción.

---

## 3. Rate limiting (formulario público)

- Límites actuales: validar cédula 30/min por IP; enviar reporte 5/hora por IP.  
- El contador se guarda **en memoria** (dict por IP). En despliegues con varios workers o reinicios, el límite se reinicia.

**Recomendaciones:**  
- Para un solo worker (p. ej. Render con 1 instancia), el comportamiento es aceptable; documentar que tras despliegue o reinicio los contadores se reinician.  
- Si más adelante se usan varios workers, valorar un almacén compartido (Redis o BD) para el rate limit por IP, reutilizando la misma ventana temporal y máximo de intentos.  
- Mantener el mensaje claro en frontend ante 429 (“Demasiadas consultas…” / “límite de envíos por hora”), ya implementado.

---

## 4. Experiencia del cliente (frontend)

### 4.1 Errores no 200 en enviar reporte

Si el backend devuelve 400/500 con un body que no es JSON o con estructura distinta, `enviarReportePublico` hace `res.json()` y puede lanzar o no mostrar el mensaje del servidor.

**Recomendación:**  
- Comprobar `res.ok` antes de `res.json()`.  
- Si `!res.ok`: leer el body como texto, intentar `JSON.parse` para obtener `detail` o `error`; mostrar en toast el mensaje del backend o un mensaje genérico (“Error al enviar. Intente más tarde o contacte a …”).  
- Para 503 (servicio no disponible), mostrar un mensaje que indique “Servicio temporalmente no disponible” y, si se desea, el enlace/WhatsApp de contacto.  
→ **Implementado:** Manejo de `!res.ok`, respuesta no JSON y mensaje específico para 503 en `cobrosService.enviarReportePublico`.

### 4.2 Enlace público estable

- El link canónico del formulario termina en `/rapicredit` y está centralizado en `PUBLIC_REPORTE_PAGO_PATH`.  
**Recomendación:** Usar este mismo enlace en comunicaciones (SMS, correos, carteles): `https://rapicredit.onrender.com/pagos/rapicredit` (o el dominio definitivo). No difundir solo `/reporte-pago` para evitar tener dos URLs de referencia.

### 4.3 Accesibilidad y móvil

- Formulario por pasos con campos obligatorios y toasts por error.  
**Recomendación:** Revisar en móvil que el `input type="date"` abra el selector nativo y que los toasts no tapen botones críticos. Opcional: añadir `aria-live` en la zona de mensajes para lectores de pantalla.  
→ **Implementado:** Región `aria-live="polite"` con anuncio del paso actual en cada pantalla del formulario (ReportePagoPage).

---

## 5. Datos y consistencia

### 5.1 Cédula en BD (clientes)

- Búsquedas (cobros público, importar desde Cobros) usan cédula normalizada **sin guión** (ej. `V12345678`).  
**Recomendación:** Asegurar que en la tabla `clientes` la cédula se guarde de forma consistente (por ejemplo siempre sin guión, o normalizar en el mismo formato en todos los flujos de alta/actualización). Si ya hay datos con y sin guión, valorar una migración o una búsqueda que acepte ambas formas (por ejemplo con `REPLACE(cedula, '-', '')` en consultas).  
→ **Implementado:** En validar-cedula y enviar-reporte (cobros público) y en importar-desde-cobros (pagos) se usa búsqueda con `REPLACE(cedula, '-', '')` para aceptar cédula con o sin guión en BD.

### 5.2 Importar desde Cobros → Pagos

- Solo se importan reportes con estado **aprobado**; se aplican las mismas reglas que la carga masiva (documento único, 1 crédito activo por cédula, etc.). Los que no cumplen van a Revisar Pagos con observación “Cobros (reportados aprobados)”.  
**Recomendación:** Formar a operadores en que, tras “Importar reportados aprobados”, revisen el aviso de “X con error” y usen “Descargar Excel en revisión pagos” para corregir crédito o datos y luego “Mover a pagos” desde Revisar Pagos cuando corresponda.

---

## 6. Monitoreo y operación

### 6.1 Health y alertas

- `GET /api/v1/health/db` ya incluye tablas `pagos_reportados` y `usuarios`.  
**Recomendación:** Configurar alertas (Render, Uptime Robot, etc.) sobre:  
  - `GET /api/v1/health` (API viva).  
  - `GET /api/v1/health/db` (status distinto de "ok" o tablas faltantes).  
  - Opcional: `GET /api/v1/health/cobros` si se implementa (Gemini configurado + SMTP presente).

### 6.2 Logs útiles

- Ya se registran errores de Gemini y de envío de correo.  
**Recomendación:** Incluir en logs de Cobros (al menos en ERROR):  
  - `referencia_interna` cuando falle el envío del recibo (para poder reenviar desde admin).  
  - Tipo de error (Gemini no configurado, 429, timeout SMTP, etc.) para distinguir configuración de capacidad o red.

### 6.3 Revisión manual (en_revision)

- Los reportes que no coinciden 100% con Gemini aparecen en Cobros con estado “En revisión (manual)” y tienen los mismos botones (Aprobar / Rechazar).  
**Recomendación:** Definir un SLA interno (p. ej. revisar en_revision en menos de 24 h) y, si se desea, un pequeño dashboard o filtro por “en_revision” para no dejar reportes sin atender.

---

## 7. Seguridad (resumen)

- Formulario público: rate limit, honeypot, validación de archivo por magic bytes, sin auth.  
- Admin Cobros: bajo auth; mensaje de rechazo genérico (sin filtrar motivo interno al cliente).  
- Link público: una sola URL canónica (/rapicredit) reduce confusión y facilita bloqueos por lista blanca si en el futuro se restringe por origen.

**Recomendación:** Mantener el honeypot y el rate limit; no relajar límites sin valorar abuso (p. ej. bots probando cédulas). Si el formulario se publica en sitios muy visibles, considerar CAPTCHA en una segunda fase.

---

## 8. Resumen de acciones prioritarias

| Prioridad | Acción |
|-----------|--------|
| Alta | Configurar `GEMINI_API_KEY` y SMTP en producción antes de dar el link a clientes. |
| Alta | Revisar resultado de `send_email()` en aprobado/rechazo; log ERROR + mensaje al usuario si falla el envío. |
| Media | En frontend, manejar `!res.ok` en enviar reporte y mostrar mensaje del backend o genérico. |
| Media | Documentar en checklist de despliegue: GEMINI, SMTP, BD y, si aplica, modo pruebas desactivado. |
| Baja | Unificar formato de cédula en `clientes` o búsqueda que acepte con/sin guión. |
| Baja | Valorar health `/health/cobros` (Gemini + SMTP configurados) y alertas sobre health/db. |

Implementar las de prioridad alta y media da una base sólida para que el módulo Cobros funcione bien en producción y los clientes reciban el recibo o la notificación de rechazo de forma fiable.
