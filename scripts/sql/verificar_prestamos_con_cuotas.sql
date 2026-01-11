-- ============================================================================
-- VERIFICACIÓN: PRÉSTAMOS APROBADOS CON CUOTAS GENERADAS
-- ============================================================================
-- Verifica que todos los préstamos aprobados tengan cuotas generadas
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1. RESUMEN GENERAL
-- ----------------------------------------------------------------------------
SELECT 
    'RESUMEN GENERAL' as tipo_reporte,
    COUNT(*) FILTER (WHERE estado = 'APROBADO') as total_prestamos_aprobados,
    COUNT(*) FILTER (WHERE estado = 'APROBADO' AND EXISTS (
        SELECT 1 FROM cuotas c WHERE c.prestamo_id = prestamos.id
    )) as prestamos_aprobados_con_cuotas,
    COUNT(*) FILTER (WHERE estado = 'APROBADO' AND NOT EXISTS (
        SELECT 1 FROM cuotas c WHERE c.prestamo_id = prestamos.id
    )) as prestamos_aprobados_sin_cuotas,
    ROUND(
        (COUNT(*) FILTER (WHERE estado = 'APROBADO' AND EXISTS (
            SELECT 1 FROM cuotas c WHERE c.prestamo_id = prestamos.id
        ))::DECIMAL / 
        NULLIF(COUNT(*) FILTER (WHERE estado = 'APROBADO'), 0)) * 100, 
        2
    ) as porcentaje_con_cuotas
FROM prestamos;

-- ----------------------------------------------------------------------------
-- 2. PRÉSTAMOS APROBADOS SIN CUOTAS (si los hay)
-- ----------------------------------------------------------------------------
SELECT 
    'PRESTAMOS SIN CUOTAS' as tipo_reporte,
    p.id,
    p.cedula,
    p.total_financiamiento,
    p.numero_cuotas,
    p.fecha_aprobacion,
    p.estado,
    COUNT(c.id) as cuotas_existentes
FROM prestamos p
LEFT JOIN cuotas c ON c.prestamo_id = p.id
WHERE p.estado = 'APROBADO'
GROUP BY p.id, p.cedula, p.total_financiamiento, p.numero_cuotas, p.fecha_aprobacion, p.estado
HAVING COUNT(c.id) = 0
ORDER BY p.fecha_aprobacion DESC
LIMIT 50;

-- ----------------------------------------------------------------------------
-- 3. DISTRIBUCIÓN DE CUOTAS POR PRÉSTAMO
-- ----------------------------------------------------------------------------
WITH cuotas_por_prestamo AS (
    SELECT 
        p.id,
        p.numero_cuotas,
        COUNT(c.id) as cuotas_generadas
    FROM prestamos p
    LEFT JOIN cuotas c ON c.prestamo_id = p.id
    WHERE p.estado = 'APROBADO'
    GROUP BY p.id, p.numero_cuotas
)
SELECT 
    'DISTRIBUCION CUOTAS' as tipo_reporte,
    numero_cuotas as cuotas_esperadas,
    COUNT(*) as cantidad_prestamos,
    ROUND(AVG(cuotas_generadas), 2) as promedio_cuotas_generadas,
    MIN(cuotas_generadas) as minimo_cuotas,
    MAX(cuotas_generadas) as maximo_cuotas
FROM cuotas_por_prestamo
GROUP BY numero_cuotas
ORDER BY numero_cuotas;

-- ----------------------------------------------------------------------------
-- 4. PRÉSTAMOS CON NÚMERO INCORRECTO DE CUOTAS
-- ----------------------------------------------------------------------------
SELECT 
    'CUOTAS INCORRECTAS' as tipo_reporte,
    p.id,
    p.cedula,
    p.numero_cuotas as cuotas_esperadas,
    COUNT(c.id) as cuotas_generadas,
    (p.numero_cuotas - COUNT(c.id)) as diferencia
FROM prestamos p
LEFT JOIN cuotas c ON c.prestamo_id = p.id
WHERE p.estado = 'APROBADO'
GROUP BY p.id, p.cedula, p.numero_cuotas
HAVING COUNT(c.id) != p.numero_cuotas
ORDER BY ABS(p.numero_cuotas - COUNT(c.id)) DESC
LIMIT 50;

-- ----------------------------------------------------------------------------
-- 5. ESTADÍSTICAS GENERALES DE CUOTAS
-- ----------------------------------------------------------------------------
WITH cuotas_por_prestamo AS (
    SELECT 
        prestamo_id,
        COUNT(*) as cantidad_cuotas
    FROM cuotas
    WHERE EXISTS (
        SELECT 1 FROM prestamos p 
        WHERE p.id = cuotas.prestamo_id 
        AND p.estado = 'APROBADO'
    )
    GROUP BY prestamo_id
)
SELECT 
    'ESTADISTICAS CUOTAS' as tipo_reporte,
    COUNT(DISTINCT c.prestamo_id) as prestamos_con_cuotas,
    COUNT(c.id) as total_cuotas_generadas,
    ROUND(AVG(cpp.cantidad_cuotas), 2) as promedio_cuotas_por_prestamo,
    SUM(c.monto_cuota) FILTER (WHERE c.estado = 'PENDIENTE') as monto_total_pendiente,
    SUM(c.total_pagado) as monto_total_pagado
FROM cuotas c
INNER JOIN cuotas_por_prestamo cpp ON cpp.prestamo_id = c.prestamo_id
WHERE EXISTS (
    SELECT 1 FROM prestamos p 
    WHERE p.id = c.prestamo_id 
    AND p.estado = 'APROBADO'
);
