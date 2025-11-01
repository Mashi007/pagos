-- ============================================================================
-- VERIFICACION COMPLETA: SISTEMA DE PAGOS
-- Script para verificar todos los aspectos del sistema de pagos
-- ============================================================================

-- ============================================================================
-- PASO 1: VERIFICAR ESTRUCTURA DE TABLA PAGOS
-- ============================================================================
SELECT 
    'PASO 1: Estructura de tabla pagos' AS seccion;

SELECT 
    column_name,
    data_type,
    character_maximum_length,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_schema = 'public' 
    AND table_name = 'pagos'
ORDER BY ordinal_position;

-- ============================================================================
-- PASO 2: ESTADISTICAS GENERALES DE PAGOS
-- ============================================================================
SELECT 
    'PASO 2: Estadisticas generales de pagos' AS seccion;

SELECT 
    COUNT(*) AS total_pagos,
    COUNT(CASE WHEN prestamo_id IS NOT NULL THEN 1 END) AS pagos_con_prestamo,
    COUNT(CASE WHEN prestamo_id IS NULL THEN 1 END) AS pagos_sin_prestamo,
    COUNT(DISTINCT cedula_cliente) AS clientes_con_pagos,
    COUNT(DISTINCT prestamo_id) AS prestamos_con_pagos,
    COALESCE(SUM(monto_pagado), 0) AS monto_total_pagado,
    COALESCE(AVG(monto_pagado), 0) AS promedio_pago,
    MIN(fecha_pago) AS primer_pago,
    MAX(fecha_pago) AS ultimo_pago
FROM pagos;

-- ============================================================================
-- PASO 3: PAGOS POR ESTADO
-- ============================================================================
SELECT 
    'PASO 3: Pagos por estado' AS seccion;

SELECT 
    estado,
    COUNT(*) AS cantidad,
    COALESCE(SUM(monto_pagado), 0) AS total_monto,
    COALESCE(AVG(monto_pagado), 0) AS promedio_monto,
    MIN(fecha_pago) AS fecha_primer_pago,
    MAX(fecha_pago) AS fecha_ultimo_pago
FROM pagos
GROUP BY estado
ORDER BY cantidad DESC;

-- ============================================================================
-- PASO 4: PAGOS RECIENTES (Ultimos 20)
-- ============================================================================
SELECT 
    'PASO 4: Pagos recientes (Ultimos 20)' AS seccion;

SELECT 
    p.id AS pago_id,
    p.cedula_cliente,
    c.nombres AS nombre_cliente,
    p.monto_pagado,
    p.fecha_pago,
    p.estado AS estado_pago,
    p.prestamo_id,
    pr.cedula AS cedula_prestamo,
    p.metodo_pago,
    p.referencia_pago,
    p.usuario_registro,
    p.fecha_registro
FROM pagos p
LEFT JOIN clientes c ON p.cedula_cliente = c.cedula
LEFT JOIN prestamos pr ON p.prestamo_id = pr.id
ORDER BY p.fecha_pago DESC, p.fecha_registro DESC
LIMIT 20;

-- ============================================================================
-- PASO 5: PAGOS POR PRESTAMO
-- ============================================================================
SELECT 
    'PASO 5: Pagos agrupados por prestamo' AS seccion;

SELECT 
    p.prestamo_id,
    pr.cedula AS cedula_prestamo,
    COUNT(p.id) AS cantidad_pagos,
    COALESCE(SUM(p.monto_pagado), 0) AS total_pagado,
    COALESCE(AVG(p.monto_pagado), 0) AS promedio_pago,
    MIN(p.fecha_pago) AS primer_pago,
    MAX(p.fecha_pago) AS ultimo_pago,
    COUNT(DISTINCT p.cedula_cliente) AS clientes_diferentes
FROM pagos p
JOIN prestamos pr ON p.prestamo_id = pr.id
WHERE p.prestamo_id IS NOT NULL
GROUP BY p.prestamo_id, pr.cedula
ORDER BY total_pagado DESC
LIMIT 20;

-- ============================================================================
-- PASO 6: PAGOS POR CLIENTE
-- ============================================================================
SELECT 
    'PASO 6: Pagos agrupados por cliente' AS seccion;

SELECT 
    p.cedula_cliente,
    c.nombres AS nombre_cliente,
    COUNT(p.id) AS cantidad_pagos,
    COALESCE(SUM(p.monto_pagado), 0) AS total_pagado,
    COALESCE(AVG(p.monto_pagado), 0) AS promedio_pago,
    COUNT(DISTINCT p.prestamo_id) AS prestamos_diferentes,
    MIN(p.fecha_pago) AS primer_pago,
    MAX(p.fecha_pago) AS ultimo_pago
FROM pagos p
LEFT JOIN clientes c ON p.cedula_cliente = c.cedula
GROUP BY p.cedula_cliente, c.nombres
ORDER BY total_pagado DESC
LIMIT 20;

