-- ============================================================================
-- VERIFICACIÓN ESPECÍFICA DE CÉDULAS EN BD
-- ============================================================================
-- Script para verificar si los valores de abonos coinciden en la BD
-- para cédulas específicas que aparecen con discrepancias
-- ============================================================================

-- ----------------------------------------------------------------------------
-- VERIFICAR CÉDULAS ESPECÍFICAS CON DISCREPANCIAS
-- ----------------------------------------------------------------------------

WITH abonos_bd AS (
    -- Calcular abonos desde BD (cuotas.total_pagado)
    SELECT 
        p.cedula,
        COALESCE(SUM(c.total_pagado), 0) AS total_abonos_bd,
        COUNT(DISTINCT p.id) AS total_prestamos,
        STRING_AGG(DISTINCT p.id::text, ', ') AS ids_prestamos
    FROM prestamos p
    LEFT JOIN cuotas c ON p.id = c.prestamo_id
    WHERE p.cedula IN (
        'V23107415', 'V19226493', 'V12122176', 'V27223265', 'V27020005',
        'V14406409', 'V23681759', 'V17476568', 'V14702874'
    )
      AND p.cedula IS NOT NULL
      AND p.cedula != ''
    GROUP BY p.cedula
),
abonos_pagos AS (
    -- Calcular abonos desde pagos (como referencia alternativa)
    SELECT 
        cedula,
        COALESCE(SUM(monto_pagado), 0) AS total_abonos_pagos
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
    -- Obtener abonos desde tabla abono_2026
    SELECT 
        cedula,
        COALESCE(SUM(abonos)::numeric, 0) AS total_abonos_2026,
        COUNT(*) AS registros_en_tabla
    FROM abono_2026
    WHERE cedula IN (
        'V23107415', 'V19226493', 'V12122176', 'V27223265', 'V27020005',
        'V14406409', 'V23681759', 'V17476568', 'V14702874'
    )
    GROUP BY cedula
)
SELECT 
    COALESCE(bd.cedula, t2026.cedula) AS cedula,
    COALESCE(bd.total_abonos_bd, 0) AS abonos_bd_cuotas,
    COALESCE(p.total_abonos_pagos, 0) AS abonos_bd_pagos,
    COALESCE(t2026.total_abonos_2026, 0) AS abonos_2026,
    COALESCE(bd.total_prestamos, 0) AS total_prestamos,
    COALESCE(bd.ids_prestamos, 'N/A') AS ids_prestamos,
    COALESCE(t2026.registros_en_tabla, 0) AS registros_en_tabla,
    ABS(COALESCE(bd.total_abonos_bd, 0) - COALESCE(t2026.total_abonos_2026, 0)) AS diferencia,
    CASE 
        WHEN ABS(COALESCE(bd.total_abonos_bd, 0) - COALESCE(t2026.total_abonos_2026, 0)) <= 0.01 THEN 'Coincide'
        ELSE 'Diferencia'
    END AS estado
FROM abonos_bd bd
FULL OUTER JOIN abonos_2026 t2026 ON bd.cedula = t2026.cedula
LEFT JOIN abonos_pagos p ON bd.cedula = p.cedula
ORDER BY diferencia DESC, cedula;

-- ----------------------------------------------------------------------------
-- DETALLE POR PRÉSTAMO PARA CÉDULAS CON DISCREPANCIAS
-- ----------------------------------------------------------------------------

SELECT 
    '=== DETALLE POR PRÉSTAMO: V14406409 ===' AS info;

SELECT 
    p.id AS prestamo_id,
    p.cedula,
    p.total_financiamiento,
    p.numero_cuotas,
    p.estado,
    COALESCE(SUM(c.total_pagado), 0) AS total_abonos_prestamo,
    COUNT(c.id) AS total_cuotas,
    COUNT(CASE WHEN c.total_pagado > 0 THEN 1 END) AS cuotas_con_pago
FROM prestamos p
LEFT JOIN cuotas c ON p.id = c.prestamo_id
WHERE p.cedula = 'V14406409'
GROUP BY p.id, p.cedula, p.total_financiamiento, p.numero_cuotas, p.estado
ORDER BY p.id;

-- ----------------------------------------------------------------------------
-- DETALLE POR PRÉSTAMO: V23107415
-- ----------------------------------------------------------------------------

SELECT 
    '=== DETALLE POR PRÉSTAMO: V23107415 ===' AS info;

SELECT 
    p.id AS prestamo_id,
    p.cedula,
    p.total_financiamiento,
    p.numero_cuotas,
    p.estado,
    COALESCE(SUM(c.total_pagado), 0) AS total_abonos_prestamo,
    COUNT(c.id) AS total_cuotas,
    COUNT(CASE WHEN c.total_pagado > 0 THEN 1 END) AS cuotas_con_pago
FROM prestamos p
LEFT JOIN cuotas c ON p.id = c.prestamo_id
WHERE p.cedula = 'V23107415'
GROUP BY p.id, p.cedula, p.total_financiamiento, p.numero_cuotas, p.estado
ORDER BY p.id;

-- ----------------------------------------------------------------------------
-- DETALLE POR PRÉSTAMO: V23681759
-- ----------------------------------------------------------------------------

SELECT 
    '=== DETALLE POR PRÉSTAMO: V23681759 ===' AS info;

SELECT 
    p.id AS prestamo_id,
    p.cedula,
    p.total_financiamiento,
    p.numero_cuotas,
    p.estado,
    COALESCE(SUM(c.total_pagado), 0) AS total_abonos_prestamo,
    COUNT(c.id) AS total_cuotas,
    COUNT(CASE WHEN c.total_pagado > 0 THEN 1 END) AS cuotas_con_pago
FROM prestamos p
LEFT JOIN cuotas c ON p.id = c.prestamo_id
WHERE p.cedula = 'V23681759'
GROUP BY p.id, p.cedula, p.total_financiamiento, p.numero_cuotas, p.estado
ORDER BY p.id;

-- ----------------------------------------------------------------------------
-- VERIFICAR REGISTROS EN abono_2026 PARA ESTAS CÉDULAS
-- ----------------------------------------------------------------------------

SELECT 
    '=== REGISTROS EN abono_2026 ===' AS info;

SELECT 
    id,
    cedula,
    abonos,
    fecha_creacion,
    fecha_actualizacion
FROM abono_2026
WHERE cedula IN (
    'V23107415', 'V19226493', 'V12122176', 'V27223265', 'V27020005',
    'V14406409', 'V23681759', 'V17476568', 'V14702874'
)
ORDER BY cedula, id;
