-- ============================================================================
-- DIAGNOSTICO: POR QUE NO SE ACTUALIZAN LAS CUOTAS
-- Verifica la relacion entre pagos, prestamos y cuotas
-- ============================================================================

-- PASO 1: Verificar pagos con prestamo_id
SELECT 
    'PASO 1: Distribucion de pagos' AS seccion;

SELECT 
    COUNT(*) AS total_pagos,
    COUNT(CASE WHEN prestamo_id IS NOT NULL THEN 1 END) AS pagos_con_prestamo,
    COUNT(CASE WHEN prestamo_id IS NULL THEN 1 END) AS pagos_sin_prestamo,
    CASE 
        WHEN COUNT(CASE WHEN prestamo_id IS NULL THEN 1 END) > COUNT(CASE WHEN prestamo_id IS NOT NULL THEN 1 END)
            THEN 'ATENCION (Mas pagos sin prestamo que con prestamo)'
        ELSE 'OK'
    END AS estado
FROM pagos;

-- PASO 2: Pagos con prestamo_id que deberian actualizar cuotas
SELECT 
    'PASO 2: Pagos con prestamo_id y su relacion con cuotas' AS seccion;

SELECT 
    p.id AS pago_id,
    p.prestamo_id,
    p.cedula_cliente,
    p.monto_pagado,
    p.fecha_pago,
    COUNT(c.id) AS total_cuotas_prestamo,
    COUNT(CASE WHEN c.total_pagado > 0 THEN 1 END) AS cuotas_con_pago,
    COUNT(CASE WHEN c.estado = 'PAGADO' THEN 1 END) AS cuotas_pagadas,
    COALESCE(SUM(c.total_pagado), 0) AS total_aplicado_cuotas,
    CASE 
        WHEN COUNT(c.id) = 0 THEN 'ERROR (Prestamo sin cuotas generadas)'
        WHEN COALESCE(SUM(c.total_pagado), 0) = 0 AND p.monto_pagado > 0 
            THEN 'ERROR (Pago no aplicado a cuotas)'
        WHEN COALESCE(SUM(c.total_pagado), 0) > 0 
            THEN 'OK (Pago aplicado)'
        ELSE 'VERIFICAR'
    END AS estado
FROM pagos p
LEFT JOIN cuotas c ON p.prestamo_id = c.prestamo_id
WHERE p.prestamo_id IS NOT NULL
GROUP BY p.id, p.prestamo_id, p.cedula_cliente, p.monto_pagado, p.fecha_pago
ORDER BY p.fecha_pago DESC
LIMIT 20;

-- PASO 3: Prestamos con pagos pero cuotas sin actualizar
SELECT 
    'PASO 3: Prestamos con pagos pero cuotas sin actualizar' AS seccion;

SELECT 
    pr.id AS prestamo_id,
    pr.cedula,
    pr.estado AS estado_prestamo,
    COUNT(DISTINCT p.id) AS cantidad_pagos,
    COALESCE(SUM(p.monto_pagado), 0) AS total_pagado,
    COUNT(DISTINCT c.id) AS total_cuotas,
    COUNT(DISTINCT CASE WHEN c.total_pagado > 0 THEN c.id END) AS cuotas_con_pago,
    COALESCE(SUM(c.total_pagado), 0) AS total_aplicado_cuotas,
    CASE 
        WHEN COUNT(DISTINCT c.id) = 0 THEN 'ERROR (Sin cuotas generadas)'
        WHEN COALESCE(SUM(c.total_pagado), 0) = 0 AND COALESCE(SUM(p.monto_pagado), 0) > 0
            THEN 'ERROR (Pagos registrados pero cuotas no actualizadas)'
        WHEN COALESCE(SUM(c.total_pagado), 0) < COALESCE(SUM(p.monto_pagado), 0)
            THEN 'PARCIAL (No todo el pago aplicado)'
        ELSE 'OK'
    END AS estado
FROM prestamos pr
JOIN pagos p ON pr.id = p.prestamo_id
LEFT JOIN cuotas c ON pr.id = c.prestamo_id
GROUP BY pr.id, pr.cedula, pr.estado
HAVING COALESCE(SUM(c.total_pagado), 0) < COALESCE(SUM(p.monto_pagado), 0)
    OR (COALESCE(SUM(p.monto_pagado), 0) > 0 AND COUNT(DISTINCT CASE WHEN c.total_pagado > 0 THEN c.id END) = 0)
ORDER BY cantidad_pagos DESC
LIMIT 10;

-- PASO 4: Ejemplo de prestamo especifico (prestamo #61 del ejemplo)
SELECT 
    'PASO 4: Diagnostico prestamo #61' AS seccion;

SELECT 
    'Préstamo #61' AS tipo,
    pr.id AS prestamo_id,
    pr.cedula,
    pr.estado,
    pr.total_financiamiento,
    pr.numero_cuotas
FROM prestamos pr
WHERE pr.id = 61

UNION ALL

SELECT 
    'Pagos registrados',
    COUNT(DISTINCT p.id),
    NULL,
    COALESCE(SUM(p.monto_pagado), 0),
    NULL
FROM pagos p
WHERE p.prestamo_id = 61

UNION ALL

SELECT 
    'Cuotas generadas',
    COUNT(DISTINCT c.id),
    NULL,
    NULL,
    COUNT(DISTINCT c.id)
FROM cuotas c
WHERE c.prestamo_id = 61

UNION ALL

SELECT 
    'Cuotas con pagos aplicados',
    COUNT(DISTINCT CASE WHEN c.total_pagado > 0 THEN c.id END),
    NULL,
    COALESCE(SUM(c.total_pagado), 0),
    NULL
FROM cuotas c
WHERE c.prestamo_id = 61;

-- PASO 5: Detalle de pagos y cuotas del prestamo #61
SELECT 
    'PASO 5: Detalle prestamo #61 - Pagos y cuotas' AS seccion;

SELECT 
    p.id AS pago_id,
    p.monto_pagado,
    p.fecha_pago,
    p.fecha_registro,
    c.numero_cuota,
    c.monto_cuota,
    c.total_pagado,
    c.estado AS estado_cuota,
    CASE 
        WHEN c.total_pagado > 0 THEN 'OK (Tiene pago aplicado)'
        ELSE 'SIN PAGO'
    END AS validacion
FROM pagos p
LEFT JOIN cuotas c ON p.prestamo_id = c.prestamo_id
WHERE p.prestamo_id = 61
ORDER BY p.fecha_pago DESC, c.numero_cuota
LIMIT 20;
