-- ============================================
-- VERIFICAR: Si cada préstamo tiene cuotas
-- Para ejecutar en DBeaver
-- ============================================
-- Este script verifica:
-- 1. Préstamos que NO tienen cuotas
-- 2. Préstamos con cuotas incompletas
-- 3. Resumen por estado de préstamo
-- ============================================

-- ============================================
-- PASO 1: RESUMEN GENERAL
-- ============================================
SELECT 
    'RESUMEN GENERAL' as etapa,
    (SELECT COUNT(*) FROM public.prestamos) as total_prestamos,
    (SELECT COUNT(*) FROM public.cuotas) as total_cuotas,
    (SELECT COUNT(DISTINCT prestamo_id) FROM public.cuotas) as prestamos_con_cuotas,
    (SELECT COUNT(*) FROM public.prestamos) - (SELECT COUNT(DISTINCT prestamo_id) FROM public.cuotas) as prestamos_sin_cuotas,
    CASE 
        WHEN (SELECT COUNT(*) FROM public.prestamos) = (SELECT COUNT(DISTINCT prestamo_id) FROM public.cuotas)
        THEN 'OK - TODOS LOS PRESTAMOS TIENEN CUOTAS'
        ELSE 'ADVERTENCIA - HAY PRESTAMOS SIN CUOTAS'
    END as validacion;

-- ============================================
-- PASO 2: PRESTAMOS QUE NO TIENEN CUOTAS
-- ============================================
SELECT 
    'PRESTAMOS SIN CUOTAS' as etapa,
    p.id as prestamo_id,
    p.cedula,
    p.total_financiamiento,
    p.numero_cuotas,
    p.estado,
    p.fecha_base_calculo,
    CASE 
        WHEN p.estado = 'APROBADO' AND p.fecha_base_calculo IS NOT NULL THEN 'ERROR - DEBE TENER CUOTAS'
        WHEN p.estado != 'APROBADO' THEN 'OK - NO APROBADO (NO REQUIERE CUOTAS)'
        WHEN p.fecha_base_calculo IS NULL THEN 'OK - SIN FECHA BASE (NO REQUIERE CUOTAS)'
        ELSE 'VERIFICAR'
    END as razon
FROM public.prestamos p
LEFT JOIN public.cuotas c ON c.prestamo_id = p.id
WHERE c.id IS NULL
ORDER BY 
    CASE 
        WHEN p.estado = 'APROBADO' THEN 1
        ELSE 2
    END,
    p.id;

-- ============================================
-- PASO 3: PRESTAMOS CON CUOTAS INCOMPLETAS
-- ============================================
SELECT 
    'PRESTAMOS CON CUOTAS INCOMPLETAS' as etapa,
    p.id as prestamo_id,
    p.cedula,
    p.numero_cuotas as cuotas_esperadas,
    COUNT(c.id) as cuotas_existentes,
    p.numero_cuotas - COUNT(c.id) as cuotas_faltantes,
    CASE 
        WHEN COUNT(c.id) = 0 THEN 'SIN CUOTAS'
        WHEN COUNT(c.id) < p.numero_cuotas THEN 'INCOMPLETAS'
        WHEN COUNT(c.id) = p.numero_cuotas THEN 'COMPLETAS'
        WHEN COUNT(c.id) > p.numero_cuotas THEN 'EXCESO DE CUOTAS'
    END as estado_cuotas
FROM public.prestamos p
LEFT JOIN public.cuotas c ON c.prestamo_id = p.id
WHERE p.estado = 'APROBADO'
GROUP BY p.id, p.cedula, p.numero_cuotas
HAVING COUNT(c.id) != p.numero_cuotas
ORDER BY cuotas_faltantes DESC, p.id;

-- ============================================
-- PASO 4: VERIFICAR POR ESTADO DE PRESTAMO
-- ============================================
SELECT 
    'VERIFICACION POR ESTADO' as etapa,
    p.estado,
    COUNT(DISTINCT p.id) as total_prestamos,
    COUNT(DISTINCT c.prestamo_id) as prestamos_con_cuotas,
    COUNT(DISTINCT p.id) - COUNT(DISTINCT c.prestamo_id) as prestamos_sin_cuotas,
    COUNT(c.id) as total_cuotas,
    CASE 
        WHEN p.estado = 'APROBADO' AND COUNT(DISTINCT c.prestamo_id) < COUNT(DISTINCT p.id) THEN 'ERROR - FALTAN CUOTAS'
        WHEN p.estado = 'APROBADO' AND COUNT(DISTINCT c.prestamo_id) = COUNT(DISTINCT p.id) THEN 'OK - TODOS TIENEN CUOTAS'
        ELSE 'OK - NO REQUIERE CUOTAS'
    END as validacion
