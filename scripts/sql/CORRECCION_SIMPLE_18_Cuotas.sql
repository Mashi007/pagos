-- ================================================================
-- CORRECCIÓN SIMPLE: 18 Cuotas Completas pero Estado PENDIENTE
-- ================================================================
-- PROBLEMA: 18 cuotas están 100% pagadas pero el estado dice "PENDIENTE"
-- SOLUCIÓN: Cambiar el estado a "PAGADO"
-- ================================================================

-- ================================================================
-- PASO 1: Ver cuántas cuotas tienen este problema
-- ================================================================
SELECT 
    'ANTES de corregir' AS momento,
    COUNT(*) AS cuotas_completas_pero_pendientes
FROM cuotas
WHERE total_pagado >= monto_cuota
  AND estado = 'PENDIENTE';

-- ================================================================
-- PASO 2: CORREGIR - Cambiar estado de PENDIENTE a PAGADO
-- ================================================================
UPDATE cuotas
SET estado = 'PAGADO',
    fecha_pago = COALESCE(fecha_pago, fecha_vencimiento, CURRENT_DATE)
WHERE total_pagado >= monto_cuota
  AND estado = 'PENDIENTE';

-- ================================================================
-- PASO 3: Verificar que se corrigió
-- ================================================================
SELECT 
    'DESPUÉS de corregir' AS momento,
    COUNT(*) AS cuotas_completas_pero_pendientes
FROM cuotas
WHERE total_pagado >= monto_cuota
  AND estado = 'PENDIENTE';

-- ================================================================
-- PASO 4: Resumen final
-- ================================================================
SELECT 
    'RESUMEN FINAL' AS tipo,
    COUNT(*) AS total_cuotas,
    COUNT(CASE WHEN estado = 'PAGADO' THEN 1 END) AS cuotas_pagadas,
    COUNT(CASE WHEN estado = 'PENDIENTE' THEN 1 END) AS cuotas_pendientes,
    COUNT(CASE WHEN total_pagado >= monto_cuota AND estado = 'PENDIENTE' THEN 1 END) AS cuotas_completas_pero_pendientes
FROM cuotas;

