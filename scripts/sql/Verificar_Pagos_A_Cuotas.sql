-- ============================================================================
-- VERIFICACION ESPECIFICA: APLICACION DE PAGOS A CUOTAS
-- Verifica que los pagos se aplican correctamente a las cuotas
-- ============================================================================

-- PASO 1: Verificar pagos y sus cuotas afectadas
SELECT 
    'PASO 1: Pagos y cuotas afectadas' AS seccion;

SELECT 
    p.id AS pago_id,
    p.prestamo_id,
    p.cedula_cliente,
    p.monto_pagado,
    p.fecha_pago,
    p.estado AS estado_pago,
    COUNT(DISTINCT c.id) AS total_cuotas,
    COUNT(DISTINCT CASE WHEN c.total_pagado > 0 THEN c.id END) AS cuotas_con_pago,
    COUNT(DISTINCT CASE WHEN c.estado = 'PAGADO' THEN 1 END) AS cuotas_pagadas,
    COALESCE(SUM(c.total_pagado), 0) AS total_aplicado,
    CASE 
        WHEN COALESCE(SUM(c.total_pagado), 0) = 0 AND p.monto_pagado > 0 
            THEN 'ATENCION (Pago no aplicado)'
        WHEN COALESCE(SUM(c.total_pagado), 0) > 0 
            THEN 'OK (Pago aplicado)'
        ELSE 'SIN CUOTAS'
    END AS estado
FROM pagos p
LEFT JOIN cuotas c ON p.prestamo_id = c.prestamo_id
WHERE p.prestamo_id IS NOT NULL
GROUP BY p.id, p.prestamo_id, p.cedula_cliente, p.monto_pagado, p.fecha_pago, p.estado
ORDER BY p.fecha_pago DESC
LIMIT 20;

-- PASO 2: Detalle de pagos y cuotas específicas
SELECT 
    'PASO 2: Detalle de pagos aplicados a cuotas' AS seccion;

SELECT 
    p.id AS pago_id,
    p.prestamo_id,
    p.monto_pagado AS monto_pago,
    p.fecha_pago AS fecha_pago_registro,
    c.numero_cuota,
    c.fecha_vencimiento,
    c.monto_cuota,
    c.total_pagado AS total_pagado_cuota,
    c.capital_pagado,
    c.interes_pagado,
    c.capital_pendiente,
    c.interes_pendiente,
    c.estado AS estado_cuota,
    c.fecha_pago AS fecha_pago_cuota,
    CASE 
        WHEN c.total_pagado >= c.monto_cuota AND c.estado = 'PAGADO' 
            THEN 'OK (Cuota completamente pagada)'
        WHEN c.total_pagado > 0 AND c.total_pagado < c.monto_cuota 
            THEN 'OK (Pago parcial)'
        WHEN c.total_pagado = 0 
            THEN 'Sin pago aplicado'
        ELSE 'Verificar'
    END AS validacion
FROM pagos p
JOIN cuotas c ON p.prestamo_id = c.prestamo_id
WHERE p.prestamo_id IS NOT NULL
    AND c.total_pagado > 0
ORDER BY p.fecha_pago DESC, c.numero_cuota
LIMIT 30;

-- PASO 3: Verificar secuencia de pagos (orden de aplicación)
SELECT 
    'PASO 3: Secuencia de pagos por prestamo' AS seccion;

SELECT 
    p.prestamo_id,
    pr.cedula AS cedula_prestamo,
    p.id AS pago_id,
    p.monto_pagado,
    p.fecha_pago,
    ROW_NUMBER() OVER (PARTITION BY p.prestamo_id ORDER BY p.fecha_pago, p.id) AS orden_pago,
    COUNT(c.id) AS cuotas_afectadas,
    COUNT(CASE WHEN c.estado = 'PAGADO' THEN 1 END) AS cuotas_pagadas_por_este_pago
FROM pagos p
JOIN prestamos pr ON p.prestamo_id = pr.id
LEFT JOIN cuotas c ON p.prestamo_id = c.prestamo_id AND c.total_pagado > 0
WHERE p.prestamo_id IS NOT NULL
GROUP BY p.prestamo_id, pr.cedula, p.id, p.monto_pagado, p.fecha_pago
ORDER BY p.prestamo_id, p.fecha_pago, p.id
LIMIT 30;

-- PASO 4: Cuotas que cambiaron de PENDIENTE a PAGADO
SELECT 
    'PASO 4: Cuotas que pasaron de PENDIENTE a PAGADO' AS seccion;

