# 🔧 Guía Completa: Configurar Webhook de WhatsApp

## ✅ **CONFIRMACIÓN: El Webhook DEBE Configurarse**

Para usar el bot de WhatsApp que recibe y responde mensajes automáticamente, **DEBES configurar el webhook**.

---

## 📋 **Paso 1: Configurar Webhook Verify Token en tu Sistema**

### **1.1. Crear un Token Secreto**

Elige un token secreto único y seguro. Puede ser cualquier cadena que tú elijas:

**Ejemplos:**
- `rapicredit_whatsapp_token_2024`
- `mi_token_secreto_kohde`
- `webhook_verify_abc123xyz`

**Recomendaciones:**
- Usa al menos 20 caracteres
- Combina letras, números y guiones bajos
- No uses información personal o fácil de adivinar

### **1.2. Configurar en tu Sistema**

1. **Ve a**: Configuración → WhatsApp
2. **Busca el campo**: "Webhook Verify Token" (opcional)
3. **Ingresa tu token secreto** (el que acabas de crear)
4. **Guarda la configuración**

**⚠️ IMPORTANTE**: Guarda este token en un lugar seguro, lo necesitarás en el siguiente paso.

---

## 📋 **Paso 2: Configurar Webhook en Meta Developers**

### **2.1. Acceder a Meta Developers**

