# ✅ Sistema de Notificaciones Email - Implementación Completa

## 📦 Estado de Implementación

### ✅ Backend Completado

#### 1. **Modelos y Schemas**
- ✅ `backend/app/models/notificacion_plantilla.py` - Modelo de plantillas
- ✅ `backend/app/schemas/notificacion_plantilla.py` - Schemas de validación

#### 2. **Servicios**
- ✅ `backend/app/services/notificacion_automatica_service.py` - Servicio de notificaciones automáticas
- ✅ `backend/app/services/email_service.py` - Servicio de email existente

#### 3. **Endpoints**
- ✅ `GET /api/v1/notificaciones/plantillas` - Listar plantillas
- ✅ `POST /api/v1/notificaciones/plantillas` - Crear plantilla
- ✅ `PUT /api/v1/notificaciones/plantillas/{id}` - Actualizar plantilla
- ✅ `DELETE /api/v1/notificaciones/plantillas/{id}` - Eliminar plantilla
- ✅ `GET /api/v1/notificaciones/plantillas/{id}` - Obtener plantilla
- ✅ `POST /api/v1/notificaciones/plantillas/{id}/enviar` - Enviar con plantilla
- ✅ `POST /api/v1/notificaciones/automaticas/procesar` - Procesar automáticas
- ✅ `GET /api/v1/configuracion/email/configuracion` - Ver config email
- ✅ `PUT /api/v1/configuracion/email/configuracion` - Actualizar config email
- ✅ `POST /api/v1/configuracion/email/probar` - Probar config email

#### 4. **Migración de Base de Datos**
- ✅ `20251028_add_notificacion_plantillas.py` - Lista para ejecutar

## 🎯 Características Implementadas

### **Plantillas con Variables Dinámicas**
```python
# Las plantillas soportan variables usando {{variables}}
# Ejemplo:
"Estimado {{nombre}}, su cuota de {{monto}} vence el {{fecha_vencimiento}}"
```

**Variables Disponibles:**
- `{{nombre}}` - Nombre del cliente
- `{{monto}}` - Monto de la cuota
- `{{fecha_vencimiento}}` - Fecha de vencimiento
- `{{numero_cuota}}` - Número de cuota
- `{{credito_id}}` - ID del crédito
- `{{cedula}}` - Cédula del cliente
- `{{dias_atraso}}` - Días de atraso (si aplica)

### **Notificaciones Automáticas por Fechas**
El sistema envía notificaciones automáticas en:
- **5 días antes** del vencimiento
- **3 días antes** del vencimiento
- **1 día antes** del vencimiento
- **Día 0** (día de vencimiento)
- **1 día atrasado**
- **3 días atrasado**
- **5 días atrasado**

### **Zona Horaria Caracas**
Todas las fechas se manejan en zona horaria `America/Caracas`

## 📝 Configuración Requerida

### 1. **Configurar Email Gmail**

Ir a: **Configuración > Configuración de Email**

Campos:
- **SMTP Host:** `smtp.gmail.com`
- **SMTP Port:** `587`
- **SMTP User:** `tu-email@gmail.com`
- **SMTP Password:** `tu-app-password` (no la contraseña normal)
- **From Email:** `tu-email@gmail.com`
- **From Name:** `RapiCredit`
- **SMTP Use TLS:** `true`

**Nota:** Para Gmail necesitas generar una "App Password" en tu cuenta de Google:
1. Ve a tu cuenta de Google
2. Seguridad > Verificación en 2 pasos (habilitar)
3. Contraseñas de aplicaciones > Generar nueva

### 2. **Crear Plantillas Iniciales**

Debes crear 7 plantillas con estos tipos:

#### **Plantilla 1: 5 Días Antes**
- **Nombre:** Recordatorio de Pago - 5 Días
- **Tipo:** `PAGO_5_DIAS_ANTES`
- **Asunto:** `Recordatorio de Pago - Cuota {{numero_cuota}} - 5 días restantes`
- **Cuerpo:** (ver ejemplo abajo)

#### **Plantilla 2: 3 Días Antes**
- **Nombre:** Recordatorio de Pago - 3 Días
- **Tipo:** `PAGO_3_DIAS_ANTES`

#### **Plantilla 3: 1 Día Antes**
- **Nombre:** Recordatorio de Pago - 1 Día
- **Tipo:** `PAGO_1_DIA_ANTES`

#### **Plantilla 4: Día 0**
- **Nombre:** Recordatorio de Pago - Día de Vencimiento
- **Tipo:** `PAGO_DIA_0`

#### **Plantilla 5: 1 Día Atrasado**
- **Nombre:** Alerta de Pago Atrasado - 1 Día
- **Tipo:** `PAGO_1_DIA_ATRASADO`

#### **Plantilla 6: 3 Días Atrasado**
- **Nombre:** Alerta de Pago Atrasado - 3 Días
- **Tipo:** `PAGO_3_DIAS_ATRASADO`

#### **Plantilla 7: 5 Días Atrasado**
- **Nombre:** Alerta de Pago Atrasado - 5 Días
- **Tipo:** `PAGO_5_DIAS_ATRASADO`

## 📄 Ejemplo de Plantilla HTML

