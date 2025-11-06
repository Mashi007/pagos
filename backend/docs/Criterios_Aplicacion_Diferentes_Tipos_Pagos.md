# 📋 CRITERIOS: Aplicación de Diferentes Tipos de Pagos

**Fecha:** 2025-01-27  
**Objetivo:** Documentar todos los criterios que se aplican según el tipo de pago

---

## 🎯 CRITERIOS GENERALES (Aplican a TODOS los pagos)

### **1. Verificación de Cédula** ✅
**Criterio:** El pago solo se aplica si la cédula del pago coincide con la cédula del préstamo.

```python
# backend/app/api/v1/endpoints/pagos.py - función _verificar_prestamo_y_cedula()
if pago.cedula_cliente != prestamo.cedula:
    # ❌ NO se aplica el pago
    return False
```

**Razón:** Asegurar que el pago corresponde al cliente correcto.

---

### **2. Orden de Aplicación** ✅
**Criterio:** Los pagos se aplican a las cuotas más antiguas primero (por `fecha_vencimiento`).

```python
# Ordenamiento: fecha_vencimiento ASC, luego numero_cuota ASC
.order_by(Cuota.fecha_vencimiento, Cuota.numero_cuota)
```

**Razón:** Priorizar el pago de cuotas vencidas o próximas a vencer.

---

### **3. Solo Cuotas No Pagadas** ✅
**Criterio:** Solo se aplican pagos a cuotas con `estado != "PAGADO"`.

```python
.filter(Cuota.estado != "PAGADO")
```

**Razón:** Evitar aplicar pagos a cuotas ya completas.

---

## 💰 CRITERIOS ESPECÍFICOS POR TIPO DE PAGO

---

## 📊 TIPO 1: PAGO COMPLETO (Monto = Cuota)

**Ejemplo:** Cuota de $500, pago de $500

### **Criterios aplicados:**

1. ✅ **Aplicación directa:** Se aplica el monto completo a la cuota
2. ✅ **Distribución proporcional:** Se distribuye entre capital e interés según lo pendiente
3. ✅ **Actualización de estado:** `PAGADO` (si está conciliado) o `PENDIENTE` (si no está conciliado)
4. ✅ **Fecha de pago:** Se actualiza `fecha_pago` de la cuota

**Proceso:**
```python
monto_faltante = cuota.monto_cuota - cuota.total_pagado  # Ej: $500 - $0 = $500
monto_aplicar = min(saldo_restante, monto_faltante)     # Ej: min($500, $500) = $500

# Distribución proporcional
capital_aplicar = monto_aplicar * (capital_pendiente / total_pendiente)
interes_aplicar = monto_aplicar * (interes_pendiente / total_pendiente)
```

---

## 📊 TIPO 2: PAGO PARCIAL (Monto < Cuota)

**Ejemplo:** Cuota de $500, pago de $200

### **Criterios aplicados:**

1. ✅ **Aplicación parcial:** Se aplica solo el monto recibido
2. ✅ **Distribución proporcional:** Se distribuye entre capital e interés según lo pendiente
3. ✅ **Actualización de estado:**
   - Si cuota vencida → `PARCIAL`
   - Si cuota no vencida → `PENDIENTE`
   - Si es exceso de otro pago → `ADELANTADO`
4. ✅ **Fecha de pago:** Se actualiza `fecha_pago` de la cuota

**Proceso:**
```python
monto_faltante = cuota.monto_cuota - cuota.total_pagado  # Ej: $500 - $0 = $500
monto_aplicar = min(saldo_restante, monto_faltante)     # Ej: min($200, $500) = $200

# Distribución proporcional
capital_aplicar = $200 * (capital_pendiente / total_pendiente)
interes_aplicar = $200 * (interes_pendiente / total_pendiente)
```

**Resultado:**
- `total_pagado` = $200
- `capital_pendiente` = disminuye proporcionalmente
- `interes_pendiente` = disminuye proporcionalmente
- Estado = `PARCIAL` o `PENDIENTE` (según fecha_vencimiento)

---

## 📊 TIPO 3: PAGO EXCESIVO (Monto > Cuota)

**Ejemplo:** Cuota de $500, pago de $800

### **Criterios aplicados:**

1. ✅ **Aplicación completa a cuota actual:** Se aplica $500 a la cuota actual
2. ✅ **Exceso a siguiente cuota:** El exceso ($300) se aplica automáticamente a la siguiente cuota pendiente
3. ✅ **Actualización de estado:** Cuota actual → `PAGADO`, siguiente cuota → `ADELANTADO` o `PENDIENTE`
4. ✅ **Orden de exceso:** El exceso se aplica a la cuota más antigua pendiente

**Proceso:**
```python
# Paso 1: Aplicar a cuota actual
monto_aplicar = min($800, $500)  # = $500
# Cuota actual queda: PAGADO

# Paso 2: Exceso
saldo_restante = $800 - $500  # = $300

# Paso 3: Aplicar exceso a siguiente cuota más antigua
siguiente_cuota = obtener_cuota_mas_antigua_pendiente()
aplicar_monto_a_cuota(siguiente_cuota, $300, es_exceso=True)
```

**Resultado:**
- Cuota 1: `PAGADO` ($500 aplicados)
- Cuota 2: `ADELANTADO` o `PENDIENTE` ($300 aplicados como adelanto)

---

## 📊 TIPO 4: PAGO MÚLTIPLE (Varias cuotas con un pago)

**Ejemplo:** Pago de $1,500 para cubrir 3 cuotas de $500 cada una

### **Criterios aplicados:**

