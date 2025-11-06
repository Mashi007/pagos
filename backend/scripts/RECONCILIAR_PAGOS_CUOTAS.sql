-- ============================================================================
-- 🔧 RECONCILIACIÓN DE PAGOS CON CUOTAS - SCRIPT SQL PARA DBEAVER
-- ============================================================================
-- Fecha: 2025-01-06
-- Objetivo: Vincular pagos con cuotas usando múltiples estrategias
-- IMPORTANTE: Ejecutar en modo TRANSACCIÓN para poder hacer ROLLBACK si es necesario
-- ============================================================================

-- ============================================================================
-- ⚠️ IMPORTANTE: EJECUTAR EN MODO TRANSACCIÓN
-- ============================================================================
-- En DBeaver: Click derecho en la conexión > "Edit Connection" > 
-- Pestaña "Connection settings" > Marcar "Auto-commit" = FALSE
-- O ejecutar: BEGIN; al inicio y COMMIT; al final (o ROLLBACK; si hay problemas)
-- ============================================================================

BEGIN;

-- ============================================================================
-- 1. ESTRATEGIA 1: PAGOS CON prestamo_id Y numero_cuota
-- ============================================================================
-- Actualizar total_pagado en cuotas que tienen pagos vinculados correctamente
-- ============================================================================

-- 1.1 Ver cuántos pagos tienen prestamo_id y numero_cuota
SELECT 
    COUNT(*) as total_pagos_con_info,
    COUNT(DISTINCT prestamo_id) as prestamos_distintos,
    SUM(monto_pagado) as monto_total
FROM pagos
WHERE activo = true
  AND prestamo_id IS NOT NULL
  AND numero_cuota IS NOT NULL
  AND monto_pagado > 0;

-- 1.2 Actualizar total_pagado en cuotas (Estrategia 1)
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
        ELSE c.estado
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
FROM prestamos p
WHERE c.prestamo_id = p.id
  AND p.estado = 'APROBADO'
  AND EXISTS (
      SELECT 1
      FROM pagos pa
      WHERE pa.prestamo_id = c.prestamo_id
        AND pa.numero_cuota = c.numero_cuota
        AND pa.activo = true
        AND pa.monto_pagado > 0
  );

-- 1.3 Verificar resultados de Estrategia 1
SELECT 
    COUNT(*) as cuotas_actualizadas,
    SUM(total_pagado) as monto_total_pagado,
    COUNT(CASE WHEN estado = 'PAGADO' THEN 1 END) as cuotas_pagadas,
    COUNT(CASE WHEN estado = 'PARCIAL' THEN 1 END) as cuotas_parciales
FROM cuotas c
INNER JOIN prestamos p ON c.prestamo_id = p.id
WHERE p.estado = 'APROBADO'
  AND c.total_pagado > 0;

-- ============================================================================
-- 2. ESTRATEGIA 2: PAGOS SIN prestamo_id O numero_cuota
-- ============================================================================
-- Vincular pagos por cédula y fecha de vencimiento
-- ============================================================================

-- 2.1 Ver cuántos pagos NO tienen prestamo_id o numero_cuota
SELECT 
    COUNT(*) as total_pagos_sin_info,
    SUM(monto_pagado) as monto_total
FROM pagos
WHERE activo = true
  AND (prestamo_id IS NULL OR numero_cuota IS NULL)
  AND monto_pagado > 0;

-- 2.2 Actualizar prestamo_id y numero_cuota en pagos (Estrategia 2A: por cédula y fecha exacta)
UPDATE pagos pa
SET 
    prestamo_id = c.prestamo_id,
    numero_cuota = c.numero_cuota
FROM cuotas c
INNER JOIN prestamos p ON c.prestamo_id = p.id
WHERE pa.activo = true
  AND (pa.prestamo_id IS NULL OR pa.numero_cuota IS NULL)
  AND pa.cedula = p.cedula
  AND DATE(pa.fecha_pago) = c.fecha_vencimiento
  AND p.estado = 'APROBADO'
  AND c.estado != 'PAGADO'
  AND ABS(pa.monto_pagado - c.monto_cuota) <= (c.monto_cuota * 0.2)  -- Tolerancia 20%
  AND NOT EXISTS (
      -- Evitar duplicados: no actualizar si ya existe otro pago para esta cuota
      SELECT 1
      FROM pagos pa2
      WHERE pa2.prestamo_id = c.prestamo_id
        AND pa2.numero_cuota = c.numero_cuota
        AND pa2.activo = true
        AND pa2.id != pa.id
  );

-- 2.3 Actualizar prestamo_id y numero_cuota en pagos (Estrategia 2B: por cédula y rango de fechas ±30 días)
UPDATE pagos pa
SET 
    prestamo_id = c.prestamo_id,
    numero_cuota = c.numero_cuota
FROM cuotas c
INNER JOIN prestamos p ON c.prestamo_id = p.id
WHERE pa.activo = true
  AND (pa.prestamo_id IS NULL OR pa.numero_cuota IS NULL)
  AND pa.cedula = p.cedula
  AND DATE(pa.fecha_pago) BETWEEN c.fecha_vencimiento - INTERVAL '30 days' 
                               AND c.fecha_vencimiento + INTERVAL '30 days'
  AND p.estado = 'APROBADO'
  AND c.estado != 'PAGADO'
  AND ABS(pa.monto_pagado - c.monto_cuota) <= (c.monto_cuota * 0.3)  -- Tolerancia 30%
  AND NOT EXISTS (
      SELECT 1
      FROM pagos pa2
      WHERE pa2.prestamo_id = c.prestamo_id
        AND pa2.numero_cuota = c.numero_cuota
        AND pa2.activo = true
        AND pa2.id != pa.id
  )
  AND NOT EXISTS (
      -- No actualizar si ya se vinculó con Estrategia 2A
      SELECT 1
      FROM pagos pa3
      WHERE pa3.id = pa.id
        AND pa3.prestamo_id IS NOT NULL
        AND pa3.numero_cuota IS NOT NULL
  );

