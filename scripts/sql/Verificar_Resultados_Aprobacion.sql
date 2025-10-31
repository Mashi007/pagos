-- ============================================
-- VERIFICAR RESULTADOS DE APROBACIÓN MASIVA
-- ============================================
-- Ejecutar después de Aprobar_Prestamos_Masivos.sql
-- ============================================

-- 1. RESUMEN DE APROBACIONES
SELECT 
    'RESUMEN' AS tipo,
    COUNT(*) AS total_prestamos,
    COUNT(CASE WHEN estado = 'APROBADO' THEN 1 END) AS aprobados,
    COUNT(CASE WHEN fecha_aprobacion IS NOT NULL THEN 1 END) AS con_fecha_aprobacion,
    COUNT(CASE WHEN usuario_aprobador IS NOT NULL THEN 1 END) AS con_aprobador,
    COUNT(CASE WHEN fecha_base_calculo IS NOT NULL THEN 1 END) AS con_fecha_base_calculo
FROM public.prestamos;

-- 2. ESTADO ACTUAL (debe ser 100% APROBADO)
SELECT 
    estado,
    COUNT(*) AS cantidad,
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM public.prestamos), 2) AS porcentaje
FROM public.prestamos
GROUP BY estado
ORDER BY estado;

-- 3. PRÉSTAMOS LISTOS PARA GENERAR CUOTAS
SELECT 
    COUNT(*) AS prestamos_listos,
    SUM(numero_cuotas) AS total_cuotas_esperadas,
    AVG(numero_cuotas) AS promedio_cuotas_por_prestamo,
    MIN(numero_cuotas) AS min_cuotas,
    MAX(numero_cuotas) AS max_cuotas
FROM public.prestamos
WHERE estado = 'APROBADO'
  AND fecha_base_calculo IS NOT NULL
  AND numero_cuotas > 0
  AND total_financiamiento > 0;

-- 4. PRÉSTAMOS SIN CUOTAS (NECESITAN GENERACIÓN)
SELECT 
    COUNT(*) AS prestamos_sin_cuotas
FROM (
    SELECT 
        p.id
    FROM public.prestamos p
    LEFT JOIN public.cuotas c ON c.prestamo_id = p.id
    WHERE p.estado = 'APROBADO'
      AND p.fecha_base_calculo IS NOT NULL
      AND p.numero_cuotas > 0
      AND p.total_financiamiento > 0
    GROUP BY p.id
    HAVING COUNT(c.id) = 0
) AS prestamos_sin_cuotas;

-- Versión más simple:
SELECT 
    p.id,
    p.cedula,
    p.nombres,
    p.numero_cuotas AS cuotas_esperadas,
    COUNT(c.id) AS cuotas_generadas
FROM public.prestamos p
LEFT JOIN public.cuotas c ON c.prestamo_id = p.id
WHERE p.estado = 'APROBADO'
  AND p.fecha_base_calculo IS NOT NULL
GROUP BY p.id, p.cedula, p.nombres, p.numero_cuotas
HAVING COUNT(c.id) = 0 OR COUNT(c.id) != p.numero_cuotas
ORDER BY p.id
LIMIT 10;

