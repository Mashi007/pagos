-- Migración 014: Normalizar estados de cuotas según regla de mora
-- [MORA] Convierte ATRASADO/VENCIDA en VENCIDO o MORA según días_mora

-- 1. Recalcular dias_mora para cuotas existentes y actualizar estado
UPDATE public.cuotas c
SET 
    dias_mora = (CURRENT_DATE - c.fecha_vencimiento),
    estado = CASE
        WHEN c.total_pagado >= c.monto_cuota - 0.01 THEN 'PAGADO'
        WHEN (CURRENT_DATE - c.fecha_vencimiento) IS NULL OR (CURRENT_DATE - c.fecha_vencimiento) <= 0 THEN 'PENDIENTE'
        WHEN (CURRENT_DATE - c.fecha_vencimiento) > 90 THEN 'MORA'
        WHEN (CURRENT_DATE - c.fecha_vencimiento) > 0 AND (CURRENT_DATE - c.fecha_vencimiento) <= 90 THEN 'VENCIDO'
        ELSE c.estado
    END
WHERE c.fecha_vencimiento IS NOT NULL
  AND c.estado IN ('ATRASADO', 'VENCIDA', 'PENDIENTE');

-- 2. Validar que no quedan ATRASADO/VENCIDA (todos deben estar migrados)
-- SELECT DISTINCT estado FROM cuotas WHERE estado IN ('ATRASADO', 'VENCIDA');
-- Resultado esperado: (sin filas = éxito)

-- 3. Actualizar CHECK constraint en cuotas para incluir MORA y VENCIDO
-- (Ya debe estar en 010_check_constraints.sql)
