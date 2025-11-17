# 📋 Estructura Base de Tablas - Base de Datos

> **Documento de Referencia Principal**
> Este documento contiene la estructura completa y actualizada de todas las tablas principales del sistema.
> Última actualización: 2025-11-06 (verificado desde BD real)

---

## 📊 Resumen de Tablas Principales

| Tabla | Columnas | Descripción |
|-------|----------|-------------|
| **clientes** | 14 | Información de clientes |
| **prestamos** | 25 | Préstamos aprobados y en proceso |
| **cuotas** | 26 | Tabla de amortización (cuotas programadas) |
| **pagos** | 42 | Registro de pagos individuales |

---

## 📋 Tabla: `clientes` (14 columnas)

| Pos | Campo | Tipo | NULL | Default | Descripción |
|-----|-------|------|------|---------|-------------|
| 1 | `id` | integer | NO | `nextval('clientes_id_seq'::regclass)` | ID único |
| 2 | `cedula` | character varying(20) | NO | `'Z999999999'` | Cédula del cliente |
| 3 | `nombres` | character varying(100) | NO | - | Nombres completos |
| 5 | `telefono` | character varying(15) | NO | `'+589999999999'` | Teléfono |
| 6 | `email` | character varying(100) | NO | `'buscaremail@noemail.com'` | Email |
| 7 | `direccion` | text | NO | `'Actualizar dirección'` | Dirección |
| 8 | `fecha_nacimiento` | date | NO | `'2000-01-01'` | Fecha de nacimiento |
| 9 | `ocupacion` | character varying(100) | NO | `'Actualizar ocupación'` | Ocupación |
| 10 | `estado` | character varying(20) | NO | `'ACTIVO'` | ⭐ **ACTIVO, INACTIVO, FINALIZADO** |
| 11 | `activo` | boolean | NO | `true` | Estado activo (boolean) |
| 12 | `fecha_registro` | timestamp without time zone | NO | `'2025-10-31 00:00:00'` | Fecha de registro |
| 13 | `fecha_actualizacion` | timestamp without time zone | NO | `CURRENT_TIMESTAMP` | Fecha de actualización |
| 14 | `usuario_registro` | character varying(50) | NO | `'itmaster@rapicreditca.com'` | Usuario que registró |
| 15 | `notas` | text | NO | `'No existe observaciones'` | Notas |

**Relaciones:**
- `clientes.id` ← `prestamos.cliente_id` (FK: `fk_prestamos_cliente`)

---

## 📋 Tabla: `prestamos` (25 columnas)

| Pos | Campo | Tipo | NULL | Default | Descripción |
|-----|-------|------|------|---------|-------------|
| 1 | `id` | integer | NO | `nextval('prestamos_id_seq'::regclass)` | ID único |
| 2 | `cliente_id` | integer | NO | - | ⭐ **FK a `clientes.id`** |
| 3 | `cedula` | character varying(20) | NO | - | Cédula del cliente |
| 4 | `nombres` | character varying(100) | NO | - | Nombres del cliente |
| 5 | `total_financiamiento` | numeric(15,2) | NO | - | Monto total del préstamo |
| 6 | `fecha_requerimiento` | date | NO | - | Fecha de requerimiento |
| 7 | `modalidad_pago` | character varying(20) | NO | - | MENSUAL, QUINCENAL, SEMANAL |
| 8 | `numero_cuotas` | integer | NO | - | Número de cuotas |
| 9 | `cuota_periodo` | numeric(15,2) | NO | - | Monto de la cuota periódica |
| 10 | `tasa_interes` | numeric(5,2) | NO | `0.00` | Tasa de interés |
| 11 | `fecha_base_calculo` | date | YES | - | ⭐ **Fecha base para generar cuotas** |
| 12 | `producto` | character varying(100) | NO | - | Producto |
| 13 | `producto_financiero` | character varying(100) | NO | - | Producto financiero |
| 14 | `estado` | character varying(20) | NO | `'DRAFT'` | ⭐ **DRAFT, EN_REVISION, APROBADO, RECHAZADO, FINALIZADO** |
| 15 | `usuario_proponente` | character varying(100) | NO | `'itmaster@rapicreditca.com'` | Usuario proponente |
| 16 | `usuario_aprobador` | character varying(100) | YES | - | Usuario aprobador |
| 17 | `observaciones` | text | YES | `'No observaciones'` | Observaciones |
| 18 | `informacion_desplegable` | boolean | NO | `false` | Información desplegable |
| 19 | `fecha_registro` | timestamp without time zone | NO | `'2025-10-31 00:00:00'` | Fecha de registro |
| 20 | `fecha_aprobacion` | timestamp without time zone | YES | - | ⭐ **Fecha cuando se aprueba** |
| 21 | `fecha_actualizacion` | timestamp without time zone | NO | `CURRENT_TIMESTAMP` | Fecha de actualización |
| 22 | `concesionario` | character varying(100) | YES | - | Concesionario |
| 23 | `analista` | character varying(100) | YES | - | Analista |
| 24 | `modelo_vehiculo` | character varying(100) | YES | - | Modelo del vehículo |
| 25 | `usuario_autoriza` | character varying(100) | YES | `'operaciones@rapicreditca.com'` | Usuario autorizador |

