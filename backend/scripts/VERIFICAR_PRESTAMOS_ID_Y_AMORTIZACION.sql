-- ============================================================================
-- ✅ VERIFICAR: TODOS LOS PRÉSTAMOS TIENEN ID Y TABLA DE AMORTIZACIÓN
-- ============================================================================
-- Script para DBeaver: Confirma que todos los préstamos tienen:
--   1. ID asignado (autoincremento)
--   2. Tabla de amortización (cuotas) generada
-- ============================================================================

-- ============================================================================
-- 1. VERIFICAR PRÉSTAMOS SIN ID (debería ser 0)
-- ============================================================================
SELECT 
    'PRÉSTAMOS SIN ID' as verificacion,
    COUNT(*) as cantidad,
    CASE 
        WHEN COUNT(*) = 0 THEN '✅ Todos los préstamos tienen ID'
        ELSE '⚠️ Hay préstamos sin ID'
    END as resultado
FROM prestamos p
WHERE p.id IS NULL;

-- ============================================================================
-- 2. TOTAL DE PRÉSTAMOS Y RANGO DE IDs
-- ============================================================================
SELECT 
    'TOTAL Y RANGO DE IDs' as verificacion,
    COUNT(*) as total_prestamos,
    MIN(p.id) as id_minimo,
    MAX(p.id) as id_maximo,
    COUNT(DISTINCT p.id) as ids_unicos,
    CASE 
        WHEN COUNT(*) = COUNT(DISTINCT p.id) THEN '✅ Todos los IDs son únicos'
        ELSE '⚠️ Hay IDs duplicados'
    END as validacion_unicidad
FROM prestamos p;

-- ============================================================================
-- 3. PRÉSTAMOS POR ESTADO (con IDs)
-- ============================================================================
SELECT 
    'PRÉSTAMOS POR ESTADO' as verificacion,
    p.estado,
    COUNT(*) as cantidad,
    MIN(p.id) as id_minimo,
    MAX(p.id) as id_maximo
FROM prestamos p
GROUP BY p.estado
ORDER BY p.estado;

-- ============================================================================
-- 4. VERIFICAR PRÉSTAMOS SIN TABLA DE AMORTIZACIÓN
-- ============================================================================
-- IMPORTANTE: Solo préstamos APROBADOS deberían tener tabla de amortización
-- (si tienen fecha_base_calculo)
SELECT 
    'PRÉSTAMOS SIN CUOTAS' as verificacion,
    p.estado,
    COUNT(*) as cantidad,
    CASE 
        WHEN p.estado = 'APROBADO' THEN '⚠️ Préstamos APROBADOS sin cuotas'
        ELSE 'ℹ️ Préstamos en otros estados (normal si no están aprobados)'
    END as observacion
FROM prestamos p
LEFT JOIN cuotas c ON c.prestamo_id = p.id
WHERE c.id IS NULL
GROUP BY p.estado
ORDER BY p.estado;

-- ============================================================================
-- 5. PRÉSTAMOS APROBADOS SIN TABLA DE AMORTIZACIÓN (PROBLEMA)
-- ============================================================================
SELECT 
    'PRÉSTAMOS APROBADOS SIN CUOTAS' as verificacion,
    p.id,
    p.cedula,
    p.nombres,
    p.estado,
    p.fecha_aprobacion,
    p.fecha_base_calculo,
    CASE 
        WHEN p.fecha_base_calculo IS NULL THEN '⚠️ Sin fecha_base_calculo'
        ELSE '⚠️ Tiene fecha_base_calculo pero no tiene cuotas'
    END as problema
FROM prestamos p
LEFT JOIN cuotas c ON c.prestamo_id = p.id
WHERE p.estado = 'APROBADO'
  AND c.id IS NULL
ORDER BY p.fecha_aprobacion DESC;

-- ============================================================================
-- 6. PRÉSTAMOS APROBADOS CON TABLA DE AMORTIZACIÓN (CORRECTO)
-- ============================================================================
SELECT 
    'PRÉSTAMOS APROBADOS CON CUOTAS' as verificacion,
    COUNT(DISTINCT p.id) as cantidad_prestamos,
    COUNT(c.id) as total_cuotas,
    ROUND(AVG(cuotas_por_prestamo.cantidad), 2) as promedio_cuotas_por_prestamo,
    MIN(cuotas_por_prestamo.cantidad) as minimo_cuotas,
    MAX(cuotas_por_prestamo.cantidad) as maximo_cuotas
FROM prestamos p
INNER JOIN cuotas c ON c.prestamo_id = p.id
INNER JOIN (
    SELECT prestamo_id, COUNT(*) as cantidad
    FROM cuotas
    GROUP BY prestamo_id
) cuotas_por_prestamo ON cuotas_por_prestamo.prestamo_id = p.id
WHERE p.estado = 'APROBADO';

