-- ============================================
-- DIAGNÓSTICO DE PROBLEMAS EN CÉDULAS
-- ============================================
-- Este script identifica todos los problemas relacionados con cédulas vacías o inválidas
-- y su impacto en el procesamiento de pagos
-- ============================================

-- ============================================
-- PASO 1: RESUMEN GENERAL DE CÉDULAS
-- ============================================
SELECT 
    '=== RESUMEN GENERAL DE CÉDULAS ===' AS seccion,
    COUNT(*) AS total_registros,
    COUNT(CASE WHEN cedula_cliente IS NULL THEN 1 END) AS cedulas_null,
    COUNT(CASE WHEN cedula_cliente IS NOT NULL AND TRIM(cedula_cliente) = '' THEN 1 END) AS cedulas_vacias,
    COUNT(CASE WHEN cedula_cliente IS NOT NULL AND TRIM(cedula_cliente) != '' THEN 1 END) AS cedulas_con_valor,
    ROUND((COUNT(CASE WHEN cedula_cliente IS NOT NULL AND TRIM(cedula_cliente) = '' THEN 1 END)::numeric / COUNT(*)::numeric) * 100, 2) AS porcentaje_vacias
FROM pagos_staging;

-- ============================================
-- PASO 2: CÉDULAS QUE NO SE PROCESAN (VACÍAS)
-- ============================================
-- Estas cédulas son excluidas por el filtro: cedula_cliente IS NOT NULL AND cedula_cliente != '' AND TRIM(cedula_cliente) != ''
SELECT 
    '=== CÉDULAS VACÍAS (NO SE PROCESAN) ===' AS seccion,
    COUNT(*) AS total_registros_no_procesados,
    COALESCE(SUM(CASE 
        WHEN monto_pagado IS NOT NULL 
        AND TRIM(monto_pagado) != '' 
        AND monto_pagado ~ '^[0-9]+(\.[0-9]+)?$' 
        THEN monto_pagado::numeric 
        ELSE 0 
    END), 0) AS monto_total_no_procesado,
    ROUND((COUNT(*)::numeric / (SELECT COUNT(*) FROM pagos_staging)::numeric) * 100, 2) AS porcentaje_del_total
FROM pagos_staging
WHERE cedula_cliente IS NULL 
   OR TRIM(cedula_cliente) = '';

-- ============================================
-- PASO 3: EJEMPLOS DE REGISTROS CON CÉDULAS VACÍAS
-- ============================================
SELECT 
    '=== EJEMPLOS: REGISTROS CON CÉDULAS VACÍAS ===' AS seccion,
    id_stg,
    cedula_cliente,
    fecha_pago,
    monto_pagado,
    numero_documento,
    CASE 
        WHEN cedula_cliente IS NULL THEN 'NULL'
        WHEN TRIM(cedula_cliente) = '' THEN 'VACÍO (solo espacios)'
        ELSE 'CON VALOR'
    END AS tipo_problema,
    CASE 
        WHEN monto_pagado IS NOT NULL 
        AND TRIM(monto_pagado) != '' 
        AND monto_pagado ~ '^[0-9]+(\.[0-9]+)?$' 
        THEN monto_pagado::numeric 
        ELSE 0 
    END AS monto_pagado_numerico
FROM pagos_staging
WHERE cedula_cliente IS NULL 
   OR TRIM(cedula_cliente) = ''
ORDER BY id_stg DESC
LIMIT 50;

-- ============================================
-- PASO 4: CÉDULAS CON FORMATO INVÁLIDO
-- ============================================
-- Estas cédulas tienen caracteres no permitidos (no son números ni Z)
SELECT 
    '=== CÉDULAS CON FORMATO INVÁLIDO ===' AS seccion,
    COUNT(*) AS total_registros_formato_invalido,
    COUNT(DISTINCT cedula_cliente) AS cedulas_distintas_invalidas,
    COALESCE(SUM(CASE 
        WHEN monto_pagado IS NOT NULL 
        AND TRIM(monto_pagado) != '' 
        AND monto_pagado ~ '^[0-9]+(\.[0-9]+)?$' 
        THEN monto_pagado::numeric 
        ELSE 0 
    END), 0) AS monto_total_formato_invalido
