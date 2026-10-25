# Límite diario de Gmail (550 5.4.5 Daily user sending limit exceeded)

Cuando en los logs aparece:

```text
SMTPDataError: (550, b'5.4.5 Daily user sending limit exceeded. For more information on Gmail...')
```

o el mensaje sanitizado **"Límite diario de envío de Gmail alcanzado"**, la cuenta SMTP (Gmail) ha superado el **límite de envíos por día** y rechaza nuevos correos hasta que se reinicia el contador (aprox. 24 h).

## Límites aproximados de Gmail

| Tipo de cuenta | Límite típico por día |
|----------------|------------------------|
| Gmail personal (gmail.com) | ~100–500 mensajes/día (variable) |
| Google Workspace | ~2.000/día por usuario (según plan) |

Referencia: [Límites de envío de Gmail](https://support.google.com/a/answer/166852).

## Qué está pasando en tu caso

- El flujo de **notificaciones de cobranza** (WhatsApp + email) intenta enviar un correo por cada ítem a notificar.
- En **modo pruebas** todos los envíos se redirigen a `notificaciones@rapicreditca.com`, pero **siguen contando para el límite** de la cuenta SMTP (la que envía, no el destino).
- Si el batch es grande (cientos o miles de ítems), en pocos minutos se alcanza el límite diario de esa cuenta Gmail y el resto de envíos fallan con 550 5.4.5.

## Opciones de solución

### 1. Esperar 24 horas

El límite se reinicia cada día (ventana de 24 h). Solo sirve como parche temporal.

### 2. Usar un proveedor de email transaccional (recomendado)

Para envíos masivos (notificaciones, cobranza, códigos de estado de cuenta), es mejor usar SMTP de un proveedor pensado para ello:

| Proveedor | Ventaja | Configuración |
|-----------|---------|----------------|
| **SendGrid** | Plan gratuito ~100/día; planes de pago por volumen | SMTP: `smtp.sendgrid.net`, puerto 587, usuario `apikey`, contraseña = API Key |
| **Mailgun** | Buen volumen en planes de pago | SMTP según región (ej. `smtp.mailgun.org`), usuario/contraseña de Mailgun |
| **Amazon SES** | Muy económico a gran escala | SMTP de SES en la consola AWS |
| **Resend** | Fácil de usar, buen free tier | SMTP con API key en dashboard |

En la aplicación: **Configuración > Email** → cambiar **Servidor SMTP**, **Usuario** y **Contraseña** por los del proveedor. El resto del flujo (notificaciones, estado de cuenta, etc.) sigue igual.

### 3. Reducir volumen de envíos por correo

- Programar menos envíos por día o enviar solo por WhatsApp cuando el volumen sea alto.
- En modo pruebas, limitar el tamaño del batch o desactivar el envío por email en notificaciones si solo se quiere probar WhatsApp.

### 4. Google Workspace

Si quieres seguir con Gmail, usar una cuenta **Google Workspace** (antes G Suite) aumenta el límite a ~2.000/día por usuario; aun así, para muchos cientos de notificaciones diarias un proveedor transaccional suele ser más adecuado.

## Logs útiles

Tras el cambio en el backend, cuando se detecta este error se escribe en log:

```text
LIMITE DIARIO GMAIL ALCANZADO: Gmail rechaza mas envios hasta mañana. Opciones: 1) Esperar 24h 2) Usar SMTP de proveedor transaccional ...
```

Así puedes identificar rápido la causa sin leer el traceback completo.
