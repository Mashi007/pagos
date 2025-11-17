# 📋 GUÍA SIMPLE: Qué Corregir en la Tabla de Amortización

**Fecha:** 2025-01-27
**Objetivo:** Explicar de forma simple qué problemas hay y cómo solucionarlos

---

## 🎯 PROBLEMA PRINCIPAL

Tienes **18 cuotas** que están **100% pagadas** pero el sistema las marca como **"PENDIENTE"** en lugar de **"PAGADO"**.

**Ejemplo:**
- Cuota tiene: `total_pagado = 548.00` y `monto_cuota = 548.00` (100% pagado)
- Pero el `estado = "PENDIENTE"` ❌
- Debería ser: `estado = "PAGADO"` ✅

---

## 🔍 ¿POR QUÉ PASÓ ESTO?

Estas 18 cuotas probablemente son **pagos antiguos** o **migrados desde otro sistema** que:
- Tienen el dinero aplicado (`total_pagado >= monto_cuota`)
- Pero no tienen registro en la tabla `pagos`
- Por eso el sistema no las marca como "PAGADO"

---

## ✅ SOLUCIÓN: 3 PASOS SIMPLES

### **PASO 1: Verificar el problema**

Ejecuta este query en DBeaver para ver las 18 cuotas:

```sql
SELECT
    c.id AS cuota_id,
    c.prestamo_id,
    c.numero_cuota,
    c.monto_cuota,
    c.total_pagado,
    c.estado,
    ROUND((c.total_pagado * 100.0 / NULLIF(c.monto_cuota, 0)), 2) AS porcentaje_pagado
FROM cuotas c
WHERE c.total_pagado >= c.monto_cuota
  AND c.estado = 'PENDIENTE'
ORDER BY c.prestamo_id, c.numero_cuota;
```

**Resultado esperado:** Verás 18 filas con `porcentaje_pagado = 100.00` pero `estado = 'PENDIENTE'`

---

### **PASO 2: Corregir las 18 cuotas**

Ejecuta este UPDATE en DBeaver para corregirlas:

```sql
-- Marcar como PAGADO las cuotas completas que están PENDIENTE
UPDATE cuotas c
SET estado = 'PAGADO',
    fecha_pago = COALESCE(
        c.fecha_pago,
        c.fecha_vencimiento,  -- Usar fecha de vencimiento si no hay fecha_pago
        CURRENT_DATE
    )
WHERE c.total_pagado >= c.monto_cuota
  AND c.estado = 'PENDIENTE';
```

**Resultado esperado:**
- ✅ Se actualizan 18 cuotas
- ✅ Cambian de `PENDIENTE` a `PAGADO`

---

### **PASO 3: Verificar que se corrigió**

Ejecuta este query para verificar:

```sql
SELECT
    'VERIFICACIÓN' AS paso,
    COUNT(*) AS cuotas_completas_pendientes
FROM cuotas
WHERE total_pagado >= monto_cuota
  AND estado = 'PENDIENTE';
```

**Resultado esperado:**
- ✅ Debe mostrar `0` cuotas completas pero PENDIENTE

---

## 📊 RESUMEN FINAL ESPERADO

Después de corregir:

| Antes | Después |
|-------|---------|
| 371 cuotas PAGADAS | **389 cuotas PAGADAS** ✅ |
| 18 cuotas completas pero PENDIENTE | **0 cuotas completas pero PENDIENTE** ✅ |

---

## ❓ PREGUNTAS FRECUENTES

### ¿Es seguro hacer esto?

**Sí**, porque:
- Solo cambia el `estado` de `PENDIENTE` a `PAGADO`
- El dinero ya está aplicado (`total_pagado >= monto_cuota`)
- No cambia ningún monto, solo corrige el estado

### ¿Qué pasa si ejecuto el UPDATE dos veces?

**No pasa nada malo**, porque:
- Solo actualiza las cuotas que cumplen la condición
- Si ya están `PAGADO`, no las vuelve a actualizar

### ¿Esto afecta otros datos?

**No**, porque:
- Solo cambia el campo `estado` y `fecha_pago` de esas 18 cuotas
- No modifica montos ni otras cuotas

---

## 🚀 EJECUCIÓN RÁPIDA (TODO EN UNO)

Si quieres hacerlo todo de una vez, ejecuta este script completo:

```sql
-- ================================================================
-- CORRECCIÓN RÁPIDA: 18 Cuotas Completas pero PENDIENTE
-- ================================================================

-- 1. Ver cuántas hay antes
SELECT
    'ANTES' AS momento,
    COUNT(*) AS cuotas_completas_pendientes
FROM cuotas
WHERE total_pagado >= monto_cuota
  AND estado = 'PENDIENTE';

-- 2. Corregir
UPDATE cuotas c
SET estado = 'PAGADO',
    fecha_pago = COALESCE(c.fecha_pago, c.fecha_vencimiento, CURRENT_DATE)
WHERE c.total_pagado >= c.monto_cuota
  AND c.estado = 'PENDIENTE';

-- 3. Ver cuántas quedan después
SELECT
    'DESPUÉS' AS momento,
    COUNT(*) AS cuotas_completas_pendientes
FROM cuotas
WHERE total_pagado >= monto_cuota
  AND estado = 'PENDIENTE';

-- 4. Resumen final
SELECT
    'RESUMEN FINAL' AS tipo,
    COUNT(*) AS total_cuotas,
    COUNT(CASE WHEN estado = 'PAGADO' THEN 1 END) AS cuotas_pagadas,
    COUNT(CASE WHEN estado = 'PENDIENTE' AND total_pagado >= monto_cuota THEN 1 END) AS cuotas_completas_pendientes
FROM cuotas;
```

**Resultado esperado:**
- ✅ `ANTES`: 18 cuotas
- ✅ `DESPUÉS`: 0 cuotas
- ✅ `cuotas_pagadas`: 389 (antes 371)

---

## 📝 NOTA IMPORTANTE

Estas 18 cuotas son **pagos históricos o migrados**. Están correctamente pagadas, solo necesitan que se actualice el estado para reflejar la realidad.

