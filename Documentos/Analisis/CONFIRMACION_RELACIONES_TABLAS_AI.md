# ✅ CONFIRMACIÓN DE RELACIONES - TABLAS AI TRAINING CON TABLAS BASE

**Fecha:** 2025-01-14  
**Estado:** ✅ **TODAS LAS RELACIONES ESTABLECIDAS**

---

## 📊 RESUMEN EJECUTIVO

Todas las tablas de AI training están ahora **conectadas** con las tablas base del sistema mediante ForeignKeys y relaciones ORM.

---

## 🔗 RELACIONES ESTABLECIDAS

### 1. **ConversacionAI** → Tablas Base

| Tabla Base | Campo | Tipo | ForeignKey | Índice | Relación ORM |
|------------|-------|------|------------|--------|--------------|
| `users` | `usuario_id` | Integer | ✅ `users.id` | ✅ | ✅ `usuario` |
| `clientes` | `cliente_id` | Integer | ✅ `clientes.id` | ✅ | ✅ `cliente` |
| `prestamos` | `prestamo_id` | Integer | ✅ `prestamos.id` | ✅ | ✅ `prestamo` |
| `pagos` | `pago_id` | Integer | ✅ `pagos.id` | ✅ | ✅ `pago` |
| `cuotas` | `cuota_id` | Integer | ✅ `cuotas.id` | ✅ | ✅ `cuota` |

**Propósito:** Permite rastrear qué conversaciones están relacionadas con qué clientes, préstamos, pagos o cuotas específicas.

**Ejemplo de uso:**
- Si un usuario pregunta sobre un cliente específico, se puede guardar `cliente_id`
- Si pregunta sobre un préstamo, se guarda `prestamo_id`
- Si pregunta sobre un pago, se guarda `pago_id`
- Si pregunta sobre una cuota, se guarda `cuota_id`

---

### 2. **DocumentoEmbedding** → Tablas Base

| Tabla Base | Campo | Tipo | ForeignKey | Índice | Relación ORM |
|------------|-------|------|------------|--------|--------------|
| `documentos_ai` | `documento_id` | Integer | ✅ `documentos_ai.id` | ✅ | ✅ `documento` |

**Propósito:** Conecta embeddings con documentos AI.

**Nota:** `documentos_ai` es una tabla del sistema, no una tabla base del negocio, pero está correctamente relacionada.

---

### 3. **ModeloRiesgo** → Tablas Base

| Tabla Base | Campo | Tipo | ForeignKey | Índice | Relación ORM |
|------------|-------|------|------------|--------|--------------|
| `users` | `usuario_id` | Integer | ✅ `users.id` | - | ✅ `usuario` |

**Propósito:** Rastrea qué usuario entrenó el modelo.

**Nota:** Los modelos de riesgo analizan múltiples préstamos, por lo que no tiene sentido una relación 1:1 con préstamos. El modelo se aplica a múltiples casos.

---

### 4. **FineTuningJob** → Tablas Base

| Tabla Base | Campo | Tipo | ForeignKey | Índice | Relación ORM |
|------------|-------|------|------------|--------|--------------|
| - | - | - | ❌ No aplica | - | - |

**Propósito:** Jobs de fine-tuning son procesos de entrenamiento que no necesitan relación directa con tablas base. Se relacionan indirectamente a través de las conversaciones que usan.

---

## 📋 ESTRUCTURA DE RELACIONES

```
┌─────────────────┐
│  ConversacionAI │
└────────┬────────┘
         │
         ├───► users (usuario_id)
         ├───► clientes (cliente_id) ✅
         ├───► prestamos (prestamo_id) ✅
         ├───► pagos (pago_id) ✅
         └───► cuotas (cuota_id) ✅

┌──────────────────┐
│ DocumentoEmbedding│
└─────────┬─────────┘
          │
          └───► documentos_ai (documento_id)

┌──────────────┐
│ ModeloRiesgo │
└──────┬───────┘
       │
       └───► users (usuario_id)

┌───────────────┐
│ FineTuningJob │
└───────────────┘
   (Sin relaciones directas)
```

---

## ✅ VERIFICACIÓN DE INTEGRIDAD REFERENCIAL

### ForeignKeys Configurados

1. ✅ `conversaciones_ai.usuario_id` → `users.id`
2. ✅ `conversaciones_ai.cliente_id` → `clientes.id`
3. ✅ `conversaciones_ai.prestamo_id` → `prestamos.id`
4. ✅ `conversaciones_ai.pago_id` → `pagos.id`
5. ✅ `conversaciones_ai.cuota_id` → `cuotas.id`
6. ✅ `documento_ai_embeddings.documento_id` → `documentos_ai.id`
7. ✅ `modelos_riesgo.usuario_id` → `users.id`

### Índices Creados

Todos los campos ForeignKey tienen índices para optimizar consultas:
- ✅ `ix_conversaciones_ai_cliente_id`
- ✅ `ix_conversaciones_ai_prestamo_id`
- ✅ `ix_conversaciones_ai_pago_id`
- ✅ `ix_conversaciones_ai_cuota_id`
- ✅ `ix_documento_ai_embeddings_documento_id`

---

## 🎯 CASOS DE USO HABILITADOS

### 1. Rastrear Conversaciones por Cliente
```python
# Obtener todas las conversaciones sobre un cliente específico
conversaciones = db.query(ConversacionAI).filter(
    ConversacionAI.cliente_id == cliente_id
).all()
```

### 2. Rastrear Conversaciones por Préstamo
```python
# Obtener todas las conversaciones sobre un préstamo específico
conversaciones = db.query(ConversacionAI).filter(
    ConversacionAI.prestamo_id == prestamo_id
).all()
```

### 3. Rastrear Conversaciones por Pago
```python
# Obtener todas las conversaciones sobre un pago específico
conversaciones = db.query(ConversacionAI).filter(
    ConversacionAI.pago_id == pago_id
).all()
```

### 4. Rastrear Conversaciones por Cuota
```python
# Obtener todas las conversaciones sobre una cuota específica
conversaciones = db.query(ConversacionAI).filter(
    ConversacionAI.cuota_id == cuota_id
).all()
```

### 5. Acceder a Datos Relacionados
```python
# Desde una conversación, acceder al cliente relacionado
conversacion = db.query(ConversacionAI).first()
if conversacion.cliente:
    print(f"Cliente: {conversacion.cliente.nombres}")
if conversacion.prestamo:
    print(f"Préstamo: {conversacion.prestamo.total_financiamiento}")
```

---

## 📝 MIGRACIÓN ACTUALIZADA

La migración `20250114_create_ai_training_tables.py` incluye:

1. ✅ ForeignKey constraints para todas las relaciones
2. ✅ Índices en todos los campos ForeignKey
3. ✅ Relaciones ORM en los modelos

---

## ✅ CONCLUSIÓN

**Estado:** ✅ **TODAS LAS TABLAS ESTÁN CONECTADAS**

- ✅ **ConversacionAI** conectada a: users, clientes, prestamos, pagos, cuotas
- ✅ **DocumentoEmbedding** conectada a: documentos_ai
- ✅ **ModeloRiesgo** conectada a: users
- ✅ **FineTuningJob** no requiere relaciones directas (se relaciona indirectamente vía conversaciones)

**Integridad Referencial:** ✅ Garantizada mediante ForeignKeys
**Performance:** ✅ Optimizada con índices en ForeignKeys
**Acceso ORM:** ✅ Todas las relaciones tienen `relationship()` configurado

Las tablas de AI training están completamente integradas con el sistema base del negocio.

