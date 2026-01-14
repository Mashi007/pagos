-- ============================================
-- VERIFICAR: Si se está importando/aplicando pagos
-- Ejecutar para ver estado actual del proceso
-- ============================================

-- ============================================
-- VERIFICACIÓN 1: ESTADO DE PAGOS
-- ============================================
SELECT 
    'ESTADO DE PAGOS' as verificacion,
    COUNT(*) as total_pagos_conciliados,
    COUNT(*) FILTER (WHERE estado IN ('PAGADO', 'PARCIAL')) as pagos_con_estado_aplicado,
    COUNT(*) FILTER (WHERE estado IS NULL OR estado NOT IN ('PAGADO', 'PARCIAL')) as pagos_sin_aplicar,
    CASE 
        WHEN COUNT(*) FILTER (WHERE estado IN ('PAGADO', 'PARCIAL')) > 0 
        THEN '✅ SÍ SE ESTÁ IMPORTANDO'
        ELSE '⏳ AÚN NO HA COMENZADO'
    END as estado_importacion
FROM public.pagos
WHERE conciliado = TRUE;

-- ============================================
-- VERIFICACIÓN 2: CUOTAS CON TOTAL_PAGADO
-- ============================================
SELECT 
    'CUOTAS CON PAGOS' as verificacion,
    COUNT(*) as cuotas_con_total_pagado,
    SUM(total_pagado) as suma_total_pagado,
    COUNT(DISTINCT prestamo_id) as prestamos_afectados,
    CASE 
        WHEN COUNT(*) > 0 
        THEN '✅ SÍ SE ESTÁ IMPORTANDO'
        ELSE '⏳ AÚN NO HAY PAGOS APLICADOS'
    END as estado_importacion
FROM public.cuotas
WHERE total_pagado > 0;

-- ============================================
-- VERIFICACIÓN 3: COMPARACIÓN MONTOS
-- ============================================
SELECT 
    'COMPARACION MONTOS' as verificacion,
    (SELECT SUM(monto_pagado) FROM public.pagos WHERE conciliado = TRUE) as suma_pagos_conciliados,
    (SELECT COALESCE(SUM(total_pagado), 0) FROM public.cuotas) as suma_aplicada_cuotas,
    (SELECT SUM(monto_pagado) FROM public.pagos WHERE conciliado = TRUE) - 
    (SELECT COALESCE(SUM(total_pagado), 0) FROM public.cuotas) as diferencia,
    CASE 
        WHEN (SELECT COALESCE(SUM(total_pagado), 0) FROM public.cuotas) > 0 
        THEN '✅ SÍ SE ESTÁ IMPORTANDO'
        WHEN ABS(
            (SELECT SUM(monto_pagado) FROM public.pagos WHERE conciliado = TRUE) - 
            (SELECT COALESCE(SUM(total_pagado), 0) FROM public.cuotas)
        ) < 0.01
        THEN '✅ IMPORTACIÓN COMPLETADA'
        ELSE '⏳ AÚN NO HA COMENZADO'
    END as estado_importacion;

-- ============================================
-- VERIFICACIÓN 4: ÚLTIMOS PAGOS PROCESADOS
-- ============================================
SELECT 
    'ULTIMOS PAGOS PROCESADOS' as verificacion,
    p.id as pago_id,
    p.prestamo_id,
    p.monto_pagado,
    p.estado,
    p.fecha_pago,
    COALESCE(SUM(c.total_pagado), 0) as total_aplicado_en_cuotas,
    CASE 
        WHEN p.estado IN ('PAGADO', 'PARCIAL') THEN '✅ APLICADO'
        ELSE '⏳ PENDIENTE'
    END as estado_aplicacion
FROM public.pagos p
LEFT JOIN public.cuotas c ON c.prestamo_id = p.prestamo_id
WHERE p.conciliado = TRUE
GROUP BY p.id, p.prestamo_id, p.monto_pagado, p.estado, p.fecha_pago
ORDER BY p.id DESC
LIMIT 20;

-- ============================================
-- RESUMEN FINAL
-- ============================================
SELECT 
    'RESUMEN FINAL' as verificacion,
    CASE 
        WHEN (SELECT COUNT(*) FROM public.cuotas WHERE total_pagado > 0) > 0 
             OR (SELECT COUNT(*) FROM public.pagos WHERE conciliado = TRUE AND estado IN ('PAGADO', 'PARCIAL')) > 0
        THEN '✅ SÍ SE ESTÁ IMPORTANDO - Hay actividad'
        ELSE '⏳ AÚN NO SE HA INICIADO LA IMPORTACIÓN'
    END as estado_general,
    CURRENT_TIMESTAMP as hora_verificacion;
