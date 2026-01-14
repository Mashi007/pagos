-- ============================================
-- VERIFICAR ACTIVIDAD: Importación de Pagos
-- Ejecutar para ver si hay actividad en la BD
-- ============================================

-- ============================================
-- VERIFICACIÓN 1: ¿HAY CUOTAS CON PAGOS?
-- ============================================
SELECT 
    '¿HAY CUOTAS CON PAGOS?' as pregunta,
    COUNT(*) as cuotas_con_pago,
    SUM(total_pagado) as suma_total_pagado,
    CASE 
        WHEN COUNT(*) > 0 THEN '✅ SÍ - HAY ACTIVIDAD'
        ELSE '❌ NO - AÚN NO HAY ACTIVIDAD'
    END as respuesta
FROM public.cuotas
WHERE total_pagado > 0;

-- ============================================
-- VERIFICACIÓN 2: ¿HAY PAGOS CON ESTADO APLICADO?
-- ============================================
SELECT 
    '¿HAY PAGOS APLICADOS?' as pregunta,
    COUNT(*) FILTER (WHERE estado IN ('PAGADO', 'PARCIAL')) as pagos_aplicados,
    COUNT(*) as total_pagos_conciliados,
    CASE 
        WHEN COUNT(*) FILTER (WHERE estado IN ('PAGADO', 'PARCIAL')) > 0 
        THEN '✅ SÍ - HAY ACTIVIDAD'
        ELSE '❌ NO - AÚN NO HAY ACTIVIDAD'
    END as respuesta
FROM public.pagos
WHERE conciliado = TRUE;

-- ============================================
-- VERIFICACIÓN 3: COMPARACIÓN INICIAL VS ACTUAL
-- ============================================
SELECT 
    'COMPARACION' as verificacion,
    (SELECT COUNT(*) FROM public.pagos WHERE conciliado = TRUE) as total_pagos_conciliados,
    (SELECT COUNT(*) FROM public.pagos WHERE conciliado = TRUE AND estado IN ('PAGADO', 'PARCIAL')) as pagos_con_estado_aplicado,
    (SELECT COALESCE(SUM(total_pagado), 0) FROM public.cuotas) as monto_aplicado_en_cuotas,
    (SELECT SUM(monto_pagado) FROM public.pagos WHERE conciliado = TRUE) as monto_total_pagos_conciliados,
    CASE 
        WHEN (SELECT COALESCE(SUM(total_pagado), 0) FROM public.cuotas) > 0 
             OR (SELECT COUNT(*) FROM public.pagos WHERE conciliado = TRUE AND estado IN ('PAGADO', 'PARCIAL')) > 0
        THEN '✅ SÍ SE ESTÁ IMPORTANDO'
        ELSE '❌ NO SE ESTÁ IMPORTANDO AÚN'
    END as estado_importacion;

-- ============================================
-- VERIFICACIÓN 4: ACTIVIDAD RECIENTE (últimos 20 pagos)
-- ============================================
SELECT 
    'ACTIVIDAD RECIENTE' as verificacion,
    p.id as pago_id,
    p.prestamo_id,
    p.monto_pagado,
    p.estado,
    p.fecha_pago,
    p.fecha_conciliacion,
    CASE 
        WHEN p.estado IN ('PAGADO', 'PARCIAL') THEN '✅ APLICADO'
        WHEN p.estado IS NULL THEN '⏳ SIN ESTADO'
        ELSE '⏳ PENDIENTE'
    END as estado_aplicacion
FROM public.pagos p
WHERE p.conciliado = TRUE
ORDER BY p.id DESC
LIMIT 20;

-- ============================================
-- RESUMEN FINAL
-- ============================================
SELECT 
    'RESUMEN FINAL' as verificacion,
    CASE 
        WHEN (SELECT COUNT(*) FROM public.cuotas WHERE total_pagado > 0) > 0 
        THEN '✅ SÍ SE ESTÁ IMPORTANDO - Hay cuotas con total_pagado > 0'
        WHEN (SELECT COUNT(*) FROM public.pagos WHERE conciliado = TRUE AND estado IN ('PAGADO', 'PARCIAL')) > 0
        THEN '✅ SÍ SE ESTÁ IMPORTANDO - Hay pagos con estado aplicado'
        ELSE '❌ NO SE ESTÁ IMPORTANDO - No hay actividad visible'
    END as estado_general,
    CURRENT_TIMESTAMP as hora_verificacion;
