# 🔍 CÓMO CONTRASTAR PAGOS CONCILIADOS CON CUOTAS

> **Objetivo:** Aclarar dónde van los pagos conciliados y cómo verificarlos con las cuotas de cada préstamo

---

## 📍 RESPUESTA DIRECTA

**Los pagos conciliados van a:** `cuotas.total_pagado` en la tabla `cuotas`

**NO van a:**
- ❌ Una tabla separada
- ❌ Un campo diferente
- ❌ Directamente a `prestamos`

---

## 🔄 RELACIÓN ENTRE PAGOS Y CUOTAS

### **Flujo Completo:**

```
┌─────────────────────────────────────────┐
│ 1. TABLA: pagos                        │
│    - pagos.conciliado = TRUE           │
│    - pagos.monto_pagado = $500         │
│    - pagos.prestamo_id = 123           │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│ 2. PROCESO: aplicar_pago_a_cuotas()    │
│    - Verifica: conciliado = TRUE        │
│    - Obtiene cuotas pendientes          │
│    - Distribuye el monto entre cuotas   │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│ 3. TABLA: cuotas                        │
│    - cuotas.total_pagado += $500        │
│    - Se actualiza en las cuotas         │
│      correspondientes al préstamo       │
└─────────────────────────────────────────┘
```

---

## 📊 CÓMO CONTRASTAR/VERIFICAR

### **1. Ver Pagos Conciliados de un Préstamo:**

```sql
-- Ver todos los pagos conciliados de un préstamo específico
SELECT 
    p.id as pago_id,
    p.cedula,
    p.monto_pagado,
    p.conciliado,
    p.fecha_pago,
    p.prestamo_id
FROM public.pagos p
WHERE p.prestamo_id = 123  -- ← Cambiar por el ID del préstamo
  AND p.conciliado = TRUE
ORDER BY p.fecha_pago;
```

### **2. Ver Cuotas con Total Pagado del Mismo Préstamo:**

```sql
-- Ver las cuotas del mismo préstamo con total_pagado
SELECT 
    c.id as cuota_id,
    c.prestamo_id,
    c.numero_cuota,
    c.monto_cuota,
    c.total_pagado,  -- ← AQUÍ ESTÁN LOS PAGOS CONCILIADOS
    c.estado,
    c.fecha_pago
FROM public.cuotas c
WHERE c.prestamo_id = 123  -- ← Mismo préstamo
ORDER BY c.numero_cuota;
```

### **3. CONTRASTAR: Suma de Pagos vs Suma de Total Pagado:**

```sql
-- Verificar que la suma de pagos conciliados coincide con total_pagado
SELECT 
    p.prestamo_id,
    pr.cedula,
    -- Suma de pagos conciliados
    SUM(p.monto_pagado) as suma_pagos_conciliados,
    -- Suma de total_pagado en cuotas
    SUM(c.total_pagado) as suma_total_pagado_cuotas,
    -- Diferencia
    SUM(p.monto_pagado) - SUM(c.total_pagado) as diferencia,
    -- Validación
    CASE 
        WHEN ABS(SUM(p.monto_pagado) - SUM(c.total_pagado)) < 0.01 
        THEN 'OK - COINCIDEN'
        ELSE 'ERROR - NO COINCIDEN'
    END as validacion
FROM public.pagos p
JOIN public.prestamos pr ON pr.id = p.prestamo_id
LEFT JOIN public.cuotas c ON c.prestamo_id = p.prestamo_id
WHERE p.conciliado = TRUE
GROUP BY p.prestamo_id, pr.cedula
ORDER BY p.prestamo_id;
```

---

## 🔍 VERIFICACIÓN DETALLADA POR PRÉSTAMO

### **Script Completo para un Préstamo Específico:**