FROM pagos_staging
WHERE cedula_cliente IS NOT NULL 
   AND TRIM(cedula_cliente) != ''
   AND UPPER(TRIM(cedula_cliente)) != 'Z999999999'
   AND (
       cedula_cliente ~ '[^VEJZvejz0-9]'
       OR (cedula_cliente !~ '^[VEJZvejz][0-9]{7,9}$' AND cedula_cliente !~ '^[0-9]{7,10}$')
       OR LENGTH(TRIM(cedula_cliente)) < 7
       OR LENGTH(TRIM(cedula_cliente)) > 10
   );

-- ============================================
-- PASO 5: EJEMPLOS DE CÉDULAS CON FORMATO INVÁLIDO
-- ============================================
SELECT 
    '=== EJEMPLOS: CÉDULAS CON FORMATO INVÁLIDO ===' AS seccion,
    id_stg,
    cedula_cliente,
    fecha_pago,
    monto_pagado,
    numero_documento,
    CASE 
        WHEN cedula_cliente LIKE '%-%' THEN 'Contiene guiones (-)'
        WHEN cedula_cliente LIKE '%.%' THEN 'Contiene puntos (.)'
        WHEN cedula_cliente LIKE '% %' THEN 'Contiene espacios'
        WHEN cedula_cliente ~ '[^VEJZvejz0-9]' THEN 'Contiene caracteres no permitidos (solo V/E/J/Z/0-9)'
        WHEN LENGTH(TRIM(cedula_cliente)) < 7 THEN 'Muy corta (< 7 dígitos)'
        WHEN LENGTH(TRIM(cedula_cliente)) > 10 THEN 'Muy larga (> 10 caracteres)'
        WHEN cedula_cliente !~ '^[VEJZvejz][0-9]{7,9}$' AND cedula_cliente !~ '^[0-9]{7,10}$' THEN 'Formato incorrecto (debe ser V/E/J/Z + 7-9 dígitos O 7-10 dígitos)'
        ELSE 'Formato desconocido'
    END AS tipo_error_formato
FROM pagos_staging
WHERE cedula_cliente IS NOT NULL 
   AND TRIM(cedula_cliente) != ''
   AND UPPER(TRIM(cedula_cliente)) != 'Z999999999'
   AND (
       cedula_cliente ~ '[^VEJZvejz0-9]'
       OR (cedula_cliente !~ '^[VEJZvejz][0-9]{7,9}$' AND cedula_cliente !~ '^[0-9]{7,10}$')
       OR LENGTH(TRIM(cedula_cliente)) < 7
       OR LENGTH(TRIM(cedula_cliente)) > 10
   )
ORDER BY id_stg DESC
LIMIT 50;

