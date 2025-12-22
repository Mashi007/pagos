-- ============================================================================
-- PASOS DETALLADOS PARA DIAGNÓSTICO Y RECONCILIACIÓN DE PAGOS
-- ============================================================================
-- Este script contiene queries de diagnóstico paso a paso para entender
-- el estado actual de la vinculación entre pagos y cuotas
-- ============================================================================

-- ============================================================================
-- PASO 1: DIAGNÓSTICO INICIAL - Verificar estado actual
-- ============================================================================

-- 1.1. Verificar pagos sin prestamo_id que podrían vincularse
SELECT 
    'PASO 1.1: PAGOS CONCILIADOS SIN PRESTAMO_ID' as paso,
    COUNT(DISTINCT p.id) as total_pagos_conciliados_sin_prestamo_id,
    COUNT(DISTINCT p.cedula) as cedulas_unicas,
    COUNT(DISTINCT pr.id) as prestamos_aprobados_con_cedula_coincidente,
    SUM(p.monto_pagado) as monto_total_pagos_conciliados_sin_prestamo,
    ROUND(COUNT(DISTINCT pr.id) * 100.0 / NULLIF(COUNT(DISTINCT p.cedula), 0), 2) as porcentaje_cedulas_con_prestamo
FROM pagos p
LEFT JOIN prestamos pr ON pr.cedula = p.cedula AND pr.estado = 'APROBADO'
WHERE p.activo = true
  AND p.conciliado = true
  AND p.prestamo_id IS NULL;

-- 1.2. Verificar cuotas con pagos pero sin prestamo_id en pagos
SELECT 
    'PASO 1.2: CUOTAS CON PAGOS SIN PRESTAMO_ID EN PAGOS' as paso,
    COUNT(DISTINCT c.id) as cuotas_con_pagos_aplicados,
    COUNT(DISTINCT c.prestamo_id) as prestamos_con_cuotas_pagadas,
    COUNT(DISTINCT pr.cedula) as cedulas_unicas_prestamos,
    COUNT(DISTINCT p.id) as pagos_conciliados_con_cedula_coincidente,
    SUM(c.total_pagado) as monto_total_cuotas_pagadas,
    SUM(c.capital_pagado) as monto_total_capital_pagado
FROM cuotas c
INNER JOIN prestamos pr ON c.prestamo_id = pr.id
LEFT JOIN pagos p ON p.cedula = pr.cedula 
  AND p.activo = true 
  AND p.conciliado = true
  AND p.prestamo_id IS NULL
WHERE pr.estado = 'APROBADO'
  AND (c.capital_pagado > 0 OR c.total_pagado > 0);

-- 1.3. Muestra ejemplos de pagos conciliados sin prestamo_id con préstamos coincidentes
SELECT 
    'PASO 1.3: EJEMPLOS PAGOS SIN PRESTAMO_ID CON PRESTAMO COINCIDENTE' as paso,
    p.id as pago_id,
    p.cedula,
    p.monto_pagado,
    DATE(p.fecha_pago) as fecha_pago,
    DATE(p.fecha_conciliacion) as fecha_conciliacion,
    pr.id as prestamo_id_coincidente,
    pr.estado as estado_prestamo,
    COUNT(DISTINCT c.id) as cuotas_del_prestamo,
    COUNT(DISTINCT CASE WHEN c.total_pagado > 0 THEN c.id END) as cuotas_con_pagos
FROM pagos p
INNER JOIN prestamos pr ON pr.cedula = p.cedula AND pr.estado = 'APROBADO'
LEFT JOIN cuotas c ON c.prestamo_id = pr.id
WHERE p.activo = true
  AND p.conciliado = true
  AND p.prestamo_id IS NULL
GROUP BY p.id, p.cedula, p.monto_pagado, p.fecha_pago, p.fecha_conciliacion, pr.id, pr.estado
ORDER BY p.fecha_conciliacion DESC
LIMIT 20;

-- ============================================================================
-- PASO 2: VERIFICAR PAGOS QUE PODRÍAN ASIGNARSE A PRESTAMO_ID
-- ============================================================================

-- 2.1. Pagos conciliados sin prestamo_id que tienen UN SOLO préstamo aprobado con la misma cédula
SELECT 
    'PASO 2.1: PAGOS CON UN SOLO PRESTAMO COINCIDENTE' as paso,
    COUNT(DISTINCT p.id) as total_pagos,
    COUNT(DISTINCT p.cedula) as cedulas_unicas,
    SUM(p.monto_pagado) as monto_total
FROM pagos p
WHERE p.activo = true
  AND p.conciliado = true
  AND p.prestamo_id IS NULL
  AND (
      SELECT COUNT(*)
      FROM prestamos pr
      WHERE pr.cedula = p.cedula
        AND pr.estado = 'APROBADO'
  ) = 1;

-- 2.2. Pagos conciliados sin prestamo_id que tienen MÚLTIPLES préstamos aprobados con la misma cédula
SELECT 
    'PASO 2.2: PAGOS CON MULTIPLES PRESTAMOS COINCIDENTES' as paso,
    COUNT(DISTINCT p.id) as total_pagos,
    COUNT(DISTINCT p.cedula) as cedulas_unicas,
    SUM(p.monto_pagado) as monto_total,
    AVG(prestamos_count) as promedio_prestamos_por_cedula
