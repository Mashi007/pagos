-- ============================================================================
-- 🔧 RECONCILIACIÓN CON TOLERANCIAS AMPLIADAS
-- ============================================================================
-- Objetivo: Vincular los 2,099 pagos que no se vincularon por tolerancias estrictas
-- Tolerancias: ±60 días, 50% diferencia de monto
-- ============================================================================

-- PASO 1: Vincular pagos por cédula, fecha (±60 días) y monto (tolerancia 50%)
-- IMPORTANTE: Vincular a la cuota MÁS ANTIGUA pendiente primero
-- Permitir múltiples pagos a la misma cuota (abonos)
-- NO excluir cuotas PAGADAS (pueden estar mal marcadas por migración)
UPDATE pagos pa
SET 
    prestamo_id = c.prestamo_id,
    numero_cuota = c.numero_cuota
FROM (
    -- Subquery para obtener la cuota más antigua pendiente para cada pago
    SELECT DISTINCT ON (pa.id)
        pa.id as pago_id,
        c.prestamo_id,
        c.numero_cuota,
        c.fecha_vencimiento,
        c.monto_cuota,
        c.estado as cuota_estado
    FROM pagos pa
    INNER JOIN prestamos p ON p.cedula = pa.cedula AND p.estado = 'APROBADO'
    INNER JOIN cuotas c ON c.prestamo_id = p.id
    WHERE pa.activo = true
      AND (pa.prestamo_id IS NULL OR pa.numero_cuota IS NULL)
      AND DATE(pa.fecha_pago) BETWEEN c.fecha_vencimiento - INTERVAL '60 days' 
                                   AND c.fecha_vencimiento + INTERVAL '60 days'
      AND ABS(pa.monto_pagado - c.monto_cuota) <= (c.monto_cuota * 0.5)  -- Tolerancia 50%
    ORDER BY pa.id, 
             c.fecha_vencimiento ASC,  -- Más antigua primero
             CASE c.estado 
                 WHEN 'PENDIENTE' THEN 1
                 WHEN 'PARCIAL' THEN 2
                 WHEN 'PAGADO' THEN 3
                 ELSE 4
             END,  -- Priorizar PENDIENTE, luego PARCIAL, luego PAGADO
             ABS(pa.monto_pagado - c.monto_cuota) ASC  -- Más cercano en monto
) c
WHERE pa.id = c.pago_id
  AND pa.activo = true
  AND (pa.prestamo_id IS NULL OR pa.numero_cuota IS NULL);

-- PASO 2: Verificar cuántos se vincularon
SELECT 
    COUNT(*) as pagos_vinculados,
    COUNT(DISTINCT prestamo_id) as prestamos_afectados,
    SUM(monto_pagado) as monto_total
FROM pagos
WHERE activo = true
  AND prestamo_id IS NOT NULL
  AND numero_cuota IS NOT NULL
  AND monto_pagado > 0;

-- PASO 3: Actualizar total_pagado en cuotas después de vincular
-- IMPORTANTE: Sumar TODOS los pagos (abonos) para cada cuota
-- Estado: PAGADO si total_pagado >= monto_cuota, PARCIAL si > 0, PENDIENTE si = 0
UPDATE cuotas c
SET 
    total_pagado = COALESCE(
        (SELECT SUM(pa.monto_pagado)
         FROM pagos pa
         WHERE pa.prestamo_id = c.prestamo_id
           AND pa.numero_cuota = c.numero_cuota
           AND pa.activo = true
           AND pa.monto_pagado > 0),
        0
    ),
    estado = CASE 
        WHEN COALESCE(
            (SELECT SUM(pa.monto_pagado)
             FROM pagos pa
             WHERE pa.prestamo_id = c.prestamo_id
               AND pa.numero_cuota = c.numero_cuota
               AND pa.activo = true
               AND pa.monto_pagado > 0),
            0
        ) >= c.monto_cuota THEN 'PAGADO'
        WHEN COALESCE(
            (SELECT SUM(pa.monto_pagado)
             FROM pagos pa
             WHERE pa.prestamo_id = c.prestamo_id
               AND pa.numero_cuota = c.numero_cuota
               AND pa.activo = true
               AND pa.monto_pagado > 0),
            0
        ) > 0 THEN 'PARCIAL'
        ELSE 'PENDIENTE'
    END,
    fecha_pago = CASE 
        WHEN COALESCE(
            (SELECT SUM(pa.monto_pagado)
             FROM pagos pa
             WHERE pa.prestamo_id = c.prestamo_id
               AND pa.numero_cuota = c.numero_cuota
               AND pa.activo = true
               AND pa.monto_pagado > 0),
            0
        ) >= c.monto_cuota 
        AND c.fecha_pago IS NULL THEN
            (SELECT MIN(DATE(pa.fecha_pago))
             FROM pagos pa
             WHERE pa.prestamo_id = c.prestamo_id
               AND pa.numero_cuota = c.numero_cuota
               AND pa.activo = true
               AND pa.monto_pagado > 0)
        ELSE c.fecha_pago
    END
WHERE EXISTS (
    SELECT 1
    FROM prestamos p
    WHERE p.id = c.prestamo_id
      AND p.estado = 'APROBADO'
)
  AND EXISTS (
      SELECT 1
      FROM pagos pa
      WHERE pa.prestamo_id = c.prestamo_id
        AND pa.numero_cuota = c.numero_cuota
        AND pa.activo = true
        AND pa.monto_pagado > 0
  );

-- PASO 4: Resumen final
SELECT 
    COUNT(*) as total_pagos_vinculados,
    COUNT(DISTINCT prestamo_id) as prestamos_afectados,
    SUM(monto_pagado) as monto_total
FROM pagos
WHERE activo = true
  AND prestamo_id IS NOT NULL
  AND numero_cuota IS NOT NULL
  AND monto_pagado > 0;

SELECT 
    COUNT(*) as cuotas_con_pagos,
    SUM(total_pagado) as monto_total_pagado,
    COUNT(CASE WHEN c.estado = 'PAGADO' THEN 1 END) as cuotas_pagadas,
    COUNT(CASE WHEN c.estado = 'PARCIAL' THEN 1 END) as cuotas_parciales
FROM cuotas c
INNER JOIN prestamos p ON c.prestamo_id = p.id
WHERE p.estado = 'APROBADO'
  AND c.total_pagado > 0;

