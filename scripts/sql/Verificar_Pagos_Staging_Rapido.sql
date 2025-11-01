-- ============================================================================
-- VERIFICACION RAPIDA: PAGOS_STAGING
-- Script rapido para verificar pagos_staging
-- ============================================================================

-- Verificacion rapida 1: Existe la tabla?
SELECT 
    CASE 
        WHEN EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'pagos_staging')
            THEN 'SI (Tabla existe)'
        ELSE 'NO (Tabla no existe)'
    END AS tabla_existe;

-- Verificacion rapida 2: Estadisticas basicas
SELECT 
    'Total registros' AS metrica,
    COUNT(*)::VARCHAR AS valor
FROM pagos_staging

UNION ALL

SELECT 
    'Con prestamo_id',
    COUNT(CASE WHEN prestamo_id IS NOT NULL THEN 1 END)::VARCHAR
FROM pagos_staging

UNION ALL

SELECT 
    'Sin prestamo_id',
    COUNT(CASE WHEN prestamo_id IS NULL THEN 1 END)::VARCHAR
FROM pagos_staging

UNION ALL

SELECT 
    'Monto total',
    COALESCE(SUM(monto_pagado), 0)::VARCHAR
FROM pagos_staging;

-- Verificacion rapida 3: Ultimos 10 registros
SELECT 
    id,
    cedula_cliente,
    prestamo_id,
    monto_pagado,
    fecha_pago,
    estado,
    fecha_registro
FROM pagos_staging
ORDER BY fecha_registro DESC
LIMIT 10;

-- Verificacion rapida 4: Comparacion con pagos
SELECT 
    'pagos_staging' AS tabla,
    COUNT(*) AS registros,
    COALESCE(SUM(monto_pagado), 0) AS monto_total
FROM pagos_staging

UNION ALL

SELECT 
    'pagos' AS tabla,
    COUNT(*) AS registros,
    COALESCE(SUM(monto_pagado), 0) AS monto_total
FROM pagos;

