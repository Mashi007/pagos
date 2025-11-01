-- ============================================================================
-- VERIFICACION RAPIDA: SISTEMA DE AMORTIZACION
-- Confirma que existe la configuracion completa para generar tablas de amortizacion
-- ============================================================================

-- PASO 1: Verificar que existe la tabla cuotas
SELECT 
    'PASO 1: Verificacion de tabla cuotas' AS seccion;

SELECT 
    table_name,
    'EXISTE' AS estado
FROM information_schema.tables 
WHERE table_schema = 'public' 
    AND table_name = 'cuotas';

-- PASO 2: Verificar estructura de la tabla cuotas
SELECT 
    'PASO 2: Estructura de tabla cuotas' AS seccion;

SELECT 
    column_name,
    data_type,
    character_maximum_length,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_schema = 'public' 
    AND table_name = 'cuotas'
ORDER BY ordinal_position;

-- PASO 3: Verificar foreign key a prestamos
SELECT 
    'PASO 3: Relacion con tabla prestamos' AS seccion;

SELECT 
    tc.table_name AS tabla_origen,
    kcu.column_name AS columna_origen,
    ccu.table_name AS tabla_referencia,
    ccu.column_name AS columna_referencia,
    'EXISTE' AS estado
FROM information_schema.table_constraints AS tc
JOIN information_schema.key_column_usage AS kcu
    ON tc.constraint_name = kcu.constraint_name
JOIN information_schema.constraint_column_usage AS ccu
    ON ccu.constraint_name = tc.constraint_name
WHERE tc.constraint_type = 'FOREIGN KEY'
    AND tc.table_name = 'cuotas'
    AND ccu.table_name = 'prestamos';

-- PASO 4: Verificar indices en tabla cuotas
SELECT 
    'PASO 4: Indices en tabla cuotas' AS seccion;

SELECT 
    indexname AS nombre_indice,
    indexdef AS definicion,
    'EXISTE' AS estado
FROM pg_indexes
WHERE schemaname = 'public' 
    AND tablename = 'cuotas';

-- PASO 5: Estadisticas de cuotas generadas
SELECT 
    'PASO 5: Estadisticas de cuotas' AS seccion;

SELECT 
    COUNT(*) AS total_cuotas,
    COUNT(DISTINCT prestamo_id) AS prestamos_con_cuotas,
    COUNT(CASE WHEN estado = 'PENDIENTE' THEN 1 END) AS cuotas_pendientes,
    COUNT(CASE WHEN estado = 'PAGADO' THEN 1 END) AS cuotas_pagadas,
    COUNT(CASE WHEN estado = 'ATRASADO' THEN 1 END) AS cuotas_atrasadas,
    SUM(monto_cuota) AS total_monto_cuotas,
    AVG(monto_cuota) AS promedio_monto_cuota,
    MIN(fecha_vencimiento) AS primera_fecha_vencimiento,
    MAX(fecha_vencimiento) AS ultima_fecha_vencimiento
FROM cuotas;

-- PASO 6: Verificar que todos los prestamos aprobados tienen cuotas
SELECT 
    'PASO 6: Prestamos aprobados vs cuotas' AS seccion;

SELECT 
    COUNT(DISTINCT p.id) AS total_prestamos_aprobados,
    COUNT(DISTINCT c.prestamo_id) AS prestamos_con_cuotas,
    COUNT(DISTINCT p.id) - COUNT(DISTINCT c.prestamo_id) AS prestamos_sin_cuotas,
    CASE 
        WHEN COUNT(DISTINCT p.id) = COUNT(DISTINCT c.prestamo_id) 
            THEN 'OK (Todos tienen cuotas)'
        ELSE 'ATENCION (Hay prestamos sin cuotas)'
    END AS estado
FROM prestamos p
LEFT JOIN cuotas c ON p.id = c.prestamo_id
WHERE p.estado = 'APROBADO';

-- PASO 7: Verificar tabla pago_cuotas (relacion pagos-cuotas)
SELECT 
    'PASO 7: Verificacion tabla pago_cuotas' AS seccion;

SELECT 
    table_name,
    'EXISTE' AS estado
FROM information_schema.tables 
WHERE table_schema = 'public' 
    AND table_name = 'pago_cuotas';

-- PASO 8: Ejemplo de cuotas generadas
SELECT 
    'PASO 8: Ejemplo de cuotas generadas (5 primeros prestamos)' AS seccion;

SELECT 
    c.id AS cuota_id,
    c.prestamo_id,
    p.cedula,
    c.numero_cuota,
    c.fecha_vencimiento,
    c.monto_cuota,
    c.monto_capital,
    c.monto_interes,
    c.saldo_capital_inicial,
    c.saldo_capital_final,
    c.capital_pendiente,
    c.interes_pendiente,
    c.estado,
    p.estado AS estado_prestamo
FROM cuotas c
JOIN prestamos p ON c.prestamo_id = p.id
WHERE p.estado = 'APROBADO'
ORDER BY c.prestamo_id, c.numero_cuota
LIMIT 20;

-- PASO 9: Verificar consistencia (numero de cuotas planificado vs real)
SELECT 
    'PASO 9: Consistencia numero de cuotas' AS seccion;

SELECT 
    p.id AS prestamo_id,
    p.cedula,
    p.numero_cuotas AS cuotas_planificadas,
    COUNT(c.id) AS cuotas_reales,
    CASE 
        WHEN p.numero_cuotas = COUNT(c.id) THEN 'OK'
        WHEN COUNT(c.id) = 0 THEN 'ERROR (Sin cuotas)'
        ELSE 'INCONSISTENTE'
    END AS estado
FROM prestamos p
LEFT JOIN cuotas c ON p.id = c.prestamo_id
WHERE p.estado = 'APROBADO'
GROUP BY p.id, p.cedula, p.numero_cuotas
HAVING p.numero_cuotas != COUNT(c.id) OR COUNT(c.id) = 0
ORDER BY p.id
LIMIT 20;

-- PASO 10: Resumen final
SELECT 
    'PASO 10: Resumen final' AS seccion;

SELECT 
    'Tabla cuotas existe' AS componente,
    CASE 
        WHEN EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'cuotas')
            THEN 'OK'
        ELSE 'ERROR'
    END AS estado
UNION ALL
SELECT 
    'Relacion con prestamos',
    CASE 
        WHEN EXISTS (
            SELECT 1 FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu ON tc.constraint_name = kcu.constraint_name
            WHERE tc.table_name = 'cuotas' 
                AND kcu.column_name = 'prestamo_id'
                AND tc.constraint_type = 'FOREIGN KEY'
        )
        THEN 'OK'
        ELSE 'ERROR'
    END
UNION ALL
SELECT 
    'Cuotas generadas',
    CASE 
        WHEN (SELECT COUNT(*) FROM cuotas) > 0 THEN 'OK'
        ELSE 'SIN DATOS'
    END
UNION ALL
SELECT 
    'Todos los aprobados tienen cuotas',
    CASE 
        WHEN (
            SELECT COUNT(DISTINCT p.id) - COUNT(DISTINCT c.prestamo_id)
            FROM prestamos p
            LEFT JOIN cuotas c ON p.id = c.prestamo_id
            WHERE p.estado = 'APROBADO'
        ) = 0
        THEN 'OK'
        ELSE 'ATENCION'
    END;

