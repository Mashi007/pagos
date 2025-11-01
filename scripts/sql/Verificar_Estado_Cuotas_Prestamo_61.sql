-- ============================================================================
-- VERIFICACION: ESTADO DE CUOTAS DEL PRESTAMO #61
-- Confirma que las cuotas estan en estado PENDIENTE (correcto si no hay pagos)
-- ============================================================================

-- PASO 1: Verificar estado de todas las cuotas del préstamo #61
SELECT 
    'PASO 1: Estado de cuotas del prestamo #61' AS seccion;

SELECT 
    c.id AS cuota_id,
    c.numero_cuota,
    c.fecha_vencimiento,
    c.monto_cuota,
    c.monto_capital,
    c.monto_interes,
    c.total_pagado,
    c.capital_pagado,
    c.interes_pagado,
    c.capital_pendiente,
    c.interes_pendiente,
    c.estado,
    c.fecha_pago,
    CASE 
        WHEN c.total_pagado = 0 THEN 'OK (Sin pagos - Estado PENDIENTE es correcto)'
        WHEN c.total_pagado > 0 AND c.total_pagado < c.monto_cuota THEN 'Pago parcial (Estado puede ser PENDIENTE o ATRASADO)'
        WHEN c.total_pagado >= c.monto_cuota AND c.estado = 'PAGADO' THEN 'OK (Completamente pagada)'
        WHEN c.total_pagado >= c.monto_cuota AND c.estado != 'PAGADO' THEN 'ERROR (Deberia ser PAGADO)'
        ELSE 'OK'
    END AS validacion
FROM cuotas c
WHERE c.prestamo_id = 61
ORDER BY c.numero_cuota;

-- PASO 2: Resumen de estados del préstamo #61
SELECT 
    'PASO 2: Resumen de estados' AS seccion;

SELECT 
    estado,
    COUNT(*) AS cantidad,
    SUM(monto_cuota) AS total_monto,
    SUM(total_pagado) AS total_pagado,
    SUM(capital_pendiente + interes_pendiente) AS total_pendiente,
    CASE 
        WHEN estado = 'PENDIENTE' AND SUM(total_pagado) = 0 
            THEN 'OK (Pendiente sin pagos - Correcto)'
        WHEN estado = 'PAGADO' AND SUM(total_pagado) >= SUM(monto_cuota)
            THEN 'OK (Pagado completamente - Correcto)'
        ELSE 'Verificar'
    END AS validacion
FROM cuotas
WHERE prestamo_id = 61
GROUP BY estado
ORDER BY estado;

-- PASO 3: Verificar si hay pagos registrados para el préstamo #61
SELECT 
    'PASO 3: Pagos registrados para el prestamo #61' AS seccion;

SELECT 
    p.id AS pago_id,
    p.cedula_cliente,
    p.monto_pagado,
    p.fecha_pago,
    p.estado AS estado_pago,
    COUNT(c.id) AS cuotas_afectadas,
    SUM(c.total_pagado) AS total_aplicado_cuotas
FROM pagos p
LEFT JOIN cuotas c ON p.prestamo_id = c.prestamo_id AND c.total_pagado > 0
WHERE p.prestamo_id = 61
GROUP BY p.id, p.cedula_cliente, p.monto_pagado, p.fecha_pago, p.estado
ORDER BY p.fecha_pago DESC;

-- PASO 4: Confirmacion final
SELECT 
    'PASO 4: Confirmacion final' AS seccion;

SELECT 
    'Total cuotas del prestamo #61' AS metrica,
    COUNT(*)::VARCHAR AS valor,
    'OK' AS estado
FROM cuotas
WHERE prestamo_id = 61

UNION ALL

SELECT 
    'Cuotas en estado PENDIENTE',
    COUNT(CASE WHEN estado = 'PENDIENTE' THEN 1 END)::VARCHAR,
    CASE 
        WHEN COUNT(CASE WHEN estado = 'PENDIENTE' AND total_pagado = 0 THEN 1 END) = 
             COUNT(CASE WHEN estado = 'PENDIENTE' THEN 1 END)
        THEN 'OK (Todas las PENDIENTES sin pagos - Correcto)'
        ELSE 'Verificar'
    END
FROM cuotas
WHERE prestamo_id = 61

UNION ALL

SELECT 
    'Cuotas con pagos aplicados',
    COUNT(CASE WHEN total_pagado > 0 THEN 1 END)::VARCHAR,
    CASE 
        WHEN COUNT(CASE WHEN total_pagado > 0 THEN 1 END) = 0 
            THEN 'OK (Sin pagos - Por eso estan PENDIENTES)'
        ELSE 'OK (Hay pagos aplicados)'
    END
FROM cuotas
WHERE prestamo_id = 61

UNION ALL

SELECT 
    'Estado actual vs pagos',
    CASE 
        WHEN COUNT(CASE WHEN total_pagado = 0 THEN 1 END) = COUNT(*)
            THEN 'Todas sin pagos - Estado PENDIENTE es CORRECTO'
        WHEN COUNT(CASE WHEN total_pagado >= monto_cuota AND estado = 'PAGADO' THEN 1 END) > 0
            THEN 'Hay cuotas pagadas correctamente'
        ELSE 'Verificar consistencia'
    END,
    CASE 
        WHEN COUNT(CASE WHEN total_pagado = 0 AND estado = 'PENDIENTE' THEN 1 END) = COUNT(*)
            THEN 'OK (Correcto: Sin pagos = PENDIENTE)'
        ELSE 'Verificar'
    END
FROM cuotas
WHERE prestamo_id = 61;

