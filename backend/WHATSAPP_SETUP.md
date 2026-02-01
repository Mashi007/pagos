# 📱 Configuración de WhatsApp para Recibir Mensajes

Esta guía explica cómo configurar el sistema para recibir mensajes de WhatsApp usando Meta Business API.

## 📋 Requisitos Previos

1. **Cuenta de Meta Business** (Facebook Business)
2. **Aplicación creada en Meta Developers**
3. **WhatsApp Business API configurada**
4. **Número de teléfono verificado en Meta**

## 🔧 Pasos de Configuración

### 1. Configurar Variables de Entorno

Copia el archivo `.env.example` a `.env` y configura las siguientes variables:

```bash
# Token de verificación (puede ser cualquier string seguro)
WHATSAPP_VERIFY_TOKEN=mi_token_secreto_12345

# Access Token de Meta (obtener de Meta Developers)
WHATSAPP_ACCESS_TOKEN=tu_access_token_aqui

# Phone Number ID (obtener de Meta Developers)
WHATSAPP_PHONE_NUMBER_ID=tu_phone_number_id_aqui
```

### 2. Obtener Credenciales de Meta

1. Ve a [Meta Developers](https://developers.facebook.com/)
2. Crea o selecciona tu aplicación
3. Agrega el producto "WhatsApp"
4. Obtén:
   - **Access Token**: En "WhatsApp" > "API Setup"
   - **Phone Number ID**: En "WhatsApp" > "API Setup"
   - **Business Account ID**: En "WhatsApp" > "API Setup"

### 3. Configurar el Webhook en Meta

1. Ve a tu aplicación en Meta Developers
2. Navega a **WhatsApp** > **Configuration**
3. En la sección **Webhook**, haz clic en **Edit**
4. Configura:
   - **Callback URL**: `https://tu-dominio.com/api/v1/whatsapp/webhook`
   - **Verify Token**: El mismo valor que `WHATSAPP_VERIFY_TOKEN` en tu `.env`
5. Haz clic en **Verify and Save**

### 4. Suscribirse a Eventos

En la misma página de configuración del webhook, suscríbete a:
- ✅ **messages** (para recibir mensajes entrantes)
- ✅ **message_status** (opcional, para recibir estados de mensajes)

## 🧪 Probar la Configuración

### Verificación del Webhook

Meta enviará un GET request a tu endpoint para verificar:

```
GET /api/v1/whatsapp/webhook?hub.mode=subscribe&hub.challenge=123456789&hub.verify_token=tu_token
```

Si todo está configurado correctamente, deberías recibir el `hub.challenge` como respuesta.

### Enviar un Mensaje de Prueba

1. Envía un mensaje de WhatsApp al número configurado en Meta
2. Revisa los logs de tu aplicación
3. Deberías ver el mensaje procesado

## 📡 Endpoints Disponibles

### GET `/api/v1/whatsapp/webhook`
Verificación del webhook por Meta.

**Parámetros de Query:**
- `hub.mode`: Debe ser "subscribe"
- `hub.challenge`: Código de desafío de Meta
- `hub.verify_token`: Token de verificación

**Respuesta:**
- `200`: Retorna el `hub.challenge` si el token es válido
- `403`: Token inválido

### POST `/api/v1/whatsapp/webhook`
Recibe mensajes entrantes de WhatsApp.

**Body:** Payload JSON de Meta

**Respuesta:**
```json
{
  "success": true,
  "message": "Webhook procesado. 1 mensaje(s) procesado(s)",
  "message_id": "wamid.xxx"
}
```

## 🔍 Estructura de Mensajes

Los mensajes recibidos tienen la siguiente estructura:

```json
{
  "object": "whatsapp_business_account",
  "entry": [
    {
      "id": "entry_id",
      "changes": [
        {
          "value": {
            "messaging_product": "whatsapp",
            "metadata": {
              "display_phone_number": "+1234567890",
              "phone_number_id": "phone_number_id"
            },
            "contacts": [
              {
                "profile": {
                  "name": "Nombre Usuario"
                },
                "wa_id": "1234567890"
              }
            ],
            "messages": [
              {
                "from": "1234567890",
                "id": "wamid.xxx",
                "timestamp": "1234567890",
                "type": "text",
                "text": {
                  "body": "Hola, este es un mensaje de prueba"
                }
              }
            ]
          }
        }
      ]
    }
  ]
}
```

## 🛠️ Desarrollo Local

Para probar localmente, puedes usar herramientas como:

1. **ngrok** para exponer tu servidor local:
   ```bash
   ngrok http 8000
   ```
   Usa la URL de ngrok como Callback URL en Meta.

2. **Postman** para simular webhooks de Meta

## 📝 Logs

El sistema registra todos los mensajes recibidos. Revisa los logs para:
- Ver mensajes procesados
- Detectar errores
- Monitorear el funcionamiento

## ⚠️ Notas Importantes

1. **Seguridad**: Nunca compartas tu `WHATSAPP_VERIFY_TOKEN` o `WHATSAPP_ACCESS_TOKEN`
2. **HTTPS**: Meta requiere HTTPS para webhooks en producción
3. **Rate Limits**: Meta tiene límites de tasa, revisa la documentación oficial
4. **Token Expiration**: Los Access Tokens pueden expirar, implementa renovación si es necesario

## 🔗 Referencias

- [Meta WhatsApp Business API Docs](https://developers.facebook.com/docs/whatsapp)
- [Webhook Setup Guide](https://developers.facebook.com/docs/whatsapp/cloud-api/webhooks)

## 🐛 Solución de Problemas

### El webhook no se verifica
- Verifica que `WHATSAPP_VERIFY_TOKEN` coincida exactamente
- Asegúrate de que el endpoint esté accesible públicamente
- Revisa los logs del servidor

### No se reciben mensajes
- Verifica que estés suscrito a "messages" en Meta
- Revisa que el número esté verificado en Meta
- Comprueba los logs para errores

### Error 403 en verificación
- El token de verificación no coincide
- Verifica la configuración en `.env`
