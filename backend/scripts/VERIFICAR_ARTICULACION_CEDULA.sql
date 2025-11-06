-- ============================================================================
-- VERIFICAR ARTICULACIÓN DE PAGOS CON PRÉSTAMOS POR CÉDULA
-- ============================================================================
-- Este script verifica cuántos pagos pueden articularse con préstamos
-- usando la columna cedula cuando prestamo_id es NULL
-- ============================================================================

-- ============================================================================
-- 1. RESUMEN DE PAGOS SIN prestamo_id
-- ============================================================================
SELECT 
    '=== RESUMEN DE PAGOS SIN prestamo_id ===' AS verificacion,
    COUNT(*) AS total_pagos_sin_prestamo_id,
    COUNT(DISTINCT cedula) AS cedulas_distintas,
    SUM(monto_pagado) AS total_monto_sin_prestamo_id,
    TO_CHAR(SUM(monto_pagado), 'FM$999,999,999,990.00') AS total_formateado
FROM pagos
WHERE activo = TRUE
  AND prestamo_id IS NULL
  AND monto_pagado IS NOT NULL
  AND monto_pagado > 0;

-- ============================================================================
-- 2. PAGOS QUE PUEDEN ARTICULARSE POR CÉDULA
-- ============================================================================
WITH pagos_con_prestamos AS (
    SELECT 
        p.id AS pago_id,
        p.cedula,
        p.monto_pagado,
        p.fecha_pago,
        COUNT(DISTINCT pr.id) AS cantidad_prestamos_encontrados,
        STRING_AGG(DISTINCT pr.id::TEXT, ', ' ORDER BY pr.id) AS ids_prestamos,
        CASE 
            WHEN COUNT(DISTINCT pr.id) = 0 THEN 'SIN PRÉSTAMOS'
            WHEN COUNT(DISTINCT pr.id) = 1 THEN 'UN PRÉSTAMO'
            ELSE 'MÚLTIPLES PRÉSTAMOS'
        END AS estado_articulacion
    FROM pagos p
    LEFT JOIN prestamos pr ON (
        p.prestamo_id IS NULL 
        AND pr.cedula = p.cedula 
        AND pr.estado = 'APROBADO'
    )
    WHERE p.activo = TRUE
      AND p.prestamo_id IS NULL
      AND p.monto_pagado IS NOT NULL
      AND p.monto_pagado > 0
    GROUP BY p.id, p.cedula, p.monto_pagado, p.fecha_pago
)
SELECT 
    '=== PAGOS QUE PUEDEN ARTICULARSE ===' AS verificacion,
    estado_articulacion,
    COUNT(*) AS cantidad_pagos,
    SUM(monto_pagado) AS total_monto,
    TO_CHAR(SUM(monto_pagado), 'FM$999,999,999,990.00') AS total_formateado
FROM pagos_con_prestamos
GROUP BY estado_articulacion
ORDER BY 
    CASE estado_articulacion
        WHEN 'UN PRÉSTAMO' THEN 1
        WHEN 'MÚLTIPLES PRÉSTAMOS' THEN 2
        WHEN 'SIN PRÉSTAMOS' THEN 3
    END;

-- ============================================================================
-- 3. EJEMPLO DE PAGOS ARTICULADOS (Primeros 10)
-- ============================================================================
SELECT 
    '=== EJEMPLO DE ARTICULACIÓN ===' AS verificacion,
    p.id AS pago_id,
    p.cedula,
    p.monto_pagado,
    TO_CHAR(p.fecha_pago, 'DD/MM/YYYY') AS fecha_pago,
    pr.id AS prestamo_id_encontrado,
    pr.estado AS estado_prestamo,
    COUNT(c.id) AS cantidad_cuotas_vencidas,
    SUM(c.monto_cuota) AS total_programado
FROM pagos p
LEFT JOIN prestamos pr ON (
    p.prestamo_id IS NULL 
    AND pr.cedula = p.cedula 
    AND pr.estado = 'APROBADO'
)
LEFT JOIN cuotas c ON (
    pr.id IS NOT NULL
    AND c.prestamo_id = pr.id
    AND c.fecha_vencimiento < CURRENT_DATE
    AND c.estado != 'PAGADO'
)
WHERE p.activo = TRUE
  AND p.prestamo_id IS NULL
  AND p.monto_pagado IS NOT NULL
  AND p.monto_pagado > 0
  AND pr.id IS NOT NULL  -- Solo mostrar pagos que encontraron préstamo
GROUP BY p.id, p.cedula, p.monto_pagado, p.fecha_pago, pr.id, pr.estado
ORDER BY p.fecha_pago DESC
LIMIT 10;

-- ============================================================================
-- 4. COMPARACIÓN: TOTAL PAGADO CON ARTICULACIÓN
-- ============================================================================
WITH pagos_con_prestamos AS (
    SELECT 
        DATE_TRUNC('month', COALESCE(c.fecha_vencimiento, p.fecha_pago::date)) AS mes,
        SUM(p.monto_pagado) AS total_pagado_con_articulacion
    FROM pagos p
    LEFT JOIN prestamos pr ON (
        (p.prestamo_id IS NOT NULL AND pr.id = p.prestamo_id)
        OR (p.prestamo_id IS NULL AND pr.cedula = p.cedula AND pr.estado = 'APROBADO')
    )
    LEFT JOIN cuotas c ON (
        pr.id IS NOT NULL
        AND c.prestamo_id = pr.id
        AND c.fecha_vencimiento < CURRENT_DATE
    )
    WHERE p.activo = TRUE
      AND p.monto_pagado IS NOT NULL
      AND p.monto_pagado > 0
    GROUP BY DATE_TRUNC('month', COALESCE(c.fecha_vencimiento, p.fecha_pago::date))
)
SELECT 
    '=== COMPARACIÓN: TOTAL PAGADO ===' AS verificacion,
    TO_CHAR(mes, 'YYYY-MM') AS mes,
    TO_CHAR(mes, 'Mon YYYY') AS mes_formateado,
    SUM(total_pagado_con_articulacion) AS total_pagado,
    TO_CHAR(SUM(total_pagado_con_articulacion), 'FM$999,999,999,990.00') AS total_formateado
FROM pagos_con_prestamos
GROUP BY mes
ORDER BY mes DESC
LIMIT 12;

-- ============================================================================
-- FIN DEL SCRIPT
-- ============================================================================

