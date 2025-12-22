-- ============================================================================
-- VERIFICAR VINCULACIÓN DE PAGOS A CUOTAS DESPUÉS DE CONCILIACIÓN
-- ============================================================================
-- REGLAS PRINCIPALES:
-- 
-- 1. Si pagos.conciliado = true AND pagos.prestamo_id IS NOT NULL
--    → DEBE haber cuotas del préstamo con total_pagado > 0
-- 
-- 2. Si pagos.conciliado = false
--    → NO debe actualizar cuotas (no debe haber cuotas actualizadas por ese pago)
-- 
-- LÓGICA DE APLICACIÓN DE PAGOS A CUOTAS:
-- Cuando un pago se concilia (conciliado = true), el sistema detecta que es un pago real.
-- El pago se aplica a la ÚLTIMA CUOTA NO PAGADA (más antigua pendiente).
-- 
-- - Si solo había una cuota pendiente → pasa a estar al día (total_pagado >= monto_cuota)
-- - Si hay más de una cuota pendiente → cubre la más antigua primero
--   - La cuota más antigua puede quedar parcialmente pagada si el monto no cubre todo
--   - Las cuotas más nuevas NO deben tener pagos hasta que la anterior esté completa
-- 
-- ACTUALIZACIÓN DE MONTO Y FECHA EN CUOTAS:
-- - SOLO si el pago está conciliado (conciliado = true):
--   1. pagos.monto_pagado → se suma a cuotas.capital_pagado (y también a cuotas.total_pagado)
--   2. pagos.fecha_pago → se copia a cuotas.fecha_pago
--   3. Con fecha_pago se calculan:
--      - días de retraso/mora (dias_morosidad, dias_mora)
--      - monto de mora (monto_morosidad, monto_mora)
--      - otros KPIs relacionados con el pago
-- - Si el pago NO está conciliado → NO se actualiza NADA en cuotas
-- 
-- Este script verifica que todas las reglas se estén cumpliendo:
-- 1. Pagos conciliados con prestamo_id deben tener cuotas con capital_pagado > 0 y total_pagado > 0
-- 2. Pagos NO conciliados NO deben actualizar cuotas (ni capital_pagado, ni total_pagado, ni fecha_pago)
-- 3. Los pagos se aplican a la cuota más antigua no pagada primero
-- 4. El orden de aplicación es correcto (más antiguas primero)
-- 5. Si hay múltiples cuotas pendientes, la más antigua tiene pagos antes que las siguientes
-- 6. La suma de pagos conciliados debe aproximarse al capital_pagado y total_pagado de las cuotas
-- 7. cuotas.fecha_pago se actualiza con pagos.fecha_pago SOLO cuando el pago está conciliado
-- 8. Los días de retraso y mora se calculan correctamente basándose en fecha_pago
-- ============================================================================

-- ============================================================================
-- QUERIES DE DIAGNÓSTICO: Verificar existencia de datos
-- ============================================================================

-- DIAGNÓSTICO 1: Resumen general de pagos
SELECT 
    'DIAGNOSTICO: RESUMEN PAGOS' as tipo,
    COUNT(*) as total_pagos,
    COUNT(CASE WHEN activo = true THEN 1 END) as pagos_activos,
    COUNT(CASE WHEN conciliado = true THEN 1 END) as pagos_conciliados,
    COUNT(CASE WHEN conciliado = false THEN 1 END) as pagos_no_conciliados,
    COUNT(CASE WHEN prestamo_id IS NOT NULL THEN 1 END) as pagos_con_prestamo_id,
    COUNT(CASE WHEN activo = true AND conciliado = true AND prestamo_id IS NOT NULL THEN 1 END) as pagos_conciliados_con_prestamo,
    COUNT(CASE WHEN activo = true AND conciliado = false AND prestamo_id IS NOT NULL THEN 1 END) as pagos_no_conciliados_con_prestamo
FROM pagos;

-- DIAGNÓSTICO 2: Resumen general de cuotas
SELECT 
    'DIAGNOSTICO: RESUMEN CUOTAS' as tipo,
    COUNT(*) as total_cuotas,
    COUNT(CASE WHEN capital_pagado > 0 OR total_pagado > 0 THEN 1 END) as cuotas_con_pagos,
    COUNT(CASE WHEN capital_pagado > 0 THEN 1 END) as cuotas_con_capital_pagado,
    COUNT(CASE WHEN total_pagado > 0 THEN 1 END) as cuotas_con_total_pagado,
    COUNT(CASE WHEN fecha_pago IS NOT NULL THEN 1 END) as cuotas_con_fecha_pago
