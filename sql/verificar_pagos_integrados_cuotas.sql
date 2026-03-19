-- Verificar si todos los pagos (con préstamo y monto > 0) están integrados a sus cuotas
-- Integración = existencia de al menos un registro en cuota_pagos por pago.
-- Tablas: pagos, cuota_pagos (cuota_id, pago_id, monto_aplicado), cuotas.

-- =============================================================================
-- 1. Resumen: pagos que deberían estar aplicados vs cuántos tienen integración
-- =============================================================================
-- Solo se exigen en cuotas los pagos con prestamo_id y monto_pagado > 0.
SELECT
    COUNT(*) AS total_pagos_con_prestamo_y_monto,
    COUNT(*) FILTER (WHERE EXISTS (
        SELECT 1 FROM cuota_pagos cp WHERE cp.pago_id = p.id
    )) AS integrados_a_cuotas,
    COUNT(*) FILTER (WHERE NOT EXISTS (
        SELECT 1 FROM cuota_pagos cp WHERE cp.pago_id = p.id
    )) AS no_integrados,
    COUNT(*) FILTER (WHERE EXISTS (SELECT 1 FROM cuota_pagos cp WHERE cp.pago_id = p.id)) = COUNT(*)
        AS todos_integrados
FROM pagos p
WHERE p.prestamo_id IS NOT NULL
  AND p.monto_pagado > 0;

-- =============================================================================
-- 2. Listado de pagos NO integrados (tienen préstamo y monto pero sin cuota_pagos)
-- =============================================================================
SELECT
    p.id          AS pago_id,
    p.prestamo_id,
    p.cedula      AS cedula_cliente,
    p.fecha_pago,
    p.monto_pagado,
    p.numero_documento,
    p.referencia_pago,
    p.conciliado,
    p.estado
FROM pagos p
WHERE p.prestamo_id IS NOT NULL
  AND p.monto_pagado > 0
  AND NOT EXISTS (SELECT 1 FROM cuota_pagos cp WHERE cp.pago_id = p.id)
ORDER BY p.fecha_pago DESC, p.id DESC;

-- =============================================================================
-- 3. Desfase de monto: pagos donde lo aplicado en cuota_pagos ≠ monto_pagado
-- =============================================================================
WITH aplicado_por_pago AS (
    SELECT
        pago_id,
        SUM(monto_aplicado) AS total_aplicado
    FROM cuota_pagos
    GROUP BY pago_id
)
SELECT
    p.id          AS pago_id,
    p.prestamo_id,
    p.monto_pagado,
    COALESCE(a.total_aplicado, 0) AS total_aplicado_cuotas,
    (p.monto_pagado - COALESCE(a.total_aplicado, 0)) AS desfase
FROM pagos p
LEFT JOIN aplicado_por_pago a ON a.pago_id = p.id
WHERE p.prestamo_id IS NOT NULL
  AND p.monto_pagado > 0
  AND (ABS(COALESCE(a.total_aplicado, 0) - p.monto_pagado) > 0.01)  -- tolerancia 1 céntimo
ORDER BY p.id;

-- =============================================================================
-- 4. Conteo por préstamo: cuántos pagos integrados vs no integrados
-- =============================================================================
SELECT
    p.prestamo_id,
    COUNT(*) AS total_pagos,
    COUNT(*) FILTER (WHERE EXISTS (SELECT 1 FROM cuota_pagos cp WHERE cp.pago_id = p.id)) AS integrados,
    COUNT(*) FILTER (WHERE NOT EXISTS (SELECT 1 FROM cuota_pagos cp WHERE cp.pago_id = p.id)) AS no_integrados
FROM pagos p
WHERE p.prestamo_id IS NOT NULL
  AND p.monto_pagado > 0
GROUP BY p.prestamo_id
HAVING COUNT(*) FILTER (WHERE NOT EXISTS (SELECT 1 FROM cuota_pagos cp WHERE cp.pago_id = p.id)) > 0
ORDER BY no_integrados DESC;
