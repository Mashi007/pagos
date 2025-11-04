-- ============================================
-- IDENTIFICAR DATOS INVÁLIDOS EN PAGOS_STAGING
-- ============================================
-- Este script identifica registros con datos inválidos o faltantes
-- Muestra en qué columna está el problema y qué tipo de error tiene
-- ============================================

-- PASO 1: Resumen general de datos válidos vs inválidos
SELECT 
    COUNT(*) AS total_registros,
    COUNT(CASE WHEN cedula_cliente IS NOT NULL AND TRIM(cedula_cliente) != '' THEN 1 END) AS cedula_cliente_valida,
    COUNT(CASE WHEN fecha_pago IS NOT NULL AND TRIM(fecha_pago) != '' THEN 1 END) AS fecha_pago_valida,
    COUNT(CASE WHEN monto_pagado IS NOT NULL AND TRIM(monto_pagado) != '' THEN 1 END) AS monto_pagado_valido,
    COUNT(CASE WHEN numero_documento IS NOT NULL AND TRIM(numero_documento) != '' THEN 1 END) AS numero_documento_valido,
    -- Contar registros completamente válidos (todos los campos tienen datos)
    COUNT(CASE 
        WHEN cedula_cliente IS NOT NULL AND TRIM(cedula_cliente) != ''
        AND fecha_pago IS NOT NULL AND TRIM(fecha_pago) != ''
        AND monto_pagado IS NOT NULL AND TRIM(monto_pagado) != ''
        AND numero_documento IS NOT NULL AND TRIM(numero_documento) != ''
        THEN 1 
    END) AS registros_completamente_validos
FROM pagos_staging;

-- PASO 2: Identificar registros con CEDULA_CLIENTE inválido o vacío
-- ⚠️ NOTA: "Z999999999" se considera válido (valor por defecto reconocido)
-- ⚠️ VALIDACIÓN: Permite V, E, J, Z al inicio + 7-9 dígitos (total 8-10 caracteres)
-- ⚠️ NO acepta signos intermedios (guiones, puntos, espacios)
SELECT 
    'CEDULA_CLIENTE' AS columna_con_error,
    id_stg,
    cedula_cliente,
    fecha_pago,
    monto_pagado,
    numero_documento,
    CASE 
        WHEN cedula_cliente IS NULL THEN '❌ NULL'
        WHEN TRIM(cedula_cliente) = '' THEN '❌ VACÍO'
        WHEN UPPER(TRIM(cedula_cliente)) = 'Z999999999' THEN '✅ VÁLIDO (valor por defecto: Z999999999)'
        WHEN cedula_cliente ~ '[^VEJZvejz0-9]' THEN '⚠️ CONTIENE SIGNOS INTERMEDIOS O CARACTERES NO PERMITIDOS'
        WHEN cedula_cliente !~ '^[VEJZvejz][0-9]{7,9}$' AND cedula_cliente !~ '^[0-9]{7,10}$' THEN '⚠️ FORMATO INVÁLIDO (debe ser V/E/J/Z + 7-9 dígitos O 7-10 dígitos)'
        WHEN LENGTH(TRIM(cedula_cliente)) < 7 THEN '⚠️ MUY CORTO (< 7 dígitos)'
        WHEN LENGTH(TRIM(cedula_cliente)) > 10 THEN '⚠️ MUY LARGO (> 10 caracteres)'
        ELSE '✅ VÁLIDO'
    END AS tipo_error,
    CASE 
        WHEN cedula_cliente IS NULL THEN 'Valor NULL'
        WHEN TRIM(cedula_cliente) = '' THEN 'Cadena vacía'
        WHEN UPPER(TRIM(cedula_cliente)) = 'Z999999999' THEN 'Valor por defecto reconocido: Z999999999'
        WHEN cedula_cliente ~ '[^VEJZvejz0-9]' THEN 'Contiene signos intermedios o caracteres no permitidos: ' || cedula_cliente
        WHEN cedula_cliente !~ '^[VEJZvejz][0-9]{7,9}$' AND cedula_cliente !~ '^[0-9]{7,10}$' THEN 'Formato incorrecto. Debe ser: V/E/J/Z + 7-9 dígitos O 7-10 dígitos. Actual: ' || cedula_cliente
        WHEN LENGTH(TRIM(cedula_cliente)) < 7 THEN 'Muy corta. Mínimo 7 dígitos. Actual: ' || cedula_cliente
        WHEN LENGTH(TRIM(cedula_cliente)) > 10 THEN 'Muy larga. Máximo 10 caracteres. Actual: ' || cedula_cliente
        ELSE 'Sin error'
    END AS descripcion_error