FROM (
    SELECT 
        p.id,
        p.cedula,
        p.monto_pagado,
        COUNT(DISTINCT pr.id) as prestamos_count
    FROM pagos p
    LEFT JOIN prestamos pr ON pr.cedula = p.cedula AND pr.estado = 'APROBADO'
    WHERE p.activo = true
      AND p.conciliado = true
      AND p.prestamo_id IS NULL
    GROUP BY p.id, p.cedula, p.monto_pagado
    HAVING COUNT(DISTINCT pr.id) > 1
) subquery;

-- 2.3. Pagos conciliados sin prestamo_id que NO tienen préstamos aprobados con la misma cédula
SELECT 
    'PASO 2.3: PAGOS SIN PRESTAMO COINCIDENTE' as paso,
    COUNT(DISTINCT p.id) as total_pagos,
    COUNT(DISTINCT p.cedula) as cedulas_unicas,
    SUM(p.monto_pagado) as monto_total
FROM pagos p
WHERE p.activo = true
  AND p.conciliado = true
  AND p.prestamo_id IS NULL
  AND NOT EXISTS (
      SELECT 1
      FROM prestamos pr
      WHERE pr.cedula = p.cedula
        AND pr.estado = 'APROBADO'
  );

-- ============================================================================
-- PASO 3: VERIFICAR ESTADO DESPUÉS DE RECONCILIACIÓN (ejecutar después del script Python)
-- ============================================================================

-- 3.1. Verificar cuántos pagos tienen prestamo_id después de reconciliación
SELECT 
    'PASO 3.1: PAGOS CON PRESTAMO_ID DESPUES DE RECONCILIACION' as paso,
    COUNT(*) as total_pagos_con_prestamo_id,
    COUNT(CASE WHEN conciliado = true THEN 1 END) as pagos_conciliados_con_prestamo_id,
    COUNT(CASE WHEN conciliado = false THEN 1 END) as pagos_no_conciliados_con_prestamo_id,
    SUM(monto_pagado) as monto_total
FROM pagos
WHERE activo = true
  AND prestamo_id IS NOT NULL;

-- 3.2. Verificar vinculación entre pagos y cuotas después de reconciliación
SELECT 
    'PASO 3.2: VINCULACION PAGOS-CUOTAS DESPUES DE RECONCILIACION' as paso,
    COUNT(DISTINCT p.id) as total_pagos_conciliados_con_prestamo,
    COUNT(DISTINCT p.prestamo_id) as prestamos_con_pagos_conciliados,
    COUNT(DISTINCT c.id) as cuotas_del_prestamo,
    COUNT(DISTINCT CASE WHEN c.capital_pagado > 0 OR c.total_pagado > 0 THEN c.id END) as cuotas_con_pagos_aplicados,
    SUM(p.monto_pagado) as monto_total_pagos,
    SUM(c.total_pagado) as monto_total_cuotas
FROM pagos p
INNER JOIN prestamos pr ON p.prestamo_id = pr.id
LEFT JOIN cuotas c ON c.prestamo_id = p.prestamo_id
WHERE p.activo = true
  AND p.conciliado = true
  AND p.prestamo_id IS NOT NULL
  AND pr.estado = 'APROBADO';

-- ============================================================================
-- PASO 4: VERIFICAR INTEGRIDAD DE DATOS
-- ============================================================================

-- 4.1. Verificar pagos con prestamo_id que no existe en tabla prestamos
SELECT 
    'PASO 4.1: PAGOS CON PRESTAMO_ID INVALIDO' as paso,
    COUNT(*) as total_pagos,
    COUNT(DISTINCT p.prestamo_id) as prestamos_id_invalidos,
    SUM(p.monto_pagado) as monto_total
FROM pagos p
WHERE p.activo = true
  AND p.prestamo_id IS NOT NULL
  AND NOT EXISTS (
      SELECT 1
      FROM prestamos pr
      WHERE pr.id = p.prestamo_id
  );

-- 4.2. Verificar pagos con prestamo_id pero cédula no coincide
SELECT 
    'PASO 4.2: PAGOS CON PRESTAMO_ID PERO CEDULA NO COINCIDE' as paso,
    COUNT(*) as total_pagos,
    COUNT(DISTINCT p.prestamo_id) as prestamos_con_cedula_diferente,
    SUM(p.monto_pagado) as monto_total
FROM pagos p
INNER JOIN prestamos pr ON p.prestamo_id = pr.id
WHERE p.activo = true
  AND p.cedula != pr.cedula;

-- ============================================================================
-- RESUMEN FINAL: Estado completo del sistema
-- ============================================================================

SELECT 
    'RESUMEN FINAL' as tipo,
    (SELECT COUNT(*) FROM pagos WHERE activo = true) as total_pagos,
    (SELECT COUNT(*) FROM pagos WHERE activo = true AND conciliado = true) as pagos_conciliados,
    (SELECT COUNT(*) FROM pagos WHERE activo = true AND prestamo_id IS NOT NULL) as pagos_con_prestamo_id,
    (SELECT COUNT(*) FROM pagos WHERE activo = true AND conciliado = true AND prestamo_id IS NOT NULL) as pagos_conciliados_con_prestamo_id,
    (SELECT COUNT(*) FROM cuotas) as total_cuotas,
    (SELECT COUNT(*) FROM cuotas WHERE capital_pagado > 0 OR total_pagado > 0) as cuotas_con_pagos,
    (SELECT COUNT(*) FROM prestamos WHERE estado = 'APROBADO') as prestamos_aprobados;
