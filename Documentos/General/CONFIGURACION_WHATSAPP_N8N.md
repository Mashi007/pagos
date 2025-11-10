# 📱 Configuración de WhatsApp Webhook para n8n

## 🎯 Objetivo

Configurar el webhook de WhatsApp Business API para trabajar con n8n, permitiendo:
- Recibir eventos de Meta WhatsApp (mensajes, estados, errores)
- Procesar mensajes recibidos de clientes
- Actualizar estados de notificaciones automáticamente
- Integrar con workflows de n8n para automatizaciones avanzadas

---

## 📋 Requisitos Previos

1. ✅ WhatsApp Business API configurado en Meta Developers
2. ✅ `webhook_verify_token` configurado en la aplicación
3. ✅ n8n instalado y accesible (local o cloud)
4. ✅ Acceso a la configuración de Meta Developers

---

## 🔧 Opción 1: n8n como Intermediario (Recomendado)

Esta opción permite usar n8n para procesar eventos antes de enviarlos al sistema.

### Paso 1: Crear Workflow en n8n

1. Abre n8n y crea un nuevo workflow
2. Agrega un nodo **"Webhook"** como trigger
3. Configura el webhook:
   - **HTTP Method**: `GET` y `POST`
   - **Path**: `/whatsapp` (o el que prefieras)
   - **Response Mode**: `Response Node`
   - **Authentication**: Ninguna (Meta maneja su propia autenticación)

### Paso 2: Configurar Verificación (GET)

Agrega un nodo **"IF"** después del Webhook:

- **Condición**: `{{ $json.query['hub.mode'] }}` equals `subscribe`
- **Si es verdadero**: Agrega un nodo **"Respond to Webhook"** que retorne:
  ```json
  {{ $json.query['hub.challenge'] }}
  ```
- **Si es falso**: Continúa al procesamiento normal

### Paso 3: Procesar Eventos (POST)

Para eventos POST (mensajes y estados):

1. Agrega un nodo **"HTTP Request"** que envíe al endpoint del sistema:
   - **Method**: `POST`
   - **URL**: `https://tu-dominio.com/api/v1/whatsapp/webhook`
   - **Body**: `{{ $json.body }}`
   - **Headers**: 
     - `Content-Type: application/json`
     - `X-Hub-Signature-256: {{ $json.headers['x-hub-signature-256'] }}` (si existe)

2. Opcional: Agrega nodos de procesamiento antes de enviar:
   - Filtrar eventos específicos
   - Transformar datos
   - Agregar lógica de negocio

### Paso 4: Configurar en Meta Developers

