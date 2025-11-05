-- ============================================================================
-- VERIFICACIÓN RÁPIDA: ESTADO DE PAGOS
-- ============================================================================
-- Este script verifica el estado actual de los pagos y su relación con préstamos
-- ============================================================================

-- ============================================================================
-- 1. RESUMEN GENERAL
-- ============================================================================
SELECT 
    '=== RESUMEN GENERAL ===' AS verificacion,
    COUNT(*) AS total_registros,
    COUNT(*) FILTER (WHERE activo = TRUE) AS registros_activos,
    COUNT(*) FILTER (WHERE activo = TRUE AND monto_pagado IS NOT NULL AND monto_pagado > 0) AS registros_activos_con_pago,
    SUM(monto_pagado) FILTER (WHERE activo = TRUE) AS total_monto_pagado,
    TO_CHAR(SUM(monto_pagado) FILTER (WHERE activo = TRUE), 'FM$999,999,999,990.00') AS total_formateado
FROM pagos;

-- ============================================================================
-- 2. PAGOS CON Y SIN prestamo_id
-- ============================================================================
SELECT 
    '=== PAGOS CON/SIN prestamo_id ===' AS verificacion,
    CASE 
        WHEN prestamo_id IS NULL THEN 'SIN prestamo_id'
        ELSE 'CON prestamo_id'
    END AS tipo_pago,
    COUNT(*) AS cantidad,
    SUM(monto_pagado) AS total_monto,
    TO_CHAR(SUM(monto_pagado), 'FM$999,999,999,990.00') AS total_formateado,
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM pagos WHERE activo = TRUE), 2) AS porcentaje
FROM pagos
WHERE activo = TRUE
  AND monto_pagado IS NOT NULL
  AND monto_pagado > 0
GROUP BY CASE 
    WHEN prestamo_id IS NULL THEN 'SIN prestamo_id'
    ELSE 'CON prestamo_id'
END;

-- ============================================================================
-- 3. PAGOS QUE PODRÍAN ARTICULARSE POR CÉDULA
-- ============================================================================
WITH pagos_sin_prestamo AS (
    SELECT 
        p.id,
        p.cedula,
        p.monto_pagado,
        COUNT(DISTINCT pr.id) AS prestamos_encontrados
    FROM pagos p
    LEFT JOIN prestamos pr ON (
        pr.cedula = p.cedula 
        AND pr.estado = 'APROBADO'
    )
    WHERE p.activo = TRUE
      AND p.prestamo_id IS NULL
      AND p.monto_pagado IS NOT NULL
      AND p.monto_pagado > 0
    GROUP BY p.id, p.cedula, p.monto_pagado
)
SELECT 
    '=== ARTICULACIÓN POSIBLE POR CÉDULA ===' AS verificacion,
    CASE 
        WHEN prestamos_encontrados = 0 THEN 'SIN PRÉSTAMOS DISPONIBLES'
        WHEN prestamos_encontrados = 1 THEN 'UN PRÉSTAMO (FÁCIL ARTICULAR)'
        ELSE 'MÚLTIPLES PRÉSTAMOS (REQUIERE SELECCIÓN)'
    END AS estado_articulacion,
    COUNT(*) AS cantidad_pagos,
    SUM(monto_pagado) AS total_monto,
    TO_CHAR(SUM(monto_pagado), 'FM$999,999,999,990.00') AS total_formateado
FROM pagos_sin_prestamo
GROUP BY estado_articulacion
ORDER BY 
    CASE estado_articulacion
        WHEN 'UN PRÉSTAMO (FÁCIL ARTICULAR)' THEN 1
        WHEN 'MÚLTIPLES PRÉSTAMOS (REQUIERE SELECCIÓN)' THEN 2
        WHEN 'SIN PRÉSTAMOS DISPONIBLES' THEN 3
    END;

-- ============================================================================
-- 4. TOTAL PAGADO POR MES (fecha_pago)
-- ============================================================================
SELECT 
    '=== TOTAL PAGADO POR MES ===' AS verificacion,
    TO_CHAR(DATE_TRUNC('month', fecha_pago::date), 'YYYY-MM') AS mes,
    TO_CHAR(DATE_TRUNC('month', fecha_pago::date), 'Mon YYYY') AS mes_formateado,
    COUNT(*) AS cantidad_pagos,
    SUM(monto_pagado) AS total_pagado,
    TO_CHAR(SUM(monto_pagado), 'FM$999,999,999,990.00') AS total_formateado
FROM pagos
WHERE activo = TRUE
  AND monto_pagado IS NOT NULL
  AND monto_pagado > 0
  AND fecha_pago IS NOT NULL
GROUP BY DATE_TRUNC('month', fecha_pago::date)
ORDER BY DATE_TRUNC('month', fecha_pago::date) DESC
LIMIT 12;

-- ============================================================================
-- FIN DEL SCRIPT
-- ============================================================================