FROM cuotas;

-- DIAGNÓSTICO 3: Resumen de préstamos
SELECT 
    'DIAGNOSTICO: RESUMEN PRESTAMOS' as tipo,
    COUNT(*) as total_prestamos,
    COUNT(CASE WHEN estado = 'APROBADO' THEN 1 END) as prestamos_aprobados,
    COUNT(CASE WHEN estado != 'APROBADO' THEN 1 END) as prestamos_no_aprobados
FROM prestamos;

-- DIAGNÓSTICO 4: Pagos conciliados con prestamo_id y sus cuotas
SELECT 
    'DIAGNOSTICO: PAGOS CONCILIADOS VS CUOTAS' as tipo,
    COUNT(DISTINCT p.id) as total_pagos_conciliados_con_prestamo,
    COUNT(DISTINCT p.prestamo_id) as prestamos_con_pagos_conciliados,
    COUNT(DISTINCT c.id) as cuotas_del_prestamo,
    COUNT(DISTINCT CASE WHEN c.capital_pagado > 0 OR c.total_pagado > 0 THEN c.id END) as cuotas_con_pagos_aplicados
FROM pagos p
LEFT JOIN cuotas c ON c.prestamo_id = p.prestamo_id
WHERE p.activo = true
  AND p.conciliado = true
  AND p.prestamo_id IS NOT NULL;

-- DIAGNÓSTICO 5: Pagos conciliados SIN prestamo_id (vinculación alternativa por cedula)
-- Verifica si hay pagos conciliados que podrían vincularse a préstamos por cedula
SELECT 
    'DIAGNOSTICO: PAGOS CONCILIADOS SIN PRESTAMO_ID' as tipo,
    COUNT(DISTINCT p.id) as total_pagos_conciliados_sin_prestamo_id,
    COUNT(DISTINCT p.cedula) as cedulas_unicas,
    COUNT(DISTINCT pr.id) as prestamos_aprobados_con_cedula_coincidente,
    SUM(p.monto_pagado) as monto_total_pagos_conciliados_sin_prestamo
FROM pagos p
LEFT JOIN prestamos pr ON pr.cedula = p.cedula AND pr.estado = 'APROBADO'
WHERE p.activo = true
  AND p.conciliado = true
  AND p.prestamo_id IS NULL;

-- DIAGNÓSTICO 6: Cuotas con pagos pero sin prestamo_id en pagos
-- Verifica si las cuotas con pagos aplicados tienen pagos vinculados por cedula
SELECT 
    'DIAGNOSTICO: CUOTAS CON PAGOS SIN PRESTAMO_ID' as tipo,
    COUNT(DISTINCT c.id) as cuotas_con_pagos_aplicados,
    COUNT(DISTINCT c.prestamo_id) as prestamos_con_cuotas_pagadas,
    COUNT(DISTINCT pr.cedula) as cedulas_unicas_prestamos,
    COUNT(DISTINCT p.id) as pagos_conciliados_con_cedula_coincidente,
    SUM(c.total_pagado) as monto_total_cuotas_pagadas
FROM cuotas c
INNER JOIN prestamos pr ON c.prestamo_id = pr.id
LEFT JOIN pagos p ON p.cedula = pr.cedula 
  AND p.activo = true 
  AND p.conciliado = true
  AND p.prestamo_id IS NULL
WHERE pr.estado = 'APROBADO'
  AND (c.capital_pagado > 0 OR c.total_pagado > 0);

-- ============================================================================
-- QUERIES DE VERIFICACIÓN PRINCIPALES
-- ============================================================================

-- 1. VERIFICAR PAGOS CONCILIADOS SIN APLICAR A CUOTAS
-- ============================================================================
-- REGLA 1: Cualquier pago conciliado con prestamo_id debe tener cuotas con:
--          - capital_pagado > 0 (monto_pagado se suma a capital_pagado)
--          - total_pagado > 0
--          - fecha_pago actualizada
-- Esta query identifica pagos conciliados que NO cumplen la regla (ERRORES)
SELECT 
    'PAGOS CONCILIADOS SIN APLICAR A CUOTAS' as tipo,
    COUNT(*) as total_pagos,
    SUM(monto_pagado) as monto_total
FROM pagos p
WHERE p.activo = true
  AND p.conciliado = true
  AND p.prestamo_id IS NOT NULL
  AND NOT EXISTS (
      SELECT 1
      FROM cuotas c
      WHERE c.prestamo_id = p.prestamo_id
        AND (c.capital_pagado > 0 OR c.total_pagado > 0)
  );

