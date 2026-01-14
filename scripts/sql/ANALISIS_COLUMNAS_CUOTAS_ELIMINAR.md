# 🔍 ANÁLISIS: Columnas a Eliminar en Tabla `cuotas`

## ✅ COLUMNA QUE DEBE EXISTIR

### `total_pagado`
- **Tipo:** NUMERIC(12,2)
- **Descripción:** Suma acumulativa de todos los abonos/pagos aplicados a la cuota
- **Fórmula:** `total_pagado = suma de todos los pagos.monto_pagado aplicados`
- **Estado:** ✅ **MANTENER** - Es la columna principal para saber cuánto se ha pagado

---

## ❌ COLUMNAS A ELIMINAR (Según Indicación)

### 1. `interes_pagado`
- **Tipo:** NUMERIC(12,2)
- **Descripción:** Interés pagado acumulativo
- **Razón para eliminar:** Si solo se usa `total_pagado`, no se necesita desglose de interés
- **Uso actual:** Se calcula proporcionalmente cuando se aplica un pago
- **Estado:** ❌ **ELIMINAR**

### 2. `mora_pagada`
- **Tipo:** NUMERIC(12,2)
- **Descripción:** Mora pagada acumulativa
- **Razón para eliminar:** Si la mora está desactivada (siempre 0%), esta columna no tiene sentido
- **Uso actual:** Se establece en 0 siempre (mora desactivada)
- **Estado:** ❌ **ELIMINAR**

### 3. `monto_mora`
- **Tipo:** NUMERIC(12,2)
- **Descripción:** Monto de mora calculado
- **Razón para eliminar:** Si la mora está desactivada (siempre 0%), esta columna no tiene sentido
- **Uso actual:** Se establece en 0 siempre (mora desactivada)
- **Estado:** ❌ **ELIMINAR**

### 4. `tasa_mora`
- **Tipo:** NUMERIC(5,2)
- **Descripción:** Tasa de mora aplicada (%)
- **Razón para eliminar:** Si la mora está desactivada (siempre 0%), esta columna no tiene sentido
- **Uso actual:** Se establece en 0 siempre (mora desactivada)
- **Estado:** ❌ **ELIMINAR**

### 5. `monto_morosidad`
- **Tipo:** NUMERIC(12,2)
- **Descripción:** Monto pendiente calculado: `monto_cuota - total_pagado`
- **Razón para eliminar:** Es un campo calculado que se puede obtener con `monto_cuota - total_pagado`
- **Uso actual:** Se calcula automáticamente pero es redundante
- **Estado:** ❌ **ELIMINAR** (se puede calcular cuando se necesite)

### 6. `monto_interes`
- **Tipo:** NUMERIC(12,2)
- **Descripción:** Monto de interés programado de la cuota
- **Razón para eliminar:** Si no se necesita desglose capital/interés, se puede eliminar
- **Uso actual:** Campo programado que indica cuánto interés tiene la cuota
- **Estado:** ❌ **ELIMINAR**

### 7. `interes_pendiente`
- **Tipo:** NUMERIC(12,2)
- **Descripción:** Interés que falta pagar de esta cuota
- **Razón para eliminar:** Si se elimina `monto_interes`, no se puede calcular `interes_pendiente`
- **Uso actual:** Se calcula como `monto_interes - interes_pagado`
- **Estado:** ❌ **ELIMINAR** (depende de `monto_interes`)

### 8. `capital_pagado`
- **Tipo:** NUMERIC(12,2)
- **Descripción:** Capital pagado acumulativo
- **Razón para eliminar:** Solo se mantiene `total_pagado`, no se necesita desglose capital/interés
- **Uso actual:** Se calcula proporcionalmente cuando se aplica un pago
- **Estado:** ❌ **ELIMINAR**

### 9. `monto_capital`
- **Tipo:** NUMERIC(12,2)
- **Descripción:** Monto de capital programado de la cuota
- **Razón para eliminar:** Solo se mantiene `monto_cuota`, no se necesita desglose capital/interés
- **Uso actual:** Campo programado que indica cuánto capital tiene la cuota
- **Estado:** ❌ **ELIMINAR**

### 10. `capital_pendiente`
- **Tipo:** NUMERIC(12,2)
- **Descripción:** Capital que falta pagar de esta cuota
- **Razón para eliminar:** Si se elimina `monto_capital`, no se puede calcular `capital_pendiente`
- **Uso actual:** Se calcula como `monto_capital - capital_pagado`
- **Estado:** ❌ **ELIMINAR** (depende de `monto_capital`)

---

## ✅ COLUMNAS A MANTENER

### Campos de Identificación
- ✅ `id`
- ✅ `prestamo_id`
- ✅ `numero_cuota`

### Fechas
- ✅ `fecha_vencimiento` - Fecha programada de vencimiento
- ✅ `fecha_pago` - Fecha cuando se pagó

### Montos Programados
- ✅ `monto_cuota` - Monto total programado (MANTENER)
- ❌ `monto_capital` - **ELIMINAR** (no se necesita desglose capital)
- ❌ `monto_interes` - **ELIMINAR** (no se necesita desglose interés)

### Saldos
- ✅ `saldo_capital_inicial`
- ✅ `saldo_capital_final`

### Montos Pagados
- ✅ `total_pagado` - **MANTENER** (suma de abonos)
- ❌ `capital_pagado` - **ELIMINAR** (no se necesita desglose capital)

