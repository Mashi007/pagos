# 📊 Confirmación: Cálculo de Morosidad

> **Documento de confirmación sobre dónde y cómo se calcula la morosidad**  
> Última actualización: 2025-11-06

---

## 🎯 Tabla donde se Calcula la Morosidad

**Tabla:** `cuotas`

**Columnas de Morosidad:**
- `cuotas.dias_morosidad` (INTEGER) - Días de atraso
- `cuotas.monto_morosidad` (NUMERIC(12,2)) - Monto pendiente en dinero

---

## 📋 Campos Utilizados para el Cálculo

### **1. Cálculo de `dias_morosidad` (Días de Morosidad)**

**Función:** `_actualizar_morosidad_cuota()`  
**Ubicación:** `backend/app/api/v1/endpoints/pagos.py` (líneas 994-1030)

**Campos utilizados:**
- `cuotas.fecha_vencimiento` (DATE) - Fecha límite de pago de la cuota
- `cuotas.fecha_pago` (DATE, nullable) - Fecha real de pago (si existe)
- `fecha_hoy` (DATE) - Fecha actual del sistema

**Lógica de Cálculo:**

```python
# CASO 1: Cuota tiene fecha_pago (ya fue pagada)
if cuota.fecha_pago:
    if cuota.fecha_pago > cuota.fecha_vencimiento:
        # Pagada después del vencimiento: calcular días de atraso
        dias_morosidad = (cuota.fecha_pago - cuota.fecha_vencimiento).days
    else:
        # Pagada a tiempo o adelantada: 0 días de morosidad
        dias_morosidad = 0

# CASO 2: Cuota NO tiene fecha_pago (aún no pagada)
else:
    if cuota.fecha_vencimiento < fecha_hoy:
        # Vencida y no pagada: calcular días desde vencimiento hasta hoy
        dias_morosidad = (fecha_hoy - cuota.fecha_vencimiento).days
    else:
        # No vencida aún: 0 días de morosidad
        dias_morosidad = 0
```

**Fórmula:**
- **Si está pagada:** `dias_morosidad = MAX(0, fecha_pago - fecha_vencimiento)`
- **Si NO está pagada:** `dias_morosidad = MAX(0, fecha_hoy - fecha_vencimiento)`

---

### **2. Cálculo de `monto_morosidad` (Monto de Morosidad en Dinero)**

**Función:** `_actualizar_morosidad_cuota()`  
**Ubicación:** `backend/app/api/v1/endpoints/pagos.py` (líneas 1023-1025)

**Campos utilizados:**
- `cuotas.monto_cuota` (NUMERIC(12,2)) - Monto total programado de la cuota
- `cuotas.total_pagado` (NUMERIC(12,2)) - Suma acumulativa de todos los pagos aplicados

**Lógica de Cálculo:**

```python
# Calcular monto pendiente
monto_pendiente = cuota.monto_cuota - (cuota.total_pagado or Decimal("0.00"))

# Asegurar que nunca sea negativo (si hay sobrepago, monto_morosidad = 0)
monto_morosidad = max(Decimal("0.00"), monto_pendiente)
```

**Fórmula:**
```
monto_morosidad = MAX(0, monto_cuota - total_pagado)
```

**Ejemplos:**
- `monto_cuota = 100.00`, `total_pagado = 50.00` → `monto_morosidad = 50.00`
- `monto_cuota = 100.00`, `total_pagado = 100.00` → `monto_morosidad = 0.00`
- `monto_cuota = 100.00`, `total_pagado = 120.00` → `monto_morosidad = 0.00` (sobrepago)

---

## 🔄 Cuándo se Actualiza la Morosidad

**La morosidad se actualiza automáticamente en los siguientes casos:**

1. **Cuando se aplica un pago a una cuota:**
   - Función: `_aplicar_monto_a_cuota()` (línea 1156)
   - Se llama a `_actualizar_morosidad_cuota()` después de aplicar el pago

2. **Cuando se actualiza el estado de una cuota:**
   - Función: `_actualizar_estado_cuota()` (línea 1084)
   - Se llama a `_actualizar_morosidad_cuota()` al finalizar la actualización

---

## 📊 Resumen de Campos

### **Tabla: `cuotas`**

| Campo | Tipo | Descripción | Uso en Cálculo |
|-------|------|-------------|----------------|
| `fecha_vencimiento` | DATE | Fecha límite de pago | ✅ Usado para calcular `dias_morosidad` |
| `fecha_pago` | DATE (nullable) | Fecha real de pago | ✅ Usado para calcular `dias_morosidad` (si existe) |
| `monto_cuota` | NUMERIC(12,2) | Monto total programado | ✅ Usado para calcular `monto_morosidad` |
| `total_pagado` | NUMERIC(12,2) | Suma de pagos aplicados | ✅ Usado para calcular `monto_morosidad` |
| `dias_morosidad` | INTEGER | **RESULTADO:** Días de atraso | ⭐ Calculado automáticamente |
| `monto_morosidad` | NUMERIC(12,2) | **RESULTADO:** Monto pendiente | ⭐ Calculado automáticamente |

---

## ✅ Confirmación Final

### **Tabla:**
✅ **`cuotas`** - Es la única tabla donde se calcula y almacena la morosidad

### **Campos para `dias_morosidad`:**
1. ✅ `cuotas.fecha_vencimiento` (obligatorio)
2. ✅ `cuotas.fecha_pago` (opcional - si existe, se usa; si no, se usa `fecha_hoy`)
3. ✅ `fecha_hoy` (fecha actual del sistema - solo si no hay `fecha_pago`)

### **Campos para `monto_morosidad`:**
1. ✅ `cuotas.monto_cuota` (monto programado)
2. ✅ `cuotas.total_pagado` (suma acumulativa de pagos)

### **Fórmulas:**
- **`dias_morosidad`:** 
  - Si pagada: `MAX(0, fecha_pago - fecha_vencimiento)`
  - Si no pagada: `MAX(0, fecha_hoy - fecha_vencimiento)`
  
- **`monto_morosidad`:** 
  - `MAX(0, monto_cuota - total_pagado)`

---

**Última actualización:** 2025-11-06