**Relaciones:**
- `prestamos.cliente_id` → `clientes.id` (FK: `fk_prestamos_cliente`)
- `prestamos.id` ← `cuotas.prestamo_id`
- `prestamos.id` ← `pagos.prestamo_id` (FK: `fk_pagos_prestamo`)

---

## 📋 Tabla: `cuotas` (26 columnas)

| Pos | Campo | Tipo | NULL | Default | Descripción |
|-----|-------|------|------|---------|-------------|
| 1 | `id` | integer | NO | `nextval('cuotas_id_seq'::regclass)` | ID único |
| 2 | `prestamo_id` | integer | NO | - | ⭐ **FK a `prestamos.id`** |
| 3 | `numero_cuota` | integer | NO | - | ⭐ **Número de cuota (1, 2, 3, ...)** |
| 4 | `fecha_vencimiento` | date | NO | - | ⭐ **Fecha límite programada (fija)** |
| 5 | `fecha_pago` | date | YES | - | ⭐ **Fecha real de pago (se actualiza)** |
| 6 | `monto_cuota` | numeric(12,2) | NO | - | Monto total programado |
| 7 | `monto_capital` | numeric(12,2) | NO | - | Monto de capital programado |
| 8 | `monto_interes` | numeric(12,2) | NO | - | Monto de interés programado |
| 9 | `saldo_capital_inicial` | numeric(12,2) | NO | - | Saldo inicial |
| 10 | `saldo_capital_final` | numeric(12,2) | NO | - | Saldo final |
| 11 | `capital_pagado` | numeric(12,2) | YES | - | ⭐ **SUMA ACUMULATIVA** de capital |
| 12 | `interes_pagado` | numeric(12,2) | YES | - | ⭐ **SUMA ACUMULATIVA** de interés |
| 13 | `mora_pagada` | numeric(12,2) | YES | - | ⭐ **SUMA ACUMULATIVA** de mora |
| 14 | `total_pagado` | numeric(12,2) | YES | - | ⭐ **SUMA ACUMULATIVA de todos los pagos** |
| 15 | `capital_pendiente` | numeric(12,2) | NO | - | Capital pendiente |
| 16 | `interes_pendiente` | numeric(12,2) | NO | - | Interés pendiente |
| 17 | `dias_mora` | integer | YES | - | Días de mora (calculado) |
| 18 | `monto_mora` | numeric(12,2) | YES | - | Monto de mora (calculado) |
| 19 | `tasa_mora` | numeric(5,2) | YES | - | Tasa de mora (%) |
| 20 | `estado` | character varying(20) | NO | - | ⭐ **PENDIENTE, PAGADO, ATRASADO, PARCIAL, ADELANTADO** |
| 21 | `observaciones` | character varying(500) | YES | - | Observaciones |
| 22 | `es_cuota_especial` | boolean | YES | - | Cuota especial |
| 23 | `creado_en` | timestamp with time zone | YES | `now()` | Fecha de creación |
| 24 | `actualizado_en` | timestamp with time zone | YES | - | Fecha de actualización |
| 25 | `dias_morosidad` | integer | YES | `0` | ⭐ **Días de morosidad (calculado automático)** |
| 26 | `monto_morosidad` | numeric(12,2) | YES | `0.00` | ⭐ **Monto pendiente (calculado automático)** |

