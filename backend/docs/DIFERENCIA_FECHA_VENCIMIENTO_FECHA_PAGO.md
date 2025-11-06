# 📅 DIFERENCIA: fecha_vencimiento vs fecha_pago

## 🎯 RESUMEN RÁPIDO

| Campo | Tipo | ¿Cuándo se establece? | ¿Quién lo establece? | ¿Puede cambiar? |
|-------|------|----------------------|---------------------|-----------------|
| `fecha_vencimiento` | DATE | ✅ **Al generar la cuota** | Sistema (automático) | ❌ NO (fija) |
| `fecha_pago` | DATE (nullable) | ✅ **Al registrar un pago** | Usuario/Sistema | ✅ SÍ (se actualiza) |

---

## 📋 EXPLICACIÓN DETALLADA

### 1. `fecha_vencimiento` - Fecha Límite de Pago

**Definición:** Fecha programada/límite cuando debe pagarse la cuota.

**Características:**
- ✅ Se establece **automáticamente** al generar la tabla de amortización
- ✅ Se calcula desde `fecha_base_calculo` del préstamo
- ✅ **NO cambia** después de generarse (es fija)
- ✅ Se usa para calcular morosidad (si `fecha_vencimiento < CURRENT_DATE` y no está pagada → vencida)

**Ejemplo:**
```python
# Préstamo con fecha_base_calculo = 2025-10-31
# Modalidad: MENSUAL
# Cuota 1: fecha_vencimiento = 2025-11-30
# Cuota 2: fecha_vencimiento = 2025-12-31
# Cuota 3: fecha_vencimiento = 2026-01-31
```

**Cálculo:**
```python
if modalidad == "MENSUAL":
    fecha_vencimiento = fecha_base_calculo + relativedelta(months=numero_cuota)
    # Cuota 1: 2025-10-31 + 1 mes = 2025-11-30
    # Cuota 2: 2025-10-31 + 2 meses = 2025-12-31
```

---

### 2. `fecha_pago` - Fecha Real de Pago

**Definición:** Fecha real cuando se efectuó el pago de la cuota.

**Características:**
- ✅ Se establece **al registrar un pago**
- ✅ Inicialmente es `NULL` (cuota pendiente)
- ✅ **SÍ cambia** cuando se registra un pago
- ✅ Puede ser anterior, igual o posterior a `fecha_vencimiento`

**Ejemplos de Escenarios:**

#### Escenario 1: Pago a Tiempo
```
fecha_vencimiento: 2025-11-30
fecha_pago:        2025-11-28  ← Pago ANTES del vencimiento
Estado: PAGADO
```

#### Escenario 2: Pago Tardío (Mora)
```
fecha_vencimiento: 2025-11-30
fecha_pago:        2025-12-15  ← Pago DESPUÉS del vencimiento
Estado: PAGADO (pero con mora)
dias_mora: 15 días
```

#### Escenario 3: Pago Adelantado
```
fecha_vencimiento: 2025-11-30
fecha_pago:        2025-10-15  ← Pago MUCHO ANTES del vencimiento
Estado: ADELANTADO
```

#### Escenario 4: Cuota Pendiente
```
fecha_vencimiento: 2025-11-30
fecha_pago:        NULL  ← Aún no se ha pagado
Estado: PENDIENTE (o ATRASADO si fecha_vencimiento < CURRENT_DATE)
```

---

## 🔍 COMPARACIÓN VISUAL

### Ejemplo Real de una Cuota

```sql
-- Cuota generada inicialmente
SELECT 
    numero_cuota,
    fecha_vencimiento,  -- 2025-11-30 (programada)
    fecha_pago,         -- NULL (aún no pagada)
    monto_cuota,        -- 500.00
    total_pagado,       -- 0.00
    estado              -- PENDIENTE
FROM cuotas
WHERE prestamo_id = 3708 AND numero_cuota = 1;

-- Resultado:
-- numero_cuota: 1
-- fecha_vencimiento: 2025-11-30
-- fecha_pago: NULL
-- monto_cuota: 500.00
-- total_pagado: 0.00
-- estado: PENDIENTE
```

```sql
-- Después de registrar un pago el 2025-11-28
SELECT 
    numero_cuota,
    fecha_vencimiento,  -- 2025-11-30 (NO cambió - es fija)
    fecha_pago,         -- 2025-11-28 (se actualizó - fecha real de pago)
    monto_cuota,        -- 500.00
    total_pagado,       -- 500.00 (se actualizó)
    estado              -- PAGADO (se actualizó)
FROM cuotas
WHERE prestamo_id = 3708 AND numero_cuota = 1;

-- Resultado:
-- numero_cuota: 1
-- fecha_vencimiento: 2025-11-30 (igual - no cambia)
-- fecha_pago: 2025-11-28 (actualizado - fecha real)
-- monto_cuota: 500.00
-- total_pagado: 500.00 (actualizado)
-- estado: PAGADO (actualizado)
```

---

## 📊 CASOS DE USO

### 1. Calcular Morosidad

```sql
-- Cuotas vencidas (fecha_vencimiento pasó, pero no pagadas)
SELECT 
    numero_cuota,
    fecha_vencimiento,
    fecha_pago,
    CURRENT_DATE - fecha_vencimiento as dias_vencido
FROM cuotas
WHERE prestamo_id = 3708
  AND fecha_vencimiento < CURRENT_DATE  -- Vencida
  AND fecha_pago IS NULL                -- No pagada
  AND estado != 'PAGADO';
```

**Lógica:**
- Si `fecha_vencimiento < CURRENT_DATE` y `fecha_pago IS NULL` → **VENCIDA**
- Si `fecha_pago IS NOT NULL` → **PAGADA** (aunque haya sido tardía)

