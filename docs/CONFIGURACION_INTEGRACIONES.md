# 📧 Configuración de Integraciones - RapiCredit

## 🎯 **INTEGRACIONES ACTIVAS**

Este sistema utiliza **únicamente**:
- ✅ **Email (Gmail/Workspace)**
- ✅ **WhatsApp (Meta Developers API)**

❌ **NO se usa Twilio ni SMS**

---

## 📧 **1. CONFIGURACIÓN DE EMAIL (Gmail/Workspace)**

### **Paso 1: Crear cuenta de Gmail/Workspace**
```
Email recomendado: noreply@rapicredit.com
```

### **Paso 2: Generar App Password**

#### Para Gmail Personal:
1. Ir a: https://myaccount.google.com/apppasswords
2. Activar "Verificación en 2 pasos"
3. Generar "Contraseña de aplicación"
4. Copiar el código de 16 caracteres

#### Para Google Workspace:
1. Admin Console → Seguridad → API Controls
2. Habilitar "Less secure app access" o usar OAuth 2.0
3. Generar credenciales

### **Paso 3: Configurar Variables de Entorno**

```bash
# Email Configuration
EMAIL_ENABLED=true
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=noreply@rapicredit.com
SMTP_PASSWORD=xxxx xxxx xxxx xxxx  # App Password de 16 caracteres
FROM_EMAIL=noreply@rapicredit.com
FROM_NAME=RapiCredit
SMTP_USE_TLS=true
SMTP_USE_SSL=false
```

### **Paso 4: Verificar Configuración**

```python
# Endpoint de prueba
POST /api/v1/notificaciones/test-email
{
  "to_email": "test@example.com",
  "subject": "Prueba de Email",
  "body": "Este es un email de prueba"
}
```

---

## 💬 **2. CONFIGURACIÓN DE WHATSAPP (Meta Developers)**

### **Paso 1: Crear Cuenta de Meta Business**
1. Ir a: https://business.facebook.com/
2. Crear "Meta Business Account"
3. Verificar la cuenta de negocio

### **Paso 2: Configurar WhatsApp Business API**
1. Ir a: https://developers.facebook.com/
2. Crear una App → Tipo: "Business"
3. Agregar producto: "WhatsApp"
4. Configurar WhatsApp Business API

### **Paso 3: Obtener Credenciales**

#### Access Token:
```
1. Dashboard → WhatsApp → API Setup
2. Copiar "Temporary access token" (válido 24h)
3. Para producción: generar "Permanent access token"
```

#### Phone Number ID:
```
1. Dashboard → WhatsApp → API Setup
2. Copiar "Phone number ID" (número de 15 dígitos)
```

#### Business Account ID:
```
1. Dashboard → WhatsApp → API Setup
2. Copiar "WhatsApp Business Account ID"
```

### **Paso 4: Configurar Webhooks (Opcional)**
```
Webhook URL: https://rapicredit-backend.onrender.com/api/v1/webhooks/whatsapp
Verify Token: [generar token aleatorio seguro]
```

### **Paso 5: Configurar Variables de Entorno**

```bash
# WhatsApp Configuration (Meta Developers)
WHATSAPP_ENABLED=true
WHATSAPP_API_URL=https://graph.facebook.com/v18.0
WHATSAPP_ACCESS_TOKEN=EAAxxxxxxxxxxxxxxxxxxxxxxxxxx
WHATSAPP_PHONE_NUMBER_ID=123456789012345
WHATSAPP_BUSINESS_ACCOUNT_ID=987654321098765
WHATSAPP_WEBHOOK_VERIFY_TOKEN=mi_token_seguro_123
```

### **Paso 6: Crear Templates en Meta**

Los mensajes de WhatsApp **deben usar templates aprobados** para envíos masivos.

#### Ejemplo de Template:
```
Nombre: recordatorio_pago
Idioma: Español (es)
Categoría: UTILITY

Contenido:
🔔 Hola {{1}}, te recordamos que tienes una cuota de ${{2}} con vencimiento el {{3}}. 
Por favor realiza tu pago a tiempo.
```

