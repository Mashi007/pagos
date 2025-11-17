# 🔧 Pasos para Configurar Webhook de WhatsApp

## ✅ **CONFIRMACIÓN: El Webhook DEBE Configurarse**

Para usar el bot de WhatsApp que recibe y responde mensajes automáticamente, **DEBES configurar el webhook**.

---

## 📋 **PASO 1: Crear Token Secreto**

### **1.1. Elige un Token Único**

Crea un token secreto que usarás para verificar el webhook. Puede ser cualquier cadena que tú elijas:

**Ejemplos:**
- `rapicredit_whatsapp_token_2024`
- `mi_token_secreto_kohde_2024`
- `webhook_verify_abc123xyz`

**Recomendaciones:**
- ✅ Usa al menos 20 caracteres
- ✅ Combina letras, números y guiones bajos
- ✅ No uses información personal

**⚠️ IMPORTANTE**: Guarda este token, lo necesitarás en ambos lugares (tu sistema y Meta).

---

## 📋 **PASO 2: Configurar Token en tu Sistema**

### **2.1. Acceder a Configuración**

1. **Ve a**: Configuración → WhatsApp
2. **Busca el campo**: "Webhook Verify Token"

### **2.2. Ingresar Token**

1. **Ingresa tu token secreto** en el campo "Webhook Verify Token"
   - Ejemplo: `rapicredit_whatsapp_token_2024`
2. **Guarda la configuración** (botón "Guardar Configuración")

**✅ Verificación**: El token se guardará en la base de datos.

---

## 📋 **PASO 3: Configurar Webhook en Meta Developers**

### **3.1. Acceder a Meta Developers**

1. **Abre tu navegador** y ve a: https://developers.facebook.com/
2. **Inicia sesión** con tu cuenta de Facebook/Meta
3. **Selecciona tu App**: **Angelica** (ID: `1093645312947179`)

### **3.2. Ir a Configuración de WhatsApp**

1. **En el menú lateral izquierdo**, haz clic en **"WhatsApp"**
2. **Haz clic en "Configuration"** (Configuración)
3. **Busca la sección "Webhook"**

### **3.3. Configurar Callback URL**

**En el campo "Callback URL", ingresa:**

```
https://rapicredit.onrender.com/api/v1/whatsapp/webhook
```

**⚠️ IMPORTANTE**: 
- Debe ser HTTPS (tu servidor ya lo tiene)
- Debe ser accesible desde internet (tu servidor ya lo es)
- No debe tener espacios ni caracteres especiales

### **3.4. Configurar Verify Token**

**En el campo "Verify Token", ingresa:**

- El **mismo token** que configuraste en tu sistema
- Ejemplo: `rapicredit_whatsapp_token_2024`
- ⚠️ **DEBE ser exactamente el mismo** (sin espacios, mismo texto)

### **3.5. Verificar Webhook**

1. **Haz clic en "Verify and Save"** (Verificar y Guardar)
2. **Meta enviará un GET request** a tu servidor para verificar
3. **Si el token coincide**, verás un ✅ checkmark verde
4. **El webhook quedará activo**

**¿Qué pasa durante la verificación?**
- Meta envía: `GET /api/v1/whatsapp/webhook?hub.mode=subscribe&hub.verify_token=TU_TOKEN&hub.challenge=ABC123`
- Tu servidor verifica que el token coincida
- Tu servidor responde con: `ABC123`
- Meta activa el webhook ✅

### **3.6. Suscribirse a Eventos**

**Después de verificar, suscríbete a eventos:**

1. En la misma página de Webhook
2. Busca **"Webhook fields"** o **"Subscribe to fields"**
3. **Marca estos campos:**
   - ✅ **`messages`** - Para recibir mensajes de clientes (OBLIGATORIO para bot)
   - ✅ **`message_status`** - Para recibir actualizaciones de estado (opcional pero recomendado)

4. **Guarda los cambios**

---

## ✅ **PASO 4: Verificar que Funciona**

### **4.1. Verificar en Meta Developers**