-- ============================================
-- PASO 6: IMPACTO EN MONTO TOTAL
-- ============================================
-- Calcula cuánto dinero está en registros que NO se procesan
SELECT 
    '=== IMPACTO EN MONTO TOTAL ===' AS seccion,
    -- Total de registros con cédula válida
    COUNT(CASE 
        WHEN cedula_cliente IS NOT NULL 
        AND TRIM(cedula_cliente) != '' 
        AND (
       UPPER(TRIM(cedula_cliente)) = 'Z999999999'
       OR (cedula_cliente ~ '^[VEJZvejz][0-9]{7,9}$' AND LENGTH(TRIM(cedula_cliente)) >= 8 AND LENGTH(TRIM(cedula_cliente)) <= 10)
       OR (cedula_cliente ~ '^[0-9]{7,10}$' AND LENGTH(TRIM(cedula_cliente)) >= 7 AND LENGTH(TRIM(cedula_cliente)) <= 10)
   )
        THEN 1 
    END) AS registros_procesados,
    -- Monto total de registros procesados
    COALESCE(SUM(CASE 
        WHEN cedula_cliente IS NOT NULL 
        AND TRIM(cedula_cliente) != '' 
        AND (
       UPPER(TRIM(cedula_cliente)) = 'Z999999999'
       OR (cedula_cliente ~ '^[VEJZvejz][0-9]{7,9}$' AND LENGTH(TRIM(cedula_cliente)) >= 8 AND LENGTH(TRIM(cedula_cliente)) <= 10)
       OR (cedula_cliente ~ '^[0-9]{7,10}$' AND LENGTH(TRIM(cedula_cliente)) >= 7 AND LENGTH(TRIM(cedula_cliente)) <= 10)
   )
        AND monto_pagado IS NOT NULL 
        AND TRIM(monto_pagado) != '' 
        AND monto_pagado ~ '^[0-9]+(\.[0-9]+)?$' 
        THEN monto_pagado::numeric 
        ELSE 0 
    END), 0) AS monto_procesado,
    -- Total de registros con cédula vacía o NULL
    COUNT(CASE 
        WHEN cedula_cliente IS NULL 
        OR TRIM(cedula_cliente) = '' 
        THEN 1 
    END) AS registros_no_procesados,
    -- Monto total de registros NO procesados
    COALESCE(SUM(CASE 
        WHEN (cedula_cliente IS NULL OR TRIM(cedula_cliente) = '')
        AND monto_pagado IS NOT NULL 
        AND TRIM(monto_pagado) != '' 
        AND monto_pagado ~ '^[0-9]+(\.[0-9]+)?$' 
        THEN monto_pagado::numeric 
        ELSE 0 
    END), 0) AS monto_no_procesado,
    -- Total de registros con formato inválido
    COUNT(CASE 
        WHEN cedula_cliente IS NOT NULL 
        AND TRIM(cedula_cliente) != '' 
        AND (
            cedula_cliente ~ '[^VEJZvejz0-9]'
            OR (cedula_cliente !~ '^[VEJZvejz][0-9]{7,9}$' AND cedula_cliente !~ '^[0-9]{7,10}$')
            OR LENGTH(TRIM(cedula_cliente)) < 7
            OR LENGTH(TRIM(cedula_cliente)) > 10
        )
        AND UPPER(TRIM(cedula_cliente)) != 'Z999999999'
        THEN 1 
    END) AS registros_formato_invalido,
    -- Monto total de registros con formato inválido
    COALESCE(SUM(CASE 
        WHEN cedula_cliente IS NOT NULL 
        AND TRIM(cedula_cliente) != '' 
        AND (
            cedula_cliente ~ '[^VEJZvejz0-9]'
            OR (cedula_cliente !~ '^[VEJZvejz][0-9]{7,9}$' AND cedula_cliente !~ '^[0-9]{7,10}$')
            OR LENGTH(TRIM(cedula_cliente)) < 7
            OR LENGTH(TRIM(cedula_cliente)) > 10
        )
        AND UPPER(TRIM(cedula_cliente)) != 'Z999999999'
        AND monto_pagado IS NOT NULL 
        AND TRIM(monto_pagado) != '' 
        AND monto_pagado ~ '^[0-9]+(\.[0-9]+)?$' 
        THEN monto_pagado::numeric 
        ELSE 0 
    END), 0) AS monto_formato_invalido,
    -- Porcentaje de monto no procesado
    CASE 
        WHEN COALESCE(SUM(CASE 
            WHEN monto_pagado IS NOT NULL 
            AND TRIM(monto_pagado) != '' 
            AND monto_pagado ~ '^[0-9]+(\.[0-9]+)?$' 
            THEN monto_pagado::numeric 
            ELSE 0 
        END), 0) > 0 
        THEN ROUND(
            (COALESCE(SUM(CASE 
                WHEN (cedula_cliente IS NULL OR TRIM(cedula_cliente) = '')
                AND monto_pagado IS NOT NULL 
                AND TRIM(monto_pagado) != '' 
                AND monto_pagado ~ '^[0-9]+(\.[0-9]+)?$' 
                THEN monto_pagado::numeric 
                ELSE 0 
            END), 0)::numeric / 
            COALESCE(SUM(CASE 
                WHEN monto_pagado IS NOT NULL 
                AND TRIM(monto_pagado) != '' 
                AND monto_pagado ~ '^[0-9]+(\.[0-9]+)?$' 
                THEN monto_pagado::numeric 
                ELSE 0 
            END), 0)::numeric) * 100, 2)
        ELSE 0
    END AS porcentaje_monto_no_procesado
