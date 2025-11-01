-- ============================================================================
-- VERIFICACION SEGURA: PAGOS_STAGING (MANEJA VALORES NO NUMERICOS)
-- Este script maneja valores "ERROR" o inválidos en monto_pagado
-- ============================================================================

-- PASO 1: Verificar valores inválidos en monto_pagado
SELECT 
    'PASO 1: Verificar valores invalidos en monto_pagado' AS seccion;

SELECT 
    monto_pagado,
    COUNT(*) AS cantidad,
    'VALOR INVALIDO' AS tipo
FROM pagos_staging
WHERE monto_pagado ~ '[^0-9.]' 
    OR monto_pagado IS NULL
    OR TRIM(monto_pagado) = ''
    OR UPPER(TRIM(monto_pagado)) = 'ERROR'
GROUP BY monto_pagado
ORDER BY cantidad DESC
LIMIT 20;

-- PASO 2: Comparacion simple (solo registros validos)
SELECT 
    'PASO 2: Comparacion simple (solo registros validos)' AS seccion;

SELECT 
    'pagos' AS tabla,
    COUNT(*)::VARCHAR AS total_registros,
    COALESCE(SUM(monto_pagado), 0)::VARCHAR AS monto_total
FROM pagos

UNION ALL

SELECT 
    'pagos_staging (validos)' AS tabla,
    COUNT(*)::VARCHAR,
    COALESCE(SUM(CASE 
        WHEN monto_pagado ~ '^[0-9]+\.?[0-9]*$' 
            THEN CAST(monto_pagado AS NUMERIC)
        ELSE 0
    END), 0)::VARCHAR
FROM pagos_staging
WHERE monto_pagado IS NOT NULL 
    AND TRIM(monto_pagado) != ''
    AND UPPER(TRIM(monto_pagado)) != 'ERROR'
    AND monto_pagado ~ '^[0-9]+\.?[0-9]*$';

-- PASO 3: Estadisticas de pagos_staging (solo validos)
SELECT 
    'PASO 3: Estadisticas de pagos_staging (solo registros validos)' AS seccion;

SELECT 
    COUNT(*) AS total_registros,
    COUNT(CASE 
        WHEN monto_pagado IS NOT NULL 
            AND TRIM(monto_pagado) != ''
            AND UPPER(TRIM(monto_pagado)) != 'ERROR'
            AND monto_pagado ~ '^[0-9]+\.?[0-9]*$'
        THEN 1 
    END) AS registros_validos,
    COUNT(CASE 
        WHEN monto_pagado ~ '[^0-9.]' 
            OR UPPER(TRIM(monto_pagado)) = 'ERROR'
            OR monto_pagado IS NULL
            OR TRIM(monto_pagado) = ''
        THEN 1 
    END) AS registros_invalidos,
    COUNT(DISTINCT cedula_cliente) AS clientes_unicos,
    COALESCE(SUM(CASE 
        WHEN monto_pagado ~ '^[0-9]+\.?[0-9]*$' 
            THEN CAST(monto_pagado AS NUMERIC)
        ELSE 0
    END), 0) AS monto_total_valido,
    COALESCE(AVG(CASE 
        WHEN monto_pagado ~ '^[0-9]+\.?[0-9]*$' 
            THEN CAST(monto_pagado AS NUMERIC)
    END), 0) AS promedio_pago_valido
FROM pagos_staging;

-- PASO 4: Muestra de pagos_staging (solo validos)
SELECT 
    'PASO 4: Muestra de pagos_staging (solo registros validos)' AS seccion;

SELECT 
    id_stg,
    cedula_cliente,
    CAST(monto_pagado AS NUMERIC) AS monto_pagado,
    fecha_pago,
    numero_documento
FROM pagos_staging
WHERE monto_pagado ~ '^[0-9]+\.?[0-9]*$'
    AND monto_pagado IS NOT NULL
    AND TRIM(monto_pagado) != ''
    AND UPPER(TRIM(monto_pagado)) != 'ERROR'
ORDER BY id_stg DESC
LIMIT 20;

