# 📱 Número de Envío WhatsApp: ¿Debe Estar en Producción?

## 🎯 **Respuesta Rápida**

**NO necesariamente debe estar en producción.** Puedes usar el número en modo **desarrollo/sandbox** para pruebas, pero tiene limitaciones.

---

## 📋 **Dos Números Diferentes**

### **1. Número que ENVÍA (Phone Number ID)** ⭐

**Este es el número de tu WhatsApp Business verificado en Meta.**

- **Dónde se configura**: `Phone Number ID` en la configuración
- **Ejemplo**: `627189243818989`
- **Qué es**: ID del número de WhatsApp Business que Meta asigna
- **Número real**: Ejemplo `+15556549812` (este es el número de teléfono real)

**Este número:**
- ✅ Debe estar **verificado en Meta Business**
- ✅ Debe estar **asociado a tu App** en Meta Developers
- ✅ Puede estar en **modo desarrollo** o **producción**
- ✅ Es el que aparece como **remitente** en los mensajes

### **2. Número que RECIBE (Destinatario)**

**Este es el número del cliente que recibe el mensaje.**

- **Dónde se configura**: En la base de datos (tabla `clientes.telefono`)
- **Ejemplo**: `+584121234567`
- **Qué es**: Número de WhatsApp del cliente

**Este número:**
- ✅ Puede ser cualquier número de WhatsApp válido
- ✅ En **modo pruebas**, todos los mensajes se redirigen a `telefono_pruebas`
- ✅ En **modo producción**, se envía al número real del cliente

---

## 🔧 **Cómo Funciona el Envío**

### **URL de Envío a Meta:**

```python
# El sistema construye esta URL:
url = f"{api_url}/{phone_number_id}/messages"
# Ejemplo: https://graph.facebook.com/v18.0/627189243818989/messages
```

**El `phone_number_id` es el número que ENVÍA el mensaje.**

### **Payload que se Envía:**

```json
{
  "messaging_product": "whatsapp",
  "to": "584121234567",  // ← Número que RECIBE (destinatario)
  "type": "text",
  "text": {
    "body": "Mensaje aquí"
  }
}
```

**El `to` es el número que RECIBE el mensaje.**

---

## 🧪 **Modo Desarrollo vs Producción en Meta**

### **Modo Desarrollo (Sandbox)** ⚠️

**Características:**
- ✅ Puedes probar sin costo
- ✅ Limitado a **5 números de prueba** que agregues manualmente
- ✅ Solo puedes enviar a números que agregues en Meta Developers
- ❌ NO puedes enviar a cualquier número
- ❌ Limitado a 1,000 mensajes/día

**Cómo agregar números de prueba:**
1. Ve a Meta Developers → WhatsApp → API Setup
2. Busca "To" o "Phone numbers"
3. Haz clic en "Manage phone number list"
4. Agrega números de prueba (máximo 5)

**¿Puedes usar este modo para pruebas?**
- ✅ **SÍ**, pero solo puedes enviar a los 5 números que agregues
- ✅ Útil para desarrollo y pruebas iniciales
- ❌ NO útil para producción real

### **Modo Producción** ✅

**Características:**
- ✅ Puedes enviar a **cualquier número** de WhatsApp
- ✅ Sin límite de números de prueba
- ✅ Límites más altos (según tu tier)
- ⚠️ Puede tener costos según el plan
- ⚠️ Requiere verificación completa de negocio

**¿Cuándo usar este modo?**
- ✅ Cuando estés listo para enviar a clientes reales
- ✅ Cuando hayas probado todo en desarrollo
- ✅ Cuando tu negocio esté verificado en Meta

---

## 🎯 **Recomendación: Flujo de Trabajo**

### **Paso 1: Desarrollo (Sandbox)**

1. **Usa el número en modo desarrollo** en Meta
2. **Agrega 5 números de prueba** en Meta Developers
3. **Configura `modo_pruebas: 'true'`** en tu sistema
4. **Configura `telefono_pruebas`** con uno de tus números de prueba
5. **Prueba envíos** a esos números

**Ventajas:**
- ✅ Gratis
- ✅ Sin riesgo de enviar a clientes reales
- ✅ Perfecto para desarrollo

### **Paso 2: Pruebas con Producción**

