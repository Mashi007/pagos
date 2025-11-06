-- ============================================================================
-- RESUMEN: VINCULACION DE PAGOS COMPLETA
-- ============================================================================

-- PASO 1: Resumen general de pagos vinculados
SELECT 
    'PASO 1: Resumen general' AS seccion;

SELECT 
    COUNT(*) AS total_pagos_en_bd,
    COUNT(CASE WHEN prestamo_id IS NOT NULL THEN 1 END) AS pagos_con_prestamo_id,
    COUNT(CASE WHEN prestamo_id IS NULL THEN 1 END) AS pagos_sin_prestamo_id,
    ROUND(
        (COUNT(CASE WHEN prestamo_id IS NOT NULL THEN 1 END)::NUMERIC / COUNT(*)::NUMERIC) * 100, 
        2
    ) AS porcentaje_vinculados
FROM pagos;

-- PASO 2: Pagos vinculados que necesitan aplicarse a cuotas
SELECT 
    'PASO 2: Pagos vinculados que necesitan aplicarse a cuotas' AS seccion;

SELECT 
    p.id AS pago_id,
    p.prestamo_id,
    p.cedula_cliente,
    p.monto_pagado,
    TO_CHAR(p.fecha_pago, 'DD/MM/YYYY') AS fecha_pago,
    COUNT(DISTINCT c.id) AS total_cuotas_prestamo,
    COUNT(DISTINCT CASE WHEN c.total_pagado > 0 THEN c.id END) AS cuotas_con_pago,
    COALESCE(SUM(c.total_pagado), 0) AS total_aplicado_cuotas,
    CASE 
        WHEN COUNT(DISTINCT c.id) = 0 THEN 'ERROR (Prestamo sin cuotas generadas)'
        WHEN COALESCE(SUM(c.total_pagado), 0) = 0 AND p.monto_pagado > 0 
            THEN 'PENDIENTE (No aplicado a cuotas)'
        WHEN COALESCE(SUM(c.total_pagado), 0) > 0 AND COALESCE(SUM(c.total_pagado), 0) < p.monto_pagado
            THEN 'PARCIAL (No todo el pago aplicado)'
        WHEN COALESCE(SUM(c.total_pagado), 0) >= p.monto_pagado
            THEN 'OK (Aplicado completamente)'
        ELSE 'VERIFICAR'
    END AS estado_aplicacion
FROM pagos p
LEFT JOIN cuotas c ON p.prestamo_id = c.prestamo_id
WHERE p.prestamo_id IS NOT NULL
GROUP BY p.id, p.prestamo_id, p.cedula_cliente, p.monto_pagado, p.fecha_pago
HAVING COALESCE(SUM(c.total_pagado), 0) = 0 AND p.monto_pagado > 0
ORDER BY p.fecha_pago DESC
LIMIT 50;

-- PASO 3: Resumen de pagos pendientes de aplicar
SELECT 
    'PASO 3: Resumen de pagos pendientes de aplicar a cuotas' AS seccion;

SELECT 
    COUNT(DISTINCT p.id) AS total_pagos_pendientes,
    COUNT(DISTINCT p.prestamo_id) AS prestamos_afectados,
    COUNT(DISTINCT p.cedula_cliente) AS clientes_afectados,
    COALESCE(SUM(p.monto_pagado), 0) AS monto_total_pendiente
FROM pagos p
LEFT JOIN cuotas c ON p.prestamo_id = c.prestamo_id
WHERE p.prestamo_id IS NOT NULL
GROUP BY p.id, p.monto_pagado
HAVING COALESCE(SUM(c.total_pagado), 0) = 0 AND p.monto_pagado > 0;

