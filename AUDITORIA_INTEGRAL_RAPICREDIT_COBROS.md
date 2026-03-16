# Auditoría integral: RapiCredit Cobros (Reporte de pago público)

**URL auditada:** https://rapicredit.onrender.com/pagos/rapicredit-cobros  
**Fecha:** 16 de marzo de 2026  
**Alcance:** Formulario público de reporte de pago (sin login), backend `/api/v1/cobros/public`, frontend `ReportePagoPage`, seguridad, UX y mejoras.

---

## 1. Resumen ejecutivo

El flujo **RapiCredit Cobros** permite a los clientes reportar un pago (cédula → datos del pago → institución → fecha/monto → número de operación → comprobante → confirmación) sin autenticación. La auditoría revisa seguridad, validaciones, rate limiting, accesibilidad, UX y posibles mejoras.

**Conclusión:** El flujo está bien estructurado, con medidas de seguridad adecuadas (rate limit, honeypot, validación por magic bytes, límites de longitud). Se identifican mejoras en SEO/meta para la ruta pública, consistencia de validación cédula front/back, y algunas mejoras menores de UX y resiliencia.

---

## 2. Arquitectura revisada

| Capa | Ubicación | Descripción |
|------|-----------|-------------|
| Ruta pública | `App.tsx`: `/rapicredit-cobros`, `/reporte-pago` | Ambas sirven `ReportePagoPage`; redirección `/rapicredit` → `/rapicredit-cobros` |
| Página | `frontend/src/pages/ReportePagoPage.tsx` | Flujo en pasos (0–8), validación en cliente, honeypot, notificaciones |
| Servicio | `frontend/src/services/cobrosService.ts` | `validarCedulaPublico`, `enviarReportePublico` (sin token; 429/503 manejados) |
| API pública | `backend/app/api/v1/endpoints/cobros_publico.py` | `GET /validar-cedula`, `POST /enviar-reporte` (sin auth) |
| Rate limit | `backend/app/core/cobros_public_rate_limit.py` | 30 req/min validar cédula, 5 envíos/hora por IP (memoria o Redis) |

---

## 3. Seguridad

### 3.1 Implementado correctamente

- **Rate limiting por IP**
  - Validar cédula: 30 solicitudes/minuto.
  - Enviar reporte: 5 por hora.
  - Soporte Redis opcional para entornos multi-instancia.
- **Honeypot anti-bot:** Campo `contact_website` (oculto, `tabIndex={-1}`, `aria-hidden`). Backend rechaza si viene con valor; front envía siempre vacío.
- **Validación de archivo en backend:** Magic bytes (JPEG, PNG, PDF); rechazo de Excel y tipos no permitidos; tamaño máx. 5 MB.
- **Sanitización de nombre de archivo:** `_sanitize_filename` evita path traversal y caracteres no seguros.
- **Límites de longitud:** Cédula, institución, número de operación, observación acotados; evita abuso e inyección.
- **Sin autenticación en endpoints públicos:** Diseño explícito; no se expone información de otros clientes (solo nombre/email del titular de la cédula consultada).
- **CORS:** Configurado desde `settings.cors_origins_list`; credenciales permitidas donde aplica.

### 3.2 Recomendaciones

- **CSP (index.html):** `connect-src` incluye `https://rapicredit.onrender.com` y `https://pagos-f2qf.onrender.com`. Mantener solo los orígenes necesarios y revisar si en producción todo va al mismo dominio (evitar abrir de más).
- **Headers de seguridad:** Valorar añadir en el servidor (Render/proxy) headers como `X-Content-Type-Options: nosniff`, `X-Frame-Options`, `Referrer-Policy` para la ruta pública.
- **Logs de honeypot:** El backend ya registra `[COBROS_PUBLIC] Honeypot activado desde IP %s`; mantener y revisar en caso de picos de bots.

---

## 4. Validaciones frontend vs backend

### 4.1 Alineación actual

- **Cédula:** Front: V/E/G/J + 6–11 dígitos, normalización sin puntos/guiones. Back: `validate_cedula` (módulo validadores) + lookup en BD (Cliente + Préstamo). Coinciden en formato; backend además exige que exista cliente con préstamo.
- **Monto:** Front: 0.01–999_999_999.99. Back: `monto > 0` y `monto > 999_999_999.99` rechazado. Alineados.
- **Fecha:** Front: obligatoria, no futura. Back: `fecha_pago > date.today()` rechazado. Alineados.
- **Archivo:** Front: JPG/PNG/PDF, máx. 5 MB. Back: mismos tipos por content-type + magic bytes, máx. 5 MB. Backend más estricto (evita spoofing).
- **Institución / número de operación:** Longitud máx. 100 en ambos.

### 4.2 Observación

- Comentario en frontend menciona "V/E/J/**Z**" en cédula; el regex y backend usan **V, E, G, J**. Corregir el comentario a "V, E, G o J" para evitar confusión (la Z no es estándar en cédulas venezolanas en este flujo).

---

## 5. Experiencia de usuario (UX)

### 5.1 Fortalezas

- Flujo por pasos claro (bienvenida → cédula → datos → institución → fecha/monto → número operación → comprobante → confirmación → éxito).
- Mensajes de error concretos por campo (validación en cliente y respuestas del API).
- Notificaciones (éxito/error) con cierre manual y auto-dismiss 10 s; `role="alert"` y accesibles.
- Botones "Atrás" en cada paso; "Ingresar otro pago" y "Termina" en pantalla de éxito.
- Área de toque adecuada (`min-h-[44px]`, `min-w-[44px]`, `touch-manipulation`).
- Referencia interna mostrada en paso 8; texto sobre envío de recibo por correo y contacto WhatsApp.