FROM pagos_staging;

-- ============================================
-- PASO 7: DISTRIBUCIÓN POR TIPO DE PROBLEMA
-- ============================================
SELECT 
    '=== DISTRIBUCIÓN POR TIPO DE PROBLEMA ===' AS seccion,
    CASE 
        WHEN cedula_cliente IS NULL THEN '❌ NULL'
        WHEN TRIM(cedula_cliente) = '' THEN '❌ VACÍO'
        WHEN UPPER(TRIM(cedula_cliente)) != 'Z999999999' AND (
            cedula_cliente ~ '[^VEJZvejz0-9]'
            OR (cedula_cliente !~ '^[VEJZvejz][0-9]{7,9}$' AND cedula_cliente !~ '^[0-9]{7,10}$')
            OR LENGTH(TRIM(cedula_cliente)) < 7
            OR LENGTH(TRIM(cedula_cliente)) > 10
        ) THEN '⚠️ FORMATO INVÁLIDO'
        WHEN LENGTH(TRIM(cedula_cliente)) < 3 AND UPPER(TRIM(cedula_cliente)) != 'Z999999999' THEN '⚠️ MUY CORTO'
        WHEN UPPER(TRIM(cedula_cliente)) = 'Z999999999' THEN '✅ VALOR POR DEFECTO (Z999999999)'
        ELSE '✅ VÁLIDO'
    END AS tipo_problema,
    COUNT(*) AS cantidad_registros,
    ROUND((COUNT(*)::numeric / (SELECT COUNT(*) FROM pagos_staging)::numeric) * 100, 2) AS porcentaje_registros,
    COALESCE(SUM(CASE 
        WHEN monto_pagado IS NOT NULL 
        AND TRIM(monto_pagado) != '' 
        AND monto_pagado ~ '^[0-9]+(\.[0-9]+)?$' 
        THEN monto_pagado::numeric 
        ELSE 0 
    END), 0) AS monto_total
FROM pagos_staging
GROUP BY 
    CASE 
        WHEN cedula_cliente IS NULL THEN '❌ NULL'
        WHEN TRIM(cedula_cliente) = '' THEN '❌ VACÍO'
        WHEN UPPER(TRIM(cedula_cliente)) != 'Z999999999' AND (
            cedula_cliente ~ '[^VEJZvejz0-9]'
            OR (cedula_cliente !~ '^[VEJZvejz][0-9]{7,9}$' AND cedula_cliente !~ '^[0-9]{7,10}$')
            OR LENGTH(TRIM(cedula_cliente)) < 7
            OR LENGTH(TRIM(cedula_cliente)) > 10
        ) THEN '⚠️ FORMATO INVÁLIDO'
        WHEN LENGTH(TRIM(cedula_cliente)) < 3 AND UPPER(TRIM(cedula_cliente)) != 'Z999999999' THEN '⚠️ MUY CORTO'
        WHEN UPPER(TRIM(cedula_cliente)) = 'Z999999999' THEN '✅ VALOR POR DEFECTO (Z999999999)'
        ELSE '✅ VÁLIDO'
    END
ORDER BY cantidad_registros DESC;