1. Ve a WhatsApp → Configuration → Webhook
2. Deberías ver:
   - ✅ **Callback URL**: `https://rapicredit.onrender.com/api/v1/whatsapp/webhook`
   - ✅ **Status**: Verde (activo)
   - ✅ **Webhook fields**: `messages` (y opcionalmente `message_status`)

### **4.2. Probar Enviando un Mensaje**

1. **Envía un mensaje desde WhatsApp** a tu número de negocio
   - Ejemplo: "Hola" o "Buenos días"

2. **Verifica en los logs del backend** que se recibió:
   ```
   📨 Mensaje recibido de +584121234567: Hola...
   ✅ Mensaje procesado: Cliente encontrado, Respuesta enviada
   ```

3. **Verifica que recibiste la respuesta** en tu WhatsApp
   - Deberías recibir una respuesta automática del bot

### **4.3. Verificar en el CRM**

1. **Ve a**: API → `/api/v1/conversaciones-whatsapp`
2. **Deberías ver** la conversación guardada:
   - Mensaje recibido (INBOUND)
   - Respuesta enviada (OUTBOUND)

---

## 🔍 **Troubleshooting**

### **Problema: Verificación Falla en Meta**

**Síntomas:**
- Meta muestra error: "Verification failed"
- El webhook no se activa

**Soluciones:**

1. **Verifica que el token coincida exactamente:**
   - Token en tu sistema = Token en Meta
   - Debe ser exactamente igual (sin espacios, mismo texto)
   - Copia y pega para evitar errores de tipeo

2. **Verifica que la URL sea accesible:**
   ```bash
   # Prueba manualmente:
   curl "https://rapicredit.onrender.com/api/v1/whatsapp/webhook?hub.mode=subscribe&hub.verify_token=TU_TOKEN&hub.challenge=test"
   ```
   - Debe responder con: `test`
   - Si no responde, hay un problema con la URL

3. **Verifica los logs del backend:**
   - Busca errores en la verificación
   - Verifica que el endpoint esté funcionando
   - Busca: `⚠️ Webhook verification` o `✅ Webhook verificado`

### **Problema: No Llegan Mensajes**

**Síntomas:**
- Envías mensaje desde WhatsApp
- No se procesa en el sistema
- No recibes respuesta

**Soluciones:**

1. **Verifica que el webhook esté activo** en Meta Developers
   - Debe mostrar status verde

2. **Verifica que estés suscrito a `messages`**
   - En Meta Developers → Webhook → Webhook fields
   - Debe estar marcado `messages`

3. **Revisa los logs del backend:**
   - Busca: `📨 Mensaje recibido`
   - Si no aparece, el webhook no está llegando

4. **Verifica que la URL sea correcta:**
   - Debe ser HTTPS
   - Debe ser accesible desde internet
   - No debe tener errores de conexión

### **Problema: Token No Coincide**

**Síntomas:**
- Error: "Token de verificación inválido"
- Webhook no se verifica

**Soluciones:**

1. **Copia el token exacto** de tu sistema
2. **Pégalo en Meta Developers** (sin espacios adicionales)
3. **Verifica que no haya caracteres especiales** ocultos
4. **Intenta con un token más simple** para probar (ej: `test123`)

---

## 📊 **URL del Webhook**

### **URL Completa:**

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
- [ ] Configuración guardada exitosamente
- [ ] Token guardado en lugar seguro

### **En Meta Developers:**
- [ ] Callback URL configurada: `https://rapicredit.onrender.com/api/v1/whatsapp/webhook`
- [ ] Verify Token configurado (mismo que en tu sistema)
- [ ] Webhook verificado exitosamente (checkmark verde)
- [ ] Suscrito a `messages`
- [ ] (Opcional) Suscrito a `message_status`

### **Verificación:**
- [ ] Envié mensaje de prueba desde WhatsApp
- [ ] Mensaje se procesó en el sistema (ver logs)
- [ ] Recibí respuesta automática del bot
- [ ] Conversación aparece en `/api/v1/conversaciones-whatsapp`

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