-- 1B. VERIFICAR PAGOS NO CONCILIADOS QUE NO DEBEN ACTUALIZAR CUOTAS
-- ============================================================================
-- REGLA 2: Pagos NO conciliados NO deben actualizar cuotas
-- Esta query verifica que los pagos no conciliados no están afectando cuotas
-- (Nota: Esta verificación es informativa, ya que el sistema debería prevenir esto)
SELECT 
    'PAGOS NO CONCILIADOS CON PRESTAMO_ID' as tipo,
    COUNT(*) as total_pagos_no_conciliados,
    SUM(monto_pagado) as monto_total,
    COUNT(DISTINCT prestamo_id) as prestamos_afectados
FROM pagos p
WHERE p.activo = true
  AND p.conciliado = false
  AND p.prestamo_id IS NOT NULL;

-- 2. VERIFICAR PAGOS CONCILIADOS Y SUS CUOTAS ASOCIADAS
-- ============================================================================
-- Muestra la relación entre pagos conciliados y cuotas del mismo préstamo
SELECT 
    'PAGOS Y CUOTAS ASOCIADAS' as tipo,
    p.id as pago_id,
    p.prestamo_id,
    p.monto_pagado,
    DATE(p.fecha_pago) as fecha_pago,
    DATE(p.fecha_conciliacion) as fecha_conciliacion,
    c.numero_cuota,
    c.fecha_vencimiento,
    c.total_pagado,
    DATE(c.fecha_pago) as fecha_pago_cuota,
    c.estado as estado_cuota
FROM pagos p
INNER JOIN cuotas c ON c.prestamo_id = p.prestamo_id
WHERE p.activo = true
  AND p.conciliado = true
  AND p.prestamo_id IS NOT NULL
  AND c.total_pagado > 0
ORDER BY p.prestamo_id, c.fecha_vencimiento, c.numero_cuota
LIMIT 50;

-- 3. VERIFICAR QUE PAGOS CONCILIADOS ACTUALIZARON CUOTAS
-- ============================================================================
-- Resumen de pagos conciliados y cuotas actualizadas por préstamo
-- Verifica que pagos.monto_pagado se actualizó en cuotas.capital_pagado
SELECT 
    'PAGOS CONCILIADOS CON CUOTAS ACTUALIZADAS' as tipo,
    COUNT(DISTINCT p.id) as total_pagos_conciliados,
    COUNT(DISTINCT c.prestamo_id) as total_prestamos_afectados,
    COUNT(DISTINCT c.id) as total_cuotas_afectadas,
    SUM(p.monto_pagado) as monto_total_pagos,
    SUM(c.capital_pagado) as monto_total_capital_pagado,
    SUM(c.total_pagado) as monto_total_cuotas,
    ROUND(SUM(c.capital_pagado) * 100.0 / NULLIF(SUM(p.monto_pagado), 0), 2) as porcentaje_capital_aplicado,
    ROUND(SUM(c.total_pagado) * 100.0 / NULLIF(SUM(p.monto_pagado), 0), 2) as porcentaje_total_aplicado
FROM pagos p
INNER JOIN cuotas c ON c.prestamo_id = p.prestamo_id
WHERE p.activo = true
  AND p.conciliado = true
  AND p.prestamo_id IS NOT NULL
  AND (c.capital_pagado > 0 OR c.total_pagado > 0);

