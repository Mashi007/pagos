-- ============================================================================
-- VERIFICACION: TABLA PAGOS_STAGING
-- Verifica la tabla de staging donde están los pagos antes de migrar
-- ============================================================================

-- PASO 1: Verificar que existe la tabla pagos_staging
SELECT 
    'PASO 1: Verificar existencia de tabla pagos_staging' AS seccion;

SELECT 
    table_name,
    'EXISTE' AS estado
FROM information_schema.tables 
WHERE table_schema = 'public' 
    AND table_name = 'pagos_staging';

-- PASO 2: Estructura de la tabla pagos_staging
SELECT 
    'PASO 2: Estructura de tabla pagos_staging' AS seccion;

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

-- PASO 3: Estadisticas generales de pagos_staging
SELECT 
    'PASO 3: Estadisticas generales' AS seccion;

SELECT 
    COUNT(*) AS total_registros,
    COUNT(DISTINCT cedula_cliente) AS clientes_unicos,
    COUNT(DISTINCT prestamo_id) AS prestamos_unicos,
    COUNT(CASE WHEN prestamo_id IS NOT NULL THEN 1 END) AS registros_con_prestamo,
    COUNT(CASE WHEN prestamo_id IS NULL THEN 1 END) AS registros_sin_prestamo,
    COALESCE(SUM(monto_pagado), 0) AS monto_total,
    COALESCE(AVG(monto_pagado), 0) AS promedio_pago,
    MIN(fecha_pago) AS primer_pago,
    MAX(fecha_pago) AS ultimo_pago
FROM pagos_staging;

-- PASO 4: Primeros 20 registros de pagos_staging
SELECT 
    'PASO 4: Primeros 20 registros' AS seccion;

SELECT 
    id,
    cedula_cliente,
    prestamo_id,
    monto_pagado,
    fecha_pago,
    metodo_pago,
    referencia_pago,
    estado,
    fecha_registro,
    usuario_registro
FROM pagos_staging
ORDER BY fecha_pago DESC, fecha_registro DESC
LIMIT 20;

-- PASO 5: Comparacion entre pagos_staging y pagos
SELECT 
    'PASO 5: Comparacion pagos_staging vs pagos' AS seccion;

SELECT 
    'pagos_staging' AS tabla,
    COUNT(*) AS total_registros,
    COALESCE(SUM(monto_pagado), 0) AS monto_total
FROM pagos_staging

UNION ALL

SELECT 
    'pagos' AS tabla,
    COUNT(*) AS total_registros,
    COALESCE(SUM(monto_pagado), 0) AS monto_total
FROM pagos;

-- PASO 6: Registros en staging que no estan en pagos (posibles pendientes de migrar)
SELECT 
    'PASO 6: Registros en staging no migrados' AS seccion;

SELECT 
    ps.id AS staging_id,
    ps.cedula_cliente,
    ps.prestamo_id,
    ps.monto_pagado,
    ps.fecha_pago,
    ps.fecha_registro AS fecha_registro_staging,
    CASE 
        WHEN p.id IS NULL THEN 'NO MIGRADO'
        ELSE 'MIGRADO'
    END AS estado_migracion
FROM pagos_staging ps
LEFT JOIN pagos p ON ps.id = p.id OR (
    ps.cedula_cliente = p.cedula_cliente 
    AND ps.monto_pagado = p.monto_pagado 
    AND ps.fecha_pago = p.fecha_pago
    AND (ps.prestamo_id = p.prestamo_id OR (ps.prestamo_id IS NULL AND p.prestamo_id IS NULL))
)
WHERE p.id IS NULL
ORDER BY ps.fecha_registro DESC
LIMIT 20;

-- PASO 7: Registros duplicados entre staging y pagos
SELECT 
    'PASO 7: Verificar duplicados' AS seccion;

SELECT 
    ps.id AS staging_id,
    p.id AS pago_id,
    ps.cedula_cliente,
    ps.monto_pagado,
    ps.fecha_pago,
    'DUPLICADO' AS estado
FROM pagos_staging ps
JOIN pagos p ON (
    ps.cedula_cliente = p.cedula_cliente 
    AND ps.monto_pagado = p.monto_pagado 
    AND ps.fecha_pago = p.fecha_pago
    AND (ps.prestamo_id = p.prestamo_id OR (ps.prestamo_id IS NULL AND p.prestamo_id IS NULL))
)
LIMIT 20;

-- PASO 8: Pagos_staging por estado
SELECT 
    'PASO 8: Pagos_staging por estado' AS seccion;

SELECT 
    estado,
    COUNT(*) AS cantidad,
    COALESCE(SUM(monto_pagado), 0) AS total_monto,
    COALESCE(AVG(monto_pagado), 0) AS promedio
FROM pagos_staging
WHERE estado IS NOT NULL
GROUP BY estado
ORDER BY cantidad DESC;