1. **Solicita acceso a producción** en Meta (si no lo tienes)
2. **Mantén `modo_pruebas: 'true'`** en tu sistema
3. **Configura `telefono_pruebas`** con tu número personal
4. **Prueba envíos** - todos irán a tu número de prueba

**Ventajas:**
- ✅ Puedes probar con números reales (pero redirigidos)
- ✅ Verifica que todo funcione antes de producción real
- ✅ Seguro (no envía a clientes reales)

### **Paso 3: Producción Real**

1. **Asegúrate de que el número esté en producción** en Meta
2. **Cambia `modo_pruebas: 'false'`** en tu sistema
3. **Los mensajes se enviarán a clientes reales**

**Ventajas:**
- ✅ Envíos reales a clientes
- ✅ Sin limitaciones de números de prueba

---

## ⚠️ **Importante: Verificación del Número**

### **El número que ENVÍA debe estar:**

1. **Verificado en Meta Business:**
   - Debe estar asociado a una cuenta de Meta Business
   - Debe estar verificado (Meta envía código SMS)

2. **Asociado a tu App:**
   - Debe estar agregado en Meta Developers → WhatsApp
   - Debe tener permisos para enviar mensajes

3. **Activo:**
   - No debe estar suspendido
   - Debe tener permisos de envío habilitados

### **Cómo Verificar:**

1. Ve a [Meta Developers](https://developers.facebook.com/)
2. Selecciona tu App → WhatsApp → API Setup
3. Verifica que el número aparezca en "From" o "Phone number ID"
4. Si no aparece, agrégalo desde Meta Business

---

## 📊 **Resumen: ¿Debe Estar en Producción?**

| Escenario | ¿Debe estar en Producción? | ¿Puede estar en Desarrollo? |
|-----------|---------------------------|----------------------------|
| **Pruebas iniciales** | ❌ NO | ✅ SÍ (Sandbox) |
| **Desarrollo** | ❌ NO | ✅ SÍ (Sandbox) |
| **Pruebas con números reales** | ⚠️ Recomendado | ⚠️ Posible pero limitado |
| **Producción real** | ✅ SÍ | ❌ NO |

---

## 🔍 **Cómo Verificar el Modo del Número**

### **En Meta Developers:**

1. Ve a WhatsApp → API Setup
2. Busca el número en "From" o "Phone number ID"
3. Si dice "Sandbox" o "Development" → Está en desarrollo
4. Si no dice nada o dice "Production" → Está en producción

### **En tu Sistema:**

**Modo Pruebas (`modo_pruebas: 'true'`):**
- Todos los mensajes se redirigen a `telefono_pruebas`
- El número que ENVÍA sigue siendo el mismo (`phone_number_id`)
- Útil para pruebas sin afectar clientes reales

**Modo Producción (`modo_pruebas: 'false'`):**
- Los mensajes se envían a números reales de clientes
- El número que ENVÍA sigue siendo el mismo (`phone_number_id`)
- Solo usar cuando estés listo para producción

---

## 🎯 **Recomendación Final**

### **Para Empezar:**

1. ✅ **Usa el número en modo desarrollo** (Sandbox)
2. ✅ **Agrega números de prueba** en Meta
3. ✅ **Configura `modo_pruebas: 'true'`** en tu sistema
4. ✅ **Prueba todo** antes de pasar a producción

### **Para Producción:**

1. ✅ **Solicita acceso a producción** en Meta
2. ✅ **Verifica que el número esté en producción**
3. ✅ **Prueba con `modo_pruebas: 'true'`** primero
4. ✅ **Cuando estés seguro, cambia a `modo_pruebas: 'false'`**

---

## 📝 **Notas Importantes**

1. **El número que ENVÍA (`phone_number_id`) es siempre el mismo**, independientemente del modo
2. **El modo desarrollo/sandbox tiene limitaciones** (solo 5 números de prueba)
3. **El `modo_pruebas` en tu sistema** solo afecta a dónde se ENVÍA, no quién ENVÍA
4. **Para producción real**, el número debe estar en producción en Meta

---

## 🔗 **Referencias**

- [Meta WhatsApp Business API - Sandbox](https://developers.facebook.com/docs/whatsapp/cloud-api/get-started)
- [Meta WhatsApp Business API - Production](https://developers.facebook.com/docs/whatsapp/cloud-api/overview)
- [Guía de Configuración](Documentos/General/Configuracion/GUIA_CONFIGURACION_WHATSAPP_META.md)