FROM pagos_staging
WHERE cedula_cliente IS NULL 
   OR TRIM(cedula_cliente) = ''
   OR (UPPER(TRIM(cedula_cliente)) != 'Z999999999' AND (
       cedula_cliente ~ '[^VEJZvejz0-9]'
       OR (cedula_cliente !~ '^[VEJZvejz][0-9]{7,9}$' AND cedula_cliente !~ '^[0-9]{7,10}$')
       OR LENGTH(TRIM(cedula_cliente)) < 7
       OR LENGTH(TRIM(cedula_cliente)) > 10
   ))
ORDER BY id_stg DESC
LIMIT 100;

-- PASO 3: Identificar registros con FECHA_PAGO inválido o vacío
SELECT 
    'FECHA_PAGO' AS columna_con_error,
    id_stg,
    cedula_cliente,
    fecha_pago,
    monto_pagado,
    numero_documento,
    CASE 
        WHEN fecha_pago IS NULL THEN '❌ NULL'
        WHEN TRIM(fecha_pago) = '' THEN '❌ VACÍO'
        WHEN fecha_pago !~ '^\d{4}-\d{2}-\d{2}' THEN '⚠️ FORMATO INCORRECTO (no es YYYY-MM-DD)'
        WHEN fecha_pago::timestamp IS NULL THEN '⚠️ NO SE PUEDE CONVERTIR A TIMESTAMP'
        ELSE '✅ VÁLIDO'
    END AS tipo_error,
    CASE 
        WHEN fecha_pago IS NULL THEN 'Valor NULL'
        WHEN TRIM(fecha_pago) = '' THEN 'Cadena vacía'
        WHEN fecha_pago !~ '^\d{4}-\d{2}-\d{2}' THEN 'Formato incorrecto. Esperado: YYYY-MM-DD HH:MI:SS. Actual: ' || LEFT(fecha_pago, 20)
        ELSE 'Sin error'
    END AS descripcion_error
FROM pagos_staging
WHERE fecha_pago IS NULL 
   OR TRIM(fecha_pago) = ''
   OR fecha_pago !~ '^\d{4}-\d{2}-\d{2}'
ORDER BY id_stg DESC
LIMIT 100;

-- PASO 4: Identificar registros con MONTO_PAGADO inválido o vacío
SELECT 
    'MONTO_PAGADO' AS columna_con_error,
    id_stg,
    cedula_cliente,
    fecha_pago,
    monto_pagado,
    numero_documento,
    CASE 
        WHEN monto_pagado IS NULL THEN '❌ NULL'
        WHEN TRIM(monto_pagado) = '' THEN '❌ VACÍO'
        WHEN monto_pagado !~ '^[0-9]+(\.[0-9]+)?$' THEN '⚠️ FORMATO INCORRECTO (no es numérico)'
        WHEN (monto_pagado ~ '^[0-9]+(\.[0-9]+)?$' AND TRIM(monto_pagado) != '' AND NULLIF(monto_pagado, '')::numeric < 0) THEN '⚠️ VALOR NEGATIVO'
        ELSE '✅ VÁLIDO'
    END AS tipo_error,
    CASE 
        WHEN monto_pagado IS NULL THEN 'Valor NULL'
        WHEN TRIM(monto_pagado) = '' THEN 'Cadena vacía'
        WHEN monto_pagado !~ '^[0-9]+(\.[0-9]+)?$' THEN 'Formato incorrecto. Esperado: número. Actual: ' || monto_pagado
        WHEN (monto_pagado ~ '^[0-9]+(\.[0-9]+)?$' AND TRIM(monto_pagado) != '' AND NULLIF(monto_pagado, '')::numeric < 0) THEN 'Valor negativo no permitido. Actual: ' || monto_pagado
        WHEN (monto_pagado ~ '^[0-9]+(\.[0-9]+)?$' AND TRIM(monto_pagado) != '' AND NULLIF(monto_pagado, '')::numeric = 0) THEN 'Valor 0 (válido como valor por defecto)'
        ELSE 'Sin error'
    END AS descripcion_error
FROM pagos_staging
WHERE monto_pagado IS NULL 
   OR TRIM(monto_pagado) = ''
   OR monto_pagado !~ '^[0-9]+(\.[0-9]+)?$'
   OR (monto_pagado ~ '^[0-9]+(\.[0-9]+)?$' AND TRIM(monto_pagado) != '' AND NULLIF(monto_pagado, '')::numeric < 0)
ORDER BY id_stg DESC
LIMIT 100;

