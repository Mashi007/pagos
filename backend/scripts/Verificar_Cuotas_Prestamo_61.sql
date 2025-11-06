-- ============================================================================
-- VERIFICACIÓN COMPLETA: CUOTAS DEL PRÉSTAMO #61
-- ============================================================================
-- Este script verifica el estado real de las cuotas en la base de datos
-- y compara con lo que debería mostrar el frontend

-- PASO 1: Información básica del préstamo
SELECT 
    'PASO 1: Información del Préstamo #61' AS seccion;

SELECT 
    p.id,
    p.cedula,
    p.total_financiamiento,
    p.numero_cuotas,
    p.estado AS estado_prestamo,
    p.fecha_aprobacion,
    p.fecha_base_calculo
FROM prestamos p
WHERE p.id = 61;

-- PASO 2: Verificar cuotas en la base de datos
SELECT 
    'PASO 2: Cuotas del Préstamo #61' AS seccion;

SELECT 
    c.id,
    c.numero_cuota,
    TO_CHAR(c.fecha_vencimiento, 'DD/MM/YYYY') AS fecha_vencimiento,
    c.monto_cuota,
    c.monto_capital,
    c.monto_interes,
    c.total_pagado,
    c.capital_pagado,
    c.interes_pagado,
    c.capital_pendiente,
    c.interes_pendiente,
    c.estado,
    c.dias_mora,
    c.monto_mora,
    TO_CHAR(c.fecha_pago, 'DD/MM/YYYY') AS fecha_pago,
    -- Cálculo del estado esperado
    CASE 
        WHEN c.total_pagado >= c.monto_cuota THEN 'PAGADO (total_pagado >= monto_cuota)'
        WHEN c.total_pagado > 0 AND c.fecha_vencimiento < CURRENT_DATE THEN 'ATRASADO (tiene pago parcial y está vencida)'
        WHEN c.total_pagado > 0 THEN 'PARCIAL (tiene pago parcial, no vencida)'
        WHEN c.fecha_vencimiento < CURRENT_DATE THEN 'ATRASADO (vencida sin pago)'
        ELSE 'PENDIENTE (no vencida, sin pago)'
    END AS estado_esperado,
    -- Verificación de consistencia
    CASE 
        WHEN c.estado = 'PAGADO' AND c.total_pagado < c.monto_cuota THEN '⚠️ INCONSISTENCIA: Estado PAGADO pero total_pagado < monto_cuota'
        WHEN c.estado = 'PENDIENTE' AND c.total_pagado >= c.monto_cuota THEN '⚠️ INCONSISTENCIA: Estado PENDIENTE pero total_pagado >= monto_cuota'
        WHEN c.estado != 'PAGADO' AND c.total_pagado >= c.monto_cuota THEN '⚠️ INCONSISTENCIA: Debería ser PAGADO'
        ELSE '✓ OK'
    END AS validacion_consistencia
FROM cuotas c
WHERE c.prestamo_id = 61
ORDER BY c.numero_cuota;

-- PASO 3: Resumen de estados
SELECT 
    'PASO 3: Resumen de Estados' AS seccion;

SELECT 
    c.estado,
    COUNT(*) AS cantidad,
    SUM(c.monto_cuota) AS monto_total_cuotas,
    SUM(c.total_pagado) AS monto_total_pagado,
    SUM(c.capital_pendiente + c.interes_pendiente) AS saldo_pendiente
FROM cuotas c
WHERE c.prestamo_id = 61
GROUP BY c.estado
ORDER BY c.estado;

-- PASO 4: Verificar pagos asociados al préstamo
SELECT 
    'PASO 4: Pagos Registrados para el Préstamo #61' AS seccion;

SELECT 
    p.id AS pago_id,
    TO_CHAR(p.fecha_pago, 'DD/MM/YYYY') AS fecha_pago,
    p.monto_pagado,
    p.cedula_cliente,
    p.prestamo_id,
    CASE 
        WHEN p.prestamo_id = 61 THEN '✓ Vinculado correctamente'
        WHEN p.prestamo_id IS NULL THEN '⚠️ Sin vincular'
        ELSE '⚠️ Vinculado a otro préstamo'
    END AS estado_vinculacion
FROM pagos p
WHERE p.prestamo_id = 61
   OR (p.prestamo_id IS NULL AND EXISTS (
       SELECT 1 FROM prestamos pr 
       WHERE pr.id = 61 AND pr.cedula = p.cedula_cliente
   ))
ORDER BY p.fecha_pago;

-- PASO 5: Verificar relación pagos-cuotas
SELECT 
    'PASO 5: Relación Pagos-Cuotas' AS seccion;

SELECT 
    pc.pago_id,
    pc.cuota_id,
    TO_CHAR(p.fecha_pago, 'DD/MM/YYYY') AS fecha_pago,
    p.monto_pagado,
    c.numero_cuota,
    c.monto_cuota,
    c.total_pagado,
    c.estado
FROM pago_cuotas pc
INNER JOIN pagos p ON pc.pago_id = p.id
INNER JOIN cuotas c ON pc.cuota_id = c.id
WHERE c.prestamo_id = 61
ORDER BY c.numero_cuota, p.fecha_pago;

-- PASO 6: Diagnóstico final
SELECT 
    'PASO 6: Diagnóstico Final' AS seccion;

WITH diagnostico AS (
    SELECT 
        COUNT(*) AS total_cuotas,
        COUNT(CASE WHEN c.estado = 'PENDIENTE' THEN 1 END) AS cuotas_pendientes,
        COUNT(CASE WHEN c.estado = 'PAGADO' THEN 1 END) AS cuotas_pagadas,
        COUNT(CASE WHEN c.estado = 'ATRASADO' THEN 1 END) AS cuotas_atrasadas,
        COUNT(CASE WHEN c.total_pagado >= c.monto_cuota AND c.estado != 'PAGADO' THEN 1 END) AS inconsistencias_estado,
        COUNT(CASE WHEN c.total_pagado < c.monto_cuota AND c.estado = 'PAGADO' THEN 1 END) AS inconsistencias_pago,
        COALESCE(SUM(p.monto_pagado), 0) AS total_pagado_en_pagos,
        SUM(c.total_pagado) AS total_pagado_en_cuotas
    FROM cuotas c
    LEFT JOIN pagos p ON p.prestamo_id = 61
    WHERE c.prestamo_id = 61
)
SELECT 
    total_cuotas,
    cuotas_pendientes,
    cuotas_pagadas,
    cuotas_atrasadas,
    inconsistencias_estado,
    inconsistencias_pago,
    total_pagado_en_pagos,
    total_pagado_en_cuotas,
    CASE 
        WHEN inconsistencias_estado > 0 OR inconsistencias_pago > 0 THEN '⚠️ HAY INCONSISTENCIAS - Requiere corrección'
        WHEN total_pagado_en_pagos > 0 AND total_pagado_en_cuotas = 0 THEN '⚠️ HAY PAGOS PERO NO SE APLICARON A CUOTAS'
        WHEN total_pagado_en_cuotas > 0 AND cuotas_pagadas = 0 THEN '⚠️ HAY PAGOS EN CUOTAS PERO ESTADOS NO ACTUALIZADOS'
        ELSE '✓ SISTEMA CONSISTENTE'
    END AS diagnostico_final
FROM diagnostico;

