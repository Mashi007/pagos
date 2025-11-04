-- ============================================
-- VERIFICACIÓN AUTOMÁTICA DE COLUMNAS ADICIONALES CON DATOS
-- ============================================
-- Este script verifica automáticamente si las columnas adicionales tienen datos
-- Ejecuta PRIMERO el PASO 1 para identificar los nombres de las columnas adicionales
-- Luego ejecuta el PASO 2 ajustando los nombres de columnas
-- ============================================

-- PASO 1: Identificar TODAS las columnas adicionales (que no sean las 5 básicas)
SELECT 
    column_name,
    data_type,
    is_nullable,
    CASE 
        WHEN column_name IN ('id_stg', 'cedula_cliente', 'fecha_pago', 'monto_pagado', 'numero_documento') 
        THEN '✅ BÁSICA'
        ELSE '⚠️ ADICIONAL'
    END AS tipo
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'pagos_staging'
  AND column_name NOT IN ('id_stg', 'cedula_cliente', 'fecha_pago', 'monto_pagado', 'numero_documento')
ORDER BY ordinal_position;

-- PASO 2: Verificar si las columnas adicionales tienen datos
-- ⚠️ IMPORTANTE: Reemplaza 'column5', 'column6', 'column7', 'column8' 
-- con los nombres REALES que aparecieron en el PASO 1

