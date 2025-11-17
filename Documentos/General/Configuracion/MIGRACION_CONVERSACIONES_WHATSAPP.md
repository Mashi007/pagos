# 📋 Migración: Tabla conversaciones_whatsapp

## ✅ **Migración Creada**

**Archivo**: `backend/alembic/versions/20250117_create_conversaciones_whatsapp.py`

### **Información de la Migración:**

- **Revision ID**: `20250117_conversaciones_whatsapp`
- **Down Revision**: `20251114_05_modelos_impago_cuotas`
- **Fecha**: 2025-01-17

---

## 📊 **Tabla Creada: `conversaciones_whatsapp`**

### **Campos:**

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id` | Integer | Primary Key |
| `message_id` | String(100) | ID del mensaje en Meta (único) |
| `from_number` | String(20) | Número que envía el mensaje |
| `to_number` | String(20) | Número que recibe el mensaje |
| `message_type` | String(20) | Tipo: text, image, document, etc. |
| `body` | Text | Contenido del mensaje |
| `timestamp` | DateTime | Timestamp del mensaje (de Meta) |
| `direccion` | String(10) | INBOUND o OUTBOUND |
| `cliente_id` | Integer | FK a clientes.id (nullable) |
| `procesado` | Boolean | Si fue procesado por el bot |
| `respuesta_enviada` | Boolean | Si se envió respuesta |
| `respuesta_id` | Integer | FK a conversaciones_whatsapp.id (self-reference) |
| `respuesta_bot` | Text | Respuesta generada por el bot |
| `respuesta_meta_id` | String(100) | ID de mensaje de respuesta en Meta |
| `error` | Text | Error al procesar o responder |
| `creado_en` | DateTime | Fecha de creación |
| `actualizado_en` | DateTime | Fecha de actualización |

### **Índices Creados:**

- `ix_conversaciones_whatsapp_id` - Índice en `id`
- `ix_conversaciones_whatsapp_message_id` - Índice único en `message_id`
- `ix_conversaciones_whatsapp_from_number` - Índice en `from_number`
- `ix_conversaciones_whatsapp_timestamp` - Índice en `timestamp`
- `ix_conversaciones_whatsapp_cliente_id` - Índice en `cliente_id`
- `ix_conversaciones_whatsapp_creado_en` - Índice en `creado_en`

### **Foreign Keys:**

- `cliente_id` → `clientes.id`
- `respuesta_id` → `conversaciones_whatsapp.id` (self-reference)

---

## 🚀 **Cómo Ejecutar la Migración**

### **Opción 1: Usando Alembic Directamente**

```bash
cd backend
alembic upgrade head
```

### **Opción 2: Verificar Estado**

```bash
cd backend
alembic current
alembic history
```

### **Opción 3: Aplicar Migración Específica**

```bash
cd backend
alembic upgrade 20250117_conversaciones_whatsapp
```

### **Opción 4: Revertir Migración (si es necesario)**

```bash
cd backend
alembic downgrade -1
```

---

## ✅ **Verificación**

Después de ejecutar la migración, verifica que la tabla se creó correctamente:

```sql
-- Verificar que la tabla existe
SELECT table_name 
FROM information_schema.tables 
WHERE table_name = 'conversaciones_whatsapp';

-- Ver estructura de la tabla
\d conversaciones_whatsapp  -- PostgreSQL
-- o
DESCRIBE conversaciones_whatsapp;  -- MySQL
```

---

## 📝 **Notas Importantes**

1. **La migración verifica** si la tabla ya existe antes de crearla
2. **Si la tabla existe**, se omite la creación (no falla)
3. **El downgrade** elimina la tabla y todos sus índices de forma segura
4. **Los índices** se crean automáticamente para optimizar consultas

---

## 🔗 **Referencias**

- [Documento del Bot WhatsApp](Documentos/General/Configuracion/BOT_WHATSAPP_CRM.md)
- [Modelo ConversacionWhatsApp](../backend/app/models/conversacion_whatsapp.py)