-- 4. VERIFICAR ORDEN CORRECTO: Cuotas más antiguas deben tener pagos primero
-- ============================================================================
-- REGLA: Los pagos se aplican a la última cuota no pagada (más antigua pendiente)
-- Verifica que las cuotas con pagos aplicados siguen el orden de fecha_vencimiento
-- Si hay múltiples cuotas pendientes, la más antigua debe tener pagos antes que las siguientes
SELECT 
    'ORDEN DE APLICACION POR FECHA VENCIMIENTO' as tipo,
    c.prestamo_id,
    c.numero_cuota,
    c.fecha_vencimiento,
    c.capital_pagado,
    c.total_pagado,
    c.monto_cuota,
    c.estado,
    CASE 
        WHEN c.total_pagado >= c.monto_cuota THEN 'COMPLETA'
        WHEN c.total_pagado > 0 OR c.capital_pagado > 0 THEN 'PARCIAL'
        ELSE 'SIN PAGO'
    END as estado_pago,
    ROW_NUMBER() OVER (PARTITION BY c.prestamo_id ORDER BY c.fecha_vencimiento, c.numero_cuota) as orden_esperado,
    CASE 
        WHEN (c.capital_pagado > 0 OR c.total_pagado > 0) AND 
             LAG(COALESCE(c.capital_pagado, 0) + COALESCE(c.total_pagado, 0)) OVER (PARTITION BY c.prestamo_id ORDER BY c.fecha_vencimiento, c.numero_cuota) = 0
        THEN 'OK'
        WHEN (c.capital_pagado = 0 AND c.total_pagado = 0) AND 
             LEAD(COALESCE(c.capital_pagado, 0) + COALESCE(c.total_pagado, 0)) OVER (PARTITION BY c.prestamo_id ORDER BY c.fecha_vencimiento, c.numero_cuota) > 0
        THEN 'ERROR: Cuota posterior tiene pagos pero esta no'
        WHEN (c.capital_pagado > 0 OR c.total_pagado > 0) AND 
             LAG(c.total_pagado) OVER (PARTITION BY c.prestamo_id ORDER BY c.fecha_vencimiento, c.numero_cuota) < 
             LAG(c.monto_cuota) OVER (PARTITION BY c.prestamo_id ORDER BY c.fecha_vencimiento, c.numero_cuota)
             AND LAG(c.total_pagado) OVER (PARTITION BY c.prestamo_id ORDER BY c.fecha_vencimiento, c.numero_cuota) > 0
        THEN 'ADVERTENCIA: Cuota anterior no está completa pero esta tiene pagos'
        ELSE 'OK'
    END as validacion_orden
FROM cuotas c
INNER JOIN prestamos p ON c.prestamo_id = p.id
WHERE p.estado = 'APROBADO'
  AND EXISTS (
      SELECT 1
      FROM pagos pag
      WHERE pag.prestamo_id = c.prestamo_id
        AND pag.conciliado = true
        AND pag.activo = true
  )
ORDER BY c.prestamo_id, c.fecha_vencimiento, c.numero_cuota
LIMIT 100;

-- 5. VERIFICAR PROPORCIONALIDAD POR PRÉSTAMO
-- ============================================================================
-- Verifica que la suma de pagos conciliados por préstamo se aproxima al total_pagado de las cuotas
-- NOTA: Un pago puede aplicarse a múltiples cuotas, y una cuota puede recibir múltiples pagos
WITH pagos_por_prestamo AS (
    SELECT 
        prestamo_id,
        SUM(monto_pagado) as suma_pagos_conciliados
    FROM pagos
    WHERE conciliado = true
      AND activo = true
      AND prestamo_id IS NOT NULL
    GROUP BY prestamo_id
),
cuotas_por_prestamo AS (
    SELECT 
        prestamo_id,
        SUM(capital_pagado) as suma_capital_pagado_cuotas,
        SUM(total_pagado) as suma_total_pagado_cuotas
    FROM cuotas c
    INNER JOIN prestamos pr ON c.prestamo_id = pr.id
    WHERE pr.estado = 'APROBADO'
      AND (c.capital_pagado > 0 OR c.total_pagado > 0)
    GROUP BY prestamo_id
)
SELECT 
    'VERIFICACION PROPORCIONALIDAD POR PRESTAMO' as tipo,
    COALESCE(pp.prestamo_id, cp.prestamo_id) as prestamo_id,
    COALESCE(pp.suma_pagos_conciliados, 0) as suma_pagos_conciliados,
    COALESCE(cp.suma_capital_pagado_cuotas, 0) as suma_capital_pagado_cuotas,
    COALESCE(cp.suma_total_pagado_cuotas, 0) as suma_total_pagado_cuotas,
    ABS(COALESCE(pp.suma_pagos_conciliados, 0) - COALESCE(cp.suma_capital_pagado_cuotas, 0)) as diferencia_capital,
    ABS(COALESCE(pp.suma_pagos_conciliados, 0) - COALESCE(cp.suma_total_pagado_cuotas, 0)) as diferencia_total,
    CASE 
        WHEN ABS(COALESCE(pp.suma_pagos_conciliados, 0) - COALESCE(cp.suma_capital_pagado_cuotas, 0)) < 0.01 
             AND ABS(COALESCE(pp.suma_pagos_conciliados, 0) - COALESCE(cp.suma_total_pagado_cuotas, 0)) < 0.01
        THEN 'OK'
        ELSE 'DIFERENCIA'
    END as estado
FROM pagos_por_prestamo pp
FULL OUTER JOIN cuotas_por_prestamo cp ON pp.prestamo_id = cp.prestamo_id
WHERE ABS(COALESCE(pp.suma_pagos_conciliados, 0) - COALESCE(cp.suma_capital_pagado_cuotas, 0)) > 0.01
   OR ABS(COALESCE(pp.suma_pagos_conciliados, 0) - COALESCE(cp.suma_total_pagado_cuotas, 0)) > 0.01
