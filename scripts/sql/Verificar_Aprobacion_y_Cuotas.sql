-- ============================================
-- VERIFICACIÓN: APROBACIÓN Y CUOTAS DE PRÉSTAMOS
-- ============================================
-- Fecha: 2025-10-31
-- Descripción: Verifica que todos los préstamos estén aprobados
--              y tengan su tabla de amortización completa
-- ============================================

-- ============================================
-- 1. RESUMEN GENERAL
-- ============================================
SELECT 
    'RESUMEN GENERAL' AS tipo,
    COUNT(*) AS total_prestamos,
    COUNT(CASE WHEN estado = 'APROBADO' THEN 1 END) AS aprobados,
    COUNT(CASE WHEN estado != 'APROBADO' THEN 1 END) AS no_aprobados,
    COUNT(CASE WHEN fecha_aprobacion IS NOT NULL THEN 1 END) AS con_fecha_aprobacion,
    COUNT(CASE WHEN fecha_base_calculo IS NOT NULL THEN 1 END) AS con_fecha_base
FROM public.prestamos;

-- ============================================
-- 2. PRÉSTAMOS SIN APROBAR O SIN FECHA DE APROBACIÓN
-- ============================================
SELECT 
    id,
    cedula,
    nombres,
    estado,
    total_financiamiento,
    numero_cuotas,
    fecha_requerimiento,
    fecha_aprobacion,
    fecha_base_calculo,
    usuario_proponente,
    usuario_aprobador
FROM public.prestamos
WHERE estado != 'APROBADO' OR fecha_aprobacion IS NULL
ORDER BY id;

-- ============================================
-- 3. PRÉSTAMOS APROBADOS SIN CUOTAS O CON CUOTAS INCOMPLETAS
-- ============================================
SELECT 
    p.id,
    p.cedula,
    p.nombres,
    p.estado,
    p.total_financiamiento,
    p.numero_cuotas AS cuotas_esperadas,
    p.cuota_periodo,
    p.tasa_interes,
    p.fecha_base_calculo,
    COUNT(c.id) AS cuotas_generadas,
    CASE 
        WHEN COUNT(c.id) = 0 THEN 'SIN CUOTAS'
        WHEN COUNT(c.id) < p.numero_cuotas THEN 'CUOTAS INCOMPLETAS'
        WHEN COUNT(c.id) > p.numero_cuotas THEN 'CUOTAS EXCESIVAS'
        ELSE 'OK'
    END AS estado_cuotas
FROM public.prestamos p
LEFT JOIN public.cuotas c ON c.prestamo_id = p.id
WHERE p.estado = 'APROBADO'
GROUP BY p.id, p.cedula, p.nombres, p.estado, p.total_financiamiento, 
         p.numero_cuotas, p.cuota_periodo, p.tasa_interes, p.fecha_base_calculo
HAVING COUNT(c.id) = 0 OR COUNT(c.id) != p.numero_cuotas
ORDER BY p.id;

-- ============================================
-- 4. RESUMEN DE CUOTAS POR PRÉSTAMO
-- ============================================
SELECT 
    p.id,
    p.cedula,
    p.nombres,
    p.numero_cuotas AS cuotas_esperadas,
    COUNT(c.id) AS cuotas_generadas,
    COUNT(CASE WHEN c.estado = 'PENDIENTE' THEN 1 END) AS cuotas_pendientes,
    COUNT(CASE WHEN c.estado = 'PAGADO' THEN 1 END) AS cuotas_pagadas,
    COUNT(CASE WHEN c.estado = 'ATRASADO' THEN 1 END) AS cuotas_atrasadas,
    SUM(COALESCE(c.monto_cuota, 0)) AS total_monto_cuotas,
    p.total_financiamiento AS monto_prestamo,
    CASE 
        WHEN ABS(SUM(COALESCE(c.monto_cuota, 0)) - p.total_financiamiento) < 0.01 
        THEN 'OK' 
        ELSE 'DIFERENCIA'
    END AS validacion_monto
FROM public.prestamos p
LEFT JOIN public.cuotas c ON c.prestamo_id = p.id
WHERE p.estado = 'APROBADO'
GROUP BY p.id, p.cedula, p.nombres, p.numero_cuotas, p.total_financiamiento
ORDER BY p.id
LIMIT 50;

-- ============================================
-- 5. ESTADÍSTICAS POR ESTADO
-- ============================================
SELECT 
    estado,
    COUNT(*) AS cantidad_prestamos,
    SUM(total_financiamiento) AS monto_total,
    AVG(numero_cuotas) AS promedio_cuotas,
    COUNT(CASE WHEN fecha_aprobacion IS NOT NULL THEN 1 END) AS con_aprobacion,
    COUNT(CASE WHEN fecha_base_calculo IS NOT NULL THEN 1 END) AS con_fecha_base
FROM public.prestamos
GROUP BY estado
ORDER BY estado;

-- ============================================
-- 6. PRÉSTAMOS CON PROBLEMAS (PARA REVISIÓN)
-- ============================================
SELECT 
    p.id,
    p.cedula,
    p.nombres,
    p.estado,
    p.total_financiamiento,
    p.numero_cuotas,
    p.fecha_base_calculo,
    COUNT(c.id) AS cuotas_existentes,
    CASE 
        WHEN p.estado != 'APROBADO' THEN 'NO APROBADO'
        WHEN p.fecha_base_calculo IS NULL THEN 'SIN FECHA BASE'
        WHEN COUNT(c.id) = 0 THEN 'SIN CUOTAS'
        WHEN COUNT(c.id) != p.numero_cuotas THEN 'CUOTAS INCOMPLETAS'
        WHEN p.total_financiamiento <= 0 THEN 'MONTO INVÁLIDO'
        WHEN p.numero_cuotas <= 0 THEN 'CUOTAS INVÁLIDAS'
        ELSE 'OK'
    END AS problema
FROM public.prestamos p
LEFT JOIN public.cuotas c ON c.prestamo_id = p.id
GROUP BY p.id, p.cedula, p.nombres, p.estado, p.total_financiamiento, 
         p.numero_cuotas, p.fecha_base_calculo
HAVING 
    p.estado != 'APROBADO' 
    OR p.fecha_base_calculo IS NULL
    OR COUNT(c.id) = 0 
    OR COUNT(c.id) != p.numero_cuotas
    OR p.total_financiamiento <= 0
    OR p.numero_cuotas <= 0
ORDER BY p.id;

-- ============================================
-- 7. VERIFICACIÓN DE CONSISTENCIA
-- ============================================
SELECT 
    'VERIFICACIÓN DE CONSISTENCIA' AS tipo,
    COUNT(DISTINCT p.id) AS prestamos_aprobados,
    COUNT(DISTINCT c.prestamo_id) AS prestamos_con_cuotas,
    COUNT(c.id) AS total_cuotas,
    SUM(c.monto_cuota) AS total_monto_cuotas,
    SUM(p.total_financiamiento) AS total_prestamos,
    CASE 
        WHEN ABS(SUM(c.monto_cuota) - SUM(p.total_financiamiento)) < 1.00 
        THEN 'OK' 
        ELSE 'REVISAR'
    END AS validacion
FROM public.prestamos p
LEFT JOIN public.cuotas c ON c.prestamo_id = p.id
WHERE p.estado = 'APROBADO';

-- ============================================
-- FIN DEL SCRIPT
-- ============================================