**Relaciones:**
- `cuotas.prestamo_id` → `prestamos.id`

**Campos Clave:**
- `total_pagado` = **SUMA ACUMULATIVA** de todos los `pagos.monto_pagado` aplicados a esta cuota
  - ⚠️ **IMPORTANTE:** Solo se actualiza cuando los pagos están **conciliados** (`pagos.conciliado = True` o `pagos.verificado_concordancia = 'SI'`)
- `dias_morosidad` = Calculado automáticamente:
  - **Si pagada tardíamente:** `(fecha_pago - fecha_vencimiento).days`
  - **Si no pagada y vencida:** `(CURRENT_DATE - fecha_vencimiento).days`
  - **Si pagada a tiempo o no vencida:** `0`
- `monto_morosidad` = Calculado automáticamente: `MAX(0, monto_cuota - total_pagado)`
  - **Campos utilizados:** `monto_cuota`, `total_pagado`
  - **Nunca negativo:** Si hay sobrepago, `monto_morosidad = 0`

---

## 📋 Tabla: `pagos` (42 columnas - Principales)

| Pos | Campo | Tipo | NULL | Default | Descripción |
|-----|-------|------|------|---------|-------------|
| 1 | `id` | integer | NO | `nextval('pagos_id_seq'::regclass)` | ID único |
| 2 | `prestamo_id` | integer | YES | - | ⭐ **FK a `prestamos.id`** |
| 3 | `numero_cuota` | integer | YES | - | Número de cuota (opcional) |
| 4 | `codigo_pago` | character varying(30) | YES | - | Código único |
| 5 | `monto_cuota_programado` | numeric(12,2) | YES | - | Monto programado |
| 6 | `monto_pagado` | numeric(12,2) | NO | - | ⭐ **REGISTRO INDIVIDUAL de cada pago** |
| 7 | `monto_capital` | numeric(12,2) | YES | - | Capital del pago |
| 8 | `monto_interes` | numeric(12,2) | YES | - | Interés del pago |
| 9 | `monto_mora` | numeric(12,2) | YES | - | Mora del pago |
| 10 | `descuento` | numeric(12,2) | YES | - | Descuento |
| 11 | `monto_total` | numeric(12,2) | YES | - | Monto total |
| 12 | `fecha_pago` | timestamp without time zone | NO | - | ⭐ **Fecha y hora del pago** |
| 13 | `fecha_vencimiento` | date | YES | - | Fecha de vencimiento (opcional) |
| 14 | `hora_pago` | time without time zone | YES | `CURRENT_TIME` | Hora del pago |
| 15 | `dias_mora` | integer | YES | - | Días de mora |
| 16 | `tasa_mora` | numeric(5,2) | YES | - | Tasa de mora |
| 17 | `metodo_pago` | character varying(20) | YES | - | Método de pago |
| 18 | `numero_operacion` | character varying(50) | YES | - | Número de operación |
| 19 | `comprobante` | character varying(50) | YES | - | Comprobante |
| 20 | `banco` | character varying(50) | YES | - | Banco |
| 21 | `estado` | character varying(20) | YES | `'PAGADO'` | Estado del pago |
| 22 | `tipo_pago` | character varying(20) | YES | - | Tipo de pago |
| 23 | `observaciones` | text | YES | - | Observaciones |
| 24 | `usuario_registro` | character varying(50) | YES | - | Usuario que registró |
| 25 | `creado_en` | timestamp without time zone | YES | `now()` | Fecha de creación |
| 26 | `cedula` | character varying(20) | YES | - | Cédula del cliente |
| 27 | `fecha_registro` | timestamp without time zone | NO | `CURRENT_TIMESTAMP` | Fecha de registro |
| 28 | `institucion_bancaria` | character varying(100) | YES | - | Institución bancaria |
| 29 | `referencia_pago` | character varying(100) | NO | `''` | Referencia del pago |
| 30 | `numero_documento` | character varying | YES | - | ⭐ **Número de documento bancario (para conciliación)** |
| 31 | `documento_nombre` | character varying(255) | YES | - | Nombre del documento |
| 32 | `documento_tipo` | character varying(10) | YES | - | Tipo de documento |
| 33 | `documento_tamaño` | integer | YES | - | Tamaño del documento |
| 34 | `documento_ruta` | character varying(500) | YES | - | Ruta del documento |
| 35 | `conciliado` | boolean | YES | `false` | ⭐ **Estado de conciliación** |
| 36 | `fecha_conciliacion` | timestamp without time zone | YES | - | ⭐ **Fecha de conciliación** |
| 37 | `activo` | boolean | YES | `true` | ⭐ **Estado activo** |
| 38 | `notas` | text | YES | - | Notas |
| 39 | `fecha_actualizacion` | timestamp without time zone | YES | - | Fecha de actualización |
| 40 | `verificado_concordancia` | character varying(2) | NO | `'NO'` | ⭐ **Verificación de concordancia (SI/NO)** |
| 42 | `monto` | integer | YES | - | Monto (campo adicional) |
| 43 | `documento` | character varying(50) | YES | - | Documento (campo adicional) |

