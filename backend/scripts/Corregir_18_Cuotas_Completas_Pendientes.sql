-- ================================================================
-- CORRECCIÓN ESPECÍFICA: 18 Cuotas Completas pero Estado PENDIENTE
-- ================================================================
-- Estas cuotas tienen total_pagado >= monto_cuota pero estado = PENDIENTE
-- La razón probable es que no están conciliadas o no se actualizó el estado
-- ================================================================

-- ================================================================
-- PASO 1: IDENTIFICAR LAS 18 CUOTAS
-- ================================================================
SELECT 
    'PASO 1: Identificar cuotas completas pero PENDIENTE' AS paso,
    c.id AS cuota_id,
    c.prestamo_id,
    c.numero_cuota,
    c.monto_cuota,
    c.total_pagado,
    c.estado,
    c.fecha_vencimiento,
    c.fecha_pago,
    ROUND((c.total_pagado * 100.0 / NULLIF(c.monto_cuota, 0)), 2) AS porcentaje_pagado,
    -- Verificar si hay pagos conciliados para este préstamo
    (SELECT COUNT(*) FROM pagos p WHERE p.prestamo_id = c.prestamo_id AND p.conciliado = true) AS pagos_conciliados,
    (SELECT COUNT(*) FROM pagos p WHERE p.prestamo_id = c.prestamo_id) AS total_pagos
FROM cuotas c
WHERE c.total_pagado >= c.monto_cuota
  AND c.estado = 'PENDIENTE'
ORDER BY c.prestamo_id, c.numero_cuota;

-- ================================================================
-- PASO 2: VERIFICAR CONCILIACIÓN DE PAGOS
-- ================================================================
-- Ver si los préstamos tienen pagos conciliados
SELECT 
    'PASO 2: Verificación de conciliación' AS paso,
    c.prestamo_id,
    COUNT(DISTINCT c.id) AS cuotas_completas_pendientes,
    COUNT(DISTINCT p.id) AS total_pagos_prestamo,
    COUNT(DISTINCT CASE WHEN p.conciliado = true THEN p.id END) AS pagos_conciliados,
    COUNT(DISTINCT CASE WHEN p.conciliado = false THEN p.id END) AS pagos_no_conciliados,
    SUM(p.monto_pagado) AS total_pagado_prestamo
FROM cuotas c
LEFT JOIN pagos p ON p.prestamo_id = c.prestamo_id
WHERE c.total_pagado >= c.monto_cuota
  AND c.estado = 'PENDIENTE'
GROUP BY c.prestamo_id
ORDER BY c.prestamo_id;

-- ================================================================
-- PASO 3: OPCIÓN 1 - Marcar como PAGADO si están conciliados
-- ================================================================
-- Solo marcar como PAGADO si TODOS los pagos del préstamo están conciliados
UPDATE cuotas c
SET estado = 'PAGADO',
    fecha_pago = COALESCE(
        c.fecha_pago,
        (SELECT MIN(p.fecha_pago) 
         FROM pagos p 
         WHERE p.prestamo_id = c.prestamo_id 
           AND p.fecha_pago IS NOT NULL)
    )
WHERE c.total_pagado >= c.monto_cuota
  AND c.estado = 'PENDIENTE'
  -- Verificar que TODOS los pagos del préstamo están conciliados
  AND EXISTS (
      SELECT 1 
      FROM pagos p
      WHERE p.prestamo_id = c.prestamo_id
        AND p.conciliado = true
  )
  AND NOT EXISTS (
      SELECT 1 
      FROM pagos p
      WHERE p.prestamo_id = c.prestamo_id
        AND p.conciliado = false
  );

-- Verificar cuántas se actualizaron
SELECT 
    'PASO 3: Cuotas actualizadas a PAGADO' AS paso,
    COUNT(*) AS cuotas_actualizadas
FROM cuotas
WHERE total_pagado >= monto_cuota
  AND estado = 'PAGADO';

-- ================================================================
-- PASO 4: OPCIÓN 2 - Marcar como PAGADO si NO hay pagos en tabla pagos
-- ================================================================
-- Si no hay pagos en la tabla pagos, pero la cuota está completa,
-- probablemente fueron pagos históricos o migrados
-- En este caso, marcar como PAGADO directamente
UPDATE cuotas c
SET estado = 'PAGADO',
    fecha_pago = COALESCE(
        c.fecha_pago,
        c.fecha_vencimiento -- Usar fecha de vencimiento como fecha de pago estimada
    )
WHERE c.total_pagado >= c.monto_cuota
  AND c.estado = 'PENDIENTE'
  -- No hay pagos en la tabla pagos para este préstamo
  AND NOT EXISTS (
      SELECT 1 
      FROM pagos p
      WHERE p.prestamo_id = c.prestamo_id
  );

-- Verificar cuántas se actualizaron
SELECT 
    'PASO 4: Cuotas actualizadas (sin pagos en tabla)' AS paso,
    COUNT(*) AS cuotas_actualizadas
FROM cuotas
WHERE total_pagado >= monto_cuota
  AND estado = 'PAGADO';

-- ================================================================
-- PASO 5: OPCIÓN 3 - Forzar PAGADO si total_pagado >= monto_cuota
-- ================================================================
-- ⚠️ SOLO EJECUTAR SI LAS OPCIONES 1 Y 2 NO FUNCIONARON
-- Esta opción fuerza el estado a PAGADO sin verificar conciliación
-- Útil para pagos históricos o migrados que no tienen registro en pagos
/*
UPDATE cuotas c
SET estado = 'PAGADO',
    fecha_pago = COALESCE(
        c.fecha_pago,
        c.fecha_vencimiento,
        CURRENT_DATE
    )
WHERE c.total_pagado >= c.monto_cuota
  AND c.estado = 'PENDIENTE';
*/

-- ================================================================
-- PASO 6: VERIFICACIÓN POST-CORRECCIÓN
-- ================================================================
SELECT 
    'PASO 6: Verificación final' AS paso,
    COUNT(*) AS total_cuotas_completas_pendientes,
    CASE 
        WHEN COUNT(*) = 0 THEN '✅ TODAS CORREGIDAS'
        ELSE CONCAT('⚠️ QUEDAN ', COUNT(*), ' CUOTAS PENDIENTES')
    END AS estado
FROM cuotas
WHERE total_pagado >= monto_cuota
  AND estado = 'PENDIENTE';

-- Resumen final
SELECT 
    'RESUMEN FINAL' AS tipo,
    COUNT(*) AS total_cuotas,
    COUNT(CASE WHEN estado = 'PAGADO' THEN 1 END) AS cuotas_pagadas,
    COUNT(CASE WHEN estado = 'PENDIENTE' AND total_pagado >= monto_cuota THEN 1 END) AS cuotas_completas_pendientes,
    COUNT(CASE WHEN estado = 'PENDIENTE' AND total_pagado < monto_cuota AND total_pagado > 0 THEN 1 END) AS cuotas_parciales_pendientes,
    COUNT(CASE WHEN estado = 'PENDIENTE' AND total_pagado = 0 THEN 1 END) AS cuotas_sin_pago_pendientes
FROM cuotas;