-- ============================================
-- PASO 8: VERIFICAR SI CÉDULAS VACÍAS TIENEN OTROS DATOS VÁLIDOS
-- ============================================
-- Esto ayuda a identificar si se pueden recuperar algunos registros
SELECT 
    '=== CÉDULAS VACÍAS CON OTROS DATOS VÁLIDOS ===' AS seccion,
    COUNT(*) AS total_cedulas_vacias,
    COUNT(CASE 
        WHEN fecha_pago IS NOT NULL 
        AND TRIM(fecha_pago) != '' 
        AND fecha_pago ~ '^\d{4}-\d{2}-\d{2}' 
        THEN 1 
    END) AS con_fecha_valida,
    COUNT(CASE 
        WHEN monto_pagado IS NOT NULL 
        AND TRIM(monto_pagado) != '' 
        AND monto_pagado ~ '^[0-9]+(\.[0-9]+)?$' 
        AND monto_pagado::numeric > 0
        THEN 1 
    END) AS con_monto_valido,
    COUNT(CASE 
        WHEN numero_documento IS NOT NULL 
        AND TRIM(numero_documento) != '' 
        THEN 1 
    END) AS con_numero_documento
FROM pagos_staging
WHERE cedula_cliente IS NULL 
   OR TRIM(cedula_cliente) = '';

-- ============================================
-- PASO 9: RESUMEN DE IMPACTO EN KPIs
-- ============================================
SELECT 
    '=== RESUMEN DE IMPACTO ===' AS seccion,
    'Total de registros en pagos_staging' AS metric,
    COUNT(*) AS valor
FROM pagos_staging
UNION ALL
SELECT 
    '=== RESUMEN DE IMPACTO ===' AS seccion,
    'Registros que SÍ se procesan (cédula válida)' AS metric,
    COUNT(*) AS valor
FROM pagos_staging
WHERE cedula_cliente IS NOT NULL 
   AND TRIM(cedula_cliente) != ''
   AND (
       UPPER(TRIM(cedula_cliente)) = 'Z999999999'
       OR (cedula_cliente ~ '^[VEJZvejz][0-9]{7,9}$' AND LENGTH(TRIM(cedula_cliente)) >= 8 AND LENGTH(TRIM(cedula_cliente)) <= 10)
       OR (cedula_cliente ~ '^[0-9]{7,10}$' AND LENGTH(TRIM(cedula_cliente)) >= 7 AND LENGTH(TRIM(cedula_cliente)) <= 10)
   )
UNION ALL
SELECT 
    '=== RESUMEN DE IMPACTO ===' AS seccion,
    'Registros que NO se procesan (cédula vacía/NULL)' AS metric,
    COUNT(*) AS valor
FROM pagos_staging
WHERE cedula_cliente IS NULL 
   OR TRIM(cedula_cliente) = ''
UNION ALL
SELECT 
    '=== RESUMEN DE IMPACTO ===' AS seccion,
    'Registros con formato inválido (no se procesan)' AS metric,
    COUNT(*) AS valor
FROM pagos_staging
WHERE cedula_cliente IS NOT NULL 
   AND TRIM(cedula_cliente) != ''
   AND UPPER(TRIM(cedula_cliente)) != 'Z999999999'
   AND (
       cedula_cliente ~ '[^VEJZvejz0-9]'
       OR (cedula_cliente !~ '^[VEJZvejz][0-9]{7,9}$' AND cedula_cliente !~ '^[0-9]{7,10}$')
       OR LENGTH(TRIM(cedula_cliente)) < 7
       OR LENGTH(TRIM(cedula_cliente)) > 10
   );

-- ============================================
-- INSTRUCCIONES:
-- ============================================
-- 1. PASO 1: Resumen general de cédulas
-- 2. PASO 2: Cuántos registros NO se procesan por cédula vacía
-- 3. PASO 3: Ejemplos de registros con cédulas vacías
-- 4. PASO 4: Cédulas con formato inválido
-- 5. PASO 5: Ejemplos de cédulas con formato inválido
-- 6. PASO 6: Impacto en monto total (dinero no procesado)
-- 7. PASO 7: Distribución por tipo de problema
-- 8. PASO 8: Verificar si cédulas vacías tienen otros datos válidos
-- 9. PASO 9: Resumen final de impacto
-- ============================================
-- ⚠️ INTERPRETACIÓN:
-- - Si "monto_no_procesado" es alto, significa que hay dinero que no se está contabilizando
-- - Si "registros_no_procesados" es alto, significa que hay pagos que no aparecen en listados
-- - Los registros con formato inválido también se excluyen del procesamiento
-- ============================================

