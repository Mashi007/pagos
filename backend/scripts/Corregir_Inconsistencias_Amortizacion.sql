-- ================================================================
-- CORRECCIÓN: Inconsistencias en Estado de Amortización
-- ================================================================
-- Este script corrige:
-- 1. Cuotas con total_pagado >= monto_cuota pero estado PENDIENTE
-- 2. Cuotas con total_pagado < monto_cuota pero estado PAGADO
-- 3. Cuotas sin registro en pago_cuotas pero con total_pagado > 0
-- ================================================================

-- ================================================================
-- PASO 1: IDENTIFICAR PROBLEMAS
-- ================================================================
-- Cuotas con total_pagado >= monto_cuota pero estado PENDIENTE
SELECT 
    'PROBLEMA 1: Cuotas completas pero estado PENDIENTE' AS problema,
    COUNT(*) AS cantidad,
    SUM(monto_cuota) AS total_monto,
    SUM(total_pagado) AS total_pagado
FROM cuotas
WHERE total_pagado >= monto_cuota 
  AND estado = 'PENDIENTE';

-- Cuotas con total_pagado < monto_cuota pero estado PAGADO
SELECT 
    'PROBLEMA 2: Cuotas parciales pero estado PAGADO' AS problema,
    COUNT(*) AS cantidad,
    SUM(monto_cuota) AS total_monto,
    SUM(total_pagado) AS total_pagado
FROM cuotas
WHERE total_pagado < monto_cuota 
  AND estado = 'PAGADO';

-- Cuotas con total_pagado > 0 pero sin registro en pago_cuotas
SELECT 
    'PROBLEMA 3: Cuotas con pagos pero sin registro en pago_cuotas' AS problema,
    COUNT(*) AS cantidad,
    SUM(total_pagado) AS total_pagado_sin_registro
FROM cuotas c
WHERE c.total_pagado > 0
  AND NOT EXISTS (
      SELECT 1 FROM pago_cuotas pc WHERE pc.cuota_id = c.id
  );

-- ================================================================
-- PASO 2: CORREGIR ESTADO - Cuotas completas pero PENDIENTE
-- ================================================================
-- ⚠️ IMPORTANTE: Solo marcar como PAGADO si TODOS los pagos están conciliados
-- Si no están conciliados, mantener PENDIENTE pero registrar el problema

-- OPCIÓN 2.1: Cuotas con pagos conciliados → Marcar como PAGADO
UPDATE cuotas c
SET estado = 'PAGADO',
    fecha_pago = COALESCE(
        fecha_pago,
        (SELECT MIN(p.fecha_pago) 
         FROM pagos p 
         WHERE p.prestamo_id = c.prestamo_id 
           AND p.fecha_pago IS NOT NULL)
    )
WHERE c.total_pagado >= c.monto_cuota
  AND c.estado = 'PENDIENTE'
  AND EXISTS (
      -- Verificar que hay pagos conciliados para este préstamo
      SELECT 1 
      FROM pagos p
      WHERE p.prestamo_id = c.prestamo_id
        AND p.conciliado = true
  )
  AND NOT EXISTS (
      -- No actualizar si hay pagos NO conciliados
      SELECT 1 
      FROM pagos p
      WHERE p.prestamo_id = c.prestamo_id
        AND p.conciliado = false
  );

-- OPCIÓN 2.2: Cuotas sin pagos en tabla pagos (pagos históricos/migrados) → Marcar como PAGADO
-- Si total_pagado >= monto_cuota pero no hay registros en pagos, probablemente son pagos históricos
UPDATE cuotas c
SET estado = 'PAGADO',
    fecha_pago = COALESCE(
        c.fecha_pago,
        c.fecha_vencimiento, -- Usar fecha de vencimiento como referencia
        CURRENT_DATE
    )
WHERE c.total_pagado >= c.monto_cuota
  AND c.estado = 'PENDIENTE'
  AND NOT EXISTS (
      -- No hay pagos en la tabla pagos para este préstamo
      SELECT 1 
      FROM pagos p
      WHERE p.prestamo_id = c.prestamo_id
  );

-- ================================================================
-- PASO 3: CORREGIR ESTADO - Cuotas parciales pero PAGADO
-- ================================================================
UPDATE cuotas c
SET estado = CASE 
    WHEN c.fecha_vencimiento < CURRENT_DATE THEN 'PARCIAL'
    ELSE 'PENDIENTE'
