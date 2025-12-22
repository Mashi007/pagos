-- ============================================================================
-- SCRIPT PARA VERIFICAR CONCILIACIÓN DE CUOTAS DESPUÉS DE MIGRACIÓN
-- ============================================================================
-- Identifica cuotas que tienen total_pagado >= monto_cuota pero sus pagos
-- no están conciliados, y proporciona queries para corregirlas
-- ============================================================================

-- 1. RESUMEN GENERAL DE CONCILIACIÓN
-- ============================================================================
SELECT 
    'RESUMEN GENERAL' as tipo,
    COUNT(DISTINCT c.id) as total_cuotas_pagadas,
    COUNT(DISTINCT CASE WHEN c.estado = 'PAGADO' THEN c.id END) as cuotas_estado_pagado,
    COUNT(DISTINCT CASE WHEN c.total_pagado >= c.monto_cuota AND c.estado != 'PAGADO' THEN c.id END) as cuotas_pagadas_sin_estado,
    COUNT(DISTINCT c.prestamo_id) as prestamos_afectados
FROM cuotas c
INNER JOIN prestamos p ON c.prestamo_id = p.id
WHERE p.estado = 'APROBADO'
  AND c.total_pagado >= c.monto_cuota
  AND c.total_pagado > 0;

-- 2. CUOTAS CON PAGOS SIN CONCILIAR
-- ============================================================================
SELECT 
    'CUOTAS CON PAGOS SIN CONCILIAR' as tipo,
    c.id as cuota_id,
    c.prestamo_id,
    c.numero_cuota,
    c.total_pagado,
    c.monto_cuota,
    c.estado,
    COUNT(p.id) as total_pagos,
    COUNT(CASE WHEN p.conciliado = true THEN 1 END) as pagos_conciliados,
    COUNT(CASE WHEN p.conciliado = false OR p.conciliado IS NULL THEN 1 END) as pagos_sin_conciliar,
    STRING_AGG(p.id::text, ', ' ORDER BY p.id) as ids_pagos_sin_conciliar
FROM cuotas c
INNER JOIN prestamos pr ON c.prestamo_id = pr.id
LEFT JOIN pagos p ON p.prestamo_id = c.prestamo_id 
    AND p.activo = true
    AND p.numero_documento IS NOT NULL
    AND p.numero_documento != ''
WHERE pr.estado = 'APROBADO'
  AND c.total_pagado >= c.monto_cuota
  AND c.total_pagado > 0
GROUP BY c.id, c.prestamo_id, c.numero_cuota, c.total_pagado, c.monto_cuota, c.estado
HAVING COUNT(CASE WHEN p.conciliado = false OR p.conciliado IS NULL THEN 1 END) > 0
ORDER BY c.prestamo_id, c.numero_cuota
LIMIT 50;

-- 3. PRÉSTAMOS CON PAGOS SIN CONCILIAR
-- ============================================================================
SELECT 
    'PRESTAMOS CON PAGOS SIN CONCILIAR' as tipo,
    p.id as prestamo_id,
    p.cedula,
    COUNT(DISTINCT c.id) as cuotas_pagadas_sin_conciliar,
    COUNT(DISTINCT pag.id) as total_pagos_sin_conciliar,
    SUM(pag.monto_pagado) as monto_total_sin_conciliar
FROM prestamos p
INNER JOIN cuotas c ON c.prestamo_id = p.id
INNER JOIN pagos pag ON pag.prestamo_id = p.id
WHERE p.estado = 'APROBADO'
  AND c.total_pagado >= c.monto_cuota
  AND c.total_pagado > 0
  AND pag.activo = true
  AND (pag.conciliado = false OR pag.conciliado IS NULL)
  AND pag.numero_documento IS NOT NULL
  AND pag.numero_documento != ''
GROUP BY p.id, p.cedula
ORDER BY total_pagos_sin_conciliar DESC
LIMIT 50;

-- 4. ESTADÍSTICAS POR ESTADO DE CUOTA
-- ============================================================================
SELECT 
    'ESTADISTICAS POR ESTADO' as tipo,
    c.estado,
    COUNT(*) as total_cuotas,
    COUNT(CASE WHEN c.total_pagado >= c.monto_cuota THEN 1 END) as cuotas_completamente_pagadas,
    COUNT(CASE WHEN c.total_pagado >= c.monto_cuota AND c.estado != 'PAGADO' THEN 1 END) as pagadas_sin_estado_pagado,
    SUM(c.total_pagado) as total_pagado_acumulado
