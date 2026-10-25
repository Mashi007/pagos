# Políticas de credenciales: Gmail y WhatsApp

Confirmación de que las credenciales ingresadas **no se vacían** y se cumplen las políticas de Gmail y WhatsApp.

---

## 1. Gmail (Email / SMTP e IMAP)

### Comportamiento en el backend

- **GET** `/api/v1/configuracion/email/configuracion`: las contraseñas **nunca** se envían al frontend. Se devuelven como `"***"` (smtp_password, imap_password).
- **PUT** `/api/v1/configuracion/email/configuracion`: si el frontend envía `smtp_password` o `imap_password` vacío o `"***"`, el backend **no sobrescribe** la contraseña ya guardada. Solo se actualiza cuando se envía una contraseña nueva real.
- **Persistencia**: la configuración (incluidas las contraseñas reales) se guarda en la tabla `configuracion` (clave `email_config`). Las credenciales no se pierden al reiniciar ni al redesplegar (si la BD persiste).

### Políticas Gmail aplicadas

- **Contraseña de aplicación (App Password)**: Gmail exige usar una contraseña de aplicación para SMTP/IMAP, no la contraseña de la cuenta. El backend no valida el formato; el usuario debe crearla en [Cuenta Google > Seguridad > Contraseñas de aplicación](https://myaccount.google.com/apppasswords).
- **SMTP**: puerto 587 (TLS) o 465 (SSL). El backend acepta `smtp_port` y `smtp_use_tls`.
- **IMAP**: puerto 993 (SSL) o 143 (STARTTLS). El backend acepta `imap_port` e `imap_use_ssl`.
- Las contraseñas **nunca** se registran en logs (solo se registran los nombres de los campos actualizados, no los valores).

**Código relevante:** `app/api/v1/endpoints/configuracion_email.py`  
- `_is_password_masked()`: considera vacío o `"***"` como enmascarado y no sobrescribe.  
- En GET se reemplaza el valor real por `"***"` antes de devolver la respuesta.

---

## 2. WhatsApp (Meta Business API)

### Comportamiento en el backend

- **GET** `/api/v1/configuracion/whatsapp/configuracion`: el `access_token` y el `webhook_verify_token` **nunca** se envían en claro; se devuelven como `"***"`.
- **PUT** `/api/v1/configuracion/whatsapp/configuracion`: si el frontend envía `access_token` o `webhook_verify_token` vacío o `"***"`, el backend **no sobrescribe** el valor ya guardado. Solo se actualiza cuando se envía un token nuevo real.
- **Persistencia**: la configuración WhatsApp (incluido el token real) se guarda en la tabla `configuracion` (clave `whatsapp_config`). Las credenciales no se pierden al reiniciar.

### Políticas WhatsApp aplicadas

- **Access Token**: token de larga duración de Meta (Facebook) para la API de WhatsApp Business. No se expone en respuestas GET ni se sobrescribe con valores enmascarados.
- **Webhook Verify Token**: token que Meta envía al verificar el webhook; debe coincidir con el configurado en el backend. Tampoco se expone ni se vacía por enmascarado.
- Las credenciales **nunca** se registran en logs (solo los nombres de campos).

**Código relevante:** `app/api/v1/endpoints/configuracion_whatsapp.py`  
- `_is_token_masked()`: mismo criterio que en email (vacío o `"***"` → no sobrescribir).  
- GET y respuesta del PUT enmascaran `access_token` y `webhook_verify_token` con `"***"`.

---

## Resumen

| Aspecto | Gmail (Email) | WhatsApp |
|--------|----------------|----------|
| Credenciales no se vacían al guardar | Sí: si se envía `***` o vacío, no se sobrescribe | Sí: mismo criterio para token y verify token |
| No se exponen en GET | Sí: contraseñas como `***` | Sí: tokens como `***` |
| Persistencia en BD | Sí: tabla `configuracion` | Sí: tabla `configuracion` |
| No se escriben en logs | Sí: solo nombres de campos | Sí: solo nombres de campos |

Las credenciales ingresadas se mantienen y se cumplen las políticas de no exposición y no vaciado por valores enmascarados en ambos casos.