SELECT 
    c.prestamo_id,
    c.numero_cuota,
    c.monto_cuota,
    c.total_pagado,
    c.capital_pagado,
    c.interes_pagado,
    c.estado,
    c.fecha_pago,
    COUNT(p.id) AS cantidad_pagos_aplicados,
    COALESCE(SUM(p.monto_pagado), 0) AS total_pagos_registrados,
    CASE 
        WHEN c.total_pagado >= c.monto_cuota AND c.estado = 'PAGADO' 
            THEN 'OK (Correctamente pagada)'
        WHEN c.total_pagado >= c.monto_cuota AND c.estado != 'PAGADO' 
            THEN 'ERROR (Deberia ser PAGADO)'
        ELSE 'OK (Parcial)'
    END AS validacion
FROM cuotas c
LEFT JOIN pagos p ON c.prestamo_id = p.prestamo_id
WHERE c.estado = 'PAGADO'
GROUP BY c.prestamo_id, c.numero_cuota, c.monto_cuota, c.total_pagado, 
         c.capital_pagado, c.interes_pagado, c.estado, c.fecha_pago
ORDER BY c.fecha_pago DESC, c.prestamo_id, c.numero_cuota
LIMIT 20;

-- PASO 5: Pagos que completaron cuotas
SELECT 
    'PASO 5: Pagos que completaron cuotas' AS seccion;

WITH pagos_cuotas AS (
    SELECT 
        p.id AS pago_id,
        p.prestamo_id,
        p.monto_pagado,
        p.fecha_pago,
        c.id AS cuota_id,
        c.numero_cuota,
        c.total_pagado AS total_pagado_cuota,
        c.monto_cuota,
        c.estado
    FROM pagos p
    JOIN cuotas c ON p.prestamo_id = c.prestamo_id
    WHERE p.prestamo_id IS NOT NULL
        AND c.total_pagado > 0
)
SELECT 
    pago_id,
    prestamo_id,
    monto_pagado,
    fecha_pago,
    COUNT(DISTINCT cuota_id) AS cuotas_afectadas,
    COUNT(DISTINCT CASE WHEN estado = 'PAGADO' THEN cuota_id END) AS cuotas_completadas,
    SUM(CASE WHEN estado = 'PAGADO' THEN monto_cuota ELSE 0 END) AS monto_cuotas_completadas
FROM pagos_cuotas
GROUP BY pago_id, prestamo_id, monto_pagado, fecha_pago
HAVING COUNT(DISTINCT CASE WHEN estado = 'PAGADO' THEN cuota_id END) > 0
ORDER BY fecha_pago DESC
LIMIT 20;

-- PASO 6: Resumen de aplicacion de pagos
SELECT 
    'PASO 6: Resumen de aplicacion de pagos' AS seccion;

SELECT 
    COUNT(DISTINCT p.id) AS total_pagos_con_prestamo,
    COUNT(DISTINCT p.prestamo_id) AS prestamos_con_pagos,
    COUNT(DISTINCT c.id) AS cuotas_con_pagos,
    COUNT(DISTINCT CASE WHEN c.estado = 'PAGADO' THEN c.id END) AS cuotas_pagadas,
    COALESCE(SUM(p.monto_pagado), 0) AS total_pagado,
    COALESCE(SUM(c.total_pagado), 0) AS total_aplicado_cuotas,
    CASE 
        WHEN COUNT(DISTINCT CASE WHEN c.total_pagado > 0 THEN c.id END) > 0 
            THEN 'OK (Hay pagos aplicados)'
        ELSE 'SIN PAGOS APLICADOS'
    END AS estado
FROM pagos p
LEFT JOIN cuotas c ON p.prestamo_id = c.prestamo_id
WHERE p.prestamo_id IS NOT NULL;

-- PASO 7: Confirmacion final
SELECT 
    'PASO 7: Confirmacion final' AS seccion;

SELECT 
    'Pagos registrados' AS metrica,
    COUNT(*)::VARCHAR AS valor,
    'OK' AS estado
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
        ) THEN 'OK (Sistema aplicando pagos)'
        ELSE 'SIN APLICACION'
    END
FROM pagos p

UNION ALL

SELECT 
    'Cuotas con pagos aplicados',
    COUNT(CASE WHEN total_pagado > 0 THEN 1 END)::VARCHAR,
    CASE 
        WHEN COUNT(CASE WHEN total_pagado > 0 THEN 1 END) > 0 
            THEN 'OK (Hay cuotas actualizadas)'
        ELSE 'SIN CUOTAS ACTUALIZADAS'
    END
FROM cuotas

UNION ALL

SELECT 
    'Cuotas que cambiaron a PAGADO',
    COUNT(CASE WHEN estado = 'PAGADO' THEN 1 END)::VARCHAR,
    CASE 
        WHEN COUNT(CASE WHEN estado = 'PAGADO' AND total_pagado >= monto_cuota THEN 1 END) = 
             COUNT(CASE WHEN estado = 'PAGADO' THEN 1 END)
        THEN 'OK (Todas las PAGADAS correctamente)'
        ELSE 'ERROR (Hay inconsistencias)'
    END
FROM cuotas;