-- PASO 5: Identificar registros con NUMERO_DOCUMENTO inválido o vacío
-- ⚠️ NOTA: "NO DEFINIDO" se considera válido (valor por defecto reconocido)
-- ⚠️ NOTA: No hay restricciones de formato, cualquier denominación es permitida
SELECT 
    'NUMERO_DOCUMENTO' AS columna_con_error,
    id_stg,
    cedula_cliente,
    fecha_pago,
    monto_pagado,
    numero_documento,
    CASE 
        WHEN numero_documento IS NULL THEN '❌ NULL'
        WHEN TRIM(numero_documento) = '' THEN '❌ VACÍO'
        WHEN UPPER(TRIM(numero_documento)) = 'NO DEFINIDO' THEN '✅ VÁLIDO (valor por defecto: NO DEFINIDO)'
        ELSE '✅ VÁLIDO (cualquier denominación es permitida)'
    END AS tipo_error,
    CASE 
        WHEN numero_documento IS NULL THEN 'Valor NULL'
        WHEN TRIM(numero_documento) = '' THEN 'Cadena vacía'
        WHEN UPPER(TRIM(numero_documento)) = 'NO DEFINIDO' THEN 'Valor por defecto reconocido: NO DEFINIDO'
        ELSE 'Sin error (cualquier denominación es permitida)'
    END AS descripcion_error
FROM pagos_staging
WHERE numero_documento IS NULL 
   OR TRIM(numero_documento) = ''
ORDER BY id_stg DESC
LIMIT 100;

-- PASO 6: Resumen de errores por tipo
SELECT 
    'CEDULA_CLIENTE' AS columna,
    COUNT(CASE WHEN cedula_cliente IS NULL THEN 1 END) AS error_null,
    COUNT(CASE WHEN cedula_cliente IS NOT NULL AND TRIM(cedula_cliente) = '' THEN 1 END) AS error_vacio,
    COUNT(CASE WHEN cedula_cliente IS NOT NULL AND TRIM(cedula_cliente) != '' AND LENGTH(TRIM(cedula_cliente)) < 7 AND UPPER(TRIM(cedula_cliente)) != 'Z999999999' THEN 1 END) AS error_muy_corto,
    COUNT(CASE WHEN cedula_cliente IS NOT NULL AND TRIM(cedula_cliente) != '' AND UPPER(TRIM(cedula_cliente)) != 'Z999999999' AND (
        cedula_cliente ~ '[^VEJZvejz0-9]'
        OR (cedula_cliente !~ '^[VEJZvejz][0-9]{7,9}$' AND cedula_cliente !~ '^[0-9]{7,10}$')
        OR LENGTH(TRIM(cedula_cliente)) > 10
    ) THEN 1 END) AS error_formato_invalido,
    COUNT(*) AS total_errores
FROM pagos_staging
WHERE cedula_cliente IS NULL 
   OR TRIM(cedula_cliente) = ''
   OR (UPPER(TRIM(cedula_cliente)) != 'Z999999999' AND (
       cedula_cliente ~ '[^VEJZvejz0-9]'
       OR (cedula_cliente !~ '^[VEJZvejz][0-9]{7,9}$' AND cedula_cliente !~ '^[0-9]{7,10}$')
       OR LENGTH(TRIM(cedula_cliente)) < 7
       OR LENGTH(TRIM(cedula_cliente)) > 10
   ))
UNION ALL
SELECT 
    'FECHA_PAGO' AS columna,
    COUNT(CASE WHEN fecha_pago IS NULL THEN 1 END) AS error_null,
    COUNT(CASE WHEN fecha_pago IS NOT NULL AND TRIM(fecha_pago) = '' THEN 1 END) AS error_vacio,
    COUNT(CASE WHEN fecha_pago IS NOT NULL AND TRIM(fecha_pago) != '' AND fecha_pago !~ '^\d{4}-\d{2}-\d{2}' THEN 1 END) AS error_formato_invalido,
    0 AS error_muy_corto,
    COUNT(*) AS total_errores
FROM pagos_staging
WHERE fecha_pago IS NULL 
   OR TRIM(fecha_pago) = ''
   OR fecha_pago !~ '^\d{4}-\d{2}-\d{2}'
