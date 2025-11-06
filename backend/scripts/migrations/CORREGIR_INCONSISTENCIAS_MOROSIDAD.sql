-- ============================================================================
-- CORRECCIÓN: Inconsistencias en monto_morosidad
-- ============================================================================
-- Fecha: 2025-11-06
-- Descripción: Corrige las 741 inconsistencias detectadas donde
--              monto_morosidad != (monto_cuota - total_pagado)
-- ============================================================================

-- ============================================================================
-- PASO 1: Identificar Inconsistencias
-- ============================================================================

-- Ver cuotas con inconsistencias
SELECT 
    'INCONSISTENCIAS DETECTADAS' as verificacion,
    id,
    prestamo_id,
    numero_cuota,
    monto_cuota,
    total_pagado,
    monto_morosidad as monto_morosidad_actual,
    (monto_cuota - COALESCE(total_pagado, 0)) as monto_morosidad_correcto,
    ABS(monto_morosidad - (monto_cuota - COALESCE(total_pagado, 0))) as diferencia,
    estado,
    fecha_vencimiento,
    fecha_pago
FROM cuotas
WHERE ABS(monto_morosidad - (monto_cuota - COALESCE(total_pagado, 0))) > 0.01
ORDER BY diferencia DESC
LIMIT 20;

-- ============================================================================
-- PASO 2: Corregir Inconsistencias
-- ============================================================================

-- Actualizar monto_morosidad con el valor correcto
UPDATE cuotas
SET monto_morosidad = GREATEST(0, monto_cuota - COALESCE(total_pagado, 0))
WHERE ABS(monto_morosidad - (monto_cuota - COALESCE(total_pagado, 0))) > 0.01;

-- ============================================================================
-- PASO 3: Verificar Corrección
-- ============================================================================

-- Verificar que ya no hay inconsistencias
SELECT 
    'VERIFICACIÓN POST-CORRECCIÓN' as verificacion,
    COUNT(*) as total_cuotas,
    COUNT(CASE WHEN ABS(monto_morosidad - (monto_cuota - COALESCE(total_pagado, 0))) > 0.01 THEN 1 END) as inconsistencias_restantes
FROM cuotas;

-- ============================================================================
-- PASO 4: Verificar dias_morosidad también
-- ============================================================================

-- Verificar que dias_morosidad está correcto para cuotas no pagadas
SELECT 
    'VERIFICACIÓN: dias_morosidad para cuotas no pagadas' as verificacion,
    COUNT(*) as total_cuotas_no_pagadas,
    COUNT(CASE 
        WHEN fecha_pago IS NULL 
             AND fecha_vencimiento < CURRENT_DATE 
             AND dias_morosidad != (CURRENT_DATE - fecha_vencimiento)::INTEGER 
        THEN 1 
    END) as inconsistencias_dias
FROM cuotas
WHERE fecha_pago IS NULL
  AND fecha_vencimiento < CURRENT_DATE;

-- ============================================================================
-- PASO 5: Corregir dias_morosidad si es necesario
-- ============================================================================

-- Actualizar dias_morosidad para cuotas no pagadas
UPDATE cuotas
SET dias_morosidad = (CURRENT_DATE - fecha_vencimiento)::INTEGER
WHERE fecha_pago IS NULL
  AND fecha_vencimiento < CURRENT_DATE
  AND dias_morosidad != (CURRENT_DATE - fecha_vencimiento)::INTEGER;

-- ============================================================================
-- PASO 6: Verificación Final Completa
-- ============================================================================

-- Resumen final
SELECT 
    'RESUMEN FINAL' as verificacion,
    COUNT(*) as total_cuotas,
    COUNT(CASE WHEN dias_morosidad > 0 THEN 1 END) as cuotas_con_dias_morosidad,
    COUNT(CASE WHEN monto_morosidad > 0 THEN 1 END) as cuotas_con_monto_morosidad,
    COUNT(CASE WHEN ABS(monto_morosidad - (monto_cuota - COALESCE(total_pagado, 0))) > 0.01 THEN 1 END) as inconsistencias_monto,
    COUNT(CASE 
        WHEN fecha_pago IS NULL 
             AND fecha_vencimiento < CURRENT_DATE 
             AND dias_morosidad != (CURRENT_DATE - fecha_vencimiento)::INTEGER 
        THEN 1 
    END) as inconsistencias_dias,
    SUM(dias_morosidad) as total_dias_morosidad,
    SUM(monto_morosidad) as total_monto_morosidad
FROM cuotas;

-- ============================================================================
-- ✅ CORRECCIÓN COMPLETADA
-- ============================================================================

