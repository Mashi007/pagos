-- ============================================
-- CALCULAR: Cuánto falta para completar la importación
-- Ejecutar para ver progreso y tiempo estimado
-- ============================================

-- ============================================
-- PROGRESO ACTUAL
-- ============================================
SELECT 
    'PROGRESO ACTUAL' as tipo,
    (SELECT COUNT(*) FROM public.pagos WHERE conciliado = TRUE) as total_pagos_conciliados,
    (SELECT COUNT(*) FROM public.pagos 
     WHERE conciliado = TRUE 
       AND estado IN ('PAGADO', 'PARCIAL')) as pagos_aplicados,
    (SELECT COUNT(*) FROM public.pagos 
     WHERE conciliado = TRUE 
       AND (estado IS NULL OR estado NOT IN ('PAGADO', 'PARCIAL'))) as pagos_pendientes,
    ROUND(
        (SELECT COUNT(*) FROM public.pagos 
         WHERE conciliado = TRUE 
           AND estado IN ('PAGADO', 'PARCIAL'))::numeric / 
        NULLIF((SELECT COUNT(*) FROM public.pagos WHERE conciliado = TRUE), 0) * 100, 
        2
    ) as porcentaje_completado,
    ROUND(
        (SELECT COUNT(*) FROM public.pagos 
         WHERE conciliado = TRUE 
           AND (estado IS NULL OR estado NOT IN ('PAGADO', 'PARCIAL')))::numeric / 
        NULLIF((SELECT COUNT(*) FROM public.pagos WHERE conciliado = TRUE), 0) * 100, 
        2
    ) as porcentaje_pendiente;

-- ============================================
-- MONTOS: CUÁNTO FALTA POR APLICAR
-- ============================================
SELECT 
    'MONTOS PENDIENTES' as tipo,
    (SELECT SUM(monto_pagado) FROM public.pagos WHERE conciliado = TRUE) as monto_total_pagos_conciliados,
    (SELECT COALESCE(SUM(total_pagado), 0) FROM public.cuotas) as monto_aplicado_en_cuotas,
    (SELECT SUM(monto_pagado) FROM public.pagos WHERE conciliado = TRUE) - 
    (SELECT COALESCE(SUM(total_pagado), 0) FROM public.cuotas) as monto_faltante_por_aplicar,
    ROUND(
        (SELECT COALESCE(SUM(total_pagado), 0) FROM public.cuotas)::numeric / 
        NULLIF((SELECT SUM(monto_pagado) FROM public.pagos WHERE conciliado = TRUE), 0) * 100, 
        2
    ) as porcentaje_monto_aplicado,
    ROUND(
        ((SELECT SUM(monto_pagado) FROM public.pagos WHERE conciliado = TRUE) - 
         (SELECT COALESCE(SUM(total_pagado), 0) FROM public.cuotas))::numeric / 
        NULLIF((SELECT SUM(monto_pagado) FROM public.pagos WHERE conciliado = TRUE), 0) * 100, 
        2
    ) as porcentaje_monto_pendiente;

-- ============================================
-- ESTIMACIÓN DE TIEMPO RESTANTE
-- ============================================
-- Nota: Esta estimación asume ~1-2 segundos por pago
SELECT 
    'ESTIMACION TIEMPO' as tipo,
    (SELECT COUNT(*) FROM public.pagos 
     WHERE conciliado = TRUE 
       AND (estado IS NULL OR estado NOT IN ('PAGADO', 'PARCIAL'))) as pagos_pendientes,
    CASE 
        WHEN (SELECT COUNT(*) FROM public.pagos 
              WHERE conciliado = TRUE 
                AND (estado IS NULL OR estado NOT IN ('PAGADO', 'PARCIAL'))) > 0
        THEN 
            -- Estimación: 1.5 segundos por pago (promedio conservador)
            ROUND(
                (SELECT COUNT(*) FROM public.pagos 
                 WHERE conciliado = TRUE 
                   AND (estado IS NULL OR estado NOT IN ('PAGADO', 'PARCIAL'))) * 1.5 / 60, 
                0
            )
        ELSE 0
    END as minutos_estimados_restantes,
    CASE 
        WHEN (SELECT COUNT(*) FROM public.pagos 
              WHERE conciliado = TRUE 
                AND (estado IS NULL OR estado NOT IN ('PAGADO', 'PARCIAL'))) > 0
        THEN 
            CONCAT(
                ROUND(
                    (SELECT COUNT(*) FROM public.pagos 
                     WHERE conciliado = TRUE 
                       AND (estado IS NULL OR estado NOT IN ('PAGADO', 'PARCIAL'))) * 1.5 / 3600, 
                    1
                ),
                ' horas'
            )
        ELSE '✅ COMPLETADO'
    END as tiempo_estimado_restante;

-- ============================================
-- RESUMEN: CUÁNTO FALTA
-- ============================================
SELECT 
    'RESUMEN: CUANTO FALTA' as tipo,
    (SELECT COUNT(*) FROM public.pagos 
     WHERE conciliado = TRUE 
       AND (estado IS NULL OR estado NOT IN ('PAGADO', 'PARCIAL'))) as pagos_pendientes,
    (SELECT SUM(monto_pagado) FROM public.pagos WHERE conciliado = TRUE) - 
    (SELECT COALESCE(SUM(total_pagado), 0) FROM public.cuotas) as monto_faltante,
    CASE 
        WHEN (SELECT COUNT(*) FROM public.pagos 
              WHERE conciliado = TRUE 
                AND (estado IS NULL OR estado NOT IN ('PAGADO', 'PARCIAL'))) = 0
             AND ABS(
                 (SELECT SUM(monto_pagado) FROM public.pagos WHERE conciliado = TRUE) - 
                 (SELECT COALESCE(SUM(total_pagado), 0) FROM public.cuotas)
             ) < 0.01
        THEN '✅ COMPLETADO - 100%'
        WHEN (SELECT COUNT(*) FROM public.pagos 
              WHERE conciliado = TRUE 
                AND (estado IS NULL OR estado NOT IN ('PAGADO', 'PARCIAL'))) > 0
        THEN CONCAT(
            ROUND(
                (SELECT COUNT(*) FROM public.pagos 
                 WHERE conciliado = TRUE 
                   AND (estado IS NULL OR estado NOT IN ('PAGADO', 'PARCIAL')))::numeric / 
                NULLIF((SELECT COUNT(*) FROM public.pagos WHERE conciliado = TRUE), 0) * 100, 
                1
            ),
            '% PENDIENTE'
        )
        ELSE '⏳ VERIFICAR'
    END as estado_general;
