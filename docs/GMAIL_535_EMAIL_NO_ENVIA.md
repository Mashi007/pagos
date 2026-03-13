# Gmail 535: "Username and Password not accepted" – el correo no se envía

## Qué aparece en los logs

```
SMTPAuthenticationError: (535, b'5.7.8 Username and Password not accepted...')
[notif_envio_email] Email fallido ... error=Usuario o contraseña no aceptados. Gmail personal: usa Contraseña de aplicación...
```

La conexión SMTP a `smtp.gmail.com:587` funciona, pero **Gmail rechaza el usuario y la contraseña** (código 535). Por eso los correos de notificaciones fallan.

---

## Causa

Gmail ya **no permite** iniciar sesión con la contraseña normal de la cuenta en aplicaciones externas, salvo que uses:

- **Cuenta personal (@gmail.com):** contraseña de aplicación (App Password).
- **Google Workspace:** a veces la contraseña normal sirve; si no, el admin puede permitir “aplicaciones menos seguras” o usar OAuth.

Si en **Configuración > Email** tienes puesta la contraseña normal de Gmail, recibirás 535.

---

## Solución (cuenta Gmail personal)

1. Activar **verificación en dos pasos** en la cuenta Google:
   - https://myaccount.google.com/security  
   - “Verificación en dos pasos” → Activar.

2. Crear una **contraseña de aplicación**:
   - https://myaccount.google.com/apppasswords  
   - (Si no ves “Contraseñas de aplicaciones”, confirma que la verificación en dos pasos está activa.)
   - Selecciona “Correo” y el dispositivo “Otro” (nombre tipo “RapiCredit”).
   - Google te muestra una contraseña de 16 caracteres (por ejemplo `abcd efgh ijkl mnop`).

3. En la app (**Configuración > Email**):
   - **Usuario SMTP:** tu correo (ej. `notificaciones@rapicreditca.com` o la cuenta Gmail que uses).
   - **Contraseña SMTP:** la **contraseña de aplicación** de 16 caracteres (puedes pegarla sin espacios: `abcdefghijklmnop`).
   - Guardar.

4. Volver a lanzar el envío de notificaciones; el login SMTP debería aceptarse y los correos enviarse.

---

## Si usas Google Workspace (cuenta corporativa)

- Prueba primero con la **contraseña normal** de la cuenta; en muchos dominios sigue funcionando.
- Si también da 535:
  - El administrador del dominio puede tener bloqueado el acceso SMTP o “aplicaciones menos seguras”.
  - Opciones: que el admin permita SMTP para esa cuenta, o usar también **contraseña de aplicación** (si el Workspace lo permite): misma cuenta Google → Seguridad → Verificación en dos pasos → Contraseñas de aplicaciones.

---

## Resumen

| Tipo de cuenta        | Qué poner en “Contraseña SMTP”                         |
|-----------------------|--------------------------------------------------------|
| Gmail personal        | Contraseña de aplicación (no la contraseña normal)   |
| Google Workspace      | Probar contraseña normal; si falla, App Password o admin |

Enlace oficial: [Contraseñas de aplicaciones (Google)](https://support.google.com/accounts/answer/185833).

---

## Plantilla HTML no se ve / correo en texto plano

Si el correo llega en texto plano en lugar de con la plantilla HTML (tablas, formato):

- La plantilla guardada en **Configuración > Notificaciones > Plantillas** (cuerpo del email) debe estar en **HTML** (con etiquetas como `<table>`, `<div>`, `<p>`, etc.), no solo texto.
- El backend envía como HTML cuando detecta esas etiquetas en el cuerpo. Para el caso "Retrasadas" y otros, la plantilla asignada por tipo puede ser COBRANZA (tabla de cuotas) o cualquier plantilla cuyo cuerpo sea HTML.

## Adjuntos que no llegan

- **"Adjunto por caso ... no encontrado"**  
  Los PDF de "Documentos PDF anexos" se leen desde disco. En **Render el disco es efímero**: tras cada deploy la carpeta se vacía. Opciones: (1) Usar **disco persistente** de Render para esa ruta; (2) Guardar PDF en BD o S3 (requiere cambio de código).
- **Carta de cobranza (PDF generado)**  
  Si en Envíos por tipo tienes **"Incluir PDF anexo"**, se genera y adjunta `Carta_Cobranza.pdf`; no depende de disco. Si no está marcado, solo se usan adjuntos fijos (que fallan en Render sin disco persistente).

## Otros avisos que suelen salir en los mismos logs

- **WhatsApp "Status: failed"**  
  La API devuelve 200 pero Meta luego informa el mensaje como “failed”. Puede deberse a número inválido, usuario bloqueado, plantilla no aprobada o restricciones del negocio. Revisar en Meta Business Suite / webhooks el motivo del fallo.

- **Adjuntos fijos "no encontrado" / "disco persistente"**  
  En Render el sistema de archivos es efímero. Los PDF subidos en “Documentos PDF anexos” se pierden al redesplegar. Para que persistan hace falta un almacenamiento persistente (por ejemplo disco persistente de Render o S3) y que la app guarde/lea los adjuntos allí; mientras tanto, hay que volver a subir los PDF tras cada deploy si se usan adjuntos fijos.