-- PASO 5: Muestra de registros inválidos
SELECT 
    'PASO 5: Muestra de registros invalidos' AS seccion;

SELECT 
    id_stg,
    cedula_cliente,
    monto_pagado,
    fecha_pago,
    numero_documento,
    CASE 
        WHEN monto_pagado IS NULL THEN 'NULL'
        WHEN TRIM(monto_pagado) = '' THEN 'VACIO'
        WHEN UPPER(TRIM(monto_pagado)) = 'ERROR' THEN 'ERROR'
        WHEN monto_pagado ~ '[^0-9.]' THEN 'CARACTERES INVÁLIDOS'
        ELSE 'OTRO'
    END AS tipo_error
FROM pagos_staging
WHERE monto_pagado IS NULL
    OR TRIM(monto_pagado) = ''
    OR UPPER(TRIM(monto_pagado)) = 'ERROR'
    OR monto_pagado ~ '[^0-9.]'
ORDER BY id_stg DESC
LIMIT 20;

-- PASO 6: Pagos_staging validos que NO estan en pagos
SELECT 
    'PASO 6: Pagos_staging validos no migrados' AS seccion;

SELECT 
    ps.id_stg,
    ps.cedula_cliente,
    CAST(ps.monto_pagado AS NUMERIC) AS monto_pagado,
    ps.fecha_pago,
    ps.numero_documento,
    CASE 
        WHEN p.id IS NULL THEN 'NO MIGRADO'
        ELSE 'MIGRADO'
    END AS estado_migracion
FROM pagos_staging ps
LEFT JOIN pagos p ON (
    UPPER(TRIM(ps.cedula_cliente)) = UPPER(TRIM(p.cedula_cliente))
    AND CAST(ps.monto_pagado AS NUMERIC) = p.monto_pagado
    AND CAST(ps.fecha_pago AS DATE) = p.fecha_pago::DATE
)
WHERE ps.monto_pagado ~ '^[0-9]+\.?[0-9]*$'
    AND ps.monto_pagado IS NOT NULL
    AND TRIM(ps.monto_pagado) != ''
    AND UPPER(TRIM(ps.monto_pagado)) != 'ERROR'
    AND p.id IS NULL
ORDER BY ps.id_stg DESC
LIMIT 20;

-- PASO 7: Resumen final
SELECT 
    'PASO 7: Resumen final' AS seccion;

SELECT 
    'Total en pagos_staging' AS metrica,
    COUNT(*)::VARCHAR AS valor,
    'OK' AS estado
FROM pagos_staging

UNION ALL

SELECT 
    'Registros validos en staging',
    COUNT(CASE 
        WHEN monto_pagado ~ '^[0-9]+\.?[0-9]*$' 
            AND monto_pagado IS NOT NULL
            AND TRIM(monto_pagado) != ''
            AND UPPER(TRIM(monto_pagado)) != 'ERROR'
        THEN 1 
    END)::VARCHAR,
    'OK'
FROM pagos_staging

UNION ALL

SELECT 
    'Registros invalidos en staging',
    COUNT(CASE 
        WHEN monto_pagado IS NULL
            OR TRIM(monto_pagado) = ''
            OR UPPER(TRIM(monto_pagado)) = 'ERROR'
            OR monto_pagado ~ '[^0-9.]'
        THEN 1 
    END)::VARCHAR,
    CASE 
        WHEN COUNT(CASE 
            WHEN monto_pagado IS NULL
                OR TRIM(monto_pagado) = ''
                OR UPPER(TRIM(monto_pagado)) = 'ERROR'
                OR monto_pagado ~ '[^0-9.]'
            THEN 1 
        END) > 0
        THEN 'ATENCION (Hay registros con valores invalidos)'
        ELSE 'OK'
    END
FROM pagos_staging

UNION ALL

SELECT 
    'Monto total validos (staging)',
    COALESCE(SUM(CASE 
        WHEN monto_pagado ~ '^[0-9]+\.?[0-9]*$' 
            THEN CAST(monto_pagado AS NUMERIC)
        ELSE 0
    END), 0)::VARCHAR,
    'OK'
FROM pagos_staging;

