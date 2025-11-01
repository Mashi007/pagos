-- ============================================================================
-- APLICAR PAGOS PENDIENTES A CUOTAS
-- Script para aplicar pagos que fueron registrados pero no se aplicaron a cuotas
-- IMPORTANTE: Revisar antes de ejecutar
-- ============================================================================

-- PASO 1: Identificar pagos que no se aplicaron a cuotas
SELECT 
    'PASO 1: Pagos que no se aplicaron a cuotas' AS seccion;

SELECT 
    p.id AS pago_id,
    p.prestamo_id,
    p.cedula_cliente,
    p.monto_pagado,
    p.fecha_pago,
    COUNT(c.id) AS total_cuotas,
    COUNT(CASE WHEN c.total_pagado > 0 THEN 1 END) AS cuotas_con_pago,
    COALESCE(SUM(c.total_pagado), 0) AS total_aplicado,
    CASE 
        WHEN COUNT(c.id) = 0 THEN 'ERROR (Prestamo sin cuotas)'
        WHEN COALESCE(SUM(c.total_pagado), 0) = 0 THEN 'PENDIENTE (No aplicado)'
        WHEN COALESCE(SUM(c.total_pagado), 0) < p.monto_pagado THEN 'PARCIAL'
        ELSE 'OK'
    END AS estado
FROM pagos p
LEFT JOIN cuotas c ON p.prestamo_id = c.prestamo_id
WHERE p.prestamo_id IS NOT NULL
GROUP BY p.id, p.prestamo_id, p.cedula_cliente, p.monto_pagado, p.fecha_pago
HAVING COALESCE(SUM(c.total_pagado), 0) = 0 AND p.monto_pagado > 0
ORDER BY p.fecha_pago DESC
LIMIT 20;

-- ============================================================================
-- IMPORTANTE: Los pagos se deben aplicar mediante el backend
-- Este script solo identifica los pagos pendientes
-- Para aplicarlos, usar el endpoint API o un script Python
-- ============================================================================

-- PASO 2: Resumen de pagos pendientes
SELECT 
    'PASO 2: Resumen de pagos pendientes' AS seccion;

SELECT 
    COUNT(DISTINCT p.id) AS pagos_pendientes,
    COUNT(DISTINCT p.prestamo_id) AS prestamos_afectados,
    COALESCE(SUM(p.monto_pagado), 0) AS monto_total_pendiente
FROM pagos p
LEFT JOIN cuotas c ON p.prestamo_id = c.prestamo_id
WHERE p.prestamo_id IS NOT NULL
GROUP BY p.id, p.prestamo_id, p.monto_pagado
HAVING COALESCE(SUM(c.total_pagado), 0) = 0 AND p.monto_pagado > 0;

-- NOTA: Para aplicar estos pagos, se debe:
-- 1. Usar el endpoint POST /api/v1/pagos/{pago_id}/aplicar-cuotas (si existe)
-- 2. O crear un script Python que llame a aplicar_pago_a_cuotas() para cada pago pendiente
-- 3. O ejecutar manualmente la lógica de aplicación para cada pago