END
WHERE c.total_pagado < c.monto_cuota
  AND c.total_pagado > 0
  AND c.estado = 'PAGADO';

-- ================================================================
-- PASO 4: CORREGIR ESTADO - Cuotas sin pagos pero PAGADO
-- ================================================================
UPDATE cuotas c
SET estado = CASE 
    WHEN c.fecha_vencimiento < CURRENT_DATE THEN 'ATRASADO'
    ELSE 'PENDIENTE'
END
WHERE c.total_pagado = 0
  AND c.estado = 'PAGADO';

-- ================================================================
-- PASO 5: VERIFICAR CUOTAS CON PAGOS PERO SIN REGISTRO EN pago_cuotas
-- ================================================================
-- ⚠️ NOTA: Estas cuotas pueden haber sido actualizadas directamente
-- sin pasar por la función aplicar_pago_a_cuotas()
-- 
-- OPCIONES:
-- 1. Crear registros en pago_cuotas basándose en los pagos del préstamo
-- 2. Dejar como están (si los pagos fueron aplicados manualmente)
--
-- Por ahora, solo identificamos el problema para análisis posterior

-- Crear una vista temporal para análisis
CREATE OR REPLACE VIEW cuotas_sin_pago_cuotas AS
SELECT 
    c.id AS cuota_id,
    c.prestamo_id,
    c.numero_cuota,
    c.total_pagado,
    c.monto_cuota,
    c.estado,
    (SELECT COUNT(*) FROM pagos p WHERE p.prestamo_id = c.prestamo_id) AS cantidad_pagos_prestamo,
    (SELECT SUM(monto_pagado) FROM pagos p WHERE p.prestamo_id = c.prestamo_id) AS total_pagos_prestamo
FROM cuotas c
WHERE c.total_pagado > 0
  AND NOT EXISTS (
      SELECT 1 FROM pago_cuotas pc WHERE pc.cuota_id = c.id
  );

-- ================================================================
-- PASO 6: VERIFICACIÓN POST-CORRECCIÓN
-- ================================================================
-- Verificar que los estados ahora son coherentes
SELECT 
    'VERIFICACIÓN POST-CORRECCIÓN' AS paso,
    CASE 
        WHEN total_pagado >= monto_cuota THEN 'COMPLETO (>=100%)'
        WHEN total_pagado > 0 THEN 'PARCIAL (>0% y <100%)'
        ELSE 'SIN PAGO (0%)'
    END AS categoria_pago,
    estado,
    COUNT(*) AS cantidad
FROM cuotas
GROUP BY 
    CASE 
        WHEN total_pagado >= monto_cuota THEN 'COMPLETO (>=100%)'
        WHEN total_pagado > 0 THEN 'PARCIAL (>0% y <100%)'
        ELSE 'SIN PAGO (0%)'
    END,
    estado
ORDER BY categoria_pago, estado;

-- ================================================================
-- PASO 7: REPORTE DE CORRECCIONES APLICADAS
-- ================================================================
SELECT 
    'RESUMEN DE CORRECCIONES' AS tipo,
    COUNT(*) AS total_cuotas,
    COUNT(CASE WHEN estado = 'PAGADO' THEN 1 END) AS cuotas_pagadas,
    COUNT(CASE WHEN estado = 'PENDIENTE' THEN 1 END) AS cuotas_pendientes,
    COUNT(CASE WHEN estado = 'PARCIAL' THEN 1 END) AS cuotas_parciales,
    COUNT(CASE WHEN estado = 'ATRASADO' THEN 1 END) AS cuotas_atrasadas,
    COUNT(CASE WHEN fecha_pago IS NOT NULL THEN 1 END) AS cuotas_con_fecha_pago,
    SUM(CASE WHEN total_pagado >= monto_cuota THEN 1 ELSE 0 END) AS cuotas_completas,
    SUM(CASE WHEN total_pagado > 0 AND total_pagado < monto_cuota THEN 1 ELSE 0 END) AS cuotas_parciales_pago,
    SUM(CASE WHEN total_pagado = 0 THEN 1 ELSE 0 END) AS cuotas_sin_pago
FROM cuotas;

