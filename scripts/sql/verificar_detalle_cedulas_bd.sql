-- ============================================================================
-- VERIFICACIÓN DETALLADA: Abonos por Cédula en BD
-- ============================================================================
-- Este script verifica en detalle los abonos por cédula desde la BD
-- mostrando todos los préstamos y sus abonos individuales
-- ============================================================================

-- ----------------------------------------------------------------------------
-- VERIFICAR CÉDULAS ESPECÍFICAS CON DETALLE POR PRÉSTAMO
-- ----------------------------------------------------------------------------

-- Cédulas a verificar (las que aparecen en la imagen con discrepancias)
WITH cedulas_a_verificar AS (
    SELECT unnest(ARRAY[
        'V23107415', 'V19226493', 'V12122176', 'V27223265', 'V27020005',
        'V14406409', 'V23681759', 'V17476568', 'V14702874'
    ]) AS cedula
),
abonos_por_prestamo AS (
    -- Abonos por cada préstamo individual
    SELECT 
        p.cedula,
        p.id AS prestamo_id,
        p.total_financiamiento,
        p.numero_cuotas,
        p.estado,
        COALESCE(SUM(c.total_pagado), 0) AS abonos_prestamo,
        COUNT(c.id) AS total_cuotas,
        COUNT(CASE WHEN c.total_pagado > 0 THEN 1 END) AS cuotas_con_pago
    FROM prestamos p
    LEFT JOIN cuotas c ON p.id = c.prestamo_id
    WHERE p.cedula IN (SELECT cedula FROM cedulas_a_verificar)
      AND p.cedula IS NOT NULL
      AND p.cedula != ''
    GROUP BY p.id, p.cedula, p.total_financiamiento, p.numero_cuotas, p.estado
),
abonos_totales_bd AS (
    -- Total de abonos por cédula (suma de todos los préstamos)
    SELECT 
        cedula,
        SUM(abonos_prestamo) AS total_abonos_bd,
        COUNT(*) AS total_prestamos,
        STRING_AGG(prestamo_id::text || ' ($' || abonos_prestamo::text || ')', ', ') AS detalle_prestamos
    FROM abonos_por_prestamo
    GROUP BY cedula
),
abonos_2026 AS (
    -- Abonos desde tabla abono_2026
    SELECT 
        cedula,
        COALESCE(SUM(abonos)::numeric, 0) AS total_abonos_2026,
        COUNT(*) AS registros_en_tabla
    FROM abono_2026
    WHERE cedula IN (SELECT cedula FROM cedulas_a_verificar)
    GROUP BY cedula
)
SELECT 
    COALESCE(bd.cedula, t2026.cedula) AS cedula,
    COALESCE(bd.total_abonos_bd, 0) AS total_abonos_bd,
    COALESCE(t2026.total_abonos_2026, 0) AS total_abonos_2026,
    ABS(COALESCE(bd.total_abonos_bd, 0) - COALESCE(t2026.total_abonos_2026, 0)) AS diferencia,
    COALESCE(bd.total_prestamos, 0) AS total_prestamos,
    COALESCE(bd.detalle_prestamos, 'Sin préstamos') AS detalle_prestamos,
    COALESCE(t2026.registros_en_tabla, 0) AS registros_en_tabla,
    CASE 
        WHEN ABS(COALESCE(bd.total_abonos_bd, 0) - COALESCE(t2026.total_abonos_2026, 0)) <= 0.01 THEN 'Coincide'
        ELSE 'Diferencia'
    END AS estado
FROM abonos_totales_bd bd
FULL OUTER JOIN abonos_2026 t2026 ON bd.cedula = t2026.cedula
ORDER BY diferencia DESC, cedula;

-- ----------------------------------------------------------------------------
-- DETALLE COMPLETO POR PRÉSTAMO PARA TODAS LAS CÉDULAS
-- ----------------------------------------------------------------------------

SELECT 
    '=== DETALLE COMPLETO POR PRÉSTAMO ===' AS info;