-- 2.4 Actualizar total_pagado en cuotas después de vincular pagos (Estrategia 2)
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
        ELSE c.estado
    END
FROM prestamos p
WHERE c.prestamo_id = p.id
  AND p.estado = 'APROBADO'
  AND EXISTS (
      SELECT 1
      FROM pagos pa
      WHERE pa.prestamo_id = c.prestamo_id
        AND pa.numero_cuota = c.numero_cuota
        AND pa.activo = true
        AND pa.monto_pagado > 0
  );

-- 2.5 Verificar resultados de Estrategia 2
SELECT 
    COUNT(*) as pagos_vinculados_estrategia2,
    COUNT(DISTINCT prestamo_id) as prestamos_afectados
FROM pagos
WHERE activo = true
  AND prestamo_id IS NOT NULL
  AND numero_cuota IS NOT NULL
  AND monto_pagado > 0;

-- ============================================================================
-- 3. CORREGIR CUOTAS MARCADAS COMO PAGADO SIN PAGOS
-- ============================================================================
-- Cambiar estado de cuotas marcadas como PAGADO pero sin pagos registrados
-- ============================================================================

-- 3.1 Ver cuántas cuotas están marcadas como PAGADO pero sin pagos
SELECT 
    COUNT(*) as cuotas_pagadas_sin_pagos,
    SUM(monto_cuota) as monto_total
FROM cuotas c
INNER JOIN prestamos p ON c.prestamo_id = p.id
WHERE c.estado = 'PAGADO'
  AND p.estado = 'APROBADO'
  AND NOT EXISTS (
      SELECT 1
      FROM pagos pa
      WHERE pa.prestamo_id = c.prestamo_id
        AND pa.numero_cuota = c.numero_cuota
        AND pa.activo = true
        AND pa.monto_pagado > 0
  );

-- 3.2 Cambiar estado a PENDIENTE si no hay pagos
UPDATE cuotas c
SET 
    estado = 'PENDIENTE',
    fecha_pago = NULL,
    total_pagado = 0
FROM prestamos p
WHERE c.prestamo_id = p.id
  AND c.estado = 'PAGADO'
  AND p.estado = 'APROBADO'
  AND NOT EXISTS (
      SELECT 1
      FROM pagos pa
      WHERE pa.prestamo_id = c.prestamo_id
        AND pa.numero_cuota = c.numero_cuota
        AND pa.activo = true
        AND pa.monto_pagado > 0
  );

-- 3.3 Verificar resultados
SELECT 
    COUNT(*) as cuotas_corregidas
FROM cuotas c
INNER JOIN prestamos p ON c.prestamo_id = p.id
WHERE c.estado = 'PENDIENTE'
  AND p.estado = 'APROBADO'
  AND c.total_pagado = 0
  AND c.fecha_pago IS NULL;

-- ============================================================================
-- 4. RESUMEN FINAL
-- ============================================================================

-- 4.1 Resumen de pagos vinculados
SELECT 
    'PAGOS VINCULADOS' as metrica,
    COUNT(*) as total_pagos,
    COUNT(DISTINCT prestamo_id) as prestamos_afectados,
    SUM(monto_pagado) as monto_total
FROM pagos
WHERE activo = true
  AND prestamo_id IS NOT NULL
  AND numero_cuota IS NOT NULL
  AND monto_pagado > 0;

-- 4.2 Resumen de cuotas con pagos
SELECT 
    'CUOTAS CON PAGOS' as metrica,
    COUNT(*) as total_cuotas,
    COUNT(CASE WHEN total_pagado > 0 THEN 1 END) as cuotas_con_pagos,
    COUNT(CASE WHEN estado = 'PAGADO' THEN 1 END) as cuotas_pagadas,
    COUNT(CASE WHEN estado = 'PARCIAL' THEN 1 END) as cuotas_parciales,
    SUM(total_pagado) as monto_total_pagado
FROM cuotas c
INNER JOIN prestamos p ON c.prestamo_id = p.id
WHERE p.estado = 'APROBADO';

-- 4.3 Resumen de morosidad mensual (últimos 12 meses)
SELECT 
    TO_CHAR(DATE_TRUNC('month', c.fecha_vencimiento), 'YYYY-MM') as mes,
    COUNT(*) as cantidad_cuotas,
    SUM(c.monto_cuota) as monto_programado,
    SUM(COALESCE(c.total_pagado, 0)) as monto_pagado,
    SUM(c.monto_cuota) - SUM(COALESCE(c.total_pagado, 0)) as morosidad
FROM cuotas c
INNER JOIN prestamos p ON c.prestamo_id = p.id
WHERE p.estado = 'APROBADO'
  AND c.fecha_vencimiento >= DATE_TRUNC('month', CURRENT_DATE - INTERVAL '12 months')
GROUP BY DATE_TRUNC('month', c.fecha_vencimiento)
ORDER BY mes DESC;

-- ============================================================================
-- ⚠️ DECISIÓN: COMMIT O ROLLBACK
-- ============================================================================
-- Revisa los resultados de las queries de resumen antes de decidir
-- 
-- Si los resultados son correctos:
-- COMMIT;
-- 
-- Si hay problemas o quieres revertir:
-- ROLLBACK;
-- ============================================================================

-- Descomenta una de estas líneas:
-- COMMIT;  -- Para guardar los cambios
-- ROLLBACK;  -- Para revertir los cambios