ORDER BY diferencia_capital DESC, diferencia_total DESC
LIMIT 20;

-- 6. RESUMEN: Estado de Vinculación
-- ============================================================================
-- Resumen general verificando que todos los pagos conciliados actualizaron cuotas
-- REGLA 1: Todo pago conciliado con prestamo_id debe tener cuotas con:
--          - capital_pagado > 0 (pagos.monto_pagado se suma a capital_pagado)
--          - total_pagado > 0
--          - fecha_pago actualizada
SELECT 
    'RESUMEN VINCULACION' as tipo,
    COUNT(DISTINCT p.id) as total_pagos_conciliados,
    COUNT(DISTINCT CASE WHEN c.capital_pagado > 0 OR c.total_pagado > 0 THEN c.prestamo_id END) as prestamos_con_cuotas_actualizadas,
    COUNT(DISTINCT CASE WHEN c.capital_pagado > 0 OR c.total_pagado > 0 THEN c.id END) as cuotas_con_pagos_aplicados,
    SUM(p.monto_pagado) as monto_total_pagos_conciliados,
    SUM(CASE WHEN c.capital_pagado > 0 THEN c.capital_pagado ELSE 0 END) as monto_total_capital_pagado,
    SUM(CASE WHEN c.total_pagado > 0 THEN c.total_pagado ELSE 0 END) as monto_total_cuotas,
    COUNT(DISTINCT CASE WHEN c.fecha_pago IS NOT NULL AND (c.capital_pagado > 0 OR c.total_pagado > 0) THEN c.id END) as cuotas_con_fecha_pago,
    ROUND(COUNT(DISTINCT CASE WHEN c.capital_pagado > 0 OR c.total_pagado > 0 THEN c.id END) * 100.0 / NULLIF(COUNT(DISTINCT p.id), 0), 2) as promedio_cuotas_por_pago,
    COUNT(DISTINCT CASE WHEN (c.capital_pagado IS NULL OR c.capital_pagado = 0) AND (c.total_pagado IS NULL OR c.total_pagado = 0) THEN p.id END) as pagos_sin_cuotas_actualizadas
FROM pagos p
LEFT JOIN cuotas c ON c.prestamo_id = p.prestamo_id
WHERE p.activo = true
  AND p.conciliado = true
  AND p.prestamo_id IS NOT NULL;

-- 7. VERIFICAR APLICACIÓN A ÚLTIMA CUOTA NO PAGADA
-- ============================================================================
-- REGLA: El pago se aplica a la última cuota no pagada (más antigua pendiente)
-- Verifica que los pagos se aplicaron correctamente a la cuota más antigua no pagada
-- Si solo había una cuota pendiente, debe estar al día (total_pagado >= monto_cuota)
-- Si hay más de una, la más antigua debe tener pagos aplicados
WITH cuotas_ordenadas AS (
    SELECT 
        c.prestamo_id,
        c.id as cuota_id,
        c.numero_cuota,
        c.fecha_vencimiento,
        c.capital_pagado,
        c.total_pagado,
        c.monto_cuota,
        c.estado,
        ROW_NUMBER() OVER (PARTITION BY c.prestamo_id ORDER BY c.fecha_vencimiento, c.numero_cuota) as orden_cuota,
        CASE 
            WHEN c.total_pagado >= c.monto_cuota THEN 'COMPLETA'
            WHEN c.total_pagado > 0 OR c.capital_pagado > 0 THEN 'PARCIAL'
            ELSE 'SIN PAGO'
        END as estado_pago
    FROM cuotas c
    INNER JOIN prestamos pr ON c.prestamo_id = pr.id
    WHERE pr.estado = 'APROBADO'
      AND EXISTS (
          SELECT 1
          FROM pagos p
          WHERE p.prestamo_id = c.prestamo_id
            AND p.conciliado = true
            AND p.activo = true
      )
)
SELECT 
    'APLICACION A ULTIMA CUOTA NO PAGADA' as tipo,
    co.prestamo_id,
    co.numero_cuota,
    co.fecha_vencimiento,
    co.capital_pagado,
    co.total_pagado,
    co.monto_cuota,
    co.estado_pago,
    co.orden_cuota,
    CASE 
        WHEN (co.capital_pagado > 0 OR co.total_pagado > 0) AND co.orden_cuota = 1 THEN 'OK: Primera cuota tiene pagos'
        WHEN (co.capital_pagado > 0 OR co.total_pagado > 0) AND co.orden_cuota > 1 
             AND EXISTS (
                 SELECT 1 
                 FROM cuotas_ordenadas co2 
                 WHERE co2.prestamo_id = co.prestamo_id 
                   AND co2.orden_cuota < co.orden_cuota 
                   AND co2.total_pagado < co2.monto_cuota
             )
        THEN 'ERROR: Cuota posterior tiene pagos pero anterior no está completa'
        WHEN (co.capital_pagado = 0 AND co.total_pagado = 0) AND co.orden_cuota = 1 THEN 'OK: Primera cuota sin pagos aún'
        ELSE 'OK'
    END as validacion
