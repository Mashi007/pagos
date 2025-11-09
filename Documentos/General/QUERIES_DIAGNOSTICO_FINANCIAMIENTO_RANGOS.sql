-- 🔍 QUERIES DE DIAGNÓSTICO: Endpoint financiamiento-por-rangos
-- Ejecutar estas queries para diagnosticar por qué retorna 0 préstamos

-- ============================================
-- 1. VERIFICACIÓN BÁSICA
-- ============================================

-- Total de préstamos
SELECT COUNT(*) as total_prestamos FROM prestamos;

-- Préstamos por estado
SELECT estado, COUNT(*) as cantidad 
FROM prestamos 
GROUP BY estado 
ORDER BY cantidad DESC;

-- ============================================
-- 2. VERIFICAR PRÉSTAMOS APROBADOS
-- ============================================

-- Total de préstamos aprobados
SELECT COUNT(*) as total_aprobados 
FROM prestamos 
WHERE estado = 'APROBADO';

-- ============================================
-- 3. VERIFICAR PRÉSTAMOS CON MONTO VÁLIDO
-- ============================================

-- Préstamos aprobados con total_financiamiento > 0
SELECT COUNT(*) as prestamos_validos
FROM prestamos 
WHERE estado = 'APROBADO' 
AND total_financiamiento IS NOT NULL 
AND total_financiamiento > 0;

-- Préstamos aprobados con total_financiamiento NULL
SELECT COUNT(*) as prestamos_null
FROM prestamos 
WHERE estado = 'APROBADO' 
AND total_financiamiento IS NULL;

-- Préstamos aprobados con total_financiamiento = 0
SELECT COUNT(*) as prestamos_cero
FROM prestamos 
WHERE estado = 'APROBADO' 
AND total_financiamiento = 0;

-- ============================================
-- 4. VERIFICAR FECHAS
-- ============================================

-- Préstamos válidos con fecha_registro
SELECT COUNT(*) as con_fecha_registro
FROM prestamos 
WHERE estado = 'APROBADO' 
AND total_financiamiento IS NOT NULL 
AND total_financiamiento > 0
AND fecha_registro IS NOT NULL;

-- Préstamos válidos con fecha_aprobacion
SELECT COUNT(*) as con_fecha_aprobacion
FROM prestamos 
WHERE estado = 'APROBADO' 
AND total_financiamiento IS NOT NULL 
AND total_financiamiento > 0
AND fecha_aprobacion IS NOT NULL;

-- Préstamos válidos con fecha_base_calculo
SELECT COUNT(*) as con_fecha_base
FROM prestamos 
WHERE estado = 'APROBADO' 
AND total_financiamiento IS NOT NULL 
AND total_financiamiento > 0
AND fecha_base_calculo IS NOT NULL;

-- Préstamos válidos SIN ninguna fecha
SELECT COUNT(*) as sin_ninguna_fecha
FROM prestamos 
WHERE estado = 'APROBADO' 
AND total_financiamiento IS NOT NULL 
AND total_financiamiento > 0
AND fecha_registro IS NULL
AND fecha_aprobacion IS NULL
AND fecha_base_calculo IS NULL;

-- ============================================
-- 5. VERIFICAR RANGO DEL AÑO 2025
-- ============================================

-- Préstamos válidos en rango del año 2025 (usando OR entre fechas)
SELECT COUNT(*) as en_rango_2025
FROM prestamos 
WHERE estado = 'APROBADO'
AND total_financiamiento IS NOT NULL 
AND total_financiamiento > 0
AND (
    (fecha_registro IS NOT NULL 
     AND fecha_registro >= '2025-01-01' 
     AND fecha_registro <= '2025-12-31')
    OR
    (fecha_aprobacion IS NOT NULL 
     AND fecha_aprobacion >= '2025-01-01' 
     AND fecha_aprobacion <= '2025-12-31')
    OR
    (fecha_base_calculo IS NOT NULL 
     AND fecha_base_calculo >= '2025-01-01' 
     AND fecha_base_calculo <= '2025-12-31')
);

