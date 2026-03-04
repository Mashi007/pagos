-- Migration: 020_fix_cuota_pagos_orden_aplicacion.sql
-- Propósito: Corregir datos ya insertados en cuota_pagos con orden_aplicacion = NULL
-- Causa: Migración 016 no seteaba orden_aplicacion en INSERT

BEGIN;

-- 1. Ver cuántos registros tienen orden_aplicacion = NULL
SELECT 'Registros con orden_aplicacion NULL:' as info, COUNT(*) as total
FROM public.cuota_pagos
WHERE orden_aplicacion IS NULL;

-- 2. Actualizar orden_aplicacion a 1 para todos los registros NULL
UPDATE public.cuota_pagos
SET orden_aplicacion = 1
WHERE orden_aplicacion IS NULL;

-- 3. Verificar que se actualizaron
SELECT 'Registros actualizados, verificando:' as info, COUNT(*) as total_ahora
FROM public.cuota_pagos;

SELECT 'Con orden_aplicacion NULL ahora:' as info, COUNT(*) as total
FROM public.cuota_pagos
WHERE orden_aplicacion IS NULL;
-- Resultado esperado: 0

COMMIT;

-- NOTAS:
-- - orden_aplicacion = 1 indica que es el ÚNICO pago histórico para esa cuota
-- - Nuevos pagos tendrán orden_aplicacion incremental (1, 2, 3, ...) en código backend
-- - Esto es correcto para datos legacy (solo un pago por cuota en datos antiguos)