FROM cuotas_ordenadas co
WHERE co.total_pagado > 0
ORDER BY co.prestamo_id, co.fecha_vencimiento, co.numero_cuota
LIMIT 50;

-- 8. VERIFICAR ACTUALIZACIÓN DE MONTO (capital_pagado) Y FECHA EN CUOTAS
-- ============================================================================
-- REGLA: SOLO si el pago está conciliado (conciliado = true):
--        1. pagos.monto_pagado → se suma a cuotas.capital_pagado (y total_pagado)
--        2. pagos.fecha_pago → se copia a cuotas.fecha_pago
-- Verifica que las cuotas con pagos conciliados aplicados tienen ambos campos actualizados
-- NOTA: Una cuota puede recibir múltiples pagos conciliados, fecha_pago debería ser la del último pago aplicado
WITH fecha_pago_por_cuota AS (
    SELECT 
        c.prestamo_id,
        c.id as cuota_id,
        MAX(DATE(p.fecha_pago)) as fecha_pago_ultimo_pago
    FROM cuotas c
    INNER JOIN prestamos pr ON c.prestamo_id = pr.id
    INNER JOIN pagos p ON p.prestamo_id = c.prestamo_id
      AND p.conciliado = true
      AND p.activo = true
    WHERE pr.estado = 'APROBADO'
      AND (c.capital_pagado > 0 OR c.total_pagado > 0)
    GROUP BY c.prestamo_id, c.id
)
SELECT 
    'VERIFICACION MONTO Y FECHA EN CUOTAS' as tipo,
    c.prestamo_id,
    c.numero_cuota,
    c.fecha_vencimiento,
    c.capital_pagado,
    c.total_pagado,
    DATE(c.fecha_pago) as fecha_pago_cuota,
    fp.fecha_pago_ultimo_pago,
    COALESCE(SUM(p.monto_pagado), 0) as suma_montos_pagos_conciliados,
    c.dias_morosidad,
    c.dias_mora,
    CASE 
        WHEN (c.capital_pagado IS NULL OR c.capital_pagado = 0) 
             AND (c.total_pagado IS NULL OR c.total_pagado = 0)
             AND EXISTS (SELECT 1 FROM pagos p2 WHERE p2.prestamo_id = c.prestamo_id AND p2.conciliado = true AND p2.activo = true)
        THEN 'ERROR: Tiene pagos conciliados pero capital_pagado y total_pagado no se actualizaron'
        WHEN (c.capital_pagado > 0 OR c.total_pagado > 0) 
             AND c.fecha_pago IS NULL
        THEN 'ERROR: Tiene monto actualizado pero fecha_pago no se actualizó'
        WHEN c.fecha_pago IS NOT NULL 
             AND (c.capital_pagado > 0 OR c.total_pagado > 0)
             AND fp.fecha_pago_ultimo_pago IS NOT NULL
             AND ABS(DATE(c.fecha_pago) - fp.fecha_pago_ultimo_pago) > 1
        THEN 'ADVERTENCIA: fecha_pago_cuota difiere de fecha_pago_ultimo_pago en más de 1 día'
        WHEN c.capital_pagado > 0 
             AND c.total_pagado > 0
             AND c.fecha_pago IS NOT NULL 
        THEN 'OK: capital_pagado, total_pagado y fecha_pago actualizados'
        ELSE 'OK: Sin pagos aplicados'
    END as validacion
FROM cuotas c
INNER JOIN prestamos pr ON c.prestamo_id = pr.id
LEFT JOIN fecha_pago_por_cuota fp ON fp.cuota_id = c.id
LEFT JOIN pagos p ON p.prestamo_id = c.prestamo_id
  AND p.conciliado = true
  AND p.activo = true
WHERE pr.estado = 'APROBADO'
  AND (c.capital_pagado > 0 OR c.total_pagado > 0)
  AND EXISTS (
      SELECT 1
      FROM pagos pag
      WHERE pag.prestamo_id = c.prestamo_id
        AND pag.conciliado = true
        AND pag.activo = true
  )