-- Préstamos válidos SIN filtros de fecha
SELECT COUNT(*) as sin_filtro_fecha
FROM prestamos 
WHERE estado = 'APROBADO' 
AND total_financiamiento IS NOT NULL 
AND total_financiamiento > 0;

-- ============================================
-- 6. RANGOS DE FECHAS
-- ============================================

-- Fecha mínima y máxima de fecha_registro
SELECT 
    MIN(fecha_registro) as min_fecha_registro,
    MAX(fecha_registro) as max_fecha_registro
FROM prestamos 
WHERE estado = 'APROBADO' 
AND total_financiamiento IS NOT NULL 
AND total_financiamiento > 0
AND fecha_registro IS NOT NULL;

-- Fecha mínima y máxima de fecha_aprobacion
SELECT 
    MIN(fecha_aprobacion) as min_fecha_aprobacion,
    MAX(fecha_aprobacion) as max_fecha_aprobacion
FROM prestamos 
WHERE estado = 'APROBADO' 
AND total_financiamiento IS NOT NULL 
AND total_financiamiento > 0
AND fecha_aprobacion IS NOT NULL;

-- ============================================
-- 7. DISTRIBUCIÓN POR RANGOS DE MONTO
-- ============================================

-- Ver distribución de montos (primeros rangos)
SELECT 
    CASE 
        WHEN total_financiamiento >= 0 AND total_financiamiento < 300 THEN '0-300'
        WHEN total_financiamiento >= 300 AND total_financiamiento < 600 THEN '300-600'
        WHEN total_financiamiento >= 600 AND total_financiamiento < 900 THEN '600-900'
        WHEN total_financiamiento >= 900 AND total_financiamiento < 1200 THEN '900-1200'
        WHEN total_financiamiento >= 1200 AND total_financiamiento < 1500 THEN '1200-1500'
        WHEN total_financiamiento >= 1500 AND total_financiamiento < 3000 THEN '1500-3000'
        WHEN total_financiamiento >= 3000 AND total_financiamiento < 5000 THEN '3000-5000'
        WHEN total_financiamiento >= 5000 AND total_financiamiento < 10000 THEN '5000-10000'
        WHEN total_financiamiento >= 10000 AND total_financiamiento < 20000 THEN '10000-20000'
        WHEN total_financiamiento >= 20000 AND total_financiamiento < 50000 THEN '20000-50000'
        ELSE '50000+'
    END as rango,
    COUNT(*) as cantidad,
    SUM(total_financiamiento) as monto_total
FROM prestamos 
WHERE estado = 'APROBADO' 
AND total_financiamiento IS NOT NULL 
AND total_financiamiento > 0
GROUP BY rango
ORDER BY MIN(total_financiamiento);

-- ============================================
-- 8. RESUMEN COMPLETO
-- ============================================

SELECT 
    (SELECT COUNT(*) FROM prestamos) as total_prestamos,
    (SELECT COUNT(*) FROM prestamos WHERE estado = 'APROBADO') as total_aprobados,
    (SELECT COUNT(*) FROM prestamos 
     WHERE estado = 'APROBADO' 
     AND total_financiamiento IS NOT NULL 
     AND total_financiamiento > 0) as prestamos_validos,
    (SELECT COUNT(*) FROM prestamos 
     WHERE estado = 'APROBADO'
     AND total_financiamiento IS NOT NULL 
     AND total_financiamiento > 0
     AND (
         (fecha_registro >= '2025-01-01' AND fecha_registro <= '2025-12-31')
         OR
         (fecha_aprobacion >= '2025-01-01' AND fecha_aprobacion <= '2025-12-31')
         OR
         (fecha_base_calculo >= '2025-01-01' AND fecha_base_calculo <= '2025-12-31')
     )) as en_rango_2025;