**⚠️ Importante:** Los templates deben ser aprobados por Meta (puede tardar 24-48h).

### **Paso 7: Verificar Configuración**

```python
# Endpoint de prueba
POST /api/v1/notificaciones/test-whatsapp
{
  "to_number": "+593999999999",
  "message": "Este es un mensaje de prueba"
}
```

---

## 🔧 **3. CONFIGURACIÓN EN RENDER**

### **Backend (Variables de Entorno)**
```
1. Render Dashboard → Service → Environment
2. Agregar todas las variables listadas arriba
3. Save Changes
4. El servicio se reiniciará automáticamente
```

### **Frontend (No requiere configuración adicional)**
```
El frontend usa las APIs del backend.
No necesita variables de entorno para notificaciones.
```

---

## ✅ **4. VALIDACIÓN DE CONFIGURACIÓN**

### **Verificar Email:**
```bash
# Debe retornar: {"status": "configured", "ready": true}
GET /api/v1/configuracion/notificaciones
```

### **Verificar WhatsApp:**
```bash
# Debe retornar: {"status": "configured", "provider": "META_CLOUD_API", "ready": true}
GET /api/v1/configuracion/notificaciones
```

---

## 🚨 **5. TROUBLESHOOTING**

### **Error: "Credenciales de email no configuradas"**
✅ Verificar que `SMTP_USER` y `SMTP_PASSWORD` estén configurados
✅ Verificar que el App Password de Gmail sea correcto

### **Error: "Credenciales de Meta Developers no configuradas"**
✅ Verificar que `WHATSAPP_ACCESS_TOKEN` y `WHATSAPP_PHONE_NUMBER_ID` estén configurados
✅ Verificar que el token de Meta no haya expirado

### **Error: "Template not found" (WhatsApp)**
✅ Crear y aprobar templates en Meta Business Manager
✅ Esperar 24-48h para aprobación de templates
✅ Verificar que el nombre del template sea exacto

### **Error: "SMTP authentication failed"**
✅ Verificar que la verificación en 2 pasos esté activa en Gmail
✅ Generar nuevo App Password
✅ Verificar que no haya espacios en el password

---

## 📊 **6. LÍMITES Y CONSIDERACIONES**

### **Gmail:**
- Límite diario: 500 emails/día (Gmail personal)
- Límite diario: 2000 emails/día (Workspace)
- Recomendación: Usar cuenta de Workspace para producción

### **WhatsApp (Meta):**
- Límite inicial: 250 conversaciones/24h
- Aumenta automáticamente con buen uso
- Templates requieren aprobación previa
- Mensajes fuera de 24h ventana requieren template

---

## 🔐 **7. SEGURIDAD**

✅ **NUNCA** commitear credenciales en el código
✅ Usar variables de entorno en Render
✅ Rotar tokens cada 90 días
✅ Usar tokens permanentes en producción (no temporales)
✅ Implementar rate limiting en endpoints de notificaciones
✅ Monitorear logs de errores

---

## 📞 **8. SOPORTE**

### **Gmail:**
- Documentación: https://support.google.com/mail/answer/7126229
- App Passwords: https://myaccount.google.com/apppasswords

### **Meta Developers:**
- Documentación: https://developers.facebook.com/docs/whatsapp
- Cloud API: https://developers.facebook.com/docs/whatsapp/cloud-api
- Business Manager: https://business.facebook.com/

---

## 🎉 **9. RESUMEN EJECUTIVO**

Para poner en producción:

1. ✅ Crear cuenta Gmail/Workspace
2. ✅ Generar App Password
3. ✅ Crear Meta Business Account
4. ✅ Configurar WhatsApp Business API
5. ✅ Crear y aprobar templates
6. ✅ Configurar variables de entorno en Render
7. ✅ Probar endpoints de notificaciones
8. ✅ Monitorear logs de errores

**Estado actual:** ⚠️ Pendiente de configurar credenciales reales
**Tiempo estimado de configuración:** 2-4 horas
**Costo:** Gratis (con límites de uso)

