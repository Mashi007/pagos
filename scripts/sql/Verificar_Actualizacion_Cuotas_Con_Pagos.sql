-- ============================================================================
-- VERIFICACION: ACTUALIZACION DE CUOTAS CON PAGOS
-- Confirma que las cuotas se actualizan cuando se registran pagos
-- ============================================================================

-- PASO 1: Verificar que hay pagos registrados
SELECT 
    'PASO 1: Pagos registrados en el sistema' AS seccion;

SELECT 
    COUNT(*) AS total_pagos,
    COUNT(CASE WHEN prestamo_id IS NOT NULL THEN 1 END) AS pagos_con_prestamo,
    COUNT(CASE WHEN prestamo_id IS NULL THEN 1 END) AS pagos_sin_prestamo,
    COALESCE(SUM(monto_pagado), 0) AS monto_total_pagado
FROM pagos;

-- PASO 2: Verificar cuotas con pagos aplicados
SELECT 
    'PASO 2: Cuotas con pagos aplicados' AS seccion;

SELECT 
    COUNT(*) AS total_cuotas,
    COUNT(CASE WHEN total_pagado > 0 THEN 1 END) AS cuotas_con_pago,
    COUNT(CASE WHEN total_pagado = 0 THEN 1 END) AS cuotas_sin_pago,
    COUNT(CASE WHEN estado = 'PAGADO' THEN 1 END) AS cuotas_pagadas,
    COUNT(CASE WHEN estado = 'PENDIENTE' THEN 1 END) AS cuotas_pendientes,
    COUNT(CASE WHEN estado = 'ATRASADO' THEN 1 END) AS cuotas_atrasadas,
    COUNT(CASE WHEN total_pagado >= monto_cuota THEN 1 END) AS cuotas_completamente_pagadas,
    COALESCE(SUM(total_pagado), 0) AS total_pagado_cuotas,
    COALESCE(SUM(monto_cuota), 0) AS total_monto_cuotas
FROM cuotas;

-- PASO 3: Verificar consistencia: cuotas PAGADAS deben tener total_pagado >= monto_cuota
SELECT 
    'PASO 3: Consistencia estado PAGADO vs total_pagado' AS seccion;

SELECT 
    COUNT(*) AS total_cuotas_pagadas,
    COUNT(CASE WHEN total_pagado >= monto_cuota THEN 1 END) AS cuotas_correctamente_pagadas,
    COUNT(CASE WHEN total_pagado < monto_cuota THEN 1 END) AS cuotas_inconsistentes,
    CASE 
        WHEN COUNT(CASE WHEN total_pagado < monto_cuota THEN 1 END) = 0 
            THEN 'OK (Todas las cuotas PAGADAS tienen total_pagado >= monto_cuota)'
        ELSE 'ATENCION (Hay cuotas PAGADAS con total_pagado < monto_cuota)'
    END AS estado
FROM cuotas
WHERE estado = 'PAGADO';

-- PASO 4: Ejemplos de cuotas actualizadas con pagos
SELECT 
    'PASO 4: Ejemplos de cuotas con pagos aplicados' AS seccion;

SELECT 
    c.id AS cuota_id,
    c.prestamo_id,
    p.cedula AS cedula_cliente,
    c.numero_cuota,
    c.fecha_vencimiento,
    c.monto_cuota,
    c.total_pagado,
    c.capital_pagado,
    c.interes_pagado,
    c.capital_pendiente,
    c.interes_pendiente,
    c.estado,
    c.fecha_pago,
    CASE 
        WHEN c.total_pagado >= c.monto_cuota THEN 'OK (Completamente pagada)'
        WHEN c.total_pagado > 0 THEN 'Parcial'
        ELSE 'Sin pago'
    END AS estado_pago,
    CASE 
        WHEN c.total_pagado >= c.monto_cuota AND c.estado = 'PAGADO' THEN 'OK'
        WHEN c.total_pagado >= c.monto_cuota AND c.estado != 'PAGADO' THEN 'ERROR (Deberia ser PAGADO)'
        WHEN c.total_pagado < c.monto_cuota AND c.estado = 'PAGADO' THEN 'ERROR (No deberia ser PAGADO)'
        ELSE 'OK'
    END AS validacion_estado