GROUP BY c.prestamo_id, c.numero_cuota, c.fecha_vencimiento, c.capital_pagado, c.total_pagado, c.fecha_pago, fp.fecha_pago_ultimo_pago, c.dias_morosidad, c.dias_mora
ORDER BY c.prestamo_id, c.fecha_vencimiento, c.numero_cuota
LIMIT 50;

-- 9. VERIFICAR CÁLCULO DE DÍAS DE RETRASO Y MORA
-- ============================================================================
-- REGLA: Con fecha_pago se calculan días de retraso (dias_morosidad, dias_mora)
-- Verifica que los días de retraso se calculan correctamente
-- Fórmula: dias_retraso = fecha_pago - fecha_vencimiento (si fecha_pago > fecha_vencimiento)
-- NOTA: Solo se calcula si el pago está conciliado y fecha_pago se actualizó
SELECT 
    'VERIFICACION CALCULO DIAS RETRASO' as tipo,
    c.prestamo_id,
    c.numero_cuota,
    c.fecha_vencimiento,
    DATE(c.fecha_pago) as fecha_pago_cuota,
    c.capital_pagado,
    c.total_pagado,
    c.dias_morosidad,
    c.dias_mora,
    CASE 
        WHEN c.fecha_pago IS NOT NULL AND c.fecha_vencimiento IS NOT NULL
             AND DATE(c.fecha_pago) > c.fecha_vencimiento
        THEN (DATE(c.fecha_pago) - c.fecha_vencimiento)
        ELSE 0
    END as dias_retraso_calculado,
    c.monto_morosidad,
    c.monto_mora,
    CASE 
        WHEN c.fecha_pago IS NULL AND (c.capital_pagado > 0 OR c.total_pagado > 0) THEN 'ERROR: Sin fecha_pago para calcular retraso'
        WHEN c.fecha_pago IS NOT NULL AND c.fecha_vencimiento IS NOT NULL
             AND DATE(c.fecha_pago) > c.fecha_vencimiento
             AND (c.dias_morosidad IS NULL OR c.dias_morosidad = 0)
        THEN 'ADVERTENCIA: Pago con retraso pero dias_morosidad no calculado'
        WHEN c.fecha_pago IS NOT NULL AND c.fecha_vencimiento IS NOT NULL
             AND DATE(c.fecha_pago) <= c.fecha_vencimiento
             AND (c.dias_morosidad IS NOT NULL AND c.dias_morosidad > 0)
        THEN 'ADVERTENCIA: Pago a tiempo pero tiene dias_morosidad'
        WHEN c.fecha_pago IS NOT NULL AND c.fecha_vencimiento IS NOT NULL
             AND DATE(c.fecha_pago) > c.fecha_vencimiento
             AND ABS(COALESCE(c.dias_morosidad, 0) - (DATE(c.fecha_pago) - c.fecha_vencimiento)) <= 1
        THEN 'OK'
        WHEN c.fecha_pago IS NOT NULL AND c.fecha_vencimiento IS NOT NULL
             AND DATE(c.fecha_pago) <= c.fecha_vencimiento
             AND COALESCE(c.dias_morosidad, 0) = 0
        THEN 'OK'
        ELSE 'OK'
    END as validacion_retraso
FROM cuotas c
INNER JOIN prestamos pr ON c.prestamo_id = pr.id
WHERE pr.estado = 'APROBADO'
  AND (c.capital_pagado > 0 OR c.total_pagado > 0)
  AND c.fecha_pago IS NOT NULL
ORDER BY c.prestamo_id, c.fecha_vencimiento, c.numero_cuota
LIMIT 50;

