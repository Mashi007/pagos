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
- El **webhook de WhatsApp** y el servicio (`whatsapp_service.py`) usan la config guardada en BD: antes de cada uso se llama a `sync_from_db()` en `app.core.whatsapp_config_holder`, que carga desde la tabla `configuracion`. Así Comunicaciones (envío/recepción, verificación del webhook, descarga de imágenes) usan la **configuración guardada en Configuración > WhatsApp**, con fallback a variables de entorno si no hay nada en BD.

**Resumen:** Comunicaciones está **integrada** con la configuración WhatsApp: muestra el estado, enlaza a Configuración > WhatsApp y el envío/recepción usan la config de BD (holder + sync_from_db), alineado con Email.

---

## 3. Configuración > Email y Configuración > WhatsApp

- **Email:** usada por Notificaciones (envío de correos), tickets (notificación por correo) y por la pestaña Configuración dentro de Notificaciones (enlace a Configuración > Email). **Integrada con envío real** vía `sync_from_db()` antes de cada `send_email()`.
- **WhatsApp:** usada por Comunicaciones (estado + enlace a Configuración > WhatsApp). Config guardada en BD; envío/recepción y webhook usan esa config vía `whatsapp_config_holder.sync_from_db()` antes de cada uso (fallback a .env si no hay config en BD).

---

## 4. Enlaces añadidos en el CRM

- **Notificaciones > Configuración:** card con texto "Los correos de notificaciones usan la configuración de Gmail/SMTP guardada en Configuración > Email" y enlace "Configurar en Configuración (Email)" → `/configuracion?tab=email`.
- **Comunicaciones:** card con "Configuración WhatsApp cargada" / "Configura WhatsApp y Email para enviar y recibir" y enlace "Configurar en Configuración (WhatsApp)" → `/configuracion?tab=whatsapp`.

Así, tanto Notificaciones como Comunicaciones quedan **articulados** con la configuración de Gmail y WhatsApp y con enlaces directos a donde se configuran.
