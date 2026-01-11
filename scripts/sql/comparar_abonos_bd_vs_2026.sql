-- ============================================================================
-- COMPARACIÓN: Abonos BD vs abono_2026
-- ============================================================================
-- Este script compara los abonos (cantidad total pagada) por cédula entre:
-- 1. Base de Datos: suma de cuotas.total_pagado agrupada por cédula
-- 2. Tabla abono_2026: columna abonos (integer)
-- ============================================================================

-- ----------------------------------------------------------------------------
-- COMPARACIÓN COMPLETA CON DIFERENCIAS
-- ----------------------------------------------------------------------------

WITH abonos_bd AS (
    -- Calcular abonos desde BD (cuotas.total_pagado)
    SELECT 
        p.cedula,
        COALESCE(SUM(c.total_pagado), 0) AS total_abonos_bd
    FROM prestamos p
    LEFT JOIN cuotas c ON p.id = c.prestamo_id
    WHERE p.cedula IS NOT NULL
      AND p.cedula != ''
    GROUP BY p.cedula
),
abonos_2026 AS (
    -- Obtener abonos desde tabla abono_2026 (sumar si hay duplicados)
    SELECT 
        cedula,
        COALESCE(SUM(abonos)::numeric, 0) AS total_abonos_2026
    FROM abono_2026
    WHERE cedula IS NOT NULL
    GROUP BY cedula
)
SELECT 
    COALESCE(bd.cedula, t2026.cedula) AS cedula,
    COALESCE(bd.total_abonos_bd, 0) AS abonos_bd,
    COALESCE(t2026.total_abonos_2026, 0) AS abonos_2026,
    ABS(COALESCE(bd.total_abonos_bd, 0) - COALESCE(t2026.total_abonos_2026, 0)) AS diferencia,
    CASE 
        WHEN bd.cedula IS NULL THEN 'Solo en abono_2026'
        WHEN t2026.cedula IS NULL THEN 'Solo en BD'
        WHEN ABS(COALESCE(bd.total_abonos_bd, 0) - COALESCE(t2026.total_abonos_2026, 0)) <= 0.01 THEN 'Coincide'
        ELSE 'Diferencia'
    END AS estado
FROM abonos_bd bd
FULL OUTER JOIN abonos_2026 t2026 ON bd.cedula = t2026.cedula
ORDER BY diferencia DESC, cedula;

-- ----------------------------------------------------------------------------
-- SOLO DISCREPANCIAS (con diferencia mayor a $0.01) - OPCIONAL
-- ----------------------------------------------------------------------------
-- NOTA: Esta sección está comentada porque se deben mostrar TODAS las cédulas
-- Descomentar solo si necesitas filtrar discrepancias específicamente

/*
SELECT 
    '=== SOLO DISCREPANCIAS ===' AS info;

WITH abonos_bd AS (
    SELECT 
        p.cedula,
        COALESCE(SUM(c.total_pagado), 0) AS total_abonos_bd
    FROM prestamos p
    LEFT JOIN cuotas c ON p.id = c.prestamo_id
    WHERE p.cedula IS NOT NULL
      AND p.cedula != ''
    GROUP BY p.cedula
),
abonos_2026 AS (
    SELECT 
        cedula,
        COALESCE(SUM(abonos)::numeric, 0) AS total_abonos_2026
    FROM abono_2026
    WHERE cedula IS NOT NULL
    GROUP BY cedula
)
SELECT 
    COALESCE(bd.cedula, t2026.cedula) AS cedula,
    COALESCE(bd.total_abonos_bd, 0) AS abonos_bd,
    COALESCE(t2026.total_abonos_2026, 0) AS abonos_2026,
    ABS(COALESCE(bd.total_abonos_bd, 0) - COALESCE(t2026.total_abonos_2026, 0)) AS diferencia,
    CASE 
        WHEN bd.cedula IS NULL THEN 'Solo en abono_2026'
        WHEN t2026.cedula IS NULL THEN 'Solo en BD'
        ELSE 'Diferencia'
    END AS estado
FROM abonos_bd bd
FULL OUTER JOIN abonos_2026 t2026 ON bd.cedula = t2026.cedula
WHERE ABS(COALESCE(bd.total_abonos_bd, 0) - COALESCE(t2026.total_abonos_2026, 0)) > 0.01
ORDER BY diferencia DESC, cedula;
*/

-- ----------------------------------------------------------------------------
-- RESUMEN ESTADÍSTICO
-- ----------------------------------------------------------------------------

SELECT 
    '=== RESUMEN ESTADÍSTICO ===' AS info;

WITH abonos_bd AS (
    SELECT 
        p.cedula,
        COALESCE(SUM(c.total_pagado), 0) AS total_abonos_bd
    FROM prestamos p
    LEFT JOIN cuotas c ON p.id = c.prestamo_id
    WHERE p.cedula IS NOT NULL
      AND p.cedula != ''
    GROUP BY p.cedula
),
abonos_2026 AS (
    SELECT 
        cedula,
        COALESCE(SUM(abonos)::numeric, 0) AS total_abonos_2026
    FROM abono_2026
    WHERE cedula IS NOT NULL
    GROUP BY cedula
),
comparacion AS (
    SELECT 
        COALESCE(bd.cedula, t2026.cedula) AS cedula,
        COALESCE(bd.total_abonos_bd, 0) AS abonos_bd,
        COALESCE(t2026.total_abonos_2026, 0) AS abonos_2026,
        ABS(COALESCE(bd.total_abonos_bd, 0) - COALESCE(t2026.total_abonos_2026, 0)) AS diferencia
    FROM abonos_bd bd
    FULL OUTER JOIN abonos_2026 t2026 ON bd.cedula = t2026.cedula
)
SELECT 
    COUNT(*) AS total_cedulas,
    COUNT(CASE WHEN diferencia <= 0.01 THEN 1 END) AS coincidencias,
    COUNT(CASE WHEN diferencia > 0.01 THEN 1 END) AS discrepancias,
    SUM(abonos_bd) AS total_abonos_bd,
    SUM(abonos_2026) AS total_abonos_2026,
    SUM(abonos_bd) - SUM(abonos_2026) AS diferencia_total,
    ROUND(AVG(CASE WHEN diferencia > 0.01 THEN diferencia END), 2) AS promedio_diferencia,
    MAX(CASE WHEN diferencia > 0.01 THEN diferencia END) AS max_diferencia
FROM comparacion;