-- ============================================================================
-- PASO 7: PAGOS POR METODO DE PAGO
-- ============================================================================
SELECT 
    'PASO 7: Pagos por metodo de pago' AS seccion;

SELECT 
    metodo_pago,
    COUNT(*) AS cantidad,
    COALESCE(SUM(monto_pagado), 0) AS total_monto,
    COALESCE(AVG(monto_pagado), 0) AS promedio_monto
FROM pagos
WHERE metodo_pago IS NOT NULL
GROUP BY metodo_pago
ORDER BY cantidad DESC;

-- ============================================================================
-- PASO 8: PAGOS POR MES
-- ============================================================================
SELECT 
    'PASO 8: Pagos por mes' AS seccion;

SELECT 
    TO_CHAR(fecha_pago, 'YYYY-MM') AS mes,
    COUNT(*) AS cantidad_pagos,
    COALESCE(SUM(monto_pagado), 0) AS total_pagado,
    COALESCE(AVG(monto_pagado), 0) AS promedio_pago
FROM pagos
WHERE fecha_pago IS NOT NULL
GROUP BY TO_CHAR(fecha_pago, 'YYYY-MM')
ORDER BY mes DESC
LIMIT 12;

-- ============================================================================
-- PASO 9: VERIFICAR APLICACION DE PAGOS A CUOTAS
-- ============================================================================
SELECT 
    'PASO 9: Verificar aplicacion de pagos a cuotas' AS seccion;

SELECT 
    p.id AS pago_id,
    p.prestamo_id,
    p.cedula_cliente,
    p.monto_pagado AS monto_pago,
    p.fecha_pago,
    COUNT(c.id) AS total_cuotas_prestamo,
    COUNT(CASE WHEN c.total_pagado > 0 THEN 1 END) AS cuotas_con_pagos,
    COUNT(CASE WHEN c.estado = 'PAGADO' THEN 1 END) AS cuotas_pagadas,
    COALESCE(SUM(c.total_pagado), 0) AS total_aplicado_cuotas,
    CASE 
        WHEN COALESCE(SUM(c.total_pagado), 0) = 0 AND p.monto_pagado > 0 
            THEN 'ATENCION (Pago no aplicado a cuotas)'
        WHEN COALESCE(SUM(c.total_pagado), 0) > 0 
            THEN 'OK (Pago aplicado a cuotas)'
        ELSE 'SIN CUOTAS'
    END AS estado_aplicacion
FROM pagos p
LEFT JOIN cuotas c ON p.prestamo_id = c.prestamo_id
WHERE p.prestamo_id IS NOT NULL
GROUP BY p.id, p.prestamo_id, p.cedula_cliente, p.monto_pagado, p.fecha_pago
ORDER BY p.fecha_pago DESC
LIMIT 20;

-- ============================================================================
-- PASO 10: PAGOS SIN PRESTAMO ASOCIADO
-- ============================================================================
SELECT 
    'PASO 10: Pagos sin prestamo asociado' AS seccion;

SELECT 
    id AS pago_id,
    cedula_cliente,
    monto_pagado,
    fecha_pago,
    estado,
    metodo_pago,
    referencia_pago,
    fecha_registro
FROM pagos
WHERE prestamo_id IS NULL
ORDER BY fecha_pago DESC
LIMIT 20;

-- ============================================================================
-- PASO 11: PAGOS CON PRESTAMO PERO SIN CUOTAS
-- ============================================================================
SELECT 
    'PASO 11: Pagos con prestamo pero sin cuotas generadas' AS seccion;

SELECT 
    p.id AS pago_id,
    p.prestamo_id,
    p.cedula_cliente,
    p.monto_pagado,
    p.fecha_pago,
    COUNT(c.id) AS cuotas_generadas,
    CASE 
        WHEN COUNT(c.id) = 0 THEN 'ATENCION (Prestamo sin cuotas generadas)'
        ELSE 'OK (Prestamo tiene cuotas)'
    END AS estado
FROM pagos p
LEFT JOIN cuotas c ON p.prestamo_id = c.prestamo_id
WHERE p.prestamo_id IS NOT NULL
GROUP BY p.id, p.prestamo_id, p.cedula_cliente, p.monto_pagado, p.fecha_pago
HAVING COUNT(c.id) = 0
ORDER BY p.fecha_pago DESC
LIMIT 20;

-- ============================================================================
-- PASO 12: CONSISTENCIA: MONTO PAGO VS MONTO APLICADO A CUOTAS
-- ============================================================================
SELECT 
    'PASO 12: Consistencia monto pago vs monto aplicado' AS seccion;