-- 10. VERIFICAR ACTUALIZACIÓN COMPLETA: MONTO (capital_pagado) Y FECHA
-- ============================================================================
-- REGLA: Cuando un pago conciliado se aplica a cuotas, DEBE actualizar:
--        1. capital_pagado (pagos.monto_pagado se suma a cuotas.capital_pagado)
--        2. total_pagado (también se actualiza)
--        3. fecha_pago (pagos.fecha_pago se copia a cuotas.fecha_pago)
-- Esta query detecta cuotas que tienen pagos conciliados aplicados pero les falta alguno de estos campos
SELECT 
    'VERIFICACION ACTUALIZACION COMPLETA' as tipo,
    c.prestamo_id,
    c.numero_cuota,
    c.fecha_vencimiento,
    c.capital_pagado,
    c.total_pagado,
    DATE(c.fecha_pago) as fecha_pago_cuota,
    COUNT(DISTINCT p.id) as total_pagos_conciliados,
    SUM(p.monto_pagado) as suma_montos_pagos,
    MAX(DATE(p.fecha_pago)) as fecha_pago_ultimo_pago,
    CASE 
        WHEN (c.capital_pagado IS NULL OR c.capital_pagado = 0) 
             AND (c.total_pagado IS NULL OR c.total_pagado = 0)
             AND EXISTS (SELECT 1 FROM pagos p2 WHERE p2.prestamo_id = c.prestamo_id AND p2.conciliado = true AND p2.activo = true)
        THEN 'ERROR: Tiene pagos conciliados pero capital_pagado y total_pagado no se actualizaron'
        WHEN (c.capital_pagado > 0 OR c.total_pagado > 0)
             AND c.fecha_pago IS NULL
        THEN 'ERROR: Tiene monto actualizado pero fecha_pago no se actualizó'
        WHEN c.capital_pagado > 0 
             AND c.total_pagado > 0
             AND c.fecha_pago IS NOT NULL
        THEN 'OK: capital_pagado, total_pagado y fecha_pago se actualizaron'
        ELSE 'OK: Sin pagos conciliados aplicados'
    END as validacion_actualizacion
FROM cuotas c
INNER JOIN prestamos pr ON c.prestamo_id = pr.id
LEFT JOIN pagos p ON p.prestamo_id = c.prestamo_id
  AND p.conciliado = true
  AND p.activo = true
WHERE pr.estado = 'APROBADO'
  AND EXISTS (
      SELECT 1
      FROM pagos pag
      WHERE pag.prestamo_id = c.prestamo_id
        AND pag.conciliado = true
        AND pag.activo = true
  )
GROUP BY c.prestamo_id, c.numero_cuota, c.fecha_vencimiento, c.capital_pagado, c.total_pagado, c.fecha_pago
HAVING ((c.capital_pagado IS NULL OR c.capital_pagado = 0) AND (c.total_pagado IS NULL OR c.total_pagado = 0))
    OR ((c.capital_pagado > 0 OR c.total_pagado > 0) AND c.fecha_pago IS NULL)
ORDER BY c.prestamo_id, c.fecha_vencimiento, c.numero_cuota
LIMIT 50;

-- 11. RESUMEN COMPARATIVO: Conciliados vs No Conciliados
-- ============================================================================
-- Compara el estado de pagos conciliados vs no conciliados
-- Verifica que SOLO los pagos conciliados actualizaron cuotas (capital_pagado, total_pagado, fecha_pago)
SELECT 
    'RESUMEN COMPARATIVO' as tipo,
    CASE WHEN p.conciliado = true THEN 'CONCILIADOS' ELSE 'NO CONCILIADOS' END as estado_pago,
    COUNT(DISTINCT p.id) as total_pagos,
    COUNT(DISTINCT p.prestamo_id) as prestamos_con_pago,
    SUM(p.monto_pagado) as monto_total,
    COUNT(DISTINCT CASE WHEN c.capital_pagado > 0 OR c.total_pagado > 0 THEN c.prestamo_id END) as prestamos_con_cuotas_actualizadas,
    COUNT(DISTINCT CASE WHEN c.capital_pagado > 0 OR c.total_pagado > 0 THEN c.id END) as cuotas_con_pagos_aplicados,
    COUNT(DISTINCT CASE WHEN c.fecha_pago IS NOT NULL AND (c.capital_pagado > 0 OR c.total_pagado > 0) THEN c.id END) as cuotas_con_fecha_pago,
    CASE 
        WHEN p.conciliado = false 
             AND COUNT(DISTINCT CASE WHEN c.capital_pagado > 0 OR c.total_pagado > 0 THEN c.id END) > 0
        THEN 'ERROR: Pagos NO conciliados actualizaron cuotas (no debería pasar)'
        WHEN p.conciliado = true 
             AND COUNT(DISTINCT CASE WHEN c.capital_pagado > 0 OR c.total_pagado > 0 THEN c.id END) = 0
        THEN 'ADVERTENCIA: Pagos conciliados no actualizaron cuotas'
        ELSE 'OK'
    END as validacion
FROM pagos p
LEFT JOIN cuotas c ON c.prestamo_id = p.prestamo_id
WHERE p.activo = true
  AND p.prestamo_id IS NOT NULL
GROUP BY CASE WHEN p.conciliado = true THEN 'CONCILIADOS' ELSE 'NO CONCILIADOS' END, p.conciliado
ORDER BY estado_pago;
