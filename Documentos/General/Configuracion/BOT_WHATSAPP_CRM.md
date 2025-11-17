# 🤖 Bot de WhatsApp para CRM - Guía Completa

## 🎯 **Resumen**

Se ha implementado un bot de WhatsApp que:
- ✅ **Recibe mensajes** de clientes automáticamente
- ✅ **Responde automáticamente** con respuestas inteligentes
- ✅ **Guarda todas las conversaciones** en el CRM
- ✅ **Identifica clientes** por número de teléfono
- ✅ **Integra con el sistema** de clientes, préstamos y pagos

---

## 🔧 **Componentes Implementados**

### **1. Modelo de Conversaciones** ✅

**Archivo**: `backend/app/models/conversacion_whatsapp.py`

Almacena todas las conversaciones en la tabla `conversaciones_whatsapp`:
- Mensajes recibidos (INBOUND)
- Mensajes enviados (OUTBOUND)
- Relación con clientes
- Estado de procesamiento
- Respuestas del bot

### **2. Servicio de Bot** ✅

**Archivo**: `backend/app/services/whatsapp_bot_service.py`

Procesa mensajes y genera respuestas:
- Busca cliente por número de teléfono
- Genera respuestas automáticas
- Envía respuestas al cliente
- Guarda todo en el CRM

### **3. Webhook Mejorado** ✅

**Archivo**: `backend/app/api/v1/endpoints/whatsapp_webhook.py`

Procesa mensajes recibidos de Meta:
- Recibe webhooks de Meta
- Procesa mensajes con el bot
- Guarda conversaciones

### **4. Endpoints del CRM** ✅

**Archivo**: `backend/app/api/v1/endpoints/conversaciones_whatsapp.py`

Endpoints para ver conversaciones:
- `GET /api/v1/conversaciones-whatsapp` - Listar todas
- `GET /api/v1/conversaciones-whatsapp/{id}` - Obtener una
- `GET /api/v1/conversaciones-whatsapp/cliente/{cliente_id}` - Por cliente
- `GET /api/v1/conversaciones-whatsapp/numero/{numero}` - Por número
- `GET /api/v1/conversaciones-whatsapp/estadisticas` - Estadísticas

---

## 🚀 **Cómo Funciona**

### **Flujo Completo:**

1. **Cliente envía mensaje** a tu número de WhatsApp Business
2. **Meta envía webhook** a tu servidor (`/api/v1/whatsapp/webhook`)
3. **Bot procesa mensaje**:
   - Guarda mensaje en BD
   - Busca cliente por número de teléfono
   - Genera respuesta automática
   - Envía respuesta al cliente
   - Guarda respuesta en BD
4. **Conversación disponible** en el CRM

---

## 📋 **Configuración Requerida**

### **1. Webhook en Meta Developers**