UNION ALL
SELECT 
    'MONTO_PAGADO' AS columna,
    COUNT(CASE WHEN monto_pagado IS NULL THEN 1 END) AS error_null,
    COUNT(CASE WHEN monto_pagado IS NOT NULL AND TRIM(monto_pagado) = '' THEN 1 END) AS error_vacio,
    COUNT(CASE WHEN monto_pagado IS NOT NULL AND TRIM(monto_pagado) != '' AND monto_pagado !~ '^[0-9]+(\.[0-9]+)?$' THEN 1 END) AS error_formato_invalido,
    COUNT(CASE WHEN monto_pagado IS NOT NULL AND TRIM(monto_pagado) != '' AND monto_pagado ~ '^[0-9]+(\.[0-9]+)?$' AND NULLIF(monto_pagado, '')::numeric < 0 THEN 1 END) AS error_valor_negativo,
    COUNT(*) AS total_errores
FROM pagos_staging
WHERE monto_pagado IS NULL 
   OR TRIM(monto_pagado) = ''
   OR monto_pagado !~ '^[0-9]+(\.[0-9]+)?$'
   OR (monto_pagado ~ '^[0-9]+(\.[0-9]+)?$' AND TRIM(monto_pagado) != '' AND NULLIF(monto_pagado, '')::numeric < 0)
UNION ALL
    SELECT 
        'NUMERO_DOCUMENTO' AS columna,
        COUNT(CASE WHEN numero_documento IS NULL THEN 1 END) AS error_null,
        COUNT(CASE WHEN numero_documento IS NOT NULL AND TRIM(numero_documento) = '' THEN 1 END) AS error_vacio,
        0 AS error_formato_invalido,
        0 AS error_muy_corto,
        COUNT(*) AS total_errores
    FROM pagos_staging
    WHERE numero_documento IS NULL 
       OR TRIM(numero_documento) = '';

-- PASO 7: Registros con múltiples errores
SELECT 
    id_stg,
    cedula_cliente,
    fecha_pago,
    monto_pagado,
    numero_documento,
    CASE 
        WHEN cedula_cliente IS NULL OR TRIM(cedula_cliente) = '' OR (UPPER(TRIM(cedula_cliente)) != 'Z999999999' AND (
            cedula_cliente ~ '[^VEJZvejz0-9]'
            OR (cedula_cliente !~ '^[VEJZvejz][0-9]{7,9}$' AND cedula_cliente !~ '^[0-9]{7,10}$')
            OR LENGTH(TRIM(cedula_cliente)) < 7
            OR LENGTH(TRIM(cedula_cliente)) > 10
        )) THEN '❌'
        ELSE '✅'
    END AS cedula_cliente_ok,
    CASE 
        WHEN fecha_pago IS NULL OR TRIM(fecha_pago) = '' OR fecha_pago !~ '^\d{4}-\d{2}-\d{2}' THEN '❌'
        ELSE '✅'
    END AS fecha_pago_ok,
    CASE 
        WHEN monto_pagado IS NULL OR TRIM(monto_pagado) = '' OR monto_pagado !~ '^[0-9]+(\.[0-9]+)?$' OR (monto_pagado ~ '^[0-9]+(\.[0-9]+)?$' AND TRIM(monto_pagado) != '' AND NULLIF(monto_pagado, '')::numeric < 0) THEN '❌'
        ELSE '✅'
    END AS monto_pagado_ok,
    CASE 
        WHEN numero_documento IS NULL OR TRIM(numero_documento) = '' THEN '❌'
        ELSE '✅'
    END AS numero_documento_ok,
    (
        CASE WHEN cedula_cliente IS NULL OR TRIM(cedula_cliente) = '' OR (UPPER(TRIM(cedula_cliente)) != 'Z999999999' AND (
            cedula_cliente ~ '[^VEJZvejz0-9]'
            OR (cedula_cliente !~ '^[VEJZvejz][0-9]{7,9}$' AND cedula_cliente !~ '^[0-9]{7,10}$')
            OR LENGTH(TRIM(cedula_cliente)) < 7
            OR LENGTH(TRIM(cedula_cliente)) > 10
        )) THEN 1 ELSE 0 END +
        CASE WHEN fecha_pago IS NULL OR TRIM(fecha_pago) = '' OR fecha_pago !~ '^\d{4}-\d{2}-\d{2}' THEN 1 ELSE 0 END +
        CASE WHEN monto_pagado IS NULL OR TRIM(monto_pagado) = '' OR monto_pagado !~ '^[0-9]+(\.[0-9]+)?$' OR (monto_pagado ~ '^[0-9]+(\.[0-9]+)?$' AND TRIM(monto_pagado) != '' AND NULLIF(monto_pagado, '')::numeric < 0) THEN 1 ELSE 0 END +
        CASE WHEN numero_documento IS NULL OR TRIM(numero_documento) = '' THEN 1 ELSE 0 END
    ) AS total_errores
