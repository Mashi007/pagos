# 🔍 ANÁLISIS: Inconsistencias en monto_morosidad

## Fecha de Análisis
2025-11-06

---

## ⚠️ PROBLEMA IDENTIFICADO

### Inconsistencias Detectadas

**Total:** 741 cuotas (1.6% del total)

### Patrón Común

Todas las cuotas con inconsistencias tienen:
- ✅ `estado = 'PAGADO'`
- ✅ `total_pagado > monto_cuota` (sobrepago)
- ✅ `monto_morosidad_actual = 0.00`
- ❌ `monto_morosidad_correcto = negativo` (porque `monto_cuota - total_pagado` es negativo)

### Ejemplos

| ID | Préstamo | Cuota | monto_cuota | total_pagado | monto_morosidad_actual | monto_morosidad_correcto | diferencia |
|----|----------|-------|-------------|--------------|------------------------|--------------------------|------------|
| 35980 | 2971 | 4 | $96.00 | $1,254.00 | $0.00 | **-$1,158.00** | $1,158.00 |
| 2478 | 200 | 4 | $160.00 | $900.00 | $0.00 | **-$740.00** | $740.00 |
| 45159 | 3706 | 1 | $96.00 | $768.00 | $0.00 | **-$672.00** | $672.00 |

---

## 🔧 CAUSA RAÍZ

### Problema en el Script de Corrección

El script original comparaba con:
```sql
WHERE ABS(monto_morosidad - (monto_cuota - COALESCE(total_pagado, 0))) > 0.01
```

**Problema:** Cuando `total_pagado > monto_cuota`, el cálculo `(monto_cuota - total_pagado)` da **negativo**, pero `monto_morosidad` debe ser siempre **>= 0**.

**Solución:** Comparar con el valor correcto usando `GREATEST(0, ...)`:
```sql
WHERE ABS(monto_morosidad - GREATEST(0, monto_cuota - COALESCE(total_pagado, 0))) > 0.01
```

---

## ✅ SOLUCIÓN IMPLEMENTADA

### Script Corregido

**Ubicación:** `backend/scripts/migrations/CORREGIR_INCONSISTENCIAS_MOROSIDAD.sql`

**Cambios realizados:**
1. ✅ WHERE en identificación usa `GREATEST(0, ...)`
2. ✅ WHERE en UPDATE usa `GREATEST(0, ...)`
3. ✅ WHERE en verificaciones usa `GREATEST(0, ...)`

### Fórmula Correcta

```sql
monto_morosidad = GREATEST(0, monto_cuota - total_pagado)
```

**Explicación:**
- Si `total_pagado <= monto_cuota`: `monto_morosidad = monto_cuota - total_pagado` (lo que falta)
- Si `total_pagado > monto_cuota`: `monto_morosidad = 0` (sobrepago, no hay morosidad)

---

## 📊 ANÁLISIS DE SOBREPAGOS

### ¿Por qué hay sobrepagos?

Las 741 cuotas tienen `total_pagado > monto_cuota`, lo que indica:

1. **Pagos múltiples aplicados a la misma cuota**
   - Un pago puede cubrir múltiples cuotas
   - El exceso se aplica a la siguiente cuota
   - Pero `total_pagado` puede quedar mayor que `monto_cuota` si hay errores en la aplicación

2. **Errores en la aplicación de pagos**
   - Pagos aplicados incorrectamente
   - Duplicación de pagos
   - Errores en la lógica de distribución

3. **Datos históricos inconsistentes**
   - Migraciones previas con errores
   - Correcciones manuales incorrectas

### Impacto

- **Bajo:** Solo 741 cuotas (1.6% del total)
- **Corregible:** El script corregido resuelve el problema
- **Sin pérdida de datos:** Los sobrepagos se convierten en `monto_morosidad = 0`

---

## 🎯 PRÓXIMOS PASOS

### 1. Ejecutar Script Corregido

```sql
-- Ejecutar en DBeaver:
backend/scripts/migrations/CORREGIR_INCONSISTENCIAS_MOROSIDAD.sql
```

### 2. Verificar Corrección

Después de ejecutar, verificar que:
- ✅ `inconsistencias_restantes = 0`
- ✅ Todas las cuotas con sobrepago tienen `monto_morosidad = 0`

### 3. Investigar Causa de Sobrepagos (OPCIONAL)

Si se desea investigar por qué hay sobrepagos:
```sql
-- Ver cuotas con sobrepago
SELECT 
    id,
    prestamo_id,
    numero_cuota,
    monto_cuota,
    total_pagado,
    (total_pagado - monto_cuota) as exceso_pago,
    estado
FROM cuotas
WHERE total_pagado > monto_cuota
ORDER BY exceso_pago DESC;
```

---

## ✅ RESUMEN

### Problema
- 741 cuotas con `monto_morosidad` incorrecto
- Todas tienen sobrepago (`total_pagado > monto_cuota`)
- El script original no las capturaba correctamente

### Solución
- Script corregido que usa `GREATEST(0, ...)` en todas las comparaciones
- Actualiza `monto_morosidad = 0` para cuotas con sobrepago

### Estado
- ✅ **Script corregido y listo para ejecutar**
- ⏳ **Pendiente: Ejecutar script corregido en DBeaver**

---

**Estado:** ✅ **ANÁLISIS COMPLETO - SCRIPT CORREGIDO LISTO PARA EJECUTAR**

