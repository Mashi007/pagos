# Integración: Configuración Gmail/WhatsApp con CRM (Notificaciones y Comunicaciones)

Resumen de cómo está integrada la configuración de Gmail y WhatsApp con los componentes del CRM (Notificaciones y Comunicaciones).

---

## 1. Notificaciones (CRM)

### Frontend

- **Página:** `Notificaciones` (`/notificaciones`) con pestañas: Faltan 5/3/1 días, Hoy vence, 61+ días de mora, **Configuración**.
- **Pestaña Configuración:** renderiza el componente `ConfiguracionNotificaciones`, que:
  - Carga y guarda la **configuración de envíos** (habilitar/deshabilitar por tipo, CCO) vía `emailConfigService.obtenerConfiguracionEnvios()` y `actualizarConfiguracionEnvios()` → API `GET/PUT /api/v1/configuracion/notificaciones/envios`.
  - Muestra un **enlace a Configuración > Email** para configurar Gmail/SMTP (los correos de notificaciones usan esa config).
- **Envío de correos:** el botón "Enviar correos" en cada pestaña llama a `notificacionService.enviarNotificacionesPrevias()`, `enviarNotificacionesDiaPago()`, `enviarNotificacionesMora61()` → API `POST /api/v1/notificaciones-previas/enviar`, etc.

### Backend

- Los endpoints de envío (`notificaciones_tabs.py`) usan `send_email()` de `app.core.email`.
- **Integración con config guardada:** antes de cada envío, `send_email()` llama a `sync_from_db()` en `email_config_holder`, que **carga la configuración de email desde la tabla `configuracion`** (clave `email_config`). Así, los correos de Notificaciones usan la **configuración de Gmail/SMTP guardada en Configuración > Email**, no solo .env.

**Resumen:** La configuración de Gmail (Configuración > Email) está **integrada** con Notificaciones: los correos se envían con la config guardada en BD. La pestaña Configuración de Notificaciones gestiona envíos por tipo (previas, día pago, etc.) y enlaza a Configuración > Email para SMTP.

---

## 2. Comunicaciones (CRM)

### Frontend

- **Página:** `ComunicacionesPage` (`/comunicaciones` o `/crm/comunicaciones`) que:
  - Obtiene la **configuración WhatsApp** con `whatsappConfigService.obtenerConfiguracionWhatsApp()` → `GET /api/v1/configuracion/whatsapp/configuracion`.
  - Muestra si WhatsApp está configurado (`configurada`) y un **enlace a Configuración > WhatsApp** ("Configurar en Configuración (WhatsApp)").
  - Renderiza el componente `Comunicaciones` (lista de conversaciones, mensajes, etc.).

### Backend

- La configuración WhatsApp se persiste en BD (clave `whatsapp_config`) y se sirve enmascarada (tokens como `***`).
- El **webhook de WhatsApp** y el servicio de envío (`whatsapp_service.py`) leen actualmente el token desde **settings** (`.env`). Para que Comunicaciones use al 100% la config guardada en Configuración > WhatsApp habría que hacer que el servicio de WhatsApp cargue el token desde la BD (similar a `sync_from_db` para email); por ahora la config en BD se usa para mostrar estado en la UI y para guardar/editar desde Configuración.

**Resumen:** Comunicaciones está **conectada** a la configuración WhatsApp: muestra el estado y enlaza a Configuración > WhatsApp. El envío/recepción de mensajes por WhatsApp en el backend sigue usando preferentemente las variables de entorno; la config en BD es la fuente de verdad para la UI y para futura ampliación.

---

## 3. Configuración > Email y Configuración > WhatsApp

- **Email:** usada por Notificaciones (envío de correos), tickets (notificación por correo) y por la pestaña Configuración dentro de Notificaciones (enlace a Configuración > Email). **Integrada con envío real** vía `sync_from_db()` antes de cada `send_email()`.
- **WhatsApp:** usada por Comunicaciones (estado + enlace a Configuración > WhatsApp). Config guardada en BD; envío/recepción en backend puede seguir usando .env hasta que se añada carga desde BD en el servicio de WhatsApp.

---

## 4. Enlaces añadidos en el CRM

- **Notificaciones > Configuración:** card con texto "Los correos de notificaciones usan la configuración de Gmail/SMTP guardada en Configuración > Email" y enlace "Configurar en Configuración (Email)" → `/configuracion?tab=email`.
- **Comunicaciones:** card con "Configuración WhatsApp cargada" / "Configura WhatsApp y Email para enviar y recibir" y enlace "Configurar en Configuración (WhatsApp)" → `/configuracion?tab=whatsapp`.

Así, tanto Notificaciones como Comunicaciones quedan **articulados** con la configuración de Gmail y WhatsApp y con enlaces directos a donde se configuran.