FROM pagos_staging
WHERE 
    (cedula_cliente IS NULL OR TRIM(cedula_cliente) = '' OR (UPPER(TRIM(cedula_cliente)) != 'Z999999999' AND (
        cedula_cliente ~ '[^VEJZvejz0-9]'
        OR (cedula_cliente !~ '^[VEJZvejz][0-9]{7,9}$' AND cedula_cliente !~ '^[0-9]{7,10}$')
        OR LENGTH(TRIM(cedula_cliente)) < 7
        OR LENGTH(TRIM(cedula_cliente)) > 10
    )))
    OR (fecha_pago IS NULL OR TRIM(fecha_pago) = '' OR fecha_pago !~ '^\d{4}-\d{2}-\d{2}')
    OR (monto_pagado IS NULL OR TRIM(monto_pagado) = '' OR monto_pagado !~ '^[0-9]+(\.[0-9]+)?$' OR (monto_pagado ~ '^[0-9]+(\.[0-9]+)?$' AND TRIM(monto_pagado) != '' AND NULLIF(monto_pagado, '')::numeric < 0))
    OR (numero_documento IS NULL OR TRIM(numero_documento) = '')
ORDER BY total_errores DESC, id_stg DESC
LIMIT 100;

-- PASO 8: Contar registros válidos vs inválidos
SELECT 
    'REGISTROS COMPLETAMENTE VÁLIDOS' AS categoria,
    COUNT(*) AS cantidad,
    ROUND((COUNT(*)::numeric / (SELECT COUNT(*) FROM pagos_staging)::numeric) * 100, 2) AS porcentaje
FROM pagos_staging
WHERE 
    cedula_cliente IS NOT NULL AND TRIM(cedula_cliente) != '' AND (
        UPPER(TRIM(cedula_cliente)) = 'Z999999999'
        OR (cedula_cliente ~ '^[VEJZvejz][0-9]{7,9}$' AND LENGTH(TRIM(cedula_cliente)) >= 8 AND LENGTH(TRIM(cedula_cliente)) <= 10)
        OR (cedula_cliente ~ '^[0-9]{7,10}$' AND LENGTH(TRIM(cedula_cliente)) >= 7 AND LENGTH(TRIM(cedula_cliente)) <= 10)
    )
    AND fecha_pago IS NOT NULL AND TRIM(fecha_pago) != '' AND fecha_pago ~ '^\d{4}-\d{2}-\d{2}'
    AND monto_pagado IS NOT NULL AND TRIM(monto_pagado) != '' AND monto_pagado ~ '^[0-9]+(\.[0-9]+)?$' AND NULLIF(monto_pagado, '')::numeric >= 0
    AND numero_documento IS NOT NULL AND TRIM(numero_documento) != ''
UNION ALL
SELECT 
    'REGISTROS CON AL MENOS UN ERROR' AS categoria,
    COUNT(*) AS cantidad,
    ROUND((COUNT(*)::numeric / (SELECT COUNT(*) FROM pagos_staging)::numeric) * 100, 2) AS porcentaje
FROM pagos_staging
WHERE 
    (cedula_cliente IS NULL OR TRIM(cedula_cliente) = '' OR (UPPER(TRIM(cedula_cliente)) != 'Z999999999' AND (
        cedula_cliente ~ '[^VEJZvejz0-9]'
        OR (cedula_cliente !~ '^[VEJZvejz][0-9]{7,9}$' AND cedula_cliente !~ '^[0-9]{7,10}$')
        OR LENGTH(TRIM(cedula_cliente)) < 7
        OR LENGTH(TRIM(cedula_cliente)) > 10
    )))
    OR (fecha_pago IS NULL OR TRIM(fecha_pago) = '' OR fecha_pago !~ '^\d{4}-\d{2}-\d{2}')
    OR (monto_pagado IS NULL OR TRIM(monto_pagado) = '' OR monto_pagado !~ '^[0-9]+(\.[0-9]+)?$' OR (monto_pagado ~ '^[0-9]+(\.[0-9]+)?$' AND TRIM(monto_pagado) != '' AND NULLIF(monto_pagado, '')::numeric < 0))
    OR (numero_documento IS NULL OR TRIM(numero_documento) = '');

-- ============================================
-- INSTRUCCIONES:
-- ============================================
-- 1. PASO 1: Resumen general de datos válidos
-- 2. PASOS 2-5: Ejemplos de registros con errores por columna (máximo 100 cada uno)
-- 3. PASO 6: Resumen de errores por tipo y columna
-- 4. PASO 7: Registros con múltiples errores (ordenados por cantidad de errores)
-- 5. PASO 8: Conteo final de registros válidos vs inválidos
-- ============================================

