-- ============================================================================
-- VERIFICACION SEGURA: PAGOS_STAGING
-- Script que se adapta a la estructura real de la tabla
-- ============================================================================

-- PASO 1: Verificar existencia y estructura
SELECT 
    'PASO 1: Verificar tabla y estructura' AS seccion;

SELECT 
    table_name,
    column_name,
    data_type
FROM information_schema.columns
WHERE table_schema = 'public' 
    AND table_name = 'pagos_staging'
ORDER BY ordinal_position;

-- PASO 2: Estadisticas basicas (sin asumir columnas)
SELECT 
    'PASO 2: Estadisticas basicas' AS seccion;

SELECT 
    COUNT(*) AS total_registros,
    'OK' AS estado
FROM pagos_staging;

-- PASO 3: Muestra de datos completos
SELECT 
    'PASO 3: Muestra de datos (todos los campos)' AS seccion;

SELECT * FROM pagos_staging 
ORDER BY id DESC
LIMIT 20;

-- PASO 4: Intentar estadisticas con columnas comunes
SELECT 
    'PASO 4: Estadisticas con columnas disponibles' AS seccion;

-- Esta consulta se ajustará según las columnas que realmente existan
SELECT 
    COUNT(*) AS total,
    CASE 
        WHEN EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'pagos_staging' AND column_name = 'cedula_cliente')
            THEN COUNT(DISTINCT cedula_cliente)
        WHEN EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'pagos_staging' AND column_name = 'cedula')
            THEN COUNT(DISTINCT cedula)
        ELSE 0
    END AS clientes_unicos,
    CASE 
        WHEN EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'pagos_staging' AND column_name = 'monto_pagado')
            THEN COALESCE(SUM(monto_pagado), 0)
        WHEN EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'pagos_staging' AND column_name = 'monto')
            THEN COALESCE(SUM(monto), 0)
        ELSE 0
    END AS monto_total
FROM pagos_staging;

-- PASO 5: Comparacion simple con pagos
SELECT 
    'PASO 5: Comparacion simple' AS seccion;

SELECT 
    'pagos_staging' AS tabla,
    COUNT(*) AS registros
FROM pagos_staging

UNION ALL

SELECT 
    'pagos' AS tabla,
    COUNT(*) AS registros
FROM pagos;