FROM public.prestamos p
LEFT JOIN public.cuotas c ON c.prestamo_id = p.id
GROUP BY p.estado
ORDER BY p.estado;

-- ============================================
-- PASO 5: PRESTAMOS APROBADOS CON PROBLEMAS
-- ============================================
SELECT 
    'PRESTAMOS APROBADOS CON PROBLEMAS' as etapa,
    p.id as prestamo_id,
    p.cedula,
    p.total_financiamiento,
    p.numero_cuotas,
    p.fecha_base_calculo,
    COUNT(c.id) as cuotas_existentes,
    CASE 
        WHEN COUNT(c.id) = 0 THEN 'CRITICO - SIN CUOTAS'
        WHEN COUNT(c.id) < p.numero_cuotas THEN 'INCOMPLETO'
        WHEN COUNT(c.id) > p.numero_cuotas THEN 'EXCESO DE CUOTAS'
        ELSE 'OK'
    END as problema
FROM public.prestamos p
LEFT JOIN public.cuotas c ON c.prestamo_id = p.id
WHERE p.estado = 'APROBADO'
GROUP BY p.id, p.cedula, p.total_financiamiento, p.numero_cuotas, p.fecha_base_calculo
HAVING COUNT(c.id) != p.numero_cuotas OR COUNT(c.id) = 0
ORDER BY 
    CASE 
        WHEN COUNT(c.id) = 0 THEN 1
        WHEN COUNT(c.id) < p.numero_cuotas THEN 2
        ELSE 3
    END,
    p.id;

-- ============================================
-- PASO 6: RESUMEN DE VALIDACIONES
-- ============================================
SELECT 
    'RESUMEN VALIDACIONES' as etapa,
    (SELECT COUNT(*) FROM public.prestamos WHERE estado = 'APROBADO') as prestamos_aprobados,
    (SELECT COUNT(DISTINCT prestamo_id) FROM public.cuotas c 
     JOIN public.prestamos p ON p.id = c.prestamo_id 
     WHERE p.estado = 'APROBADO') as prestamos_aprobados_con_cuotas,
    (SELECT COUNT(*) FROM public.prestamos p
     LEFT JOIN public.cuotas c ON c.prestamo_id = p.id
     WHERE p.estado = 'APROBADO' AND c.id IS NULL) as prestamos_aprobados_sin_cuotas,
    CASE 
        WHEN (SELECT COUNT(*) FROM public.prestamos WHERE estado = 'APROBADO') = 
             (SELECT COUNT(DISTINCT prestamo_id) FROM public.cuotas c 
              JOIN public.prestamos p ON p.id = c.prestamo_id 
              WHERE p.estado = 'APROBADO')
        THEN 'OK - TODOS LOS APROBADOS TIENEN CUOTAS'
        ELSE 'ERROR - FALTAN CUOTAS EN PRESTAMOS APROBADOS'
    END as validacion_final;

-- ============================================
-- PASO 7: EJEMPLOS DE PRESTAMOS CON CUOTAS CORRECTAS
-- ============================================
SELECT 
    'EJEMPLOS PRESTAMOS CORRECTOS' as etapa,
    p.id as prestamo_id,
    p.cedula,
    p.numero_cuotas as cuotas_esperadas,
    COUNT(c.id) as cuotas_existentes,
    MIN(c.numero_cuota) as primera_cuota,
    MAX(c.numero_cuota) as ultima_cuota,
    CASE 
        WHEN COUNT(c.id) = p.numero_cuotas THEN 'OK - COMPLETAS'
        ELSE 'PROBLEMA'
    END as estado
FROM public.prestamos p
JOIN public.cuotas c ON c.prestamo_id = p.id
WHERE p.estado = 'APROBADO'
GROUP BY p.id, p.cedula, p.numero_cuotas
HAVING COUNT(c.id) = p.numero_cuotas
ORDER BY p.id
LIMIT 10;

-- ============================================
-- RESUMEN FINAL
-- ============================================
SELECT 
    '[OK] Verificación completada. Revisar resultados anteriores para identificar problemas.' as resultado;