1. Ve a [Meta Developers](https://developers.facebook.com/)
2. Selecciona tu App → WhatsApp → Configuration
3. Configura Webhook:
   - **Callback URL**: `https://tu-dominio.com/api/v1/whatsapp/webhook`
   - **Verify Token**: El mismo que configuraste en tu sistema
   - **Webhook Fields**: Marca `messages` y `message_status`

### **2. Verificar Webhook**

Meta enviará un GET request para verificar:
- Tu servidor debe responder con el `hub.challenge`
- El endpoint ya está implementado: `GET /api/v1/whatsapp/webhook`

### **3. Activar Webhook**

Una vez verificado, activa el webhook en Meta Developers.

---

## 🤖 **Respuestas del Bot**

### **Respuestas Básicas Implementadas:**

1. **Saludos**:
   - "Hola", "Buenos días", etc.
   - Respuesta: Saludo personalizado con nombre del cliente

2. **Solicitud de cédula**:
   - Si el cliente menciona "cedula" o "cédula"
   - Respuesta: Solicita número de cédula

3. **Respuestas por defecto**:
   - Si no hay cliente identificado: Solicita cédula
   - Si hay cliente: Ofrece ayuda con préstamos, cuotas, pagos

### **Próximas Mejoras:**

- ✅ Integración con Chat AI para respuestas inteligentes
- ✅ Consultas automáticas de préstamos y cuotas
- ✅ Respuestas basadas en datos del cliente

---

## 📊 **Ver Conversaciones en el CRM**

### **Endpoints Disponibles:**

#### **1. Listar Todas las Conversaciones:**

```http
GET /api/v1/conversaciones-whatsapp?page=1&per_page=20
```

**Filtros opcionales:**
- `cliente_id`: Filtrar por cliente
- `from_number`: Filtrar por número
- `direccion`: `INBOUND` o `OUTBOUND`

#### **2. Obtener Conversación Específica:**

```http
GET /api/v1/conversaciones-whatsapp/{conversacion_id}
```

#### **3. Conversaciones de un Cliente:**

```http
GET /api/v1/conversaciones-whatsapp/cliente/{cliente_id}?page=1&per_page=50
```

#### **4. Conversaciones de un Número:**

```http
GET /api/v1/conversaciones-whatsapp/numero/{numero}?page=1&per_page=50
```

#### **5. Estadísticas:**

```http
GET /api/v1/conversaciones-whatsapp/estadisticas
```

**Retorna:**
- Total de conversaciones
- Inbound vs Outbound
- Con cliente identificado vs sin identificar
- Respuestas enviadas
- Últimas 24 horas

---

## 🔍 **Estructura de Datos**

### **Tabla `conversaciones_whatsapp`:**

```sql
- id: ID único
- message_id: ID de Meta
- from_number: Número que envía
- to_number: Número que recibe
- message_type: text, image, document, etc.
- body: Contenido del mensaje
- timestamp: Fecha/hora del mensaje
- direccion: INBOUND o OUTBOUND
- cliente_id: ID del cliente (si se encontró)
- procesado: Si fue procesado por el bot
- respuesta_enviada: Si se envió respuesta
- respuesta_bot: Respuesta generada por el bot
- respuesta_meta_id: ID de mensaje de respuesta en Meta
```

---

## 🧪 **Pruebas**

### **1. Probar Webhook Localmente:**

Usa [ngrok](https://ngrok.com/) para exponer tu servidor local:

```bash
ngrok http 8000
```

Luego configura la URL de ngrok en Meta Developers.

### **2. Enviar Mensaje de Prueba:**

1. Envía un mensaje desde WhatsApp a tu número de negocio
2. Verifica en los logs que se procesó
3. Verifica que se guardó en BD
4. Verifica que se envió respuesta

### **3. Ver Conversaciones:**

```bash
# Listar todas
curl http://localhost:8000/api/v1/conversaciones-whatsapp

# Por cliente
curl http://localhost:8000/api/v1/conversaciones-whatsapp/cliente/1

# Estadísticas
curl http://localhost:8000/api/v1/conversaciones-whatsapp/estadisticas
```

---

## ⚠️ **Notas Importantes**

1. **Webhook debe ser HTTPS** en producción
2. **Webhook debe ser accesible** desde internet
3. **Verify Token** debe coincidir con el configurado
4. **Rate Limits** de Meta aplican también a webhooks
5. **Ventana de 24 horas**: Cuando un cliente envía mensaje, se abre la ventana para enviar mensajes libres

---

## 🚀 **Próximos Pasos**

1. **Crear migración** para la tabla `conversaciones_whatsapp`
2. **Crear interfaz frontend** para ver conversaciones
3. **Integrar con Chat AI** para respuestas más inteligentes
4. **Agregar comandos** específicos (ej: "consultar préstamo", "ver cuotas")
5. **Notificaciones** cuando lleguen mensajes nuevos

---

## 🔗 **Referencias**

- [Meta WhatsApp Business API - Webhooks](https://developers.facebook.com/docs/whatsapp/cloud-api/webhooks)
- [Documento de Configuración WhatsApp](Documentos/General/Configuracion/GUIA_CONFIGURACION_WHATSAPP_META.md)