1. Ve a [Meta Developers](https://developers.facebook.com/)
2. Inicia sesión con tu cuenta
3. Selecciona tu App: **Angelica** (ID: `1093645312947179`)

### **2.2. Ir a Configuración de WhatsApp**

1. En el menú lateral, haz clic en **"WhatsApp"**
2. Haz clic en **"Configuration"** (Configuración)
3. Busca la sección **"Webhook"**

### **2.3. Configurar el Webhook**

**En la sección Webhook, configura:**

1. **Callback URL**:
   ```
   https://rapicredit.onrender.com/api/v1/whatsapp/webhook
   ```
   - Esta es la URL de tu servidor donde Meta enviará los mensajes
   - Debe ser HTTPS (tu servidor ya lo tiene)

2. **Verify Token**:
   - Ingresa el **mismo token** que configuraste en tu sistema
   - Ejemplo: `rapicredit_whatsapp_token_2024`
   - ⚠️ **DEBE ser exactamente el mismo** que en tu sistema

3. **Haz clic en "Verify and Save"** (Verificar y Guardar)

### **2.4. Verificación Automática**

Meta enviará un GET request a tu servidor:
```
GET https://rapicredit.onrender.com/api/v1/whatsapp/webhook?hub.mode=subscribe&hub.verify_token=TU_TOKEN&hub.challenge=ABC123
```

**Tu servidor:**
- ✅ Verifica que el token coincida
- ✅ Responde con el `hub.challenge`
- ✅ Meta activa el webhook

**Si la verificación es exitosa:**
- ✅ Verás un checkmark verde en Meta Developers
- ✅ El webhook quedará activo

### **2.5. Suscribirse a Eventos**

Después de verificar, suscríbete a los eventos:

1. En la misma página de Webhook
2. Busca **"Webhook fields"** o **"Subscribe to fields"**
3. **Marca estos campos:**
   - ✅ `messages` - Para recibir mensajes de clientes
   - ✅ `message_status` - Para recibir actualizaciones de estado (opcional pero recomendado)

4. **Guarda los cambios**

---

## 📋 **Paso 3: Verificar que Funciona**

### **3.1. Verificar en Meta Developers**

1. Ve a WhatsApp → Configuration → Webhook
2. Deberías ver:
   - ✅ **Callback URL**: `https://rapicredit.onrender.com/api/v1/whatsapp/webhook`
   - ✅ **Status**: Verde (activo)
   - ✅ **Webhook fields**: `messages` (y opcionalmente `message_status`)

### **3.2. Probar Enviando un Mensaje**

1. **Envía un mensaje desde WhatsApp** a tu número de negocio
2. **Verifica en los logs del backend** que se recibió:
   ```
   📨 Mensaje recibido de +584121234567: Hola...
   ✅ Mensaje procesado: Cliente encontrado, Respuesta enviada
   ```

3. **Verifica que recibiste la respuesta** en tu WhatsApp

### **3.3. Verificar en el CRM**

1. **Ve a**: API → `/api/v1/conversaciones-whatsapp`
2. **Deberías ver** la conversación guardada:
   - Mensaje recibido (INBOUND)
   - Respuesta enviada (OUTBOUND)

---

## 🔍 **Troubleshooting**

### **Problema: Verificación Falla**

**Síntomas:**
- Meta muestra error al verificar
- El webhook no se activa

**Soluciones:**

1. **Verifica que el token coincida:**
   - Token en tu sistema = Token en Meta
   - Debe ser exactamente igual (sin espacios)

2. **Verifica que la URL sea accesible:**
   ```bash
   curl https://rapicredit.onrender.com/api/v1/whatsapp/webhook?hub.mode=subscribe&hub.verify_token=TU_TOKEN&hub.challenge=test
   ```
   - Debe responder con "test"

3. **Verifica los logs del backend:**
   - Busca errores en la verificación
   - Verifica que el endpoint esté funcionando

### **Problema: No Llegan Mensajes**

**Síntomas:**
- Envías mensaje desde WhatsApp
- No se procesa en el sistema

**Soluciones:**

1. **Verifica que el webhook esté activo** en Meta Developers
2. **Verifica que estés suscrito a `messages`**
3. **Revisa los logs del backend** para ver si llegan los webhooks
4. **Verifica que la URL sea correcta** (HTTPS, sin errores)

### **Problema: Token No Coincide**

**Síntomas:**
- Error: "Token de verificación inválido"
- Webhook no se verifica

**Soluciones:**

1. **Copia el token exacto** de tu sistema
2. **Pégalo en Meta Developers** (sin espacios adicionales)
3. **Verifica que no haya caracteres especiales** ocultos
4. **Intenta con un token más simple** para probar

---

## 📊 **Estructura del Webhook**

### **URL del Webhook:**

```
https://rapicredit.onrender.com/api/v1/whatsapp/webhook
```

### **Endpoints Disponibles:**

1. **GET** `/api/v1/whatsapp/webhook` - Verificación (Meta lo llama automáticamente)
2. **POST** `/api/v1/whatsapp/webhook` - Recepción de mensajes (Meta envía aquí)
3. **GET** `/api/v1/whatsapp/webhook/info` - Información del webhook

---

## ✅ **Checklist de Configuración**

### **En tu Sistema:**
- [ ] Token secreto creado
- [ ] Token configurado en "Webhook Verify Token"
- [ ] Configuración guardada
- [ ] Token guardado en lugar seguro

### **En Meta Developers:**
- [ ] Callback URL configurada: `https://rapicredit.onrender.com/api/v1/whatsapp/webhook`
- [ ] Verify Token configurado (mismo que en tu sistema)
- [ ] Webhook verificado exitosamente (checkmark verde)
- [ ] Suscrito a `messages`
- [ ] (Opcional) Suscrito a `message_status`

### **Verificación:**
- [ ] Envié mensaje de prueba desde WhatsApp
- [ ] Mensaje se procesó en el sistema
- [ ] Recibí respuesta automática
- [ ] Conversación aparece en el CRM

---

## 🔗 **Enlaces Directos**

- **Meta Developers - Tu App**: https://developers.facebook.com/apps/1093645312947179
- **WhatsApp Configuration**: https://developers.facebook.com/apps/1093645312947179/whatsapp-business/cloud-api/webhooks
- **Webhook Info Endpoint**: https://rapicredit.onrender.com/api/v1/whatsapp/webhook/info

---

## 📝 **Notas Importantes**

1. **El token debe ser el mismo** en tu sistema y en Meta
2. **La URL debe ser HTTPS** (tu servidor ya lo tiene)
3. **La URL debe ser accesible** desde internet (tu servidor ya lo es)
4. **El webhook se verifica automáticamente** cuando guardas en Meta
5. **Si cambias el token**, debes actualizarlo en ambos lugares

---

## 🚀 **Después de Configurar**

Una vez configurado el webhook:

1. ✅ **Los mensajes de clientes** llegarán automáticamente
2. ✅ **El bot responderá** automáticamente
3. ✅ **Las conversaciones se guardarán** en el CRM
4. ✅ **Podrás ver todas las conversaciones** en `/api/v1/conversaciones-whatsapp`

---

## 🔗 **Referencias**

- [Bot de WhatsApp CRM](Documentos/General/Configuracion/BOT_WHATSAPP_CRM.md)
- [Guía de Configuración WhatsApp](Documentos/General/Configuracion/GUIA_CONFIGURACION_WHATSAPP_META.md)
- [Webhook Necesario](Documentos/General/Configuracion/WEBHOOK_WHATSAPP_NECESARIO.md)