### Montos Pendientes
- ❌ `capital_pendiente` - **ELIMINAR** (depende de `monto_capital` que también se elimina)
- ❌ `interes_pendiente` - **ELIMINAR** (depende de `monto_interes` que también se elimina)

### Mora
- ⚠️ `dias_mora` - **VERIFICAR** si se necesita (actualmente siempre 0)
- ❌ `monto_mora` - **ELIMINAR**
- ❌ `tasa_mora` - **ELIMINAR**

### Morosidad
- ✅ `dias_morosidad` - Días de atraso (útil para reportes)
- ❌ `monto_morosidad` - **ELIMINAR** (se calcula como `monto_cuota - total_pagado`)

### Estado
- ✅ `estado` - Estado de la cuota (PENDIENTE, PAGADO, ATRASADO, etc.)

### Información Adicional
- ✅ `observaciones`
- ✅ `es_cuota_especial`
- ✅ `creado_en`
- ✅ `actualizado_en`

---

## 📊 RESUMEN DE COLUMNAS A ELIMINAR

| Columna | Tipo | Razón |
|---------|------|-------|
| `interes_pagado` | NUMERIC(12,2) | Redundante si solo se usa `total_pagado` |
| `mora_pagada` | NUMERIC(12,2) | Siempre 0 (mora desactivada) |
| `monto_mora` | NUMERIC(12,2) | Siempre 0 (mora desactivada) |
| `tasa_mora` | NUMERIC(5,2) | Siempre 0 (mora desactivada) |
| `monto_morosidad` | NUMERIC(12,2) | Campo calculado redundante |
| `monto_interes` | NUMERIC(12,2) | No se necesita desglose interés |
| `interes_pendiente` | NUMERIC(12,2) | Depende de `monto_interes` que se elimina |
| `capital_pagado` | NUMERIC(12,2) | No se necesita desglose capital |
| `monto_capital` | NUMERIC(12,2) | No se necesita desglose capital |
| `capital_pendiente` | NUMERIC(12,2) | Depende de `monto_capital` que se elimina |

---

## ⚠️ COLUMNAS QUE REQUIEREN VERIFICACIÓN

### 1. `monto_interes` vs `interes_pagado`
- **`monto_interes`**: Monto programado de interés (parte de la estructura de la cuota)
- **`interes_pagado`**: Monto de interés ya pagado (acumulativo)
- **Decisión:** Si se elimina `monto_interes`, también se debe eliminar `interes_pendiente`

### 2. `capital_pagado` vs `total_pagado`
- **`capital_pagado`**: Solo capital pagado
- **`total_pagado`**: Total pagado (capital + interés + mora)
- **Decisión:** Si solo se necesita el total, se puede eliminar `capital_pagado`

### 3. `dias_mora` vs `dias_morosidad`
- **`dias_mora`**: Días de mora (actualmente siempre 0)
- **`dias_morosidad`**: Días de atraso (calculado automáticamente)
- **Decisión:** Si `dias_mora` siempre es 0, se puede eliminar

---

## 🔧 SCRIPT SQL PARA ELIMINAR COLUMNAS

```sql
-- ============================================
-- ELIMINAR COLUMNAS REDUNDANTES DE CUOTAS
-- ============================================

-- PASO 1: Verificar columnas actuales
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'cuotas'
ORDER BY ordinal_position;

-- PASO 2: Eliminar columnas (ejecutar una por una)
ALTER TABLE public.cuotas DROP COLUMN IF EXISTS interes_pagado;
ALTER TABLE public.cuotas DROP COLUMN IF EXISTS mora_pagada;
ALTER TABLE public.cuotas DROP COLUMN IF EXISTS monto_mora;
ALTER TABLE public.cuotas DROP COLUMN IF EXISTS tasa_mora;
ALTER TABLE public.cuotas DROP COLUMN IF EXISTS monto_morosidad;
ALTER TABLE public.cuotas DROP COLUMN IF EXISTS monto_interes;
ALTER TABLE public.cuotas DROP COLUMN IF EXISTS interes_pendiente;

-- PASO 3: Verificar columnas después de eliminar
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'cuotas'
ORDER BY ordinal_position;
```

---

## ⚠️ ADVERTENCIAS

1. **Backup**: Hacer backup antes de eliminar columnas
2. **Código**: Actualizar código Python que use estas columnas eliminadas
3. **Verificación**: Ejecutar `verificar_columnas_cuotas_eliminar.sql` antes de eliminar
4. **Script de eliminación**: Usar `eliminar_columnas_cuotas.sql` para eliminar las columnas

## 📋 COLUMNAS CONFIRMADAS A ELIMINAR (10 columnas)

1. ✅ `interes_pagado` - Interés pagado acumulativo
2. ✅ `mora_pagada` - Mora pagada acumulativa
3. ✅ `monto_mora` - Monto de mora
4. ✅ `tasa_mora` - Tasa de mora
5. ✅ `monto_morosidad` - Monto de morosidad (calculado)
6. ✅ `monto_interes` - Monto de interés programado
7. ✅ `interes_pendiente` - Interés pendiente
8. ✅ `capital_pagado` - Capital pagado acumulativo
9. ✅ `monto_capital` - Monto de capital programado
10. ✅ `capital_pendiente` - Capital pendiente

## ✅ COLUMNAS QUE DEBEN MANTENERSE

- ✅ `monto_cuota` - Monto total programado de la cuota
- ✅ `total_pagado` - Suma acumulativa de todos los abonos/pagos

**Estructura simplificada:** Solo `monto_cuota` y `total_pagado` sin desglose capital/interés

---

**Fecha de análisis:** 2026-01-14