-- PASO 9: Pagos_staging por metodo de pago
SELECT 
    'PASO 9: Pagos_staging por metodo de pago' AS seccion;

SELECT 
    metodo_pago,
    COUNT(*) AS cantidad,
    COALESCE(SUM(monto_pagado), 0) AS total_monto
FROM pagos_staging
WHERE metodo_pago IS NOT NULL
GROUP BY metodo_pago
ORDER BY cantidad DESC;

-- PASO 10: Pagos_staging por mes
SELECT 
    'PASO 10: Pagos_staging por mes' AS seccion;

SELECT 
    TO_CHAR(fecha_pago, 'YYYY-MM') AS mes,
    COUNT(*) AS cantidad_pagos,
    COALESCE(SUM(monto_pagado), 0) AS total_pagado,
    COALESCE(AVG(monto_pagado), 0) AS promedio_pago
FROM pagos_staging
WHERE fecha_pago IS NOT NULL
GROUP BY TO_CHAR(fecha_pago, 'YYYY-MM')
ORDER BY mes DESC
LIMIT 12;

-- PASO 11: Pagos_staging agrupados por prestamo
SELECT 
    'PASO 11: Pagos_staging por prestamo' AS seccion;

SELECT 
    prestamo_id,
    COUNT(*) AS cantidad_pagos,
    COALESCE(SUM(monto_pagado), 0) AS total_pagado,
    COALESCE(AVG(monto_pagado), 0) AS promedio_pago,
    MIN(fecha_pago) AS primer_pago,
    MAX(fecha_pago) AS ultimo_pago
FROM pagos_staging
WHERE prestamo_id IS NOT NULL
GROUP BY prestamo_id
ORDER BY total_pagado DESC
LIMIT 20;

-- PASO 12: Pagos_staging agrupados por cliente
SELECT 
    'PASO 12: Pagos_staging por cliente' AS seccion;

SELECT 
    cedula_cliente,
    COUNT(*) AS cantidad_pagos,
    COALESCE(SUM(monto_pagado), 0) AS total_pagado,
    COALESCE(AVG(monto_pagado), 0) AS promedio_pago,
    COUNT(DISTINCT prestamo_id) AS prestamos_diferentes
FROM pagos_staging
GROUP BY cedula_cliente
ORDER BY total_pagado DESC
LIMIT 20;

-- PASO 13: Verificar relacion con cuotas (si tienen prestamo_id)
SELECT 
    'PASO 13: Pagos_staging y su relacion con cuotas' AS seccion;

SELECT 
    ps.id AS staging_id,
    ps.prestamo_id,
    ps.monto_pagado,
    ps.fecha_pago,
    COUNT(c.id) AS total_cuotas_prestamo,
    COUNT(CASE WHEN c.total_pagado > 0 THEN 1 END) AS cuotas_con_pago,
    COUNT(CASE WHEN c.estado = 'PAGADO' THEN 1 END) AS cuotas_pagadas,
    COALESCE(SUM(c.total_pagado), 0) AS total_aplicado_cuotas
FROM pagos_staging ps
LEFT JOIN cuotas c ON ps.prestamo_id = c.prestamo_id
WHERE ps.prestamo_id IS NOT NULL
GROUP BY ps.id, ps.prestamo_id, ps.monto_pagado, ps.fecha_pago
ORDER BY ps.fecha_pago DESC
LIMIT 20;

-- PASO 14: Resumen final
SELECT 
    'PASO 14: Resumen final' AS seccion;

SELECT 
    'Total registros en pagos_staging' AS metrica,
    COUNT(*)::VARCHAR AS valor,
    'OK' AS estado
FROM pagos_staging

UNION ALL

SELECT 
    'Registros con prestamo_id',
    COUNT(CASE WHEN prestamo_id IS NOT NULL THEN 1 END)::VARCHAR,
    CASE 
        WHEN COUNT(CASE WHEN prestamo_id IS NOT NULL THEN 1 END) > 0 
            THEN 'OK'
        ELSE 'SIN PRESTAMOS'
    END
FROM pagos_staging

UNION ALL

SELECT 
    'Monto total en staging',
    COALESCE(SUM(monto_pagado), 0)::VARCHAR,
    'OK'
FROM pagos_staging

UNION ALL

SELECT 
    'Registros no migrados',
    COUNT(*)::VARCHAR,
    CASE 
        WHEN COUNT(*) > 0 THEN 'PENDIENTE (Hay registros por migrar)'
        ELSE 'OK (Todos migrados o tabla vacia)'
    END
FROM pagos_staging ps
LEFT JOIN pagos p ON ps.id = p.id OR (
    ps.cedula_cliente = p.cedula_cliente 
    AND ps.monto_pagado = p.monto_pagado 
    AND ps.fecha_pago = p.fecha_pago
)
WHERE p.id IS NULL;

