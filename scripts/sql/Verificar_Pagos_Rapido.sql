-- ============================================================================
-- VERIFICACION RAPIDA: PAGOS
-- Script simple para verificar pagos rapidamente
-- ============================================================================

-- Verificacion rapida 1: Total de pagos
SELECT 
    'Total pagos' AS metrica,
    COUNT(*)::VARCHAR AS valor
FROM pagos

UNION ALL

SELECT 
    'Pagos con prestamo',
    COUNT(CASE WHEN prestamo_id IS NOT NULL THEN 1 END)::VARCHAR
FROM pagos

UNION ALL

SELECT 
    'Monto total pagado',
    COALESCE(SUM(monto_pagado), 0)::VARCHAR
FROM pagos

UNION ALL

SELECT 
    'Pagos de hoy',
    COUNT(CASE WHEN fecha_pago::date = CURRENT_DATE THEN 1 END)::VARCHAR
FROM pagos;

-- Verificacion rapida 2: Ultimos 10 pagos
SELECT 
    id AS pago_id,
    cedula_cliente,
    monto_pagado,
    fecha_pago,
    estado,
    prestamo_id
FROM pagos
ORDER BY fecha_pago DESC, fecha_registro DESC
LIMIT 10;

-- Verificacion rapida 3: Pagos y cuotas
SELECT 
    p.id AS pago_id,
    p.prestamo_id,
    p.monto_pagado,
    p.fecha_pago,
    COUNT(c.id) AS cuotas_afectadas,
    COUNT(CASE WHEN c.total_pagado > 0 THEN 1 END) AS cuotas_con_pago,
    COUNT(CASE WHEN c.estado = 'PAGADO' THEN 1 END) AS cuotas_pagadas
FROM pagos p
LEFT JOIN cuotas c ON p.prestamo_id = c.prestamo_id
WHERE p.prestamo_id IS NOT NULL
GROUP BY p.id, p.prestamo_id, p.monto_pagado, p.fecha_pago
ORDER BY p.fecha_pago DESC
LIMIT 10;

