-- ============================================
-- VERIFICAR PROGRESO: Aplicación de Pagos Conciliados
-- Para ejecutar en DBeaver mientras corre el script Python
-- ============================================
-- Este script muestra el progreso de la aplicación de pagos
-- Ejecutar periódicamente para ver avances
-- ============================================

-- ============================================
-- RESUMEN DE PROGRESO
-- ============================================
SELECT 
    'PROGRESO APLICACION PAGOS' as etapa,
    (SELECT COUNT(*) FROM public.pagos WHERE conciliado = TRUE) as total_pagos_conciliados,
    (SELECT COUNT(*) FROM public.pagos 
     WHERE conciliado = TRUE 
       AND estado IN ('PAGADO', 'PARCIAL')) as pagos_aplicados,
    (SELECT COUNT(*) FROM public.pagos 
     WHERE conciliado = TRUE 
       AND estado NOT IN ('PAGADO', 'PARCIAL')) as pagos_pendientes,
    (SELECT SUM(total_pagado) FROM public.cuotas) as total_aplicado_en_cuotas,
    (SELECT SUM(monto_pagado) FROM public.pagos WHERE conciliado = TRUE) as monto_total_pagos_conciliados,
    ROUND(
        (SELECT COUNT(*) FROM public.pagos 
         WHERE conciliado = TRUE 
           AND estado IN ('PAGADO', 'PARCIAL'))::numeric / 
        NULLIF((SELECT COUNT(*) FROM public.pagos WHERE conciliado = TRUE), 0) * 100, 
        2
    ) as porcentaje_completado;

-- ============================================
-- CUOTAS CON PAGOS APLICADOS
-- ============================================
SELECT 
    'CUOTAS CON PAGOS' as etapa,
    COUNT(*) as total_cuotas_con_pago,
    SUM(total_pagado) as suma_total_pagado,
    COUNT(DISTINCT prestamo_id) as prestamos_afectados
FROM public.cuotas
WHERE total_pagado > 0;

-- ============================================
-- COMPARACION: PAGOS VS CUOTAS
-- ============================================
SELECT 
    'COMPARACION' as etapa,
    (SELECT SUM(monto_pagado) FROM public.pagos WHERE conciliado = TRUE) as suma_pagos_conciliados,
    (SELECT SUM(total_pagado) FROM public.cuotas) as suma_total_pagado_cuotas,
    (SELECT SUM(monto_pagado) FROM public.pagos WHERE conciliado = TRUE) - 
    (SELECT SUM(total_pagado) FROM public.cuotas) as diferencia,
    CASE 
        WHEN ABS(
            (SELECT SUM(monto_pagado) FROM public.pagos WHERE conciliado = TRUE) - 
            (SELECT SUM(total_pagado) FROM public.cuotas)
        ) < 0.01 
        THEN 'OK - COINCIDEN'
        WHEN (SELECT SUM(total_pagado) FROM public.cuotas) < 
             (SELECT SUM(monto_pagado) FROM public.pagos WHERE conciliado = TRUE)
        THEN 'EN PROCESO - FALTAN PAGOS POR APLICAR'
        ELSE 'VERIFICAR'
    END as estado;

-- ============================================
-- PRESTAMOS CON PAGOS APLICADOS
-- ============================================
SELECT 
    'PRESTAMOS CON PAGOS APLICADOS' as etapa,
    COUNT(DISTINCT c.prestamo_id) as prestamos_con_pagos_aplicados,
    SUM(c.total_pagado) as suma_total_pagado
FROM public.cuotas c
WHERE c.total_pagado > 0;