### 5.2 Mejoras sugeridas

- **Paso 0 (bienvenida):** Incluir título semántico `<h1>` (por ejemplo "Reporte de pago") para SEO y a11y; el contenido actual ya describe el proceso.
- **Carga durante envío:** El botón muestra "Enviando..."; opcionalmente deshabilitar también "No, editar" durante el envío para evitar doble envío por doble clic.
- **Errores de red:** Si `enviarReportePublico` falla por red (no 429/503), el `catch` muestra `e?.message`; podría mostrarse un mensaje genérico amigable ("Revisa tu conexión e intenta de nuevo") y dejar el detalle técnico para logs.
- **Paso 8 – Copiar referencia:** El bloque con `#referencia` tiene `title="Copiar"` pero no hay `onClick` para copiar al portapapeles; añadir botón "Copiar referencia" mejoraría la usabilidad.

---

## 6. Accesibilidad (a11y)

- **Anuncios por paso:** `aria-live="polite"`, `aria-atomic="true"`, `sr-only` con `stepAnnouncements` por paso. Correcto.
- **Honeypot:** `aria-hidden="true"`, fuera del flujo de foco; adecuado.
- **Alertas:** NotificationBanner con `role="alert"` y botón de cerrar con `aria-label="Cerrar notificación"`.
- **Enlaces:** WhatsApp y correo con texto claro; `target="_blank"` con `rel="noopener noreferrer"` en WhatsApp.
- **Recomendación:** Asegurar que cada paso tenga un encabezado de nivel apropiado (p. ej. `h1` en bienvenida, `h2` en pasos) para estructura de encabezados coherente.

---

## 7. SEO y meta para la ruta pública

- **Situación actual:** El título y la descripción del sitio son genéricos en `index.html` ("RAPICREDIT - Sistema de Préstamos y Cobranza" y "Sistema de Préstamos y Cobranza RapiCredit"). La ruta `/pagos/rapicredit-cobros` es SPA; el contenido "Reporte de pago", "Bienvenido", etc., se renderiza en cliente.
- **Recomendación:** Para mejorar SEO y compartido en redes de la URL pública:
  - Usar React Helmet (o similar) en `ReportePagoPage` para esta ruta: `<title>Reporte de pago | RapiCredit</title>` y `<meta name="description" content="Reporte su pago de forma segura. Ingrese su cédula, datos del pago y comprobante." />`.
  - Si el despliegue permite, valorar pre-render o SSR solo para esta ruta para que crawlers vean el contenido sin ejecutar JS.

---

## 8. Backend y resiliencia

- **BD:** Uso de `get_db`, transacciones con rollback en error, reintento por duplicado de `referencia_interna`.
- **Gemini:** Si `GEMINI_API_KEY` no está configurado, el reporte se marca para revisión manual sin fallar el flujo.
- **Correo:** Si el envío del recibo falla, se registra en logs y la respuesta al usuario sigue siendo éxito (el reporte ya está guardado).
- **429/503:** El frontend muestra mensajes claros y sugiere WhatsApp en 503; adecuado para usuario final.

### Recomendación

- En `enviar_reporte_publico`, si `compare_form_with_image` (Gemini) lanza excepción no controlada, el `except Exception` actual devuelve mensaje genérico; está bien. Opcional: envolver solo la llamada a Gemini en try/except para que un fallo de API externa no haga rollback del `PagoReportado` ya persistido (hoy todo el bloque está en un único try; si Gemini falla después del commit del primer bloque, el estado podría quedar a medias). Revisar orden de operaciones: commit del registro antes de Gemini y luego actualización de estado y PDF en un segundo commit podría aislar fallos de Gemini.

---

## 9. Checklist de mejoras prioritarias

| # | Mejora | Prioridad | Esfuerzo |
|---|--------|------------|----------|
| 1 | Corregir comentario frontend: "V/E/J/Z" → "V, E, G o J" en validación cédula | Baja | Bajo |
| 2 | Añadir `<h1>` en paso 0 (bienvenida) y estructura de encabezados en pasos | Media | Bajo |
| 3 | Meta/SEO específicos para `/rapicredit-cobros` (title + description vía Helmet o similar) | Media | Bajo |
| 4 | Botón "Copiar referencia" en pantalla de éxito (paso 8) | Media | Bajo |
| 5 | Deshabilitar "No, editar" mientras `loading` en paso 7 | Baja | Bajo |
| 6 | Mensaje de error amigable en catch de red en `handleEnviar` | Baja | Bajo |
| 7 | Headers de seguridad (X-Content-Type-Options, X-Frame-Options) en servidor/proxy | Media | Depende infra |
| 8 | Revisar orden commit/Gemini en backend para aislar fallos de API externa | Baja | Medio |

---

## 10. Conclusión

El flujo de **RapiCredit Cobros** en https://rapicredit.onrender.com/pagos/rapicredit-cobros está bien implementado en seguridad (rate limit, honeypot, validación de archivos, límites), alineación front/back y accesibilidad básica. Las mejoras propuestas son sobre todo de pulido: SEO/meta para la URL pública, pequeños ajustes de UX (copiar referencia, evitar doble clic al enviar, mensaje de error de red) y corrección de comentarios. No se detectan vulnerabilidades críticas en el flujo auditado.
