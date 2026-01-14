-- ============================================
-- MONITOREO EN TIEMPO REAL: Aplicación de Pagos
-- Para ejecutar en DBeaver mientras corre el script Python
-- ============================================
-- Ejecutar este script periódicamente para ver avances
-- Actualizar cada 30 segundos - 1 minuto
-- ============================================

-- ============================================
-- RESUMEN GENERAL DE PROGRESO
-- ============================================
SELECT 
    '📊 RESUMEN GENERAL' as tipo,
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
    CURRENT_TIMESTAMP as hora_consulta;

-- ============================================
-- MONTO TOTAL: PAGOS VS CUOTAS
-- ============================================
SELECT 
    '💰 MONTOS' as tipo,
    (SELECT SUM(monto_pagado) FROM public.pagos WHERE conciliado = TRUE) as suma_pagos_conciliados,
    (SELECT COALESCE(SUM(total_pagado), 0) FROM public.cuotas) as suma_total_pagado_cuotas,
    (SELECT SUM(monto_pagado) FROM public.pagos WHERE conciliado = TRUE) - 
    (SELECT COALESCE(SUM(total_pagado), 0) FROM public.cuotas) as diferencia,
    CASE 
        WHEN ABS(
            (SELECT SUM(monto_pagado) FROM public.pagos WHERE conciliado = TRUE) - 
            (SELECT COALESCE(SUM(total_pagado), 0) FROM public.cuotas)
        ) < 0.01 
        THEN '✅ COMPLETADO'
        WHEN (SELECT COALESCE(SUM(total_pagado), 0) FROM public.cuotas) < 
             (SELECT SUM(monto_pagado) FROM public.pagos WHERE conciliado = TRUE)
        THEN '⏳ EN PROCESO'
        ELSE '⚠️ VERIFICAR'
    END as estado;

-- ============================================
-- CUOTAS AFECTADAS
-- ============================================
SELECT 
    '📋 CUOTAS' as tipo,
    COUNT(*) as total_cuotas_con_pago,
    SUM(total_pagado) as suma_total_pagado,
    COUNT(DISTINCT prestamo_id) as prestamos_afectados,
    ROUND(AVG(total_pagado), 2) as promedio_pagado_por_cuota
FROM public.cuotas
WHERE total_pagado > 0;

-- ============================================
-- PROGRESO POR ESTADO DE PAGO
-- ============================================
SELECT 
    '📈 ESTADO DE PAGOS' as tipo,
    COALESCE(estado, 'SIN ESTADO') as estado_pago,
    COUNT(*) as cantidad,
    SUM(monto_pagado) as monto_total,
    ROUND(COUNT(*)::numeric / NULLIF((SELECT COUNT(*) FROM public.pagos WHERE conciliado = TRUE), 0) * 100, 2) as porcentaje
FROM public.pagos
WHERE conciliado = TRUE
GROUP BY estado
ORDER BY cantidad DESC;

-- ============================================
-- ÚLTIMOS PAGOS APLICADOS (últimos 10)
-- ============================================
SELECT 
    '🔄 ULTIMOS PAGOS APLICADOS' as tipo,
    p.id as pago_id,
    p.prestamo_id,
    p.monto_pagado,
    p.estado,
    p.fecha_pago,
    COALESCE(SUM(c.total_pagado), 0) as total_aplicado_en_cuotas
FROM public.pagos p
LEFT JOIN public.cuotas c ON c.prestamo_id = p.prestamo_id
WHERE p.conciliado = TRUE
  AND p.estado IN ('PAGADO', 'PARCIAL')
GROUP BY p.id, p.prestamo_id, p.monto_pagado, p.estado, p.fecha_pago
ORDER BY p.fecha_pago DESC, p.id DESC
LIMIT 10;

-- ============================================
-- PRESTAMOS CON MAYOR PROGRESO
-- ============================================
SELECT 
    '🏆 PRESTAMOS CON MAS PAGOS' as tipo,
    c.prestamo_id,
    pr.cedula,
    COUNT(DISTINCT p.id) as cantidad_pagos_conciliados,
    SUM(p.monto_pagado) as monto_total_pagos,
    SUM(c.total_pagado) as monto_aplicado_cuotas,
    COUNT(*) FILTER (WHERE c.total_pagado > 0) as cuotas_con_pago
FROM public.pagos p
JOIN public.prestamos pr ON pr.id = p.prestamo_id
LEFT JOIN public.cuotas c ON c.prestamo_id = p.prestamo_id
WHERE p.conciliado = TRUE
GROUP BY c.prestamo_id, pr.cedula
HAVING SUM(c.total_pagado) > 0
ORDER BY SUM(c.total_pagado) DESC
LIMIT 10;
