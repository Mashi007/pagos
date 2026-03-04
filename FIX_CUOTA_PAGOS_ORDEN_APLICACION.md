# 🔧 FIX: orden_aplicacion NULL en cuota_pagos

**Error**: `ERROR: null value in column "orden_aplicacion" violates not-null constraint`

**Causa**: Migración 016 no seteaba `orden_aplicacion` en INSERT → quedó NULL

---

## 🚨 SOLUCIÓN RÁPIDA

### Opción A: Corregir datos existentes (Recomendado)

**Ejecutar este SQL**:

```sql
UPDATE public.cuota_pagos
SET orden_aplicacion = 1
WHERE orden_aplicacion IS NULL;
```

**Verificar**:

```sql
SELECT COUNT(*) FROM public.cuota_pagos WHERE orden_aplicacion IS NULL;
-- Resultado esperado: 0
```

### Opción B: Usar migración 020

```bash
psql $DATABASE_URL < backend/scripts/020_fix_cuota_pagos_orden_aplicacion.sql
```

---

## ✅ DESPUÉS DEL FIX

**Verificar que todo funciona**:

```sql
-- 1. No hay NULL en orden_aplicacion
SELECT COUNT(*) as nulos FROM public.cuota_pagos WHERE orden_aplicacion IS NULL;
-- Resultado: 0

-- 2. Todos tienen orden_aplicacion = 1 (para datos legacy)
SELECT DISTINCT orden_aplicacion FROM public.cuota_pagos;
-- Resultado: 1

-- 3. Total de registros
SELECT COUNT(*) as total_registros FROM public.cuota_pagos;
```

---

## 📝 CONTEXTO TÉCNICO

- **orden_aplicacion**: Secuencia FIFO de pagos aplicados a una cuota
- **Datos legacy**: Cada cuota tenía solo 1 pago (guardado en `pago_id`)
- **Valor correcto**: Todos los datos históricos tienen `orden_aplicacion = 1`
- **Futuros pagos**: Serán incrementales (1, 2, 3, ...) según orden de aplicación

---

## 🔄 ACTUALIZACIÓN DE MIGRACIÓN 016

**Cambio realizado**:

```sql
-- ANTES (❌ causaba NULL):
INSERT INTO public.cuota_pagos (cuota_id, pago_id, monto_aplicado, fecha_aplicacion, es_pago_completo, creado_en)
SELECT ...

-- DESPUÉS (✅ con orden_aplicacion):
INSERT INTO public.cuota_pagos (cuota_id, pago_id, monto_aplicado, fecha_aplicacion, orden_aplicacion, es_pago_completo, creado_en)
SELECT 
    ...,
    1 as orden_aplicacion,  # [FIXED]
    ...
```

---

**¿Ejecutas el fix?** 🚀

```bash
# Opción 1: SQL directo
UPDATE public.cuota_pagos SET orden_aplicacion = 1 WHERE orden_aplicacion IS NULL;

# Opción 2: Vía migración
psql $DATABASE_URL < backend/scripts/020_fix_cuota_pagos_orden_aplicacion.sql
```