-- Ejemplo para column5, column6, column7, column8 (ajusta según lo que veas en PASO 1):
SELECT 
    COUNT(*) AS total_registros,
    
    -- Verificar column5
    COUNT(CASE WHEN column5 IS NOT NULL AND TRIM(CAST(column5 AS TEXT)) != '' THEN 1 END) AS column5_con_datos,
    COUNT(*) - COUNT(CASE WHEN column5 IS NOT NULL AND TRIM(CAST(column5 AS TEXT)) != '' THEN 1 END) AS column5_vacios,
    CASE 
        WHEN COUNT(*) > 0 THEN
            ROUND((COUNT(CASE WHEN column5 IS NOT NULL AND TRIM(CAST(column5 AS TEXT)) != '' THEN 1 END)::numeric / COUNT(*)::numeric) * 100, 2)
        ELSE 0
    END AS column5_porcentaje_uso,
    CASE 
        WHEN COUNT(CASE WHEN column5 IS NOT NULL AND TRIM(CAST(column5 AS TEXT)) != '' THEN 1 END) = 0 THEN '❌ SIN UTILIDAD'
        WHEN COUNT(CASE WHEN column5 IS NOT NULL AND TRIM(CAST(column5 AS TEXT)) != '' THEN 1 END) < COUNT(*) * 0.1 THEN '⚠️ POCO ÚTIL (<10%)'
        WHEN COUNT(CASE WHEN column5 IS NOT NULL AND TRIM(CAST(column5 AS TEXT)) != '' THEN 1 END) < COUNT(*) * 0.5 THEN '⚠️ PARCIAL (<50%)'
        ELSE '✅ ÚTIL (>50%)'
    END AS column5_utilidad,
    
    -- Verificar column6
    COUNT(CASE WHEN column6 IS NOT NULL AND TRIM(CAST(column6 AS TEXT)) != '' THEN 1 END) AS column6_con_datos,
    COUNT(*) - COUNT(CASE WHEN column6 IS NOT NULL AND TRIM(CAST(column6 AS TEXT)) != '' THEN 1 END) AS column6_vacios,
    CASE 
        WHEN COUNT(*) > 0 THEN
            ROUND((COUNT(CASE WHEN column6 IS NOT NULL AND TRIM(CAST(column6 AS TEXT)) != '' THEN 1 END)::numeric / COUNT(*)::numeric) * 100, 2)
        ELSE 0
    END AS column6_porcentaje_uso,
    CASE 
        WHEN COUNT(CASE WHEN column6 IS NOT NULL AND TRIM(CAST(column6 AS TEXT)) != '' THEN 1 END) = 0 THEN '❌ SIN UTILIDAD'
        WHEN COUNT(CASE WHEN column6 IS NOT NULL AND TRIM(CAST(column6 AS TEXT)) != '' THEN 1 END) < COUNT(*) * 0.1 THEN '⚠️ POCO ÚTIL (<10%)'
        WHEN COUNT(CASE WHEN column6 IS NOT NULL AND TRIM(CAST(column6 AS TEXT)) != '' THEN 1 END) < COUNT(*) * 0.5 THEN '⚠️ PARCIAL (<50%)'
        ELSE '✅ ÚTIL (>50%)'
    END AS column6_utilidad,
    
    -- Verificar column7
    COUNT(CASE WHEN column7 IS NOT NULL AND TRIM(CAST(column7 AS TEXT)) != '' THEN 1 END) AS column7_con_datos,
    COUNT(*) - COUNT(CASE WHEN column7 IS NOT NULL AND TRIM(CAST(column7 AS TEXT)) != '' THEN 1 END) AS column7_vacios,
    CASE 
        WHEN COUNT(*) > 0 THEN
            ROUND((COUNT(CASE WHEN column7 IS NOT NULL AND TRIM(CAST(column7 AS TEXT)) != '' THEN 1 END)::numeric / COUNT(*)::numeric) * 100, 2)
        ELSE 0
    END AS column7_porcentaje_uso,
    CASE 
        WHEN COUNT(CASE WHEN column7 IS NOT NULL AND TRIM(CAST(column7 AS TEXT)) != '' THEN 1 END) = 0 THEN '❌ SIN UTILIDAD'
        WHEN COUNT(CASE WHEN column7 IS NOT NULL AND TRIM(CAST(column7 AS TEXT)) != '' THEN 1 END) < COUNT(*) * 0.1 THEN '⚠️ POCO ÚTIL (<10%)'
        WHEN COUNT(CASE WHEN column7 IS NOT NULL AND TRIM(CAST(column7 AS TEXT)) != '' THEN 1 END) < COUNT(*) * 0.5 THEN '⚠️ PARCIAL (<50%)'
        ELSE '✅ ÚTIL (>50%)'
    END AS column7_utilidad,
    
    -- Verificar column8
    COUNT(CASE WHEN column8 IS NOT NULL AND TRIM(CAST(column8 AS TEXT)) != '' THEN 1 END) AS column8_con_datos,
    COUNT(*) - COUNT(CASE WHEN column8 IS NOT NULL AND TRIM(CAST(column8 AS TEXT)) != '' THEN 1 END) AS column8_vacios,
    CASE 
        WHEN COUNT(*) > 0 THEN
            ROUND((COUNT(CASE WHEN column8 IS NOT NULL AND TRIM(CAST(column8 AS TEXT)) != '' THEN 1 END)::numeric / COUNT(*)::numeric) * 100, 2)
        ELSE 0
    END AS column8_porcentaje_uso,
    CASE 
        WHEN COUNT(CASE WHEN column8 IS NOT NULL AND TRIM(CAST(column8 AS TEXT)) != '' THEN 1 END) = 0 THEN '❌ SIN UTILIDAD'
        WHEN COUNT(CASE WHEN column8 IS NOT NULL AND TRIM(CAST(column8 AS TEXT)) != '' THEN 1 END) < COUNT(*) * 0.1 THEN '⚠️ POCO ÚTIL (<10%)'
        WHEN COUNT(CASE WHEN column8 IS NOT NULL AND TRIM(CAST(column8 AS TEXT)) != '' THEN 1 END) < COUNT(*) * 0.5 THEN '⚠️ PARCIAL (<50%)'
        ELSE '✅ ÚTIL (>50%)'
    END AS column8_utilidad
    
FROM pagos_staging;