**Relaciones:**
- `pagos.prestamo_id` → `prestamos.id` (FK: `fk_pagos_prestamo`)
- `pagos.numero_cuota` + `pagos.prestamo_id` → `cuotas` (relación implícita)

**Campos Clave:**
- `monto_pagado` = **REGISTRO INDIVIDUAL** de cada pago (múltiples registros por cuota)
- `prestamo_id` = **DEBE estar relacionado** - Se busca automáticamente por `cedula` y `estado = 'APROBADO'` si no viene en request
- `conciliado` = Se actualiza a `true` cuando `numero_documento` coincide en conciliación
- `verificado_concordancia` = Se actualiza a `'SI'` cuando hay coincidencia exacta
- **⚠️ REGLA:** Solo cuando `conciliado = True` o `verificado_concordancia = 'SI'`, el pago se aplica a cuotas

---

## 🔗 Relaciones Confirmadas (Foreign Keys)

| Tabla Origen | Columna Origen | Tabla Destino | Columna Destino | Constraint |
|--------------|----------------|---------------|-----------------|------------|
| `prestamos` | `cliente_id` | `clientes` | `id` | `fk_prestamos_cliente` |
| `pagos` | `prestamo_id` | `prestamos` | `id` | `fk_pagos_prestamo` |

**Nota:** `cuotas.prestamo_id` referencia a `prestamos.id`, pero la foreign key no aparece explícitamente en la consulta.

---

## ⚠️ Diferencias Clave: Campos Acumulativos vs Individuales

### `cuotas.total_pagado` (ACUMULATIVO)
- **Tipo:** Campo único por cuota
- **Actualización:** Se incrementa (`+=`) con cada pago
- **Ejemplo:** Si hay 3 pagos de $200, $150, $150 → `total_pagado = 500.00`

### `pagos.monto_pagado` (INDIVIDUAL)
- **Tipo:** Registro individual por pago
- **Actualización:** Se crea un nuevo registro (INSERT) por cada pago
- **Ejemplo:** 3 registros separados: `monto_pagado = 200.00`, `monto_pagado = 150.00`, `monto_pagado = 150.00`

---

## 📝 Campos de Fechas: Diferencias Operativas

| Campo | Tabla | Tipo | Propósito | Se Actualiza |
|-------|-------|------|-----------|--------------|
| `fecha_vencimiento` | `cuotas` | `date` | Fecha límite programada | ❌ NO (fija) |
| `fecha_pago` | `cuotas` | `date` | Fecha real de pago | ✅ SÍ (se actualiza) |
| `fecha_pago` | `pagos` | `timestamp without time zone` | Fecha y hora del pago | ❌ NO (se establece al crear) |
| `fecha_aprobacion` | `prestamos` | `timestamp without time zone` | Fecha de aprobación | ✅ SÍ (se establece al aprobar) |

