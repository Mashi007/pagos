-- ============================================================================
-- VERIFICACION RAPIDA SEGURA: PAGOS (CON PAGOS_STAGING)
-- Script seguro que primero verifica estructura
-- ============================================================================

-- Verificacion 1: Comparacion simple entre tablas
SELECT 
    'pagos' AS tabla,
    COUNT(*)::VARCHAR AS total_registros
FROM pagos

UNION ALL

SELECT 
    'pagos_staging' AS tabla,
    COUNT(*)::VARCHAR AS total_registros
FROM pagos_staging;

-- Verificacion 2: Ultimos 10 pagos (tabla principal)
SELECT 
    id AS pago_id,
    cedula_cliente,
    monto_pagado,
    fecha_pago,
    estado,
    prestamo_id,
    'pagos' AS origen
FROM pagos
ORDER BY fecha_pago DESC, fecha_registro DESC
LIMIT 10;

-- Verificacion 3: Muestra de pagos_staging (todos los campos)
SELECT 
    *,
    'pagos_staging' AS origen
FROM pagos_staging
ORDER BY 
    CASE 
        WHEN EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'pagos_staging' AND column_name = 'fecha_pago')
            THEN fecha_pago
        WHEN EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'pagos_staging' AND column_name = 'fecha_registro')
            THEN fecha_registro::date
        ELSE CURRENT_DATE
    END DESC
LIMIT 10;

-- Verificacion 4: Pagos y cuotas (solo tabla pagos)
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

