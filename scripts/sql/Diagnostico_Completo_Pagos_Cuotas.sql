-- ============================================================================
-- DIAGNOSTICO COMPLETO: VERIFICAR POR QUE NO SE ACTUALIZAN LAS CUOTAS
-- Ejecutar en DBeaver para identificar el problema
-- ============================================================================

-- PASO 1: RESUMEN GENERAL
SELECT 
    'PASO 1: Resumen general de pagos' AS seccion;

SELECT 
    COUNT(*) AS total_pagos,
    COUNT(CASE WHEN prestamo_id IS NOT NULL THEN 1 END) AS pagos_con_prestamo,
    COUNT(CASE WHEN prestamo_id IS NULL THEN 1 END) AS pagos_sin_prestamo,
    ROUND(
        (COUNT(CASE WHEN prestamo_id IS NULL THEN 1 END)::NUMERIC / COUNT(*)::NUMERIC) * 100, 
        2
    ) AS porcentaje_sin_prestamo,
    CASE 
        WHEN COUNT(CASE WHEN prestamo_id IS NULL THEN 1 END) > COUNT(CASE WHEN prestamo_id IS NOT NULL THEN 1 END)
            THEN 'ATENCION: Mas pagos sin prestamo que con prestamo'
        WHEN COUNT(CASE WHEN prestamo_id IS NULL THEN 1 END) > 0
            THEN 'ADVERTENCIA: Hay pagos sin prestamo_id'
        ELSE 'OK'
    END AS estado
FROM pagos;

-- PASO 2: PAGOS CON PRESTAMO_ID QUE DEBERIAN HABER ACTUALIZADO CUOTAS
SELECT 
    'PASO 2: Pagos con prestamo_id y su aplicacion a cuotas' AS seccion;

SELECT 
    p.id AS pago_id,
    p.prestamo_id,
    p.cedula_cliente,
    p.monto_pagado,
    TO_CHAR(p.fecha_pago, 'DD/MM/YYYY') AS fecha_pago,
    COUNT(DISTINCT c.id) AS total_cuotas_prestamo,
    COUNT(DISTINCT CASE WHEN c.total_pagado > 0 THEN c.id END) AS cuotas_con_pago,
    COUNT(DISTINCT CASE WHEN c.estado = 'PAGADO' THEN 1 END) AS cuotas_pagadas,
    COALESCE(SUM(c.total_pagado), 0) AS total_aplicado_cuotas,
    CASE 
        WHEN COUNT(DISTINCT c.id) = 0 THEN 'ERROR (Prestamo sin cuotas generadas)'
        WHEN COALESCE(SUM(c.total_pagado), 0) = 0 AND p.monto_pagado > 0 
            THEN 'ERROR (Pago NO aplicado a cuotas)'
        WHEN COALESCE(SUM(c.total_pagado), 0) > 0 AND COALESCE(SUM(c.total_pagado), 0) < p.monto_pagado
            THEN 'PARCIAL (No todo el pago aplicado)'
        WHEN COALESCE(SUM(c.total_pagado), 0) = p.monto_pagado
            THEN 'OK (Pago completamente aplicado)'
        ELSE 'VERIFICAR'
    END AS estado_aplicacion
FROM pagos p
LEFT JOIN cuotas c ON p.prestamo_id = c.prestamo_id
WHERE p.prestamo_id IS NOT NULL
GROUP BY p.id, p.prestamo_id, p.cedula_cliente, p.monto_pagado, p.fecha_pago
ORDER BY 
    CASE 
        WHEN COALESCE(SUM(c.total_pagado), 0) = 0 AND p.monto_pagado > 0 THEN 1
        WHEN COALESCE(SUM(c.total_pagado), 0) < p.monto_pagado THEN 2
        ELSE 3
    END,
    p.fecha_pago DESC
LIMIT 30;

-- PASO 3: PRESTAMOS CON PAGOS PERO CUOTAS SIN ACTUALIZAR (CRITICO)
SELECT 
    'PASO 3: Prestamos con pagos registrados pero cuotas sin actualizar (CRITICO)' AS seccion;

