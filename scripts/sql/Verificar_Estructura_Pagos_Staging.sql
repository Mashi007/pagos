-- ============================================================================
-- VERIFICAR ESTRUCTURA: PAGOS_STAGING
-- Primero verifica qué columnas tiene la tabla antes de consultar
-- ============================================================================

-- PASO 1: Verificar si existe la tabla
SELECT 
    'PASO 1: Verificar existencia de tabla' AS seccion;

SELECT 
    CASE 
        WHEN EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'pagos_staging')
            THEN 'SI (Tabla existe)'
        ELSE 'NO (Tabla no existe)'
    END AS tabla_existe;

-- PASO 2: Estructura completa de pagos_staging
SELECT 
    'PASO 2: Estructura de pagos_staging' AS seccion;

SELECT 
    column_name,
    data_type,
    character_maximum_length,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_schema = 'public' 
    AND table_name = 'pagos_staging'
ORDER BY ordinal_position;

-- PASO 3: Comparar estructura con tabla pagos
SELECT 
    'PASO 3: Comparar estructura con tabla pagos' AS seccion;

SELECT 
    'pagos_staging' AS tabla,
    column_name,
    data_type
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'pagos_staging'

UNION ALL

SELECT 
    'pagos' AS tabla,
    column_name,
    data_type
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'pagos'

ORDER BY tabla, column_name;

-- PASO 4: Verificar columnas clave
SELECT 
    'PASO 4: Verificar columnas clave' AS seccion;

SELECT 
    column_name,
    CASE 
        WHEN column_name IN ('cedula_cliente', 'cedula', 'cliente_cedula') THEN 'IDENTIFICACION CLIENTE'
        WHEN column_name IN ('prestamo_id', 'prestamo', 'id_prestamo') THEN 'PRESTAMO'
        WHEN column_name IN ('monto_pagado', 'monto', 'valor') THEN 'MONTO'
        WHEN column_name IN ('fecha_pago', 'fecha') THEN 'FECHA'
        ELSE 'OTRA'
    END AS tipo_columna
FROM information_schema.columns
WHERE table_schema = 'public' 
    AND table_name = 'pagos_staging'
    AND column_name IN (
        'cedula_cliente', 'cedula', 'cliente_cedula',
        'prestamo_id', 'prestamo', 'id_prestamo',
        'monto_pagado', 'monto', 'valor',
        'fecha_pago', 'fecha'
    );

-- PASO 5: Muestra de datos (usando columnas que seguramente existen)
SELECT 
    'PASO 5: Muestra de datos (primeros 10 registros)' AS seccion;

-- Consulta dinámica - ajustar según columnas encontradas
SELECT * FROM pagos_staging LIMIT 10;

