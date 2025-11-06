# 📋 EXPLICACIÓN: Actualización de Estado en Amortización por Pago

**Fecha:** 2025-01-27  
**Objetivo:** Documentar cómo se actualiza el estado de las cuotas cuando se aplica un pago

---

## 🔄 FLUJO COMPLETO DE ACTUALIZACIÓN

### 1. **Trigger: Creación de Pago**

Cuando se crea un pago mediante `POST /api/v1/pagos`, automáticamente se ejecuta:

```python
# backend/app/api/v1/endpoints/pagos.py - función crear_pago()
cuotas_completadas = aplicar_pago_a_cuotas(nuevo_pago, db, current_user)
```

---

### 2. **Función Principal: `aplicar_pago_a_cuotas()`**

**Ubicación:** `backend/app/api/v1/endpoints/pagos.py` (líneas 1205-1254)

**Proceso:**
1. ✅ **Verificación de cédula:** Valida que `pago.cedula_cliente == prestamo.cedula`
2. ✅ **Obtiene cuotas pendientes:** Ordenadas por `fecha_vencimiento` (más antigua primero)
3. ✅ **Aplica pago iterativamente:** Cuota por cuota hasta agotar el monto
4. ✅ **Maneja exceso:** Si sobra dinero, se aplica a la siguiente cuota pendiente

---

### 3. **Función: `_aplicar_monto_a_cuota()`**

**Ubicación:** `backend/app/api/v1/endpoints/pagos.py` (líneas 1072-1099)

**Actualiza los campos de la cuota:**
```python
# Montos pagados (suma)
cuota.capital_pagado += capital_aplicar
cuota.interes_pagado += interes_aplicar
cuota.total_pagado += monto_aplicar

# Montos pendientes (resta)
cuota.capital_pendiente = max(0, cuota.capital_pendiente - capital_aplicar)
cuota.interes_pendiente = max(0, cuota.interes_pendiente - interes_aplicar)

# Fecha de pago
cuota.fecha_pago = fecha_pago

# ✅ ACTUALIZA ESTADO (llama a _actualizar_estado_cuota)
return _actualizar_estado_cuota(cuota, fecha_hoy, db, es_exceso)
```

---

### 4. **Función Crítica: `_actualizar_estado_cuota()`**

**Ubicación:** `backend/app/api/v1/endpoints/pagos.py` (líneas 1019-1069)

**LÓGICA DE ACTUALIZACIÓN DE ESTADO:**

#### **Regla 1: Cuota Completamente Pagada** (`total_pagado >= monto_cuota`)

```python
if cuota.total_pagado >= cuota.monto_cuota:
    # Verificar si TODOS los pagos están conciliados
    todos_conciliados = _verificar_pagos_conciliados_cuota(db, cuota.id, cuota.prestamo_id)
    
    if todos_conciliados:
        cuota.estado = "PAGADO"  # ✅ Estado final
    else:
        cuota.estado = "PENDIENTE"  # Pagada pero no conciliada
```

**Estado:** `PAGADO` solo si:
- ✅ `total_pagado >= monto_cuota`
- ✅ TODOS los pagos del préstamo están conciliados (`conciliado = true`)

#### **Regla 2: Pago Parcial** (`0 < total_pagado < monto_cuota`)

```python
elif cuota.total_pagado > Decimal("0.00"):
    if cuota.fecha_vencimiento < fecha_hoy:
        cuota.estado = "PARCIAL"  # Cuota vencida con pago parcial
    else:
        if es_exceso:
            cuota.estado = "ADELANTADO"  # Pago adelantado a cuota futura
        else:
            cuota.estado = "PENDIENTE"  # Cuota vigente con pago parcial
```

**Estados posibles:**
- `PARCIAL`: Cuota vencida con pago parcial
- `ADELANTADO`: Cuota futura con pago adelantado (exceso)
- `PENDIENTE`: Cuota vigente con pago parcial

#### **Regla 3: Sin Pagos** (`total_pagado = 0`)

