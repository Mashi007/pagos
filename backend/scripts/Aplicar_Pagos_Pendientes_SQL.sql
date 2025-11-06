-- ============================================================================
-- APLICAR PAGOS PENDIENTES A CUOTAS (SQL PURO)
-- Script SQL para aplicar pagos a cuotas directamente sin Python
-- NOTA: Este script simula la lógica de aplicar_pago_a_cuotas pero en SQL
-- ============================================================================

-- PASO 1: Identificar pagos pendientes
SELECT 
    'PASO 1: Pagos pendientes de aplicar' AS seccion;

SELECT 
    p.id AS pago_id,
    p.prestamo_id,
    p.monto_pagado,
    TO_CHAR(p.fecha_pago, 'DD/MM/YYYY') AS fecha_pago,
    COUNT(DISTINCT c.id) AS total_cuotas,
    COALESCE(SUM(c.total_pagado), 0) AS total_aplicado,
    CASE 
        WHEN COUNT(DISTINCT c.id) = 0 THEN 'ERROR (Sin cuotas generadas)'
        WHEN COALESCE(SUM(c.total_pagado), 0) = 0 THEN 'PENDIENTE'
        ELSE 'PARCIAL'
    END AS estado
FROM pagos p
LEFT JOIN cuotas c ON p.prestamo_id = c.prestamo_id
WHERE p.prestamo_id IS NOT NULL
    AND p.monto_pagado > 0
GROUP BY p.id, p.prestamo_id, p.monto_pagado, p.fecha_pago
HAVING COALESCE(SUM(c.total_pagado), 0) = 0
ORDER BY p.fecha_pago ASC, p.id ASC
LIMIT 50;

-- ============================================================================
-- NOTA IMPORTANTE:
-- La aplicación de pagos a cuotas requiere lógica compleja que incluye:
-- 1. Distribución proporcional entre capital e interés
-- 2. Actualización secuencial cuota por cuota
-- 3. Manejo de pagos parciales y excedentes
-- 4. Actualización de estados (PENDIENTE -> PAGADO)
-- 
-- Por esto, se recomienda usar:
-- 1. El endpoint API: POST /api/v1/pagos/{pago_id}/aplicar-cuotas
-- 2. O el script Python: python scripts/python/Aplicar_Pagos_Pendientes.py
-- 
-- Este SQL solo sirve para identificar los pagos pendientes.
-- ============================================================================