---

## 🎯 Reglas de Negocio Críticas

### 1. Filtro de Clientes ACTIVOS
- **REQUERIDO:** Solo clientes con `estado = 'ACTIVO'` pueden crear préstamos
- **Backend:** `obtener_datos_cliente()` filtra `estado = 'ACTIVO'`
- **Frontend:** `searchClientes()` filtra `estado: 'ACTIVO'`
- **Validación:** Si un cliente existe pero está `INACTIVO` o `FINALIZADO`, se muestra error y no se permite crear préstamo

### 2. Estados de Préstamos
- **DRAFT** → **EN_REVISION** → **APROBADO** / **RECHAZADO** → **FINALIZADO**
- Al aprobar: `fecha_aprobacion = datetime.now()`
- Si tiene `fecha_base_calculo`: se genera tabla de amortización automáticamente
- **Búsqueda automática de préstamo en pagos:** Si no viene `prestamo_id` en request, se busca automáticamente por `cedula` y `estado = 'APROBADO'` (tanto en pago manual como masivo)

### 3. Estados de Cuotas
- **PENDIENTE:** `total_pagado = 0`
- **PARCIAL:** `0 < total_pagado < monto_cuota` y `fecha_vencimiento <= CURRENT_DATE`
- **ADELANTADO:** `0 < total_pagado < monto_cuota` y `fecha_vencimiento > CURRENT_DATE`
- **PAGADO:** `total_pagado >= monto_cuota` Y todos los pagos conciliados
- **ATRASADO:** `fecha_vencimiento < CURRENT_DATE` y `estado != 'PAGADO'`
- **⚠️ IMPORTANTE:** `total_pagado` solo se actualiza cuando los pagos están **conciliados** (`pagos.conciliado = True` o `pagos.verificado_concordancia = 'SI'`)

### 4. Conciliación de Pagos y Aplicación a Cuotas
- **Criterio:** Coincidencia EXACTA de `numero_documento`
- **Campos actualizados:** `conciliado = true`, `fecha_conciliacion = datetime.now()`, `verificado_concordancia = 'SI'`
- **Campos NO modificados:** `monto_pagado`, `estado`
- **⚠️ REGLA CRÍTICA:** Los pagos **SOLO se aplican a cuotas cuando están conciliados** (`conciliado = True` o `verificado_concordancia = 'SI'`)
- **Si el pago NO está conciliado:** NO se puede actualizar la tabla `cuotas` (no se actualiza `cuotas.total_pagado`)
- **Cuando se concilia:** Se aplica automáticamente a cuotas, actualizando `cuotas.total_pagado`

---

## 📊 Campos Calculados Automáticamente

### En `cuotas`:

#### **`dias_morosidad`** (integer, default: 0)
**Tabla:** `cuotas`
**Función:** `_actualizar_morosidad_cuota()` en `backend/app/api/v1/endpoints/pagos.py`

**Campos utilizados para el cálculo:**
- `cuotas.fecha_vencimiento` (DATE) - Fecha límite programada
- `cuotas.fecha_pago` (DATE, nullable) - Fecha real de pago (si existe)
- `fecha_hoy` (DATE) - Fecha actual del sistema

**Lógica:**
- **Si tiene `fecha_pago`:**
  - Si `fecha_pago > fecha_vencimiento` → `dias_morosidad = (fecha_pago - fecha_vencimiento).days`
  - Si `fecha_pago <= fecha_vencimiento` → `dias_morosidad = 0`
- **Si NO tiene `fecha_pago`:**
  - Si `fecha_vencimiento < fecha_hoy` → `dias_morosidad = (fecha_hoy - fecha_vencimiento).days`
  - Si `fecha_vencimiento >= fecha_hoy` → `dias_morosidad = 0`

