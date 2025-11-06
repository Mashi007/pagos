-- ============================================================================
-- VERIFICAR ESTADO REAL DE CUOTAS EN BD vs LO QUE DEBERÍA MOSTRAR FRONTEND
-- ============================================================================

-- Verificar un préstamo específico (ej: #3 que según tu query tiene 72 cuotas pagadas)
SELECT 
    'VERIFICACION PRESTAMO #3' AS seccion;

SELECT 
    c.id AS cuota_id,
    c.numero_cuota,
    TO_CHAR(c.fecha_vencimiento, 'DD/MM/YYYY') AS fecha_vencimiento,
    c.monto_cuota,
    c.total_pagado,
    c.estado AS estado_bd,
    CASE 
        WHEN c.total_pagado >= c.monto_cuota THEN 'DEBERIA SER PAGADO'
        WHEN c.total_pagado > 0 THEN 'DEBERIA SER PARCIAL/ATRASADO'
        ELSE 'DEBERIA SER PENDIENTE'
    END AS estado_esperado,
    CASE 
        WHEN c.estado = 'PAGADO' AND c.total_pagado >= c.monto_cuota THEN 'OK'
        WHEN c.estado != 'PAGADO' AND c.total_pagado >= c.monto_cuota THEN 'ERROR: Deberia ser PAGADO'
        ELSE 'VERIFICAR'
    END AS validacion
FROM cuotas c
WHERE c.prestamo_id = 3
ORDER BY c.numero_cuota
LIMIT 10;

-- Verificar préstamo #61 que el usuario está viendo
SELECT 
    'VERIFICACION PRESTAMO #61' AS seccion;

SELECT 
    c.id AS cuota_id,
    c.numero_cuota,
    TO_CHAR(c.fecha_vencimiento, 'DD/MM/YYYY') AS fecha_vencimiento,
    c.monto_cuota,
    c.total_pagado,
    c.capital_pagado,
    c.interes_pagado,
    c.estado AS estado_bd,
    c.fecha_pago,
    CASE 
        WHEN c.total_pagado >= c.monto_cuota THEN 'DEBERIA SER PAGADO'
        WHEN c.total_pagado > 0 THEN 'DEBERIA SER PARCIAL/ATRASADO'
        ELSE 'DEBERIA SER PENDIENTE (OK)'
    END AS estado_esperado
FROM cuotas c
WHERE c.prestamo_id = 61
ORDER BY c.numero_cuota;

-- Verificar si hay pagos para préstamo #61
SELECT 
    'PAGOS PARA PRESTAMO #61' AS seccion;

SELECT 
    p.id AS pago_id,
    p.monto_pagado,
    TO_CHAR(p.fecha_pago, 'DD/MM/YYYY') AS fecha_pago,
    TO_CHAR(p.fecha_registro, 'DD/MM/YYYY HH24:MI') AS fecha_registro
FROM pagos p
WHERE p.prestamo_id = 61;

