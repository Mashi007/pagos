-- ============================================================================
-- VERIFICACIÓN: TOTAL PAGADO REAL DESDE TABLA 'pagos'
-- ============================================================================
-- Este script verifica que el cálculo de total_pagado_real esté usando
-- correctamente el campo monto_pagado de la tabla pagos
-- ============================================================================

-- ============================================================================
-- 1. VERIFICAR TOTAL DE monto_pagado EN TABLA pagos
-- ============================================================================
SELECT 
    '=== TOTAL EN TABLA pagos ===' AS verificacion,
    COUNT(*) AS total_registros,
    SUM(monto_pagado) AS total_monto_pagado,
    TO_CHAR(SUM(monto_pagado), 'FM$999,999,999,990.00') AS total_formateado,
    COUNT(*) FILTER (WHERE activo = TRUE AND monto_pagado > 0) AS registros_activos_con_pago,
    SUM(monto_pagado) FILTER (WHERE activo = TRUE AND monto_pagado > 0) AS total_activos_con_pago
FROM pagos;

-- ============================================================================
-- 2. TOTAL PAGADO POR MES (usando fecha_pago del pago)
-- ============================================================================
SELECT 
    '=== TOTAL PAGADO POR MES (fecha_pago) ===' AS verificacion,
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
ORDER BY mes DESC;

-- ============================================================================
-- 3. TOTAL PAGADO POR MES (relacionado con mes de vencimiento de cuota)
-- ============================================================================
SELECT 
    '=== TOTAL PAGADO POR MES (mes vencimiento cuota) ===' AS verificacion,
    TO_CHAR(DATE_TRUNC('month', c.fecha_vencimiento), 'YYYY-MM') AS mes_vencimiento,
    TO_CHAR(DATE_TRUNC('month', c.fecha_vencimiento), 'Mon YYYY') AS mes_formateado,
    COUNT(DISTINCT p.id) AS cantidad_pagos,
    SUM(p.monto_pagado) AS total_pagado_real,
    TO_CHAR(SUM(p.monto_pagado), 'FM$999,999,999,990.00') AS total_formateado
FROM pagos p
INNER JOIN prestamos pr ON p.prestamo_id = pr.id
INNER JOIN cuotas c ON (
    c.prestamo_id = p.prestamo_id 
    AND (
        (p.numero_cuota IS NOT NULL AND c.numero_cuota = p.numero_cuota)
        OR (p.numero_cuota IS NULL 
            AND c.fecha_vencimiento = (
                SELECT MIN(c2.fecha_vencimiento)
                FROM cuotas c2
                WHERE c2.prestamo_id = p.prestamo_id
                  AND c2.fecha_vencimiento < CURRENT_DATE
                  AND DATE_TRUNC('month', c2.fecha_vencimiento) = DATE_TRUNC('month', c.fecha_vencimiento)
            ))
    )
)
WHERE p.activo = TRUE
  AND p.monto_pagado IS NOT NULL
  AND p.monto_pagado > 0
  AND pr.estado = 'APROBADO'
  AND c.fecha_vencimiento IS NOT NULL
  AND c.fecha_vencimiento < CURRENT_DATE
GROUP BY DATE_TRUNC('month', c.fecha_vencimiento)
ORDER BY mes_vencimiento DESC;

-- ============================================================================
-- 4. COMPARAR: Total pagos vs Total relacionado con cuotas
-- ============================================================================
SELECT 
    '=== COMPARACIÓN ===' AS verificacion,
    (SELECT SUM(monto_pagado) FROM pagos WHERE activo = TRUE AND monto_pagado > 0) AS total_pagado_sin_filtro,
    (SELECT SUM(p.monto_pagado)
     FROM pagos p
     INNER JOIN prestamos pr ON p.prestamo_id = pr.id
     INNER JOIN cuotas c ON c.prestamo_id = p.prestamo_id
     WHERE p.activo = TRUE
       AND p.monto_pagado > 0
       AND pr.estado = 'APROBADO'
       AND c.fecha_vencimiento < CURRENT_DATE
    ) AS total_pagado_con_cuotas,
    (SELECT SUM(monto_pagado) FROM pagos WHERE activo = TRUE AND monto_pagado > 0) - 
    (SELECT SUM(p.monto_pagado)
     FROM pagos p
     INNER JOIN prestamos pr ON p.prestamo_id = pr.id
     INNER JOIN cuotas c ON c.prestamo_id = p.prestamo_id
     WHERE p.activo = TRUE
       AND p.monto_pagado > 0
       AND pr.estado = 'APROBADO'
       AND c.fecha_vencimiento < CURRENT_DATE
    ) AS diferencia;

-- ============================================================================
-- 5. VERIFICAR PAGOS SIN prestamo_id (no se relacionan con cuotas)
-- ============================================================================
SELECT 
    '=== PAGOS SIN prestamo_id ===' AS verificacion,
    COUNT(*) AS cantidad_pagos_sin_prestamo,
    SUM(monto_pagado) AS total_sin_prestamo,
    TO_CHAR(SUM(monto_pagado), 'FM$999,999,999,990.00') AS total_formateado
FROM pagos
WHERE activo = TRUE
  AND monto_pagado IS NOT NULL
  AND monto_pagado > 0
  AND prestamo_id IS NULL;

-- ============================================================================
-- FIN DEL SCRIPT
-- ============================================================================