FROM cuotas c
JOIN prestamos pr ON c.prestamo_id = pr.id
JOIN clientes p ON pr.cedula = p.cedula
WHERE c.total_pagado > 0
ORDER BY c.prestamo_id, c.numero_cuota
LIMIT 20;

-- PASO 5: Verificar pagos y su impacto en cuotas
SELECT 
    'PASO 5: Pagos y cuotas afectadas' AS seccion;

SELECT 
    p.id AS pago_id,
    p.cedula_cliente,
    p.monto_pagado,
    p.fecha_pago,
    p.prestamo_id,
    COUNT(DISTINCT c.id) AS total_cuotas_prestamo,
    COUNT(DISTINCT CASE WHEN c.total_pagado > 0 THEN c.id END) AS cuotas_con_pagos,
    COUNT(DISTINCT CASE WHEN c.estado = 'PAGADO' THEN c.id END) AS cuotas_pagadas,
    COALESCE(SUM(c.total_pagado), 0) AS total_pagado_cuotas,
    CASE 
        WHEN COUNT(DISTINCT CASE WHEN c.estado = 'PAGADO' THEN c.id END) > 0 
            THEN 'OK (Hay cuotas pagadas)'
        WHEN COUNT(DISTINCT CASE WHEN c.total_pagado > 0 THEN c.id END) > 0 
            THEN 'OK (Hay cuotas con pagos parciales)'
        ELSE 'SIN IMPACTO (No se aplicaron pagos a cuotas)'
    END AS estado
FROM pagos p
LEFT JOIN cuotas c ON p.prestamo_id = c.prestamo_id
WHERE p.prestamo_id IS NOT NULL
GROUP BY p.id, p.cedula_cliente, p.monto_pagado, p.fecha_pago, p.prestamo_id
ORDER BY p.fecha_pago DESC
LIMIT 20;

-- PASO 6: Verificar transiciones de estado PENDIENTE a PAGADO
SELECT 
    'PASO 6: Verificar cambio de estado PENDIENTE a PAGADO' AS seccion;

SELECT 
    c.prestamo_id,
    c.numero_cuota,
    c.estado,
    c.monto_cuota,
    c.total_pagado,
    c.fecha_pago,
    CASE 
        WHEN c.estado = 'PAGADO' AND c.total_pagado >= c.monto_cuota 
            THEN 'OK (Estado PAGADO correcto)'
        WHEN c.estado = 'PAGADO' AND c.total_pagado < c.monto_cuota 
            THEN 'ERROR (Estado PAGADO pero total_pagado < monto_cuota)'
        WHEN c.estado = 'PENDIENTE' AND c.total_pagado >= c.monto_cuota 
            THEN 'ERROR (Estado PENDIENTE pero total_pagado >= monto_cuota)'
        WHEN c.estado = 'PENDIENTE' AND c.total_pagado > 0 
            THEN 'OK (Estado PENDIENTE con pago parcial)'
        WHEN c.estado = 'PENDIENTE' AND c.total_pagado = 0 
            THEN 'OK (Estado PENDIENTE sin pago)'
        ELSE 'OK'
    END AS validacion
FROM cuotas c
WHERE c.total_pagado > 0 OR c.estado = 'PAGADO'
ORDER BY c.prestamo_id, c.numero_cuota
LIMIT 30;

-- PASO 7: Resumen de actualizacion
SELECT 
    'PASO 7: Resumen de actualizacion de cuotas' AS seccion;

