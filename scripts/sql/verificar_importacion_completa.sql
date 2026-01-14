-- ============================================
-- VERIFICAR: Si la importación está completa
-- Ejecutar para confirmar que todo se aplicó correctamente
-- ============================================

-- ============================================
-- VERIFICACIÓN 1: ESTADO DE PAGOS
-- ============================================
SELECT 
    'ESTADO DE PAGOS' as verificacion,
    COUNT(*) as total_pagos_conciliados,
    COUNT(*) FILTER (WHERE estado IN ('PAGADO', 'PARCIAL')) as pagos_con_estado_aplicado,
    COUNT(*) FILTER (WHERE estado IS NULL OR estado NOT IN ('PAGADO', 'PARCIAL')) as pagos_sin_estado,
    CASE 
        WHEN COUNT(*) FILTER (WHERE estado IN ('PAGADO', 'PARCIAL')) = COUNT(*)
        THEN '✅ TODOS LOS PAGOS TIENEN ESTADO APLICADO'
        ELSE '⚠️ HAY PAGOS SIN ESTADO'
    END as estado
FROM public.pagos
WHERE conciliado = TRUE;

-- ============================================
-- VERIFICACIÓN 2: CUOTAS CON PAGOS APLICADOS
-- ============================================
SELECT 
    'CUOTAS CON PAGOS' as verificacion,
    COUNT(*) as total_cuotas,
    COUNT(*) FILTER (WHERE total_pagado > 0) as cuotas_con_pago,
    COUNT(*) FILTER (WHERE total_pagado = 0 OR total_pagado IS NULL) as cuotas_sin_pago,
    SUM(total_pagado) as suma_total_pagado,
    CASE 
        WHEN COUNT(*) FILTER (WHERE total_pagado > 0) > 0
        THEN '✅ HAY CUOTAS CON PAGOS APLICADOS'
        ELSE '❌ NO HAY CUOTAS CON PAGOS'
    END as estado
FROM public.cuotas;

-- ============================================
-- VERIFICACIÓN 3: COMPARACIÓN FINAL
-- ============================================
SELECT 
    'COMPARACION FINAL' as verificacion,
    (SELECT SUM(monto_pagado) FROM public.pagos WHERE conciliado = TRUE) as suma_pagos_conciliados,
    (SELECT COALESCE(SUM(total_pagado), 0) FROM public.cuotas) as suma_total_pagado_cuotas,
    (SELECT SUM(monto_pagado) FROM public.pagos WHERE conciliado = TRUE) - 
    (SELECT COALESCE(SUM(total_pagado), 0) FROM public.cuotas) as diferencia,
    CASE 
        WHEN ABS(
            (SELECT SUM(monto_pagado) FROM public.pagos WHERE conciliado = TRUE) - 
            (SELECT COALESCE(SUM(total_pagado), 0) FROM public.cuotas)
        ) < 0.01
        THEN '✅ COMPLETADO - MONTOS COINCIDEN'
        WHEN (SELECT COALESCE(SUM(total_pagado), 0) FROM public.cuotas) = 0
        THEN '❌ ERROR - NO SE APLICARON PAGOS A CUOTAS'
        ELSE '⚠️ HAY DIFERENCIA - VERIFICAR'
    END as estado_importacion;

-- ============================================
-- RESUMEN FINAL
-- ============================================
SELECT 
    'RESUMEN FINAL' as verificacion,
    CASE 
        WHEN (SELECT COUNT(*) FROM public.pagos 
              WHERE conciliado = TRUE 
                AND (estado IS NULL OR estado NOT IN ('PAGADO', 'PARCIAL'))) = 0
             AND ABS(
                 (SELECT SUM(monto_pagado) FROM public.pagos WHERE conciliado = TRUE) - 
                 (SELECT COALESCE(SUM(total_pagado), 0) FROM public.cuotas)
             ) < 0.01
        THEN '✅ IMPORTACIÓN COMPLETADA - 100%'
        WHEN (SELECT COUNT(*) FROM public.pagos 
              WHERE conciliado = TRUE 
                AND (estado IS NULL OR estado NOT IN ('PAGADO', 'PARCIAL'))) = 0
             AND (SELECT COALESCE(SUM(total_pagado), 0) FROM public.cuotas) = 0
        THEN '❌ ERROR - PAGOS CON ESTADO PERO NO APLICADOS A CUOTAS'
        ELSE '⏳ EN PROCESO O VERIFICAR'
    END as estado_general,
    CURRENT_TIMESTAMP as hora_verificacion;
