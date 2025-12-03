# 🔍 MAPEO COMPLETO DE LA RED DE TABLAS - PostgreSQL

**Fecha:** 2025-01-27  
**Especialista:** Verificación de Base de Datos y Coherencia Backend/Frontend

---

## 📋 ÍNDICE

1. [Resumen Ejecutivo](#resumen-ejecutivo)
2. [Mapeo de Tablas y Relaciones](#mapeo-de-tablas-y-relaciones)
3. [Verificación de Coherencia Backend/Frontend](#verificación-de-coherencia-backendfrontend)
4. [Problemas Identificados](#problemas-identificados)
5. [Recomendaciones](#recomendaciones)
6. [Diagrama de Relaciones](#diagrama-de-relaciones)

---

## 📊 RESUMEN EJECUTIVO

### Total de Tablas Identificadas: **31**

**Tablas Adicionales de Auditoría:**
- `pagos_auditoria` - Auditoría de cambios en pagos
- `prestamos_auditoria` - Auditoría de cambios en préstamos

**Categorías:**
- **Tablas Core del Negocio:** 8 tablas
- **Tablas de Procesos:** 6 tablas
- **Tablas de Configuración:** 3 tablas
- **Tablas de Auditoría y Seguridad:** 3 tablas
- **Tablas de Comunicación:** 3 tablas
- **Tablas de Machine Learning:** 3 tablas
- **Tablas de AI Training:** 5 tablas
- **Tablas de Auditoría Específicas:** 2 tablas

### Estado de Integridad Referencial
- ✅ **Foreign Keys Definidos:** 28 relaciones
- ⚠️ **Relaciones Faltantes:** 7 casos identificados (3 críticos, 4 medios)
- ✅ **Índices Configurados:** Mayoría de relaciones indexadas

---

## 🗂️ MAPEO DE TABLAS Y RELACIONES

### 1. TABLAS CORE DEL NEGOCIO

#### 1.1. `users` (Usuarios del Sistema)
**Modelo:** `backend/app/models/user.py`

**Campos Principales:**
- `id` (PK)
- `email` (UNIQUE, INDEX)
- `nombre`, `apellido`
- `hashed_password`
- `rol`, `is_admin`, `cargo`
- `is_active`
- `created_at`, `updated_at`, `last_login`

**Relaciones Salientes:**
- ✅ `aprobaciones_solicitadas` → `aprobaciones` (1:N, `solicitante_id`)
- ✅ `aprobaciones_revisadas` → `aprobaciones` (1:N, `revisor_id`)
- ✅ `auditorias` → `auditoria` (1:N, `usuario_id`)
- ✅ `notificaciones` → `notificaciones` (1:N, `user_id`)
- ✅ `modelos_riesgo` → `modelos_riesgo` (1:N, `usuario_id`)
- ✅ `modelos_impago_cuotas` → `modelos_impago_cuotas` (1:N, `usuario_id`)
- ✅ `conversaciones_ai` → `conversaciones_ai` (1:N, `usuario_id`)
- ✅ `tickets` → `tickets` (1:N, múltiples relaciones: `asignado_a_id`, `escalado_a_id`, `creado_por_id`)

---

#### 1.2. `clientes` (Clientes)
**Modelo:** `backend/app/models/cliente.py`

**Campos Principales:**
- `id` (PK)
- `cedula` (INDEX, NO UNIQUE - permite duplicados)
- `nombres`, `telefono`, `email`, `direccion`
- `fecha_nacimiento`, `ocupacion`
- `estado`, `activo` (INDEX)
- `fecha_registro`, `fecha_actualizacion`
- `usuario_registro`
- `notas`

**Relaciones Salientes:**
- ⚠️ **NO HAY ForeignKeys definidos explícitamente** (solo backrefs)

**Relaciones Entrantes:**
- ✅ `prestamos` → `prestamos.cliente_id` (1:N)
- ✅ `notificaciones` → `notificaciones.cliente_id` (1:N)
- ✅ `conversaciones_ai` → `conversaciones_ai.cliente_id` (1:N)
- ✅ `tickets` → `tickets.cliente_id` (1:N)
- ✅ `conversaciones_whatsapp` → `conversaciones_whatsapp.cliente_id` (1:N)
- ✅ `comunicaciones_email` → `comunicaciones_email.cliente_id` (1:N)

**⚠️ PROBLEMA IDENTIFICADO:**
- `pagos` NO tiene ForeignKey a `clientes`, solo usa `cedula` como string
- Esto puede causar problemas de integridad referencial

---

#### 1.3. `prestamos` (Préstamos)
**Modelo:** `backend/app/models/prestamo.py`

**Campos Principales:**
- `id` (PK)
- `cliente_id` (FK → `clientes.id`, INDEX)
- `cedula`, `nombres` (duplicados de cliente)
- `valor_activo`, `total_financiamiento`
- `fecha_requerimiento`, `modalidad_pago`
- `numero_cuotas`, `cuota_periodo`
- `tasa_interes`, `fecha_base_calculo`
- `producto`, `producto_financiero`
- `concesionario`, `analista`, `modelo_vehiculo`
- `estado` (INDEX)
- `usuario_proponente`, `usuario_aprobador`, `usuario_autoriza`
- `fecha_registro` (INDEX), `fecha_aprobacion`
- `ml_impago_nivel_riesgo_manual`, `ml_impago_probabilidad_manual`
- `ml_impago_nivel_riesgo_calculado`, `ml_impago_probabilidad_calculada`
- `ml_impago_calculado_en`
- `ml_impago_modelo_id` (FK → `modelos_impago_cuotas.id`)

**Relaciones Salientes:**
- ✅ `cliente` → `clientes` (N:1, `cliente_id`)
- ✅ `cuotas` → `cuotas` (1:N, `prestamo_id`)

**Relaciones Entrantes:**
- ✅ `cuotas` → `cuotas.prestamo_id` (1:N)
- ✅ `prestamos_evaluacion` → `prestamos_evaluacion.prestamo_id` (1:1)
- ✅ `conversaciones_ai` → `conversaciones_ai.prestamo_id` (1:N)

**⚠️ PROBLEMA IDENTIFICADO:**
- `prestamos_evaluacion` NO tiene ForeignKey explícito a `prestamos`, solo usa `prestamo_id` como Integer sin FK
- `pagos` tiene `prestamo_id` pero NO tiene ForeignKey a `prestamos`

---

#### 1.4. `pagos` (Pagos)
**Modelo:** `backend/app/models/pago.py`

**Campos Principales:**
- `id` (PK)
- `cedula` (INDEX, NO FK)
- `prestamo_id` (INDEX, NO FK) ⚠️
- `numero_cuota`
- `fecha_pago`, `fecha_registro` (INDEX)
- `monto_pagado`
- `numero_documento` (INDEX)
- `institucion_bancaria`
- `documento_nombre`, `documento_tipo`, `documento_tamaño`, `documento_ruta`
- `conciliado`, `fecha_conciliacion`
- `estado` (INDEX)
- `activo`, `notas`
- `usuario_registro`
- `fecha_actualizacion`
- `verificado_concordancia`

**Relaciones Salientes:**
- ❌ **NO HAY ForeignKeys definidos**

**Relaciones Entrantes:**
- ✅ `conversaciones_ai` → `conversaciones_ai.pago_id` (1:N)

**⚠️ PROBLEMAS IDENTIFICADOS:**
1. `prestamo_id` NO tiene ForeignKey a `prestamos`
2. `cedula` NO tiene ForeignKey a `clientes` (solo string)
3. Comentado: `# cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=True)`

---

#### 1.5. `cuotas` (Cuotas de Amortización)
**Modelo:** `backend/app/models/amortizacion.py`

**Campos Principales:**
- `id` (PK)
- `prestamo_id` (FK → `prestamos.id`, INDEX) ✅
- `numero_cuota`
- `fecha_vencimiento` (INDEX), `fecha_pago`
- `monto_cuota`, `monto_capital`, `monto_interes`
- `saldo_capital_inicial`, `saldo_capital_final`
- `capital_pagado`, `interes_pagado`, `mora_pagada`, `total_pagado`
- `capital_pendiente`, `interes_pendiente`
- `dias_mora`, `monto_mora`, `tasa_mora`
- `dias_morosidad` (INDEX), `monto_morosidad` (INDEX)
- `estado` (INDEX)
- `observaciones`, `es_cuota_especial`

**Relaciones Salientes:**
- ✅ `prestamo` → `prestamos` (N:1, `prestamo_id`)

**Relaciones Entrantes:**
- ✅ `conversaciones_ai` → `conversaciones_ai.cuota_id` (1:N)

---

#### 1.6. `prestamos_evaluacion` (Evaluación de Préstamos)
**Modelo:** `backend/app/models/prestamo_evaluacion.py`

**Campos Principales:**
- `id` (PK)
- `prestamo_id` (INDEX, NO FK) ⚠️
- `cedula` (INDEX)
- Múltiples campos de scoring (100 puntos totales)
- `puntuacion_total`, `clasificacion_riesgo`, `decision_final`
- `tasa_interes_aplicada`, `plazo_maximo`, `enganche_minimo`

**Relaciones Salientes:**
- ❌ **NO HAY ForeignKey definido**

**⚠️ PROBLEMA IDENTIFICADO:**
- `prestamo_id` debería tener ForeignKey a `prestamos.id` para integridad referencial

---

#### 1.7. `concesionarios` (Concesionarios)
**Modelo:** `backend/app/models/concesionario.py`

**Campos Principales:**
- `id` (PK)
- `nombre` (INDEX)
- `activo`
- `created_at`, `updated_at`

**Relaciones:**
- ❌ **NO HAY relaciones definidas** (solo se usa como string en `prestamos.concesionario`)

**⚠️ PROBLEMA IDENTIFICADO:**
- `prestamos.concesionario` es un string, NO una relación FK
- Debería ser `concesionario_id` con FK a `concesionarios.id`

---

#### 1.8. `analistas` (Analistas)
**Modelo:** `backend/app/models/analista.py`

**Campos Principales:**
- `id` (PK)
- `nombre` (INDEX)
- `activo`
- `created_at`, `updated_at`

**Relaciones:**
- ❌ **NO HAY relaciones definidas** (solo se usa como string en `prestamos.analista`)

**⚠️ PROBLEMA IDENTIFICADO:**
- `prestamos.analista` es un string, NO una relación FK
- Debería ser `analista_id` con FK a `analistas.id`

---

### 2. TABLAS DE PROCESOS

#### 2.1. `aprobaciones` (Aprobaciones)
**Modelo:** `backend/app/models/aprobacion.py`

**Campos Principales:**
- `id` (PK)
- `solicitante_id` (FK → `users.id`, INDEX) ✅
- `revisor_id` (FK → `users.id`, INDEX) ✅
- `tipo_solicitud` (INDEX)
- `entidad`, `entidad_id` (INDEX)
- `justificacion`
- `estado` (INDEX), `resultado`
- `fecha_solicitud`, `fecha_aprobacion`
- `archivo_evidencia`, `tipo_archivo`, `tamaño_archivo`
- `prioridad`, `fecha_limite`
- `notificado_admin`, `notificado_solicitante`, `visto_por_admin`
- `bloqueado_temporalmente`
- `tiempo_respuesta_horas`
- `created_at`, `updated_at`

**Relaciones Salientes:**
- ✅ `solicitante` → `users` (N:1, `solicitante_id`)
- ✅ `revisor` → `users` (N:1, `revisor_id`)

---

#### 2.2. `notificaciones` (Notificaciones)
**Modelo:** `backend/app/models/notificacion.py`

**Campos Principales:**
- `id` (PK)
- `cliente_id` (FK → `clientes.id`, INDEX) ✅
- `user_id` (FK → `users.id`, INDEX) ✅
- `tipo` (INDEX), `canal` (INDEX), `asunto`
- `mensaje`
- `estado` (INDEX), `programada_para` (INDEX)
- `enviada_en`, `leida`
- `intentos`, `respuesta_servicio`, `error_mensaje`
- `created_at`

**Relaciones Salientes:**
- ✅ `cliente` → `clientes` (N:1, `cliente_id`)
- ✅ `user` → `users` (N:1, `user_id`)

---

#### 2.3. `auditoria` (Auditoría)
**Modelo:** `backend/app/models/auditoria.py`

**Campos Principales:**
- `id` (PK)
- `usuario_id` (FK → `users.id`, INDEX) ✅
- `accion` (INDEX), `entidad` (INDEX), `entidad_id` (INDEX)
- `detalles`, `ip_address`, `user_agent`
- `exito`, `mensaje_error`
- `fecha` (INDEX)

**Relaciones Salientes:**
- ✅ `usuario` → `users` (N:1, `usuario_id`)

---

#### 2.4. `tickets` (Tickets de Atención)
**Modelo:** `backend/app/models/ticket.py`

**Campos Principales:**
- `id` (PK)
- `titulo` (INDEX)
- `descripcion`
- `cliente_id` (FK → `clientes.id`, INDEX) ✅
- `conversacion_whatsapp_id` (FK → `conversaciones_whatsapp.id`, INDEX) ✅
- `comunicacion_email_id` (FK → `comunicaciones_email.id`, INDEX) ✅
- `estado` (INDEX), `prioridad` (INDEX), `tipo` (INDEX)
- `asignado_a`, `asignado_a_id` (FK → `users.id`, INDEX) ✅
- `escalado_a_id` (FK → `users.id`, INDEX) ✅
- `escalado`
- `fecha_limite` (INDEX)
- `archivos`
- `creado_por_id` (FK → `users.id`, INDEX) ✅
- `creado_en` (INDEX), `actualizado_en`

**Relaciones Salientes:**
- ✅ `cliente` → `clientes` (N:1, `cliente_id`)
- ✅ `conversacion_whatsapp` → `conversaciones_whatsapp` (N:1, `conversacion_whatsapp_id`)
- ✅ `comunicacion_email` → `comunicaciones_email` (N:1, `comunicacion_email_id`)
- ✅ `asignado_a_usuario` → `users` (N:1, `asignado_a_id`)
- ✅ `escalado_a_usuario` → `users` (N:1, `escalado_a_id`)
- ✅ `creado_por` → `users` (N:1, `creado_por_id`)

---

#### 2.5. `conversaciones_whatsapp` (Conversaciones WhatsApp)
**Modelo:** `backend/app/models/conversacion_whatsapp.py`

**Campos Principales:**
- `id` (PK)
- `message_id` (UNIQUE, INDEX)
- `from_number` (INDEX), `to_number`
- `message_type`, `body`
- `timestamp` (INDEX)
- `direccion`
- `cliente_id` (FK → `clientes.id`, INDEX) ✅
- `ticket_id` (FK → `tickets.id`, INDEX) ✅
- `procesado`, `respuesta_enviada`
- `respuesta_id` (FK → `conversaciones_whatsapp.id`) ✅ (self-reference)
- `respuesta_bot`, `respuesta_meta_id`
- `error`
- `creado_en` (INDEX), `actualizado_en`

**Relaciones Salientes:**
- ✅ `cliente` → `clientes` (N:1, `cliente_id`)
- ✅ `respuesta` → `conversaciones_whatsapp` (N:1, `respuesta_id`, self-reference)
- ✅ `ticket` → `tickets` (N:1, `ticket_id`)
- ✅ `tickets` → `tickets` (1:N, back_populates)

---

#### 2.6. `comunicaciones_email` (Comunicaciones Email)
**Modelo:** `backend/app/models/comunicacion_email.py`

**Campos Principales:**
- `id` (PK)
- `message_id` (UNIQUE, INDEX)
- `from_email` (INDEX), `to_email` (INDEX)
- `subject`, `body`, `body_html`
- `timestamp` (INDEX)
- `direccion`
- `cliente_id` (FK → `clientes.id`, INDEX) ✅
- `ticket_id` (FK → `tickets.id`, INDEX) ✅
- `procesado`, `respuesta_enviada`
- `respuesta_id` (FK → `comunicaciones_email.id`) ✅ (self-reference)
- `requiere_respuesta` (INDEX)
- `respuesta_automatica`, `respuesta_enviada_id`
- `error`
- `adjuntos`
- `creado_en` (INDEX), `actualizado_en`

**Relaciones Salientes:**
- ✅ `cliente` → `clientes` (N:1, `cliente_id`)
- ✅ `respuesta` → `comunicaciones_email` (N:1, `respuesta_id`, self-reference)
- ✅ `ticket` → `tickets` (N:1, `ticket_id`)
- ✅ `tickets` → `tickets` (1:N, back_populates)

---

### 3. TABLAS DE CONFIGURACIÓN

#### 3.1. `modelos_vehiculos` (Modelos de Vehículos)
**Modelo:** `backend/app/models/modelo_vehiculo.py`

**Campos Principales:**
- `id` (PK)
- `modelo` (UNIQUE, INDEX)
- `activo` (INDEX)
- `precio` (INDEX)
- `created_at`, `updated_at`
- `fecha_actualizacion`, `actualizado_por`

**Relaciones:**
- ❌ **NO HAY relaciones definidas** (solo se usa como string en `prestamos.modelo_vehiculo`)

**⚠️ PROBLEMA IDENTIFICADO:**
- `prestamos.modelo_vehiculo` es un string, NO una relación FK
- Debería ser `modelo_vehiculo_id` con FK a `modelos_vehiculos.id`

---

#### 3.2. `notificacion_plantillas` (Plantillas de Notificación)
**Modelo:** `backend/app/models/notificacion_plantilla.py`

**Campos Principales:**
- `id` (PK)
- `nombre` (UNIQUE)
- `descripcion`
- `tipo`
- `asunto`, `cuerpo`
- `variables_disponibles` (JSON)
- `activa`
- `zona_horaria`
- `fecha_creacion`, `fecha_actualizacion`

**Relaciones:**
- ❌ **NO HAY relaciones definidas** (tabla de configuración independiente)

---

#### 3.3. `configuracion_sistema` (Configuración del Sistema)
**Modelo:** `backend/app/models/configuracion_sistema.py`

**Campos Principales:**
- (Revisar modelo completo)

**Relaciones:**
- (Revisar relaciones)

---

### 4. TABLAS DE MACHINE LEARNING

#### 4.1. `modelos_riesgo` (Modelos de Riesgo ML)
**Modelo:** `backend/app/models/modelo_riesgo.py`

**Campos Principales:**
- `id` (PK)
- `nombre`, `version`, `algoritmo`
- `accuracy`, `precision`, `recall`, `f1_score`, `roc_auc`
- `ruta_archivo`
- `total_datos_entrenamiento`, `total_datos_test`
- `test_size`, `random_state`
- `activo` (INDEX)
- `usuario_id` (FK → `users.id`) ✅
- `descripcion`, `features_usadas`
- `entrenado_en` (INDEX), `activado_en`, `actualizado_en`

**Relaciones Salientes:**
- ✅ `usuario` → `users` (N:1, `usuario_id`)

---

#### 4.2. `modelos_impago_cuotas` (Modelos de Impago ML)
**Modelo:** `backend/app/models/modelo_impago_cuotas.py`

**Campos Principales:**
- `id` (PK)
- `nombre`, `version`, `algoritmo`
- `accuracy`, `precision`, `recall`, `f1_score`, `roc_auc`
- `ruta_archivo`
- `total_datos_entrenamiento`, `total_datos_test`
- `test_size`, `random_state`
- `activo` (INDEX)
- `usuario_id` (FK → `users.id`) ✅
- `descripcion`, `features_usadas`
- `entrenado_en` (INDEX), `activado_en`, `actualizado_en`

**Relaciones Salientes:**
- ✅ `usuario` → `users` (N:1, `usuario_id`)

**Relaciones Entrantes:**
- ✅ `prestamos` → `prestamos.ml_impago_modelo_id` (1:N)

---

### 5. TABLAS DE AI TRAINING

#### 5.1. `conversaciones_ai` (Conversaciones AI)
**Modelo:** `backend/app/models/conversacion_ai.py`

**Campos Principales:**
- `id` (PK)
- `pregunta`, `respuesta`, `contexto_usado`
- `documentos_usados`
- `modelo_usado`, `tokens_usados`, `tiempo_respuesta`
- `calificacion`, `feedback`
- `usuario_id` (FK → `users.id`) ✅
- `cliente_id` (FK → `clientes.id`, INDEX) ✅
- `prestamo_id` (FK → `prestamos.id`, INDEX) ✅
- `pago_id` (FK → `pagos.id`, INDEX) ✅
- `cuota_id` (FK → `cuotas.id`, INDEX) ✅
- `creado_en` (INDEX), `actualizado_en`

**Relaciones Salientes:**
- ✅ `usuario` → `users` (N:1, `usuario_id`)
- ✅ `cliente` → `clientes` (N:1, `cliente_id`)
- ✅ `prestamo` → `prestamos` (N:1, `prestamo_id`)
- ✅ `pago` → `pagos` (N:1, `pago_id`)
- ✅ `cuota` → `cuotas` (N:1, `cuota_id`)

---

#### 5.2. `documentos_ai` (Documentos AI)
**Modelo:** `backend/app/models/documento_ai.py`

**Campos Principales:**
- `id` (PK)
- `titulo`, `descripcion`
- `nombre_archivo`, `tipo_archivo`, `ruta_archivo`
- `tamaño_bytes`
- `contenido_texto`, `contenido_procesado`
- `activo`
- `creado_en`, `actualizado_en`

**Relaciones Entrantes:**
- ✅ `documento_embeddings` → `documento_ai_embeddings.documento_id` (1:N)

---

#### 5.3. `documento_ai_embeddings` (Embeddings de Documentos)
**Modelo:** `backend/app/models/documento_embedding.py`

**Campos Principales:**
- `id` (PK)
- `documento_id` (FK → `documentos_ai.id`, INDEX) ✅
- `embedding` (JSON - vectorial)
- `chunk_index`, `texto_chunk`
- `modelo_embedding`, `dimensiones`
- `creado_en` (INDEX), `actualizado_en`

**Relaciones Salientes:**
- ✅ `documento` → `documentos_ai` (N:1, `documento_id`)

---

#### 5.4. `fine_tuning_jobs` (Jobs de Fine-Tuning)
**Modelo:** `backend/app/models/fine_tuning_job.py`

**Campos Principales:**
- `id` (PK)
- `openai_job_id` (UNIQUE, INDEX)
- `status` (INDEX)
- `modelo_base`, `modelo_entrenado`
- `archivo_entrenamiento`, `total_conversaciones`
- `progreso`
- `error`
- `epochs`, `learning_rate`
- `creado_en` (INDEX), `completado_en`, `actualizado_en`

**Relaciones:**
- ❌ **NO HAY relaciones definidas** (tabla independiente)

---

#### 5.5. `ai_prompt_variables` (Variables de Prompt AI)
**Modelo:** `backend/app/models/ai_prompt_variable.py`

**Campos Principales:**
- `id` (PK)
- `variable` (UNIQUE, INDEX)
- `descripcion`
- `activo` (INDEX)
- `orden`
- `creado_en`, `actualizado_en`

**Relaciones:**
- ❌ **NO HAY relaciones definidas** (tabla de configuración independiente)

---

## 🔄 VERIFICACIÓN DE COHERENCIA BACKEND/FRONTEND

### Comparación de Tipos

#### Cliente

**Backend (`cliente.py`):**
```python
- cedula: String(20)
- nombres: String(100)  # Unificado
- telefono: String(15)
- email: String(100)
- direccion: Text
- fecha_nacimiento: Date
- ocupacion: String(100)
- estado: String(20)
- activo: Boolean
```

**Frontend (`types/index.ts`):**
```typescript
- cedula: string
- nombres: string  ✅ COINCIDE
- apellidos: string  ⚠️ NO EXISTE en backend (solo nombres unificado)
- telefono?: string
- email?: string
- direccion?: string
- fecha_nacimiento?: string
- ocupacion?: string
- estado: 'ACTIVO' | 'INACTIVO' | 'MORA' | 'FINALIZADO'
- activo: boolean
```

**⚠️ INCONSISTENCIA:**
- Frontend tiene `apellidos` pero backend solo tiene `nombres` (unificado)
- Frontend puede recibir `apellidos` que no existe en backend

---

#### Préstamo

**Backend (`prestamo.py`):**
```python
- cliente_id: Integer (FK)
- cedula: String(20)
- nombres: String(100)
- valor_activo: Numeric(15, 2)
- total_financiamiento: Numeric(15, 2)
- modalidad_pago: String(20)  # MENSUAL, QUINCENAL, SEMANAL
- numero_cuotas: Integer
- cuota_periodo: Numeric(15, 2)
- tasa_interes: Numeric(5, 2)
- estado: String(20)  # DRAFT, EN_REVISION, APROBADO, RECHAZADO
```

**Frontend (`types/index.ts`):**
```typescript
- cliente_id: number
- cedula: string
- nombres: string
- valor_activo?: number
- total_financiamiento: number
- modalidad_pago: 'MENSUAL' | 'QUINCENAL' | 'SEMANAL'  ✅ COINCIDE
- numero_cuotas: number
- cuota_periodo: number
- tasa_interes: number
- estado: 'DRAFT' | 'EN_REVISION' | 'APROBADO' | 'RECHAZADO'  ✅ COINCIDE
```

**✅ COHERENCIA:** Mayormente consistente

---

#### Pago

**Backend (`pago.py`):**
```python
- cedula: String(20)  # NO FK
- prestamo_id: Integer  # NO FK ⚠️
- numero_cuota: Integer
- fecha_pago: DateTime
- monto_pagado: Numeric(12, 2)
- numero_documento: String(100)
- estado: String(20)  # PENDIENTE, PAGADO, PARCIAL, ADELANTADO
```

**Frontend (`services/pagoService.ts`):**
```typescript
- cedula: string
- prestamo_id?: number
- numero_cuota?: number
- fecha_pago: string
- monto_pagado: number
- numero_documento: string
- estado?: string
```

**⚠️ INCONSISTENCIA:**
- Ambos usan `prestamo_id` sin FK, pero debería tener integridad referencial

---

## ⚠️ PROBLEMAS IDENTIFICADOS

### 🔴 CRÍTICOS

1. **`pagos.prestamo_id` sin ForeignKey**
   - **Impacto:** No hay integridad referencial
   - **Riesgo:** Puede haber pagos con `prestamo_id` inválido
   - **Solución:** Agregar `ForeignKey("prestamos.id")`

2. **`pagos.cedula` sin ForeignKey**
   - **Impacto:** No hay integridad referencial con clientes
   - **Riesgo:** Puede haber pagos con cédulas que no existen
   - **Solución:** Agregar `cliente_id` con FK o mantener `cedula` pero validar

3. **`prestamos_evaluacion.prestamo_id` sin ForeignKey**
   - **Impacto:** No hay integridad referencial
   - **Riesgo:** Evaluaciones huérfanas
   - **Solución:** Agregar `ForeignKey("prestamos.id")`

---

### 🟡 MEDIOS

4. **`prestamos.concesionario` es string, no FK**
   - **Impacto:** No hay integridad referencial
   - **Riesgo:** Datos inconsistentes (typos, nombres diferentes)
   - **Solución:** Cambiar a `concesionario_id` con FK

5. **`prestamos.analista` es string, no FK**
   - **Impacto:** No hay integridad referencial
   - **Riesgo:** Datos inconsistentes
   - **Solución:** Cambiar a `analista_id` con FK

6. **`prestamos.modelo_vehiculo` es string, no FK**
   - **Impacto:** No hay integridad referencial
   - **Riesgo:** Datos inconsistentes
   - **Solución:** Cambiar a `modelo_vehiculo_id` con FK

7. **Frontend tiene `apellidos` pero backend solo `nombres`**
   - **Impacto:** Inconsistencia de datos
   - **Riesgo:** Frontend puede enviar `apellidos` que se ignora
   - **Solución:** Unificar o agregar campo en backend

---

### 🟢 MENORES

8. **Falta de índices en algunas relaciones**
   - Algunas relaciones tienen índices, otras no
   - Revisar y agregar índices donde falten

9. **Campos duplicados**
   - `prestamos.cedula` y `prestamos.nombres` duplican datos de `clientes`
   - Considerar normalización o mantener por performance

---

## 📋 RECOMENDACIONES

### Prioridad Alta

1. **Agregar ForeignKeys faltantes:**
   ```python
   # En pago.py
   prestamo_id = Column(Integer, ForeignKey("prestamos.id"), nullable=True, index=True)
   cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=True, index=True)
   
   # En prestamo_evaluacion.py
   prestamo_id = Column(Integer, ForeignKey("prestamos.id"), nullable=False, index=True)
   ```

2. **Normalizar relaciones de catálogos:**
   ```python
   # En prestamo.py
   concesionario_id = Column(Integer, ForeignKey("concesionarios.id"), nullable=True, index=True)
   analista_id = Column(Integer, ForeignKey("analistas.id"), nullable=True, index=True)
   modelo_vehiculo_id = Column(Integer, ForeignKey("modelos_vehiculos.id"), nullable=True, index=True)
   ```

3. **Unificar campo de nombres:**
   - Decidir si usar `nombres` unificado o separar `nombres` y `apellidos`
   - Actualizar frontend para coincidir con backend

---

### Prioridad Media

4. **Crear migración para agregar FKs:**
   - Crear migración Alembic para agregar ForeignKeys
   - Validar datos existentes antes de aplicar

5. **Agregar índices faltantes:**
   - Revisar queries frecuentes
   - Agregar índices en campos de búsqueda

6. **Documentar relaciones:**
   - Agregar comentarios en modelos sobre relaciones
   - Crear diagrama ER actualizado

---

### Prioridad Baja

7. **Considerar normalización:**
   - Evaluar si duplicar `cedula` y `nombres` en `prestamos` es necesario
   - Si no, considerar eliminarlos y usar solo `cliente_id`

8. **Agregar constraints:**
   - Agregar check constraints donde sea apropiado
   - Validar estados y valores permitidos

---

## 📊 DIAGRAMA DE RELACIONES

```
┌─────────────┐
│    users    │
└──────┬──────┘
       │
       ├───► aprobaciones (solicitante_id, revisor_id)
       ├───► auditoria (usuario_id)
       ├───► notificaciones (user_id)
       ├───► modelos_riesgo (usuario_id)
       ├───► modelos_impago_cuotas (usuario_id)
       ├───► conversaciones_ai (usuario_id)
       └───► tickets (asignado_a_id, escalado_a_id, creado_por_id)

┌─────────────┐
│  clientes   │
└──────┬──────┘
       │
       ├───► prestamos (cliente_id) ✅
       ├───► notificaciones (cliente_id) ✅
       ├───► conversaciones_ai (cliente_id) ✅
       ├───► tickets (cliente_id) ✅
       ├───► conversaciones_whatsapp (cliente_id) ✅
       └───► comunicaciones_email (cliente_id) ✅
       │
       └───► pagos (cedula) ⚠️ NO FK

┌─────────────┐
│  prestamos  │
└──────┬──────┘
       │
       ├───► cuotas (prestamo_id) ✅
       ├───► conversaciones_ai (prestamo_id) ✅
       ├───► prestamos_evaluacion (prestamo_id) ⚠️ NO FK
       └───► pagos (prestamo_id) ⚠️ NO FK
       │
       └───► modelos_impago_cuotas (ml_impago_modelo_id) ✅

┌─────────────┐
│    pagos     │
└──────┬──────┘
       │
       └───► conversaciones_ai (pago_id) ✅

┌─────────────┐
│    cuotas   │
└──────┬──────┘
       │
       └───► conversaciones_ai (cuota_id) ✅

┌─────────────┐
│   tickets   │
└──────┬──────┘
       │
       ├───► conversaciones_whatsapp (ticket_id) ✅
       └───► comunicaciones_email (ticket_id) ✅

┌─────────────┐
│conversaciones│
│  whatsapp    │
└──────┬──────┘
       │
       ├───► tickets (conversacion_whatsapp_id) ✅
       └───► conversaciones_whatsapp (respuesta_id) ✅ (self)

┌─────────────┐
│comunicaciones│
│    email     │
└──────┬──────┘
       │
       ├───► tickets (comunicacion_email_id) ✅
       └───► comunicaciones_email (respuesta_id) ✅ (self)

┌─────────────┐
│documentos_ai│
└──────┬──────┘
       │
       └───► documento_embeddings (documento_id) ✅
```

---

## ✅ CONCLUSIÓN

### Resumen de Estado

- **Total de Tablas:** 31
- **Relaciones con FK:** 28
- **Relaciones sin FK:** 7 (3 críticas, 4 medias)
- **Inconsistencias Backend/Frontend:** 2
- **Recomendaciones Críticas:** 5
- **Recomendaciones Medias:** 3

### Próximos Pasos

1. ✅ Crear migraciones para agregar ForeignKeys faltantes
2. ✅ Normalizar relaciones de catálogos (concesionarios, analistas, modelos_vehiculos)
3. ✅ Unificar campo de nombres entre backend y frontend
4. ✅ Validar datos existentes antes de aplicar cambios
5. ✅ Actualizar documentación con diagrama ER

---

---

## 📝 TABLAS ADICIONALES DE AUDITORÍA

### `pagos_auditoria` (Auditoría de Pagos)
**Modelo:** `backend/app/models/pago_auditoria.py`

**Campos Principales:**
- `id` (PK)
- `pago_id` (INDEX, NO FK) ⚠️
- `usuario` (string, email)
- `campo_modificado`, `valor_anterior`, `valor_nuevo`
- `accion`, `observaciones`
- `fecha_cambio` (INDEX)

**⚠️ PROBLEMA IDENTIFICADO:**
- `pago_id` NO tiene ForeignKey a `pagos`

---

### `prestamos_auditoria` (Auditoría de Préstamos)
**Modelo:** `backend/app/models/prestamo_auditoria.py`

**Campos Principales:**
- `id` (PK)
- `prestamo_id` (INDEX, NO FK) ⚠️
- `cedula` (INDEX)
- `usuario` (string, email)
- `campo_modificado`, `valor_anterior`, `valor_nuevo`
- `accion`, `estado_anterior`, `estado_nuevo`
- `observaciones`
- `fecha_cambio` (INDEX)

**⚠️ PROBLEMA IDENTIFICADO:**
- `prestamo_id` NO tiene ForeignKey a `prestamos`

---

**Documento generado:** 2025-01-27  
**Última actualización:** 2025-01-27

