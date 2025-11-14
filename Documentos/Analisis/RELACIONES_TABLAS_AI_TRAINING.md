# 🔗 ANÁLISIS DE RELACIONES - TABLAS AI TRAINING

**Fecha:** 2025-01-14

## 📊 ESTADO ACTUAL DE RELACIONES

### ✅ Relaciones Existentes

1. **ConversacionAI**:
   - ✅ `usuario_id` → `users.id` (ForeignKey)
   - ✅ `relationship("User")` (ORM)

2. **DocumentoEmbedding**:
   - ✅ `documento_id` → `documentos_ai.id` (ForeignKey)
   - ✅ `relationship("DocumentoAI")` (ORM)

3. **FineTuningJob**:
   - ❌ NO tiene ForeignKeys a tablas base

4. **ModeloRiesgo**:
   - ❌ NO tiene ForeignKeys a tablas base

### ❌ Relaciones Faltantes con Tablas Base

Las tablas de AI training **NO están conectadas** a las tablas base del negocio:

- ❌ **ConversacionAI** NO tiene relación con:
  - `clientes` (no sabe qué cliente generó la conversación)
  - `prestamos` (no sabe sobre qué préstamo se preguntó)
  - `pagos` (no sabe sobre qué pago se consultó)

- ❌ **ModeloRiesgo** NO tiene relación con:
  - `prestamos` (no sabe qué préstamos analizó)
  - `clientes` (no sabe qué clientes evaluó)

- ❌ **FineTuningJob** NO tiene relación con:
  - `conversaciones_ai` (no sabe qué conversaciones usó)

## 🔧 RECOMENDACIONES

### Opcional pero Recomendado:

1. **ConversacionAI** podría tener:
   - `cliente_id` (opcional) - Si la conversación es sobre un cliente específico
   - `prestamo_id` (opcional) - Si la conversación es sobre un préstamo específico

2. **ModeloRiesgo** podría tener:
   - `prestamo_id` (opcional) - Si el modelo fue usado para evaluar un préstamo específico
   - O simplemente mantenerlo independiente (solo metadatos)

3. **FineTuningJob** podría tener:
   - Tabla intermedia `fine_tuning_job_conversaciones` para relacionar jobs con conversaciones

## ✅ CONCLUSIÓN

**Estado Actual:** Las tablas están conectadas mínimamente:
- ✅ ConversacionAI → users
- ✅ DocumentoEmbedding → documentos_ai
- ❌ NO conectadas a tablas base del negocio (clientes, préstamos, pagos)

**¿Es necesario?** Depende del caso de uso:
- Si solo necesitas entrenar modelos genéricos → NO es necesario
- Si necesitas rastrear conversaciones por cliente/préstamo → SÍ es necesario