**Fórmula:** `MAX(0, fecha_referencia - fecha_vencimiento)` donde `fecha_referencia` = `fecha_pago` (si existe) o `fecha_hoy`

---

#### **`monto_morosidad`** (numeric(12,2), default: 0.00)
**Tabla:** `cuotas`
**Función:** `_actualizar_morosidad_cuota()` en `backend/app/api/v1/endpoints/pagos.py`

**Campos utilizados para el cálculo:**
- `cuotas.monto_cuota` (NUMERIC(12,2)) - Monto total programado de la cuota
- `cuotas.total_pagado` (NUMERIC(12,2)) - Suma acumulativa de todos los pagos aplicados

**Lógica:**
```python
monto_pendiente = monto_cuota - total_pagado
monto_morosidad = MAX(0, monto_pendiente)  # Nunca negativo
```

**Fórmula:** `MAX(0, monto_cuota - total_pagado)`

**Ejemplos:**
- `monto_cuota = 100.00`, `total_pagado = 50.00` → `monto_morosidad = 50.00`
- `monto_cuota = 100.00`, `total_pagado = 100.00` → `monto_morosidad = 0.00`
- `monto_cuota = 100.00`, `total_pagado = 120.00` → `monto_morosidad = 0.00` (sobrepago)

**Cuándo se actualiza:**
- Automáticamente cuando se aplica un pago a una cuota (`_aplicar_monto_a_cuota()`)
- Automáticamente cuando se actualiza el estado de una cuota (`_actualizar_estado_cuota()`)

**Beneficios:** Optimización de queries de dashboard (valores pre-calculados)

---

## 🔍 Referencias Rápidas

### Para Búsquedas y Filtros:
- **Cliente por cédula:** `clientes.cedula`
- **Préstamos por cliente:** `prestamos.cliente_id`
- **Cuotas por préstamo:** `cuotas.prestamo_id`
- **Pagos por préstamo:** `pagos.prestamo_id`

### Para KPIs y Cálculos:
- **Total cartera:** `SUM(prestamos.total_financiamiento)` WHERE `estado = 'APROBADO'`
- **Total pagado:** `SUM(cuotas.total_pagado)` o `SUM(pagos.monto_pagado)` WHERE `activo = true`
- **Morosidad:** `SUM(cuotas.monto_morosidad)` WHERE `dias_morosidad > 0`
- **Clientes en mora:** `COUNT(DISTINCT prestamos.cedula)` WHERE `cuotas.dias_morosidad > 0`

---

---

## 🔄 Proceso de Registro y Aplicación de Pagos

### **FASE 1: Registro de Pago**
1. Se crea registro en `pagos` con `monto_pagado` (registro individual)
2. Se busca automáticamente `prestamo_id` por `cedula` y `estado = 'APROBADO'` si no viene en request
3. **⚠️ NO se aplica a cuotas inmediatamente** - El pago queda registrado pero `cuotas.total_pagado` NO se actualiza

### **FASE 2: Conciliación de Pago**
1. Cuando `numero_documento` coincide EXACTAMENTE → `conciliado = True`, `verificado_concordancia = 'SI'`
2. **✅ AHORA SÍ se aplica a cuotas automáticamente** - Se llama a `aplicar_pago_a_cuotas()`
3. Se actualiza `cuotas.total_pagado += monto_pagado` (suma acumulativa)
4. Se actualiza `cuotas.dias_morosidad` y `cuotas.monto_morosidad` automáticamente

### **Validación en Aplicación a Cuotas:**
```python
# Solo se aplica si:
1. pagos.conciliado = True O pagos.verificado_concordancia = 'SI'
2. pagos.prestamo_id NO es NULL
3. El préstamo existe y la cédula coincide
```

**Si alguna condición NO se cumple:** El pago NO se aplica a cuotas

---

**Última actualización:** 2025-11-06
**Fuente:** Verificado desde base de datos real mediante `OBTENER_ESTRUCTURA_REAL_TABLAS.sql`
**Actualizaciones:** Incluye reglas de conciliación y cálculo de morosidad confirmadas