---

### 2. Identificar Pagos Adelantados

```sql
-- Pagos adelantados (fecha_pago antes de fecha_vencimiento)
SELECT 
    numero_cuota,
    fecha_vencimiento,
    fecha_pago,
    fecha_vencimiento - fecha_pago as dias_adelantado
FROM cuotas
WHERE prestamo_id = 3708
  AND fecha_pago IS NOT NULL
  AND fecha_pago < fecha_vencimiento;
```

**Lógica:**
- Si `fecha_pago < fecha_vencimiento` → **ADELANTADO**

---

### 3. Identificar Pagos Tardíos (con Mora)

```sql
-- Pagos tardíos (fecha_pago después de fecha_vencimiento)
SELECT 
    numero_cuota,
    fecha_vencimiento,
    fecha_pago,
    fecha_pago - fecha_vencimiento as dias_tardio,
    monto_mora
FROM cuotas
WHERE prestamo_id = 3708
  AND fecha_pago IS NOT NULL
  AND fecha_pago > fecha_vencimiento;
```

**Lógica:**
- Si `fecha_pago > fecha_vencimiento` → **TARDÍO** (debe calcularse mora)

---

## 🔄 FLUJO DE ACTUALIZACIÓN

### Al Generar Cuota (Inicial)

```python
cuota = Cuota(
    prestamo_id=3708,
    numero_cuota=1,
    fecha_vencimiento=date(2025, 11, 30),  # ✅ Se establece aquí
    fecha_pago=None,                        # ✅ NULL inicialmente
    estado="PENDIENTE",
    total_pagado=Decimal("0.00")
)
```

### Al Registrar un Pago

```python
# Usuario registra pago el 2025-11-28
pago = Pago(
    prestamo_id=3708,
    numero_cuota=1,
    fecha_pago=datetime(2025, 11, 28),  # Fecha del pago
    monto_pagado=Decimal("500.00")
)

# Sistema actualiza la cuota
cuota.fecha_pago = date(2025, 11, 28)  # ✅ Se actualiza aquí
cuota.total_pagado = Decimal("500.00")
cuota.estado = "PAGADO"
```

**Nota:** `fecha_vencimiento` **NO cambia** (sigue siendo 2025-11-30)

---

## ⚠️ CASOS ESPECIALES

### 1. Pago Parcial

```sql
-- Cuota con pago parcial
fecha_vencimiento: 2025-11-30
fecha_pago:        2025-11-28  ← Se registró un pago
total_pagado:      300.00      ← Pero no es el monto completo
monto_cuota:       500.00
estado:            PARCIAL     ← Estado parcial
```

**Lógica:**
- `fecha_pago` se establece cuando se registra el primer pago
- Si `total_pagado < monto_cuota` → Estado = `PARCIAL`
- `fecha_vencimiento` sigue siendo la misma (2025-11-30)

---

### 2. Múltiples Pagos en una Cuota

```sql
-- Cuota que recibió múltiples pagos
fecha_vencimiento: 2025-11-30
fecha_pago:        2025-11-28  ← Fecha del PRIMER pago
total_pagado:      500.00      ← Suma de todos los pagos
estado:            PAGADO
```

**Lógica:**
- `fecha_pago` se establece con la fecha del **primer pago**
- Si hay múltiples pagos, `fecha_pago` no cambia (mantiene la fecha del primero)
- `total_pagado` se actualiza sumando todos los pagos

---

## 📝 RESUMEN

| Aspecto | fecha_vencimiento | fecha_pago |
|---------|-------------------|------------|
| **Propósito** | Fecha límite programada | Fecha real de pago |
| **Se establece** | Al generar cuota | Al registrar pago |
| **Valor inicial** | Fecha calculada | `NULL` |
| **Puede cambiar** | ❌ NO (fija) | ✅ SÍ (se actualiza) |
| **Uso principal** | Calcular morosidad | Registrar cuándo se pagó |
| **Ejemplo** | 2025-11-30 | 2025-11-28 (o NULL) |

---

## ✅ ACTUALIZACIÓN: Cálculo Automático de Mora

### Nueva Funcionalidad

**✅ IMPLEMENTADO:** Cuando `fecha_pago > fecha_vencimiento`, el sistema calcula automáticamente:

- `dias_mora` = Diferencia en días entre `fecha_pago` y `fecha_vencimiento`
- `monto_mora` = Monto calculado según tasa de mora diaria
- `tasa_mora` = Tasa de mora aplicada (desde settings)

**Ubicación del código:** `backend/app/api/v1/endpoints/pagos.py` - Función `_aplicar_monto_a_cuota()`

**Ejemplo:**
```
fecha_vencimiento: 2025-11-30
fecha_pago:        2025-12-15  ← 15 días después

Resultado automático:
- dias_mora: 15
- monto_mora: $5.03 (calculado automáticamente)
- tasa_mora: 0.067% (desde settings)
```

**Ver documentación completa:** `backend/docs/ACTUALIZACION_CALCULO_MORA_AUTOMATICO.md`

---

## ✅ CONCLUSIÓN

**`fecha_vencimiento`** = "¿Cuándo DEBE pagarse?" (programada, fija)  
**`fecha_pago`** = "¿Cuándo SE PAGÓ realmente?" (real, se actualiza)

**Analogía:**
- `fecha_vencimiento` = Fecha de vencimiento de una factura (fija)
- `fecha_pago` = Fecha cuando realmente pagaste la factura (puede variar)

**Nueva funcionalidad:**
- Si `fecha_pago > fecha_vencimiento` → **Mora calculada automáticamente**

---

**Estado:** ✅ **EXPLICACIÓN COMPLETA - ACTUALIZADA CON CÁLCULO AUTOMÁTICO DE MORA**