SELECT 
    p.cedula,
    p.id AS prestamo_id,
    p.total_financiamiento,
    p.numero_cuotas,
    p.estado,
    p.fecha_aprobacion,
    COALESCE(SUM(c.total_pagado), 0) AS abonos_prestamo,
    COUNT(c.id) AS total_cuotas,
    COUNT(CASE WHEN c.total_pagado > 0 THEN 1 END) AS cuotas_con_pago,
    COUNT(CASE WHEN c.total_pagado = 0 THEN 1 END) AS cuotas_sin_pago
FROM prestamos p
LEFT JOIN cuotas c ON p.id = c.prestamo_id
WHERE p.cedula IN (
    'V23107415', 'V19226493', 'V12122176', 'V27223265', 'V27020005',
    'V14406409', 'V23681759', 'V17476568', 'V14702874'
)
GROUP BY p.id, p.cedula, p.total_financiamiento, p.numero_cuotas, p.estado, p.fecha_aprobacion
ORDER BY p.cedula, p.id;

-- ----------------------------------------------------------------------------
-- COMPARAR CON PAGOS DIRECTOS (pagos.monto_pagado)
-- ----------------------------------------------------------------------------

SELECT 
    '=== COMPARACIÓN CON PAGOS DIRECTOS ===' AS info;

WITH abonos_cuotas AS (
    SELECT 
        p.cedula,
        COALESCE(SUM(c.total_pagado), 0) AS total_desde_cuotas
    FROM prestamos p
    LEFT JOIN cuotas c ON p.id = c.prestamo_id
    WHERE p.cedula IN (
        'V23107415', 'V19226493', 'V12122176', 'V27223265', 'V27020005',
        'V14406409', 'V23681759', 'V17476568', 'V14702874'
    )
      AND p.cedula IS NOT NULL
    GROUP BY p.cedula
),
abonos_pagos AS (
    SELECT 
        cedula,
        COALESCE(SUM(monto_pagado), 0) AS total_desde_pagos
    FROM pagos
    WHERE cedula IN (
        'V23107415', 'V19226493', 'V12122176', 'V27223265', 'V27020005',
        'V14406409', 'V23681759', 'V17476568', 'V14702874'
    )
      AND monto_pagado IS NOT NULL
      AND monto_pagado > 0
      AND activo = TRUE
    GROUP BY cedula
),
abonos_2026 AS (
    SELECT 
        cedula,
        COALESCE(SUM(abonos)::numeric, 0) AS total_abonos_2026
    FROM abono_2026
    WHERE cedula IN (
        'V23107415', 'V19226493', 'V12122176', 'V27223265', 'V27020005',
        'V14406409', 'V23681759', 'V17476568', 'V14702874'
    )
    GROUP BY cedula
)
SELECT 
    COALESCE(c.cedula, p.cedula, t2026.cedula) AS cedula,
    COALESCE(c.total_desde_cuotas, 0) AS abonos_desde_cuotas,
    COALESCE(p.total_desde_pagos, 0) AS abonos_desde_pagos,
    COALESCE(t2026.total_abonos_2026, 0) AS abonos_2026,
    ABS(COALESCE(c.total_desde_cuotas, 0) - COALESCE(p.total_desde_pagos, 0)) AS diferencia_cuotas_vs_pagos,
    ABS(COALESCE(c.total_desde_cuotas, 0) - COALESCE(t2026.total_abonos_2026, 0)) AS diferencia_cuotas_vs_2026,
    CASE 
        WHEN ABS(COALESCE(c.total_desde_cuotas, 0) - COALESCE(p.total_desde_pagos, 0)) > 0.01 THEN '⚠️ Diferencia cuotas vs pagos'
        WHEN ABS(COALESCE(c.total_desde_cuotas, 0) - COALESCE(t2026.total_abonos_2026, 0)) > 0.01 THEN '⚠️ Diferencia cuotas vs 2026'
        ELSE '✅ Coincide'
    END AS estado
FROM abonos_cuotas c
FULL OUTER JOIN abonos_pagos p ON c.cedula = p.cedula
FULL OUTER JOIN abonos_2026 t2026 ON COALESCE(c.cedula, p.cedula) = t2026.cedula
ORDER BY cedula;