SELECT 
    pr.id AS prestamo_id,
    pr.cedula,
    pr.estado AS estado_prestamo,
    pr.total_financiamiento,
    COUNT(DISTINCT p.id) AS cantidad_pagos,
    COALESCE(SUM(p.monto_pagado), 0) AS total_pagado_registrado,
    COUNT(DISTINCT c.id) AS total_cuotas,
    COUNT(DISTINCT CASE WHEN c.total_pagado > 0 THEN c.id END) AS cuotas_con_pago,
    COALESCE(SUM(c.total_pagado), 0) AS total_aplicado_cuotas,
    (COALESCE(SUM(p.monto_pagado), 0) - COALESCE(SUM(c.total_pagado), 0)) AS diferencia,
    CASE 
        WHEN COUNT(DISTINCT c.id) = 0 THEN 'ERROR (Sin cuotas generadas)'
        WHEN COALESCE(SUM(c.total_pagado), 0) = 0 AND COALESCE(SUM(p.monto_pagado), 0) > 0
            THEN 'ERROR CRITICO (Pagos NO aplicados)'
        WHEN COALESCE(SUM(c.total_pagado), 0) < COALESCE(SUM(p.monto_pagado), 0)
            THEN 'PARCIAL (No todo aplicado)'
        ELSE 'OK'
    END AS estado
FROM prestamos pr
JOIN pagos p ON pr.id = p.prestamo_id
LEFT JOIN cuotas c ON pr.id = c.prestamo_id
GROUP BY pr.id, pr.cedula, pr.estado, pr.total_financiamiento
HAVING COALESCE(SUM(c.total_pagado), 0) < COALESCE(SUM(p.monto_pagado), 0)
    OR (COALESCE(SUM(p.monto_pagado), 0) > 0 AND COUNT(DISTINCT CASE WHEN c.total_pagado > 0 THEN c.id END) = 0)
ORDER BY diferencia DESC, cantidad_pagos DESC
LIMIT 20;

-- PASO 4: DIAGNOSTICO ESPECIFICO PRESTAMO #61 (DEL EJEMPLO DEL USUARIO)
SELECT 
    'PASO 4: Diagnostico prestamo #61' AS seccion;

-- Informacion del prestamo
SELECT 
    'Informacion Prestamo' AS tipo,
    pr.id AS prestamo_id,
    pr.cedula,
    pr.estado,
    pr.total_financiamiento,
    pr.numero_cuotas,
    TO_CHAR(pr.fecha_aprobacion, 'DD/MM/YYYY') AS fecha_aprobacion,
    TO_CHAR(pr.fecha_base_calculo, 'DD/MM/YYYY') AS fecha_base_calculo
FROM prestamos pr
WHERE pr.id = 61;

-- Pagos registrados
SELECT 
    'Pagos Registrados' AS tipo,
    COUNT(DISTINCT p.id) AS cantidad,
    COALESCE(SUM(p.monto_pagado), 0) AS total_pagado
FROM pagos p
WHERE p.prestamo_id = 61;

-- Cuotas generadas
SELECT 
    'Cuotas Generadas' AS tipo,
    COUNT(DISTINCT c.id) AS total_cuotas,
    COUNT(DISTINCT CASE WHEN c.estado = 'PAGADO' THEN c.id END) AS cuotas_pagadas,
    COUNT(DISTINCT CASE WHEN c.estado = 'PENDIENTE' THEN c.id END) AS cuotas_pendientes,
    COUNT(DISTINCT CASE WHEN c.total_pagado > 0 THEN c.id END) AS cuotas_con_pago
FROM cuotas c
WHERE c.prestamo_id = 61;

-- Comparacion
SELECT 
    'Comparacion Pagos vs Cuotas' AS tipo,
    COALESCE((SELECT SUM(monto_pagado) FROM pagos WHERE prestamo_id = 61), 0) AS total_pagado,
    COALESCE((SELECT SUM(total_pagado) FROM cuotas WHERE prestamo_id = 61), 0) AS total_aplicado,
    (COALESCE((SELECT SUM(monto_pagado) FROM pagos WHERE prestamo_id = 61), 0) - 
     COALESCE((SELECT SUM(total_pagado) FROM cuotas WHERE prestamo_id = 61), 0)) AS diferencia;