1. ✅ **Aplicación secuencial:** Se aplica cuota por cuota, en orden
2. ✅ **Completar cuota actual:** Primero completa la cuota actual, luego pasa a la siguiente
3. ✅ **Sin exceso:** Si el monto cubre exactamente varias cuotas, todas se marcan como `PAGADO`
4. ✅ **Con exceso:** Si sobra, el exceso va a la siguiente cuota pendiente

**Proceso:**
```python
saldo_restante = $1,500

# Cuota 1: $500
monto_aplicar = min($1,500, $500)  # = $500
saldo_restante = $1,500 - $500  # = $1,000
# Cuota 1: PAGADO

# Cuota 2: $500
monto_aplicar = min($1,000, $500)  # = $500
saldo_restante = $1,000 - $500  # = $500
# Cuota 2: PAGADO

# Cuota 3: $500
monto_aplicar = min($500, $500)  # = $500
saldo_restante = $500 - $500  # = $0
# Cuota 3: PAGADO
```

---

## 📊 TIPO 5: PAGO CON CONCILIACIÓN

### **Criterios aplicados:**

1. ✅ **Verificación de conciliación:** Se verifica si TODOS los pagos del préstamo están conciliados
2. ✅ **Estado según conciliación:**
   - Si `total_pagado >= monto_cuota` Y todos conciliados → `PAGADO`
   - Si `total_pagado >= monto_cuota` PERO NO todos conciliados → `PENDIENTE`
3. ✅ **Búsqueda en múltiples tablas:** Se verifica en `pagos` y `pagos_staging`

**Proceso:**
```python
# Verificar si todos los pagos están conciliados
todos_conciliados = _verificar_pagos_conciliados_cuota(db, cuota.id, prestamo_id)

if total_pagado >= monto_cuota:
    if todos_conciliados:
        estado = "PAGADO"  # ✅
    else:
        estado = "PENDIENTE"  # ⚠️ Pagada pero no conciliada
```

---

## 🔢 CRITERIOS DE DISTRIBUCIÓN: Capital vs Interés

### **Fórmula de Distribución Proporcional:**

```python
# backend/app/api/v1/endpoints/pagos.py - función _calcular_proporcion_capital_interes()

total_pendiente = cuota.capital_pendiente + cuota.interes_pendiente

if total_pendiente > 0:
    capital_aplicar = monto_aplicar * (capital_pendiente / total_pendiente)
    interes_aplicar = monto_aplicar * (interes_pendiente / total_pendiente)
else:
    capital_aplicar = monto_aplicar  # Si no hay pendiente, todo va a capital
    interes_aplicar = 0
```

**Ejemplo:**
- Cuota tiene: `capital_pendiente = $400`, `interes_pendiente = $100`
- Pago recibido: $200
- Distribución:
  - Capital: $200 * ($400 / $500) = **$160**
  - Interés: $200 * ($100 / $500) = **$40**

**Razón:** Mantener la proporción original entre capital e interés.

---

## 📅 CRITERIOS DE ACTUALIZACIÓN DE ESTADO

### **Tabla de Decisión Completa:**

| Condición | Fecha Vencimiento | Conciliado | Exceso | Estado Final |
|-----------|-------------------|------------|--------|--------------|
| `total_pagado >= monto_cuota` | Cualquiera | ✅ Sí | - | `PAGADO` |
| `total_pagado >= monto_cuota` | Cualquiera | ❌ No | - | `PENDIENTE` |
| `0 < total_pagado < monto_cuota` | `< hoy` | - | - | `PARCIAL` |
| `0 < total_pagado < monto_cuota` | `>= hoy` | - | ❌ No | `PENDIENTE` |
| `0 < total_pagado < monto_cuota` | `>= hoy` | - | ✅ Sí | `ADELANTADO` |
| `total_pagado = 0` | `< hoy` | - | - | `ATRASADO` |
| `total_pagado = 0` | `>= hoy` | - | - | `PENDIENTE` |

---

## 🎯 RESUMEN DE CRITERIOS POR TIPO DE PAGO

| Tipo de Pago | Criterios Específicos |
|--------------|----------------------|
| **Pago Completo** | ✅ Aplicación directa, distribución proporcional, estado PAGADO/PENDIENTE según conciliación |
| **Pago Parcial** | ✅ Aplicación parcial, distribución proporcional, estado PARCIAL/PENDIENTE según fecha |
| **Pago Excesivo** | ✅ Aplicación completa + exceso a siguiente cuota, estado ADELANTADO |
| **Pago Múltiple** | ✅ Aplicación secuencial, completar cuotas en orden, estado según cada cuota |
| **Pago Conciliado** | ✅ Verificación de conciliación, estado PAGADO solo si todos conciliados |

---

## ✅ CRITERIOS COMUNES A TODOS

1. ✅ Verificación de cédula
2. ✅ Orden por fecha_vencimiento (más antigua primero)
3. ✅ Solo cuotas no pagadas
4. ✅ Distribución proporcional capital/interés
5. ✅ Actualización automática de estado
6. ✅ Actualización de fecha_pago

---

## 📝 NOTAS IMPORTANTES

1. **No hay diferencia por método de pago:** Los criterios son los mismos si el pago es en efectivo, transferencia, cheque, etc.
2. **No hay diferencia por modalidad:** Los criterios son los mismos si el préstamo es MENSUAL, QUINCENAL, SEMANAL.
3. **La diferencia está en el monto:** Los criterios cambian según si el monto es igual, menor o mayor a la cuota.
4. **La conciliación afecta el estado:** Una cuota puede estar 100% pagada pero seguir `PENDIENTE` si no está conciliada.