-- ============================================================================
-- 7. RESUMEN: PRÉSTAMOS CON Y SIN CUOTAS
-- ============================================================================
SELECT 
    'RESUMEN PRÉSTAMOS Y CUOTAS' as verificacion,
    COUNT(DISTINCT p.id) as total_prestamos,
    COUNT(DISTINCT CASE WHEN c.id IS NOT NULL THEN p.id END) as prestamos_con_cuotas,
    COUNT(DISTINCT CASE WHEN c.id IS NULL THEN p.id END) as prestamos_sin_cuotas,
    COUNT(c.id) as total_cuotas,
    CASE 
        WHEN COUNT(DISTINCT CASE WHEN p.estado = 'APROBADO' AND c.id IS NULL THEN p.id END) = 0 
        THEN '✅ Todos los préstamos APROBADOS tienen cuotas'
        ELSE '⚠️ Hay préstamos APROBADOS sin cuotas'
    END as resultado
FROM prestamos p
LEFT JOIN cuotas c ON c.prestamo_id = p.id;

-- ============================================================================
-- 8. PRÉSTAMOS APROBADOS CON fecha_base_calculo PERO SIN CUOTAS (CRÍTICO)
-- ============================================================================
SELECT 
    'CRÍTICO: APROBADOS CON fecha_base_calculo SIN CUOTAS' as verificacion,
    COUNT(*) as cantidad,
    CASE 
        WHEN COUNT(*) = 0 THEN '✅ Todos los préstamos APROBADOS con fecha_base_calculo tienen cuotas'
        ELSE '❌ Hay préstamos APROBADOS con fecha_base_calculo pero sin cuotas'
    END as resultado
FROM prestamos p
LEFT JOIN cuotas c ON c.prestamo_id = p.id
WHERE p.estado = 'APROBADO'
  AND p.fecha_base_calculo IS NOT NULL
  AND c.id IS NULL;

-- ============================================================================
-- 9. DETALLE DE PRÉSTAMOS APROBADOS CON fecha_base_calculo SIN CUOTAS
-- ============================================================================
SELECT 
    p.id as prestamo_id,
    p.cedula,
    p.nombres,
    p.estado,
    p.fecha_aprobacion,
    p.fecha_base_calculo,
    p.numero_cuotas as cuotas_esperadas,
    COUNT(c.id) as cuotas_generadas,
    CASE 
        WHEN COUNT(c.id) = 0 THEN '❌ NO tiene cuotas generadas'
        WHEN COUNT(c.id) < p.numero_cuotas THEN '⚠️ Tiene menos cuotas de las esperadas'
        ELSE '✅ Tiene todas las cuotas'
    END as estado_cuotas
FROM prestamos p
LEFT JOIN cuotas c ON c.prestamo_id = p.id
WHERE p.estado = 'APROBADO'
  AND p.fecha_base_calculo IS NOT NULL
GROUP BY p.id, p.cedula, p.nombres, p.estado, p.fecha_aprobacion, p.fecha_base_calculo, p.numero_cuotas
HAVING COUNT(c.id) = 0 OR COUNT(c.id) < p.numero_cuotas
ORDER BY p.fecha_aprobacion DESC;

-- ============================================================================
-- 10. RESUMEN FINAL COMPLETO
-- ============================================================================
SELECT 
    'RESUMEN FINAL' as verificacion,
    COUNT(*) as total_prestamos,
    COUNT(CASE WHEN p.id IS NULL THEN 1 END) as prestamos_sin_id,
    COUNT(CASE WHEN p.id IS NOT NULL THEN 1 END) as prestamos_con_id,
    COUNT(CASE WHEN p.estado = 'APROBADO' THEN 1 END) as prestamos_aprobados,
    COUNT(CASE WHEN p.estado = 'APROBADO' AND p.fecha_base_calculo IS NOT NULL THEN 1 END) as aprobados_con_fecha_base,
    COUNT(DISTINCT CASE WHEN p.estado = 'APROBADO' AND c.id IS NOT NULL THEN p.id END) as aprobados_con_cuotas,
    COUNT(DISTINCT CASE WHEN p.estado = 'APROBADO' AND p.fecha_base_calculo IS NOT NULL AND c.id IS NULL THEN p.id END) as aprobados_sin_cuotas_critico,
    CASE 
        WHEN COUNT(CASE WHEN p.id IS NULL THEN 1 END) = 0 
         AND COUNT(DISTINCT CASE WHEN p.estado = 'APROBADO' AND p.fecha_base_calculo IS NOT NULL AND c.id IS NULL THEN p.id END) = 0
        THEN '✅ PERFECTO: Todos tienen ID y todos los APROBADOS con fecha_base_calculo tienen cuotas'
        WHEN COUNT(CASE WHEN p.id IS NULL THEN 1 END) > 0
        THEN '❌ PROBLEMA: Hay préstamos sin ID'
        WHEN COUNT(DISTINCT CASE WHEN p.estado = 'APROBADO' AND p.fecha_base_calculo IS NOT NULL AND c.id IS NULL THEN p.id END) > 0
        THEN '⚠️ PROBLEMA: Hay préstamos APROBADOS con fecha_base_calculo sin cuotas'
        ELSE '✅ OK: Todos tienen ID'
    END as resultado_final
FROM prestamos p
LEFT JOIN cuotas c ON c.prestamo_id = p.id;