FROM cuotas c
INNER JOIN prestamos p ON c.prestamo_id = p.id
WHERE p.estado = 'APROBADO'
  AND c.total_pagado > 0
GROUP BY c.estado
ORDER BY total_cuotas DESC;

-- 5. QUERY PARA CONCILIAR PAGOS (EJECUTAR CON PRECAUCIÓN)
-- ============================================================================
-- ⚠️ IMPORTANTE: Esta query marca TODOS los pagos de préstamos con cuotas pagadas como conciliados
-- ⚠️ Ejecutar solo después de verificar que los datos son correctos
-- ⚠️ Hacer BACKUP antes de ejecutar

/*
BEGIN;

-- Marcar pagos como conciliados para préstamos con cuotas completamente pagadas
UPDATE pagos p
SET 
    conciliado = true,
    fecha_conciliacion = CURRENT_TIMESTAMP,
    verificado_concordancia = 'SI'
WHERE p.activo = true
  AND p.prestamo_id IN (
      SELECT DISTINCT c.prestamo_id
      FROM cuotas c
      INNER JOIN prestamos pr ON c.prestamo_id = pr.id
      WHERE pr.estado = 'APROBADO'
        AND c.total_pagado >= c.monto_cuota
        AND c.total_pagado > 0
  )
  AND (p.conciliado = false OR p.conciliado IS NULL)
  AND p.numero_documento IS NOT NULL
  AND p.numero_documento != '';

-- Verificar cuántos pagos se actualizaron
SELECT COUNT(*) as pagos_conciliados FROM pagos 
WHERE conciliado = true 
  AND fecha_conciliacion >= CURRENT_DATE;

-- Si los resultados son correctos, hacer COMMIT, sino ROLLBACK
-- COMMIT;
-- ROLLBACK;
*/

-- 6. QUERY PARA ACTUALIZAR ESTADO DE CUOTAS (EJECUTAR CON PRECAUCIÓN)
-- ============================================================================
-- ⚠️ IMPORTANTE: Esta query actualiza el estado de cuotas a PAGADO si están completamente pagadas
-- ⚠️ y todos sus pagos están conciliados
-- ⚠️ Ejecutar solo después de conciliar los pagos

/*
BEGIN;

-- Actualizar estado de cuotas a PAGADO si están completamente pagadas
-- y todos los pagos del préstamo están conciliados
UPDATE cuotas c
SET estado = 'PAGADO'
WHERE c.total_pagado >= c.monto_cuota
  AND c.total_pagado > 0
  AND c.estado != 'PAGADO'
  AND c.prestamo_id IN (
      SELECT DISTINCT p.id
      FROM prestamos p
      WHERE p.estado = 'APROBADO'
        AND NOT EXISTS (
            SELECT 1
            FROM pagos pag
            WHERE pag.prestamo_id = p.id
              AND pag.activo = true
              AND (pag.conciliado = false OR pag.conciliado IS NULL)
              AND pag.numero_documento IS NOT NULL
              AND pag.numero_documento != ''
        )
  );

-- Verificar cuántas cuotas se actualizaron
SELECT COUNT(*) as cuotas_actualizadas 
FROM cuotas 
WHERE estado = 'PAGADO' 
  AND total_pagado >= monto_cuota;

-- Si los resultados son correctos, hacer COMMIT, sino ROLLBACK
-- COMMIT;
-- ROLLBACK;
*/

-- 7. VERIFICACIÓN POST-CONCILIACIÓN
-- ============================================================================
SELECT 
    'VERIFICACION POST-CONCILIACION' as tipo,
    COUNT(DISTINCT c.id) as total_cuotas_pagadas,
    COUNT(DISTINCT CASE WHEN c.estado = 'PAGADO' THEN c.id END) as cuotas_estado_pagado,
    COUNT(DISTINCT CASE WHEN c.total_pagado >= c.monto_cuota AND c.estado != 'PAGADO' THEN c.id END) as cuotas_pagadas_sin_estado,
    COUNT(DISTINCT CASE WHEN p.conciliado = false OR p.conciliado IS NULL THEN p.id END) as pagos_sin_conciliar_restantes
FROM cuotas c
INNER JOIN prestamos pr ON c.prestamo_id = pr.id
LEFT JOIN pagos p ON p.prestamo_id = c.prestamo_id 
    AND p.activo = true
    AND p.numero_documento IS NOT NULL
    AND p.numero_documento != ''
WHERE pr.estado = 'APROBADO'
  AND c.total_pagado >= c.monto_cuota
  AND c.total_pagado > 0;
