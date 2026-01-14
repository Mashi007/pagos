-- ============================================
-- VERIFICAR: Si total_pagado está vacío antes de importar pagos
-- Para ejecutar en DBeaver
-- ============================================
-- Este script verifica si cuotas.total_pagado está vacío
-- antes de iniciar la importación de pagos conciliados
-- ============================================

-- ============================================
-- PASO 1: RESUMEN GENERAL
-- ============================================
SELECT 
    'RESUMEN GENERAL' as etapa,
    (SELECT COUNT(*) FROM public.cuotas) as total_cuotas,
    (SELECT COUNT(*) FROM public.cuotas WHERE total_pagado IS NULL OR total_pagado = 0) as cuotas_con_total_pagado_vacio,
    (SELECT COUNT(*) FROM public.cuotas WHERE total_pagado > 0) as cuotas_con_total_pagado,
    CASE 
        WHEN (SELECT COUNT(*) FROM public.cuotas WHERE total_pagado > 0) = 0
        THEN 'OK - TODAS LAS CUOTAS ESTÁN VACÍAS'
        ELSE 'ADVERTENCIA - HAY CUOTAS CON TOTAL_PAGADO'
    END as validacion;

-- ============================================
-- PASO 2: CUOTAS CON TOTAL_PAGADO > 0
-- ============================================
SELECT 
    'CUOTAS CON TOTAL_PAGADO' as etapa,
    c.id as cuota_id,
    c.prestamo_id,
    pr.cedula,
    c.numero_cuota,
    c.monto_cuota,
    c.total_pagado,
    c.estado,
    c.fecha_pago
FROM public.cuotas c
JOIN public.prestamos pr ON pr.id = c.prestamo_id
WHERE c.total_pagado > 0
ORDER BY c.prestamo_id, c.numero_cuota;

-- ============================================
-- PASO 3: RESUMEN POR PRESTAMO
-- ============================================
SELECT 
    'RESUMEN POR PRESTAMO' as etapa,
    c.prestamo_id,
    pr.cedula,
    COUNT(*) as total_cuotas,
    COUNT(*) FILTER (WHERE c.total_pagado > 0) as cuotas_con_pago,
    COUNT(*) FILTER (WHERE c.total_pagado IS NULL OR c.total_pagado = 0) as cuotas_sin_pago,
    SUM(c.total_pagado) as suma_total_pagado,
    CASE 
        WHEN COUNT(*) FILTER (WHERE c.total_pagado > 0) = 0
        THEN 'OK - SIN PAGOS'
        ELSE 'TIENE PAGOS'
    END as estado
FROM public.cuotas c
JOIN public.prestamos pr ON pr.id = c.prestamo_id
GROUP BY c.prestamo_id, pr.cedula
HAVING COUNT(*) FILTER (WHERE c.total_pagado > 0) > 0
ORDER BY suma_total_pagado DESC, c.prestamo_id;

-- ============================================
-- PASO 4: PRESTAMOS CON CUOTAS QUE TIENEN PAGOS
-- ============================================
SELECT 
    'PRESTAMOS CON CUOTAS PAGADAS' as etapa,
    c.prestamo_id,
    pr.cedula,
    pr.estado as estado_prestamo,
    COUNT(*) FILTER (WHERE c.total_pagado > 0) as cuotas_con_pago,
    SUM(c.total_pagado) as suma_total_pagado,
    MIN(c.fecha_pago) as primera_fecha_pago,
    MAX(c.fecha_pago) as ultima_fecha_pago
FROM public.cuotas c
JOIN public.prestamos pr ON pr.id = c.prestamo_id
WHERE c.total_pagado > 0
GROUP BY c.prestamo_id, pr.cedula, pr.estado
ORDER BY suma_total_pagado DESC;

-- ============================================
-- PASO 5: VERIFICAR PAGOS CONCILIADOS EXISTENTES
-- ============================================
SELECT 
    'PAGOS CONCILIADOS EXISTENTES' as etapa,
    COUNT(*) as total_pagos_conciliados,
    SUM(monto_pagado) as suma_montos_conciliados,
    COUNT(DISTINCT prestamo_id) as prestamos_con_pagos_conciliados
FROM public.pagos
WHERE conciliado = TRUE;

-- ============================================
-- PASO 6: COMPARAR PAGOS CONCILIADOS VS TOTAL_PAGADO
-- ============================================
SELECT 
    'COMPARACION PAGOS VS CUOTAS' as etapa,
    (SELECT SUM(monto_pagado) FROM public.pagos WHERE conciliado = TRUE) as suma_pagos_conciliados,
    (SELECT SUM(total_pagado) FROM public.cuotas) as suma_total_pagado_cuotas,
    (SELECT SUM(monto_pagado) FROM public.pagos WHERE conciliado = TRUE) - 
    (SELECT SUM(total_pagado) FROM public.cuotas) as diferencia,
    CASE 
        WHEN (SELECT SUM(total_pagado) FROM public.cuotas) = 0 OR 
             (SELECT SUM(total_pagado) FROM public.cuotas) IS NULL
        THEN 'OK - CUOTAS VACÍAS, LISTO PARA IMPORTAR'
        WHEN ABS(
            (SELECT SUM(monto_pagado) FROM public.pagos WHERE conciliado = TRUE) - 
            (SELECT SUM(total_pagado) FROM public.cuotas)
        ) < 0.01
        THEN 'OK - PAGOS YA APLICADOS'
        ELSE 'ADVERTENCIA - HAY DIFERENCIA'
    END as validacion;

-- ============================================
-- PASO 7: ESTADÍSTICAS DETALLADAS
-- ============================================
SELECT 
    'ESTADISTICAS DETALLADAS' as etapa,
    COUNT(*) as total_cuotas,
    COUNT(*) FILTER (WHERE total_pagado IS NULL) as cuotas_con_null,
    COUNT(*) FILTER (WHERE total_pagado = 0) as cuotas_con_cero,
    COUNT(*) FILTER (WHERE total_pagado > 0 AND total_pagado < monto_cuota) as cuotas_parciales,
    COUNT(*) FILTER (WHERE total_pagado >= monto_cuota) as cuotas_completas,
    COUNT(*) FILTER (WHERE total_pagado > 0) as cuotas_con_pago_total
FROM public.cuotas;

-- ============================================
-- RESUMEN FINAL
-- ============================================
SELECT 
    CASE 
        WHEN (SELECT COUNT(*) FROM public.cuotas WHERE total_pagado > 0) = 0
        THEN '[OK] Todas las cuotas tienen total_pagado vacío. Listo para importar pagos conciliados.'
        ELSE '[ADVERTENCIA] Hay cuotas con total_pagado > 0. Revisar antes de importar.'
    END as resultado;