1. Ve a [Meta Developers](https://developers.facebook.com/apps)
2. Selecciona tu app → **WhatsApp** → **Configuration**
3. En **Webhook**, configura:
   - **Callback URL**: `https://tu-n8n-instance.com/webhook/whatsapp`
   - **Verify Token**: (el mismo que configuraste en la aplicación)
4. Haz clic en **Verify and Save**
5. Suscríbete a los eventos:
   - ✅ `messages` (mensajes recibidos)
   - ✅ `messaging_postbacks` (botones interactivos)

---

## 🔧 Opción 2: Endpoint Directo (Sin n8n)

Si prefieres que Meta envíe directamente al sistema:

### Paso 1: Obtener Información del Webhook

```bash
GET /api/v1/whatsapp/webhook/info
```

Esto retornará:
- URL del webhook
- Token de verificación
- Instrucciones de configuración

### Paso 2: Configurar en Meta Developers

1. Ve a [Meta Developers](https://developers.facebook.com/apps)
2. Selecciona tu app → **WhatsApp** → **Configuration**
3. En **Webhook**, configura:
   - **Callback URL**: `https://tu-dominio.com/api/v1/whatsapp/webhook`
   - **Verify Token**: (el token configurado en `webhook_verify_token`)
4. Haz clic en **Verify and Save**
5. Suscríbete a los eventos

---

## 🔧 Opción 3: n8n como Receptor Final

Si quieres que n8n reciba los eventos y los procese completamente:

### Paso 1: Crear Webhook Público en n8n

1. Crea un workflow con nodo **"Webhook"**
2. Configura como **Webhook Público**
3. Copia la URL generada (ej: `https://tu-n8n.com/webhook/abc123`)

### Paso 2: Configurar Meta para Enviar a n8n

1. En Meta Developers, configura el webhook para apuntar a la URL de n8n
2. Configura el `verify_token` en n8n (puedes usar una variable de entorno)

### Paso 3: Procesar en n8n

En n8n, puedes:
- Filtrar eventos por tipo
- Guardar mensajes en base de datos
- Enviar respuestas automáticas
- Integrar con otros servicios
- Actualizar estados en el sistema principal

---

## 📡 Endpoints Disponibles

### 1. Verificación de Webhook (GET)
```
GET /api/v1/whatsapp/webhook?hub.mode=subscribe&hub.verify_token=TOKEN&hub.challenge=CHALLENGE
```

**Respuesta**: Texto plano con el `hub.challenge`

### 2. Recepción de Eventos (POST)
```
POST /api/v1/whatsapp/webhook
Content-Type: application/json
X-Hub-Signature-256: sha256=...

Body: {
  "object": "whatsapp_business_account",
  "entry": [...]
}
```

**Respuesta**:
```json
{
  "status": "success",
  "eventos_procesados": 2,
  "errores": 0
}
```

### 3. Información del Webhook (GET)
```
GET /api/v1/whatsapp/webhook/info
```

**Respuesta**: Información de configuración y URLs

---

## 🔐 Seguridad

### Verificación de Token

El endpoint de verificación valida el `webhook_verify_token` configurado en la aplicación contra el token enviado por Meta.

### Firma HMAC (Opcional)

Meta puede enviar `X-Hub-Signature-256` header con firma HMAC SHA256. Para validarla:

```python
import hmac
import hashlib

def verify_signature(payload: bytes, signature: str, secret: str) -> bool:
    expected = hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(f"sha256={expected}", signature)
```

---

## 📊 Eventos Procesados

### Estados de Mensajes

- **sent**: Mensaje enviado exitosamente
- **delivered**: Mensaje entregado al destinatario
- **read**: Mensaje leído por el destinatario
- **failed**: Mensaje falló al enviar

### Mensajes Recibidos

- **text**: Mensajes de texto
- **image**: Imágenes
- **document**: Documentos
- **audio**: Audio
- **video**: Video

---

## 🧪 Pruebas

### Probar Verificación

```bash
curl "https://tu-dominio.com/api/v1/whatsapp/webhook?hub.mode=subscribe&hub.verify_token=TU_TOKEN&hub.challenge=123456"
```

Debería retornar: `123456`

### Probar Evento

```bash
curl -X POST "https://tu-dominio.com/api/v1/whatsapp/webhook" \
  -H "Content-Type: application/json" \
  -d '{
    "object": "whatsapp_business_account",
    "entry": [{
      "id": "123",
      "changes": [{
        "value": {
          "statuses": [{
            "id": "wamid.xxx",
            "status": "delivered",
            "recipient_id": "584121234567"
          }]
        }
      }]
    }]
  }'
```

---

## 🔄 Flujo Completo con n8n

```
Meta WhatsApp → n8n Webhook → Procesamiento n8n → Sistema Principal
                ↓
         (Opcional: Base de datos, respuestas automáticas, etc.)
```

### Ejemplo de Workflow n8n

1. **Webhook** (recibe de Meta)
2. **IF** (verificar si es GET o POST)
3. **Switch** (filtrar por tipo de evento)
4. **HTTP Request** (enviar al sistema principal)
5. **Function** (procesar respuestas automáticas)
6. **HTTP Request** (enviar respuesta a cliente si es necesario)

---

## 📝 Notas Importantes

1. **Token de Verificación**: Debe ser el mismo en Meta y en la configuración de la app
2. **URL Pública**: El webhook debe ser accesible desde internet (no localhost)
3. **HTTPS**: Meta requiere HTTPS para webhooks en producción
4. **Rate Limits**: Respeta los rate limits de Meta (1000/día, 80/segundo)
5. **Logging**: Todos los eventos se registran en los logs del sistema

---

## 🐛 Troubleshooting

### Error: "Token de verificación inválido"
- Verifica que el `webhook_verify_token` en Meta coincida con el configurado en la app
- Revisa los logs para ver qué token se está recibiendo

### Error: "Modo inválido"
- Meta debe enviar `hub.mode=subscribe` para verificación
- Verifica que estés usando el endpoint GET para verificación

### No se reciben eventos
- Verifica que el webhook esté suscrito a eventos en Meta
- Revisa que la URL sea accesible desde internet
- Verifica los logs del sistema para ver si llegan requests

### Eventos no se procesan
- Revisa los logs para ver errores de procesamiento
- Verifica que la estructura del payload sea correcta
- Asegúrate de que la base de datos esté accesible

---

## 🔗 Referencias

- [Meta WhatsApp Business API Webhooks](https://developers.facebook.com/docs/whatsapp/cloud-api/webhooks)
- [n8n Webhook Documentation](https://docs.n8n.io/integrations/builtin/trigger-nodes/webhook/)
- [n8n HTTP Request Node](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.httprequest/)

