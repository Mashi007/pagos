-- ============================================
-- INFORME RÁPIDO DE AVANCE
-- Ejecutar para ver estado actual
-- ============================================

-- RESUMEN GENERAL
SELECT 
    '📊 RESUMEN GENERAL' as seccion,
    (SELECT COUNT(*) FROM public.pagos WHERE conciliado = TRUE) as total_pagos_conciliados,
    (SELECT COUNT(*) FROM public.pagos WHERE conciliado = TRUE AND estado IN ('PAGADO', 'PARCIAL')) as pagos_aplicados,
    (SELECT COUNT(*) FROM public.pagos WHERE conciliado = TRUE AND (estado IS NULL OR estado NOT IN ('PAGADO', 'PARCIAL'))) as pagos_pendientes,
    ROUND(
        (SELECT COUNT(*) FROM public.pagos WHERE conciliado = TRUE AND estado IN ('PAGADO', 'PARCIAL'))::numeric / 
        NULLIF((SELECT COUNT(*) FROM public.pagos WHERE conciliado = TRUE), 0) * 100, 
        2
    ) as porcentaje_completado;

-- MONTOS
SELECT 
    '💰 MONTOS' as seccion,
    (SELECT SUM(monto_pagado) FROM public.pagos WHERE conciliado = TRUE) as suma_pagos_conciliados,
    (SELECT COALESCE(SUM(total_pagado), 0) FROM public.cuotas) as suma_aplicada_cuotas,
    (SELECT SUM(monto_pagado) FROM public.pagos WHERE conciliado = TRUE) - 
    (SELECT COALESCE(SUM(total_pagado), 0) FROM public.cuotas) as diferencia,
    CASE 
        WHEN ABS(
            (SELECT SUM(monto_pagado) FROM public.pagos WHERE conciliado = TRUE) - 
            (SELECT COALESCE(SUM(total_pagado), 0) FROM public.cuotas)
        ) < 0.01 
        THEN '✅ COMPLETADO'
        ELSE '⏳ EN PROCESO'
    END as estado;

-- CUOTAS AFECTADAS
SELECT 
    '📋 CUOTAS' as seccion,
    COUNT(*) as cuotas_con_pago,
    SUM(total_pagado) as suma_total_pagado,
    COUNT(DISTINCT prestamo_id) as prestamos_afectados
FROM public.cuotas
WHERE total_pagado > 0;