```sql
-- ============================================
-- VERIFICAR: Pagos Conciliados vs Cuotas
-- Para un préstamo específico
-- ============================================

-- Cambiar este ID por el préstamo que quieras verificar
\set prestamo_id 123

-- PASO 1: Ver pagos conciliados del préstamo
SELECT 
    'PAGOS CONCILIADOS' as tipo,
    p.id as registro_id,
    p.monto_pagado as monto,
    p.fecha_pago,
    p.conciliado
FROM public.pagos p
WHERE p.prestamo_id = :prestamo_id
  AND p.conciliado = TRUE
ORDER BY p.fecha_pago;

-- PASO 2: Ver cuotas con total_pagado
SELECT 
    'CUOTAS CON TOTAL_PAGADO' as tipo,
    c.id as registro_id,
    c.numero_cuota,
    c.monto_cuota,
    c.total_pagado as monto,  -- ← AQUÍ ESTÁN LOS PAGOS CONCILIADOS
    c.estado,
    c.fecha_pago
FROM public.cuotas c
WHERE c.prestamo_id = :prestamo_id
ORDER BY c.numero_cuota;

-- PASO 3: Resumen comparativo
SELECT 
    'RESUMEN COMPARATIVO' as tipo,
    (SELECT SUM(monto_pagado) FROM public.pagos 
     WHERE prestamo_id = :prestamo_id AND conciliado = TRUE) as suma_pagos_conciliados,
    (SELECT SUM(total_pagado) FROM public.cuotas 
     WHERE prestamo_id = :prestamo_id) as suma_total_pagado_cuotas,
    (SELECT SUM(monto_pagado) FROM public.pagos 
     WHERE prestamo_id = :prestamo_id AND conciliado = TRUE) - 
    (SELECT SUM(total_pagado) FROM public.cuotas 
     WHERE prestamo_id = :prestamo_id) as diferencia,
    CASE 
        WHEN ABS(
            (SELECT SUM(monto_pagado) FROM public.pagos 
             WHERE prestamo_id = :prestamo_id AND conciliado = TRUE) - 
            (SELECT SUM(total_pagado) FROM public.cuotas 
             WHERE prestamo_id = :prestamo_id)
        ) < 0.01 
        THEN 'OK - COINCIDEN'
        ELSE 'ERROR - NO COINCIDEN'
    END as validacion;
```

---

## ⚠️ IMPORTANTE: Relación N:M (No 1:1)

**NO es una relación 1:1:**

- ❌ **NO:** 1 pago conciliado = 1 cuota.total_pagado
- ✅ **SÍ:** 1 pago conciliado puede distribuirse en MÚLTIPLES cuotas
- ✅ **SÍ:** 1 cuota puede recibir MÚLTIPLES pagos conciliados

### **Ejemplo:**

```
Pago Conciliado: $500
├─ Cuota 1: total_pagado += $300 (del pago)
├─ Cuota 2: total_pagado += $200 (del mismo pago)
└─ Total aplicado: $500 ✅

Otro Pago Conciliado: $200
├─ Cuota 2: total_pagado += $100 (del segundo pago)
├─ Cuota 3: total_pagado += $100 (del segundo pago)
└─ Total aplicado: $200 ✅

Resultado Final:
- Cuota 1: total_pagado = $300 (de 1 pago)
- Cuota 2: total_pagado = $300 (de 2 pagos: $200 + $100)
- Cuota 3: total_pagado = $100 (de 1 pago)
```

---

## 📝 RESUMEN

### **Dónde van los pagos conciliados:**

1. **Tabla origen:** `pagos`
   - Campo: `pagos.conciliado = TRUE`
   - Campo: `pagos.monto_pagado`

2. **Tabla destino:** `cuotas`
   - Campo: `cuotas.total_pagado` ← **AQUÍ VAN LOS PAGOS CONCILIADOS**
   - Se suma acumulativamente (`+=`)

3. **Relación:**
   - `pagos.prestamo_id` → `cuotas.prestamo_id`
   - Los pagos se distribuyen entre las cuotas del mismo préstamo

### **Cómo contrastar:**

1. Sumar `pagos.monto_pagado` donde `conciliado = TRUE` y `prestamo_id = X`
2. Sumar `cuotas.total_pagado` donde `prestamo_id = X`
3. Comparar: ambas sumas deben coincidir (o tener diferencia mínima por redondeo)

---

## ✅ CONCLUSIÓN

**Los pagos conciliados van a `cuotas.total_pagado`**

- Se suman acumulativamente
- Se distribuyen entre las cuotas pendientes del préstamo
- La suma de pagos conciliados debe coincidir con la suma de `total_pagado` en las cuotas