-- PASO 5: DETALLE DE PAGOS Y CUOTAS DEL PRESTAMO #61
SELECT 
    'PASO 5: Detalle pagos y cuotas prestamo #61' AS seccion;

SELECT 
    'PAGOS' AS tipo_registro,
    p.id AS registro_id,
    p.monto_pagado AS monto,
    TO_CHAR(p.fecha_pago, 'DD/MM/YYYY') AS fecha,
    TO_CHAR(p.fecha_registro, 'DD/MM/YYYY HH24:MI') AS fecha_registro,
    p.estado AS estado_pago,
    NULL AS numero_cuota,
    NULL AS estado_cuota,
    NULL AS total_pagado_cuota,
    NULL AS validacion
FROM pagos p
WHERE p.prestamo_id = 61

UNION ALL

SELECT 
    'CUOTAS' AS tipo_registro,
    c.id AS registro_id,
    c.monto_cuota AS monto,
    TO_CHAR(c.fecha_vencimiento, 'DD/MM/YYYY') AS fecha,
    TO_CHAR(c.fecha_pago, 'DD/MM/YYYY') AS fecha_registro,
    NULL AS estado_pago,
    c.numero_cuota,
    c.estado AS estado_cuota,
    c.total_pagado AS total_pagado_cuota,
    CASE 
        WHEN c.total_pagado >= c.monto_cuota AND c.estado = 'PAGADO' THEN 'OK (Correctamente pagada)'
        WHEN c.total_pagado >= c.monto_cuota AND c.estado != 'PAGADO' THEN 'ERROR (Deberia ser PAGADO)'
        WHEN c.total_pagado > 0 AND c.total_pagado < c.monto_cuota THEN 'Parcial'
        WHEN c.total_pagado = 0 THEN 'Sin pago'
        ELSE 'Verificar'
    END AS validacion
FROM cuotas c
WHERE c.prestamo_id = 61
ORDER BY tipo_registro DESC, fecha DESC, numero_cuota;

-- PASO 6: RESUMEN DE PROBLEMAS DETECTADOS
SELECT 
    'PASO 6: Resumen de problemas detectados' AS seccion;

SELECT 
    'Total pagos sin prestamo_id' AS problema,
    COUNT(*) AS cantidad
FROM pagos
WHERE prestamo_id IS NULL

UNION ALL

SELECT 
    'Pagos con prestamo_id pero sin cuotas generadas',
    COUNT(DISTINCT p.id)
FROM pagos p
LEFT JOIN cuotas c ON p.prestamo_id = c.prestamo_id
WHERE p.prestamo_id IS NOT NULL
GROUP BY p.id
HAVING COUNT(c.id) = 0

UNION ALL

SELECT 
    'Pagos registrados pero NO aplicados a cuotas',
    COUNT(DISTINCT p.id)
FROM pagos p
LEFT JOIN cuotas c ON p.prestamo_id = c.prestamo_id
WHERE p.prestamo_id IS NOT NULL
GROUP BY p.id, p.monto_pagado
HAVING COALESCE(SUM(c.total_pagado), 0) = 0 AND p.monto_pagado > 0

UNION ALL

SELECT 
    'Prestamos con pagos pero cuotas sin actualizar',
    COUNT(DISTINCT pr.id)
FROM prestamos pr
JOIN pagos p ON pr.id = p.prestamo_id
LEFT JOIN cuotas c ON pr.id = c.prestamo_id
GROUP BY pr.id
HAVING COALESCE(SUM(c.total_pagado), 0) < COALESCE(SUM(p.monto_pagado), 0)
    OR (COALESCE(SUM(p.monto_pagado), 0) > 0 AND COUNT(DISTINCT CASE WHEN c.total_pagado > 0 THEN c.id END) = 0);