-- PASO 3: Resumen de utilidad por columna (formato más legible)
-- ⚠️ IMPORTANTE: Ajusta los nombres de columnas según el PASO 1
/*
WITH estadisticas AS (
    SELECT 
        COUNT(*) AS total,
        COUNT(CASE WHEN column5 IS NOT NULL AND TRIM(CAST(column5 AS TEXT)) != '' THEN 1 END) AS col5_datos,
        COUNT(CASE WHEN column6 IS NOT NULL AND TRIM(CAST(column6 AS TEXT)) != '' THEN 1 END) AS col6_datos,
        COUNT(CASE WHEN column7 IS NOT NULL AND TRIM(CAST(column7 AS TEXT)) != '' THEN 1 END) AS col7_datos,
        COUNT(CASE WHEN column8 IS NOT NULL AND TRIM(CAST(column8 AS TEXT)) != '' THEN 1 END) AS col8_datos
    FROM pagos_staging
)
SELECT 
    'column5' AS columna,
    total AS total_registros,
    col5_datos AS registros_con_datos,
    total - col5_datos AS registros_vacios,
    CASE 
        WHEN total > 0 THEN ROUND((col5_datos::numeric / total::numeric) * 100, 2)
        ELSE 0
    END AS porcentaje_uso,
    CASE 
        WHEN col5_datos = 0 THEN '❌ SIN UTILIDAD - Todos NULL/vacíos'
        WHEN col5_datos < total * 0.1 THEN '⚠️ POCO ÚTIL - Menos del 10% tiene datos'
        WHEN col5_datos < total * 0.5 THEN '⚠️ PARCIALMENTE ÚTIL - Menos del 50% tiene datos'
        ELSE '✅ ÚTIL - Más del 50% tiene datos'
    END AS recomendacion
FROM estadisticas
UNION ALL
SELECT 
    'column6' AS columna,
    total AS total_registros,
    col6_datos AS registros_con_datos,
    total - col6_datos AS registros_vacios,
    CASE 
        WHEN total > 0 THEN ROUND((col6_datos::numeric / total::numeric) * 100, 2)
        ELSE 0
    END AS porcentaje_uso,
    CASE 
        WHEN col6_datos = 0 THEN '❌ SIN UTILIDAD - Todos NULL/vacíos'
        WHEN col6_datos < total * 0.1 THEN '⚠️ POCO ÚTIL - Menos del 10% tiene datos'
        WHEN col6_datos < total * 0.5 THEN '⚠️ PARCIALMENTE ÚTIL - Menos del 50% tiene datos'
        ELSE '✅ ÚTIL - Más del 50% tiene datos'
    END AS recomendacion
FROM estadisticas
UNION ALL
SELECT 
    'column7' AS columna,
    total AS total_registros,
    col7_datos AS registros_con_datos,
    total - col7_datos AS registros_vacios,
    CASE 
        WHEN total > 0 THEN ROUND((col7_datos::numeric / total::numeric) * 100, 2)
        ELSE 0
    END AS porcentaje_uso,
    CASE 
        WHEN col7_datos = 0 THEN '❌ SIN UTILIDAD - Todos NULL/vacíos'
        WHEN col7_datos < total * 0.1 THEN '⚠️ POCO ÚTIL - Menos del 10% tiene datos'
        WHEN col7_datos < total * 0.5 THEN '⚠️ PARCIALMENTE ÚTIL - Menos del 50% tiene datos'
        ELSE '✅ ÚTIL - Más del 50% tiene datos'
    END AS recomendacion
FROM estadisticas
UNION ALL
SELECT 
    'column8' AS columna,
    total AS total_registros,
    col8_datos AS registros_con_datos,
    total - col8_datos AS registros_vacios,
    CASE 
        WHEN total > 0 THEN ROUND((col8_datos::numeric / total::numeric) * 100, 2)
        ELSE 0
    END AS porcentaje_uso,
    CASE 
        WHEN col8_datos = 0 THEN '❌ SIN UTILIDAD - Todos NULL/vacíos'
        WHEN col8_datos < total * 0.1 THEN '⚠️ POCO ÚTIL - Menos del 10% tiene datos'
        WHEN col8_datos < total * 0.5 THEN '⚠️ PARCIALMENTE ÚTIL - Menos del 50% tiene datos'
        ELSE '✅ ÚTIL - Más del 50% tiene datos'
    END AS recomendacion
FROM estadisticas;
*/

-- ============================================
-- INSTRUCCIONES:
-- ============================================
-- 1. Ejecuta PASO 1 para identificar los nombres de las columnas adicionales
-- 2. Si ves column5, column6, column7, column8 u otros nombres, anótalos
-- 3. Ejecuta PASO 2 reemplazando 'column5', 'column6', etc. con los nombres reales
-- 4. El PASO 2 te mostrará:
--    - Cuántos registros tienen datos en cada columna
--    - Cuántos están vacíos
--    - Porcentaje de uso
--    - Recomendación de utilidad
-- 5. Si quieres un formato más legible, descomenta y ejecuta PASO 3
-- ============================================

