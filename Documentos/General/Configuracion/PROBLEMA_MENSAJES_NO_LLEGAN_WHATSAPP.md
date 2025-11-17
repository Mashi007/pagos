# ❌ Problema: Mensajes de WhatsApp No Llegan

## 🔍 **Diagnóstico del Problema**

### **Causa Principal: Ventana de 24 Horas de Meta**

Meta WhatsApp Business API tiene una política estricta:

> **Los mensajes de texto libre (sin template) solo se pueden enviar dentro de 24 horas desde el último mensaje del usuario.**

**Si el usuario NO ha enviado un mensaje en las últimas 24 horas, Meta RECHAZARÁ el mensaje con error `400 Bad Request`.**

---

## 📋 **Políticas de Meta que Afectan el Envío**

### ✅ **Políticas Técnicas (Cumplidas)**
- [x] Rate limiting (1000/día, 80/segundo)
- [x] Manejo de errores específicos
- [x] Retry con backoff exponencial
- [x] Timeout configurable
- [x] Validación de longitud de mensajes
- [x] Validación de números de teléfono

### ⚠️ **Políticas de Negocio (NO Cumplidas - Causa del Problema)**
- [ ] **Ventana de 24 Horas** ❌ **ESTE ES EL PROBLEMA**
- [ ] Opt-in/Opt-out (consentimiento)
- [ ] Validación de templates aprobados
- [ ] Webhooks para actualizaciones

---

## 🚨 **Por Qué No Llegan los Mensajes**

### **Escenario Actual:**

1. **El sistema envía mensajes de texto libre** (sin template)
2. **El usuario NO ha enviado un mensaje en las últimas 24 horas**
3. **Meta rechaza el mensaje** con error `400 Bad Request`
4. **El mensaje NO llega al usuario**

### **Error que Meta Devuelve:**

```json
{
  "error": {
    "message": "Message failed to send because more than 24 hours have passed since the customer last replied to this number.",
    "type": "OAuthException",
    "code": 131047,
    "error_subcode": 131026
  }
}
```

**Código de error**: `131026` = "Message outside 24-hour window"

---

## ✅ **Solución: Usar Templates Aprobados**

### **Para Enviar Mensajes Fuera de la Ventana de 24 Horas:**

1. **Crear un Template en Meta Developers**
2. **Esperar aprobación de Meta** (puede tardar horas/días)
3. **Usar el template aprobado** en lugar de mensaje libre

### **Cómo Crear un Template:**

1. Ve a [Meta Developers](https://developers.facebook.com/)
2. Selecciona tu App → WhatsApp → Message Templates
3. Crea un nuevo template
4. Espera aprobación de Meta
5. Una vez aprobado, úsalo en el código

### **Ejemplo de Template Aprobado:**

```json
{
  "name": "notificacion_pago",
  "language": "es",
  "category": "UTILITY",
  "components": [
    {
      "type": "BODY",
      "text": "Hola {{1}}, tu pago de {{2}} vence el {{3}}."
    }
  ]
}
```

---

## 🔧 **Cómo Implementar Templates en el Código**

### **Opción 1: Modificar el Código para Usar Templates**

**Archivo**: `backend/app/services/whatsapp_service.py`

```python
# En lugar de:
await whatsapp_service.send_message(
    to_number="+584121234567",
    message="Tu pago vence mañana"
)

# Usar:
await whatsapp_service.send_message(
    to_number="+584121234567",
    message="Tu pago vence mañana",
    template_name="notificacion_pago"  # ← Template aprobado
)
```

### **Opción 2: Verificar Ventana de 24 Horas**

**Implementar verificación antes de enviar:**

```python
# Verificar si el usuario envió mensaje en últimas 24h
ultima_interaccion = obtener_ultima_interaccion_whatsapp(cliente_id)
ventana_24h = datetime.now() - timedelta(hours=24)

if ultima_interaccion and ultima_interaccion > ventana_24h:
    # Dentro de ventana: enviar mensaje libre
    await whatsapp_service.send_message(to_number, message)
else:
    # Fuera de ventana: usar template
    await whatsapp_service.send_message(
        to_number, 
        message, 
        template_name="notificacion_pago"
    )
```

---

## 📊 **Logs que Verás si el Problema es la Ventana de 24h**

### **En los Logs del Backend:**

```
📤 [ENVÍO] Enviando mensaje a Meta API:
   URL: https://graph.facebook.com/v18.0/627189243818989/messages
   Destinatario: 584121234567
   Tipo: text (libre - requiere ventana 24h)
   Payload: {...}

📥 [RESPUESTA] Meta respondió:
   Status Code: 400
   Response Body: {
     "error": {
       "message": "Message failed to send because more than 24 hours have passed...",
       "code": 131047,
       "error_subcode": 131026
     }
   }

❌ [COMPLIANCE] Error enviando mensaje WhatsApp: Solicitud inválida (Código: META_BAD_REQUEST)
⚠️ [POLÍTICA META] Error 400 sin template - Probable causa: Mensaje fuera de ventana de 24 horas
⚠️ [SOLUCIÓN] Para enviar mensajes fuera de ventana de 24h, debes usar un template aprobado
```

---

## 🎯 **Pasos para Resolver el Problema**

### **Paso 1: Verificar el Error en los Logs**

1. **Ejecuta un mensaje de prueba**
2. **Revisa los logs del backend**
3. **Busca el error específico de Meta**

### **Paso 2: Si el Error es 131026 (Ventana de 24h)**

1. **Crea templates en Meta Developers**
2. **Espera aprobación**
3. **Modifica el código para usar templates**

### **Paso 3: Si el Error es Otro**

- **401 Unauthorized**: Token inválido → Regenera token
- **403 Forbidden**: Permisos insuficientes → Verifica permisos en Meta
- **400 Bad Request (otro)**: Revisa formato del mensaje/número

---

## ⚠️ **Notas Importantes**

1. **Templates Requieren Aprobación:**
   - Meta revisa cada template
   - Puede tardar horas o días
   - Solo templates aprobados funcionan fuera de ventana de 24h

2. **Mensajes Libres Solo Dentro de 24h:**
   - Si el usuario envió mensaje en últimas 24h → mensaje libre funciona
   - Si NO envió mensaje en últimas 24h → Meta rechaza mensaje libre

3. **Para Pruebas Iniciales:**
   - Envía un mensaje desde tu WhatsApp al número de negocio
   - Esto abre la ventana de 24 horas
   - Luego puedes enviar mensajes libres durante 24h

4. **Producción:**
   - Siempre usa templates aprobados para notificaciones automáticas
   - Los templates no tienen restricción de ventana de 24h

---

## 🔗 **Referencias**

- [Meta WhatsApp Business API - Message Templates](https://developers.facebook.com/docs/whatsapp/business-management-api/message-templates)
- [Meta WhatsApp Business API - 24-Hour Window](https://developers.facebook.com/docs/whatsapp/cloud-api/guides/send-messages#24-hour-window)
- [Documento de Compliance](Documentos/General/Configuracion/COMPLIANCE_WHATSAPP_META.md)