```python
else:
    if cuota.fecha_vencimiento < fecha_hoy:
        cuota.estado = "ATRASADO"  # Cuota vencida sin pagos
    else:
        cuota.estado = "PENDIENTE"  # Cuota vigente sin pagos
```

**Estados posibles:**
- `ATRASADO`: Cuota vencida sin pagos
- `PENDIENTE`: Cuota vigente sin pagos

---

## 📊 TABLA DE DECISIÓN: Estado de Cuota

| Condición | Fecha Vencimiento | Conciliado | Estado Final |
|-----------|-------------------|------------|--------------|
| `total_pagado >= monto_cuota` | Cualquiera | ✅ Sí | `PAGADO` |
| `total_pagado >= monto_cuota` | Cualquiera | ❌ No | `PENDIENTE` |
| `0 < total_pagado < monto_cuota` | `< hoy` | - | `PARCIAL` |
| `0 < total_pagado < monto_cuota` | `>= hoy` + exceso | - | `ADELANTADO` |
| `0 < total_pagado < monto_cuota` | `>= hoy` | - | `PENDIENTE` |
| `total_pagado = 0` | `< hoy` | - | `ATRASADO` |
| `total_pagado = 0` | `>= hoy` | - | `PENDIENTE` |

---

## 🔍 VERIFICACIÓN DE CONCILIACIÓN

**Función:** `_verificar_pagos_conciliados_cuota()`  
**Ubicación:** `backend/app/api/v1/endpoints/pagos.py` (líneas 973-1016)

**Proceso:**
1. Obtiene todos los pagos del préstamo (`pagos` tabla)
2. Verifica si cada pago está conciliado:
   - Si `pago.conciliado = true` → OK
   - Si `pago.conciliado = false` → Verifica en `pagos_staging` por `numero_documento`
3. Si TODOS están conciliados → `True`, sino → `False`

**Importante:** Una cuota solo pasa a `PAGADO` si TODOS los pagos del préstamo están conciliados.

---

## ✅ RESUMEN: ¿Cuándo se actualiza el estado?

### **ACTUALIZACIÓN AUTOMÁTICA:**
1. ✅ **Al crear un pago:** Se ejecuta `aplicar_pago_a_cuotas()` automáticamente
2. ✅ **Al aplicar monto a cuota:** Se actualiza `total_pagado`, `capital_pagado`, `interes_pagado`
3. ✅ **Después de aplicar monto:** Se llama `_actualizar_estado_cuota()` que evalúa las reglas
4. ✅ **Commit:** Todos los cambios se guardan en la BD con `db.commit()`

### **ESTADOS QUE CAMBIAN AUTOMÁTICAMENTE:**
- `PENDIENTE` → `PARCIAL` (cuando se aplica pago parcial a cuota vencida)
- `PENDIENTE` → `ADELANTADO` (cuando se aplica exceso a cuota futura)
- `PENDIENTE` → `PAGADO` (cuando `total_pagado >= monto_cuota` Y conciliado)
- `ATRASADO` → `PARCIAL` (cuando se aplica pago parcial a cuota vencida)
- `ATRASADO` → `PAGADO` (cuando `total_pagado >= monto_cuota` Y conciliado)

---

## 🔧 VERIFICACIÓN EN BASE DE DATOS

Ejecuta el script `Verificar_Estado_Amortizacion_Por_Pago.sql` para verificar:
1. ✅ Distribución de estados actuales
2. ✅ Coherencia entre `total_pagado` y `estado`
3. ✅ Cuotas con pagos pero estado incorrecto
4. ✅ Relación entre `pago_cuotas` y `cuotas`
5. ✅ Verificación de conciliación

---

## ⚠️ NOTAS IMPORTANTES

1. **Conciliación requerida:** Una cuota solo pasa a `PAGADO` si TODOS los pagos están conciliados
2. **Orden de aplicación:** Los pagos se aplican a las cuotas más antiguas primero (por `fecha_vencimiento`)
3. **Exceso de pago:** Si un pago cubre una cuota y sobra, el exceso se aplica automáticamente a la siguiente
4. **Verificación de cédula:** Antes de aplicar, se valida que `pago.cedula_cliente == prestamo.cedula`