WITH pagos_cuotas AS (
    SELECT 
        p.id AS pago_id,
        p.prestamo_id,
        p.monto_pagado,
        COALESCE(SUM(c.total_pagado), 0) AS total_pagado_en_cuotas
    FROM pagos p
    LEFT JOIN cuotas c ON p.prestamo_id = c.prestamo_id
    WHERE p.prestamo_id IS NOT NULL
    GROUP BY p.id, p.prestamo_id, p.monto_pagado
)
SELECT 
    pago_id,
    prestamo_id,
    monto_pagado,
    total_pagado_en_cuotas,
    monto_pagado - total_pagado_en_cuotas AS diferencia,
    CASE 
        WHEN ABS(monto_pagado - total_pagado_en_cuotas) < 0.01 
            THEN 'OK (Consistente)'
        WHEN total_pagado_en_cuotas = 0 
            THEN 'ATENCION (Pago no aplicado)'
        WHEN total_pagado_en_cuotas < monto_pagado 
            THEN 'ATENCION (Pago parcial aplicado)'
        WHEN total_pagado_en_cuotas > monto_pagado 
            THEN 'ATENCION (Aplicado mas de lo pagado)'
        ELSE 'Verificar'
    END AS estado
FROM pagos_cuotas
ORDER BY ABS(monto_pagado - total_pagado_en_cuotas) DESC
LIMIT 20;

-- ============================================================================
-- PASO 13: PAGOS POR USUARIO QUE REGISTRO
-- ============================================================================
SELECT 
    'PASO 13: Pagos por usuario que registro' AS seccion;

SELECT 
    usuario_registro,
    COUNT(*) AS cantidad_pagos,
    COALESCE(SUM(monto_pagado), 0) AS total_pagado,
    COALESCE(AVG(monto_pagado), 0) AS promedio_pago,
    MIN(fecha_registro) AS primer_registro,
    MAX(fecha_registro) AS ultimo_registro
FROM pagos
WHERE usuario_registro IS NOT NULL
GROUP BY usuario_registro
ORDER BY cantidad_pagos DESC;

-- ============================================================================
-- PASO 14: PAGOS DEL MES ACTUAL
-- ============================================================================
SELECT 
    'PASO 14: Pagos del mes actual' AS seccion;

SELECT 
    COUNT(*) AS cantidad_pagos,
    COALESCE(SUM(monto_pagado), 0) AS total_pagado,
    COALESCE(AVG(monto_pagado), 0) AS promedio_pago,
    COUNT(DISTINCT cedula_cliente) AS clientes_diferentes,
    COUNT(DISTINCT prestamo_id) AS prestamos_diferentes
FROM pagos
WHERE fecha_pago >= DATE_TRUNC('month', CURRENT_DATE)
    AND fecha_pago < DATE_TRUNC('month', CURRENT_DATE) + INTERVAL '1 month';

-- ============================================================================
-- PASO 15: PAGOS DE HOY
-- ============================================================================
SELECT 
    'PASO 15: Pagos de hoy' AS seccion;

SELECT 
    id AS pago_id,
    cedula_cliente,
    monto_pagado,
    fecha_pago,
    estado,
    prestamo_id,
    metodo_pago,
    usuario_registro
FROM pagos
WHERE fecha_pago::date = CURRENT_DATE
ORDER BY fecha_pago DESC;

-- ============================================================================
-- PASO 16: RESUMEN FINAL
-- ============================================================================
SELECT 
    'PASO 16: Resumen final' AS seccion;

SELECT 
    'Total pagos registrados' AS metrica,
    COUNT(*)::VARCHAR AS valor,
    'OK' AS estado
FROM pagos

UNION ALL

SELECT 
    'Pagos con prestamo asociado',
    COUNT(CASE WHEN prestamo_id IS NOT NULL THEN 1 END)::VARCHAR,
    CASE 
        WHEN COUNT(CASE WHEN prestamo_id IS NOT NULL THEN 1 END) > 0 
            THEN 'OK'
        ELSE 'SIN PAGOS CON PRESTAMO'
    END
FROM pagos

UNION ALL

SELECT 
    'Pagos aplicados a cuotas',
    COUNT(DISTINCT p.id)::VARCHAR,
    CASE 
        WHEN EXISTS (
            SELECT 1 FROM pagos p2
            JOIN cuotas c ON p2.prestamo_id = c.prestamo_id
            WHERE c.total_pagado > 0
        ) THEN 'OK (Hay pagos aplicados)'
        ELSE 'SIN PAGOS APLICADOS'
    END
FROM pagos

UNION ALL

SELECT 
    'Monto total pagado',
    COALESCE(SUM(monto_pagado), 0)::VARCHAR,
    'OK'
FROM pagos

UNION ALL

SELECT 
    'Sistema de pagos operativo',
    CASE 
        WHEN COUNT(*) > 0 THEN 'SI'
        ELSE 'NO (No hay pagos registrados)'
    END,
    CASE 
        WHEN COUNT(*) > 0 THEN 'OK (Sistema funcionando)'
        ELSE 'SIN DATOS'
    END
FROM pagos;