```html
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background-color: #2563eb; color: white; padding: 20px; text-align: center; }
        .content { padding: 20px; background-color: #f9fafb; }
        .details { background-color: white; padding: 15px; margin: 15px 0; border-radius: 5px; }
        .footer { text-align: center; padding: 20px; color: #666; font-size: 12px; }
        .alert { background-color: #fef2f2; border-left: 4px solid #ef4444; padding: 15px; margin: 15px 0; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📧 RapiCredit</h1>
        </div>
        
        <div class="content">
            <h2>Recordatorio de Pago</h2>
            
            <p>Estimado/a <strong>{{nombre}}</strong>,</p>
            
            <p>Le recordamos que tiene un pago pendiente:</p>
            
            <div class="details">
                <p><strong>📋 Crédito ID:</strong> {{credito_id}}</p>
                <p><strong>💵 Cuota:</strong> {{numero_cuota}}</p>
                <p><strong>💰 Monto:</strong> {{monto}} VES</p>
                <p><strong>📅 Fecha de vencimiento:</strong> {{fecha_vencimiento}}</p>
            </div>
            
            <div class="alert">
                <p><strong>⚠️ Importante:</strong></p>
                <p>Por favor, realice su pago a tiempo para evitar cargos adicionales.</p>
            </div>
            
            <p>Si ya realizó el pago, puede ignorar este mensaje.</p>
            
            <p>Saludos cordiales,<br>
            <strong>Equipo RapiCredit</strong></p>
        </div>
        
        <div class="footer">
            <p>Este es un email automático, por favor no responda.</p>
            <p>© 2025 RapiCredit. Todos los derechos reservados.</p>
        </div>
    </div>
</body>
</html>
```

## 🔄 Cómo Funciona

### **Proceso Automático**

1. **Servicio monitorea cuotas pendientes**
   - Consulta cuotas con estado PENDIENTE, ATRASADO o PARCIAL
   - Calcula días hasta/siguientes a vencimiento

2. **Selecciona plantilla según días**
   - 5 días antes → Plantilla PAGO_5_DIAS_ANTES
   - 3 días antes → Plantilla PAGO_3_DIAS_ANTES
   - etc.

3. **Envía notificación**
   - Reemplaza variables en plantilla
   - Envía email al cliente
   - Registra notificación en BD

4. **Evita duplicados**
   - Verifica si ya se envió notificación del mismo tipo hoy
   - No envía duplicados

### **Endpoint para Ejecutar Manualmente**

```bash
POST /api/v1/notificaciones/automaticas/procesar
Authorization: Bearer <token>
```

**Respuesta:**
```json
{
  "mensaje": "Procesamiento de notificaciones automáticas completado",
  "estadisticas": {
    "procesadas": 10,
    "enviadas": 8,
    "errores": 1,
    "sin_plantilla": 1,
    "sin_email": 0
  }
}
```

## 🕐 Scheduler (Cron Job)

Para automatizar, configura un cron job que llame al endpoint:

```bash
# Ejecutar cada hora
0 * * * * curl -X POST https://tu-api.com/api/v1/notificaciones/automaticas/procesar -H "Authorization: Bearer TOKEN"
```

O usa Render Cron Jobs o similar.

## ⚠️ Pendientes

### **Frontend**
- ⏳ Panel de control en módulo Notificaciones
- ⏳ UI para gestionar plantillas
- ⏳ UI para configurar email
- ⏳ Historial de notificaciones enviadas

## 🧪 Pruebas

### 1. **Probar Configuración de Email**
```bash
POST /api/v1/configuracion/email/probar
```

### 2. **Crear Plantilla de Prueba**
```bash
POST /api/v1/notificaciones/plantillas
{
  "nombre": "Prueba - 5 Días",
  "tipo": "PAGO_5_DIAS_ANTES",
  "asunto": "Recordatorio - 5 días",
  "cuerpo": "Estimado {{nombre}}, debe {{monto}}",
  "activa": true
}
```

### 3. **Enviar Notificación Manual**
```bash
POST /api/v1/notificaciones/plantillas/{id}/enviar
{
  "cliente_id": 1,
  "variables": {
    "nombre": "Juan Pérez",
    "monto": "500.00"
  }
}
```

### 4. **Ejecutar Procesamiento Automático**
```bash
POST /api/v1/notificaciones/automaticas/procesar
```

## ✅ Checklist de Implementación

- [x] Modelo de plantillas creado
- [x] Schemas de validación creados
- [x] Migración de BD creada
- [x] Servicio de notificaciones automáticas implementado
- [x] Endpoints CRUD de plantillas implementados
- [x] Endpoint de configuración de email implementado
- [x] Endpoint para procesar notificaciones automáticas implementado
- [x] Soporte para variables dinámicas `{{variables}}`
- [x] Zona horaria Caracas configurada
- [ ] Ejecutar migración en producción
- [ ] Configurar email Gmail
- [ ] Crear 7 plantillas iniciales
- [ ] Configurar cron job/scheduler
- [ ] Panel de control frontend
- [ ] UI para gestionar plantillas
- [ ] Historial de notificaciones

## 🚀 Siguiente Paso

**Ejecutar migración en producción:**
```bash
alembic upgrade head
```

Luego crear las plantillas iniciales usando el API.