WITH estadisticas AS (
    SELECT 
        COUNT(*) AS total_cuotas,
        COUNT(CASE WHEN total_pagado > 0 THEN 1 END) AS cuotas_con_pago,
        COUNT(CASE WHEN estado = 'PAGADO' THEN 1 END) AS cuotas_pagadas,
        COUNT(CASE WHEN estado = 'PAGADO' AND total_pagado >= monto_cuota THEN 1 END) AS cuotas_correctamente_pagadas,
        COUNT(CASE WHEN estado = 'PAGADO' AND total_pagado < monto_cuota THEN 1 END) AS cuotas_incorrectamente_pagadas
    FROM cuotas
)
SELECT 
    total_cuotas,
    cuotas_con_pago,
    cuotas_pagadas,
    cuotas_correctamente_pagadas,
    cuotas_incorrectamente_pagadas,
    CASE 
        WHEN cuotas_incorrectamente_pagadas = 0 
            THEN 'OK (Todas las cuotas PAGADAS tienen total_pagado >= monto_cuota)'
        ELSE 'ERROR (Hay cuotas PAGADAS con total_pagado < monto_cuota)'
    END AS confirmacion
FROM estadisticas;

-- PASO 8: Verificar si hay pagos registrados pero cuotas sin actualizar
SELECT 
    'PASO 8: Verificar pagos sin impacto en cuotas' AS seccion;

SELECT 
    p.id AS pago_id,
    p.prestamo_id,
    p.monto_pagado,
    p.fecha_pago,
    COUNT(c.id) AS total_cuotas,
    COALESCE(SUM(c.total_pagado), 0) AS total_pagado_en_cuotas,
    CASE 
        WHEN COALESCE(SUM(c.total_pagado), 0) = 0 AND p.monto_pagado > 0 
            THEN 'ATENCION (Pago registrado pero no aplicado a cuotas)'
        WHEN COALESCE(SUM(c.total_pagado), 0) > 0 
            THEN 'OK (Pago aplicado a cuotas)'
        ELSE 'SIN CUOTAS (Préstamo sin cuotas generadas)'
    END AS estado
FROM pagos p
LEFT JOIN cuotas c ON p.prestamo_id = c.prestamo_id
WHERE p.prestamo_id IS NOT NULL
GROUP BY p.id, p.prestamo_id, p.monto_pagado, p.fecha_pago
HAVING COALESCE(SUM(c.total_pagado), 0) = 0 AND p.monto_pagado > 0
ORDER BY p.fecha_pago DESC
LIMIT 10;

-- PASO 9: Confirmacion final
SELECT 
    'PASO 9: Confirmacion final' AS seccion;

SELECT 
    'Total cuotas en sistema' AS metrica,
    COUNT(*)::VARCHAR AS valor,
    'OK' AS estado
FROM cuotas

UNION ALL

SELECT 
    'Cuotas con estado PAGADO',
    COUNT(CASE WHEN estado = 'PAGADO' THEN 1 END)::VARCHAR,
    CASE 
        WHEN COUNT(CASE WHEN estado = 'PAGADO' AND total_pagado >= monto_cuota THEN 1 END) = 
             COUNT(CASE WHEN estado = 'PAGADO' THEN 1 END)
        THEN 'OK (Todas las PAGADAS tienen total_pagado >= monto_cuota)'
        ELSE 'ERROR (Hay PAGADAS con total_pagado < monto_cuota)'
    END
FROM cuotas

UNION ALL

SELECT 
    'Sistema actualiza cuotas con pagos',
    CASE 
        WHEN EXISTS (
            SELECT 1 FROM cuotas c
            JOIN pagos p ON c.prestamo_id = p.prestamo_id
            WHERE c.total_pagado > 0
        ) THEN 'SI'
        ELSE 'NO (No hay evidencia de actualizacion)'
    END,
    CASE 
        WHEN EXISTS (
            SELECT 1 FROM cuotas c
            JOIN pagos p ON c.prestamo_id = p.prestamo_id
            WHERE c.total_pagado > 0 AND c.estado = 'PAGADO'
        ) THEN 'OK (Confirmado: hay cuotas PAGADAS con pagos aplicados)'
        ELSE 'ATENCION (No hay evidencia de cambio de estado)'
    END;

