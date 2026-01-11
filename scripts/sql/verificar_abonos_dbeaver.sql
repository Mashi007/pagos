-- ============================================================================
-- VERIFICACIÓN DE ABONOS: BD vs abono_2026
-- ============================================================================
-- Script para ejecutar en DBeaver
-- Muestra TODAS las cédulas con sus abonos comparados entre BD y abono_2026
-- 
-- IMPORTANTE: La primera query muestra TODAS las cédulas (coincidencias + discrepancias)
-- Las discrepancias aparecen primero porque está ordenado por diferencia DESC
-- Si quieres ver todas en orden alfabético, usa la sección alternativa comentada
-- ============================================================================

-- ----------------------------------------------------------------------------
-- RESUMEN RÁPIDO: Total de cédulas a mostrar
-- ----------------------------------------------------------------------------

SELECT 
    '=== TOTAL DE CÉDULAS A MOSTRAR ===' AS info,
    (SELECT COUNT(DISTINCT cedula) FROM prestamos WHERE cedula IS NOT NULL AND cedula != '') AS total_bd,
    (SELECT COUNT(DISTINCT cedula) FROM abono_2026 WHERE cedula IS NOT NULL) AS total_abono_2026,
    (SELECT COUNT(DISTINCT COALESCE(p.cedula, a.cedula))
     FROM prestamos p
     FULL OUTER JOIN abono_2026 a ON p.cedula = a.cedula
     WHERE COALESCE(p.cedula, a.cedula) IS NOT NULL) AS total_unico;

-- ----------------------------------------------------------------------------
-- COMPARACIÓN COMPLETA: Todas las cédulas (INCLUYE COINCIDENCIAS Y DISCREPANCIAS)
-- ----------------------------------------------------------------------------
-- Esta query muestra TODAS las cédulas sin filtrar ninguna
-- Ordenada por diferencia DESC para ver discrepancias primero
-- Cambiar ORDER BY a "cedula" si quieres orden alfabético

WITH abonos_bd AS (
    -- Calcular abonos desde BD (suma de cuotas.total_pagado por cédula)
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
-- ALTERNATIVA: Todas las cédulas ordenadas alfabéticamente
-- ----------------------------------------------------------------------------
-- Descomentar esta sección si prefieres ver todas las cédulas en orden alfabético

/*
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
        WHEN ABS(COALESCE(bd.total_abonos_bd, 0) - COALESCE(t2026.total_abonos_2026, 0)) <= 0.01 THEN 'Coincide'
        ELSE 'Diferencia'
    END AS estado
FROM abonos_bd bd
FULL OUTER JOIN abonos_2026 t2026 ON bd.cedula = t2026.cedula
ORDER BY cedula;
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
    ROUND(COUNT(CASE WHEN diferencia <= 0.01 THEN 1 END) * 100.0 / COUNT(*), 2) AS porcentaje_coincidencias,
    ROUND(COUNT(CASE WHEN diferencia > 0.01 THEN 1 END) * 100.0 / COUNT(*), 2) AS porcentaje_discrepancias,
    SUM(abonos_bd) AS total_abonos_bd,
    SUM(abonos_2026) AS total_abonos_2026,
    SUM(abonos_bd) - SUM(abonos_2026) AS diferencia_total,
    ROUND(AVG(CASE WHEN diferencia > 0.01 THEN diferencia END), 2) AS promedio_diferencia,
    MAX(CASE WHEN diferencia > 0.01 THEN diferencia END) AS max_diferencia,
    MIN(CASE WHEN diferencia > 0.01 THEN diferencia END) AS min_diferencia
FROM comparacion;

-- ----------------------------------------------------------------------------
-- VERIFICACIÓN: Cédulas solo en BD (no están en abono_2026)
-- ----------------------------------------------------------------------------

SELECT 
    '=== CÉDULAS SOLO EN BD ===' AS info;

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
    bd.cedula,
    bd.total_abonos_bd AS abonos_bd,
    0 AS abonos_2026,
    bd.total_abonos_bd AS diferencia
FROM abonos_bd bd
LEFT JOIN abonos_2026 t2026 ON bd.cedula = t2026.cedula
WHERE t2026.cedula IS NULL
ORDER BY bd.cedula;

-- ----------------------------------------------------------------------------
-- VERIFICACIÓN: Cédulas solo en abono_2026 (no están en BD)
-- ----------------------------------------------------------------------------

SELECT 
    '=== CÉDULAS SOLO EN abono_2026 ===' AS info;

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
    t2026.cedula,
    0 AS abonos_bd,
    t2026.total_abonos_2026 AS abonos_2026,
    t2026.total_abonos_2026 AS diferencia
FROM abonos_2026 t2026
LEFT JOIN abonos_bd bd ON t2026.cedula = bd.cedula
WHERE bd.cedula IS NULL
ORDER BY t2026.cedula;

-- ----------------------------------------------------------------------------
-- TOP 20 DISCREPANCIAS MÁS GRANDES
-- ----------------------------------------------------------------------------

SELECT 
    '=== TOP 20 DISCREPANCIAS MÁS GRANDES ===' AS info;

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
ORDER BY diferencia DESC
LIMIT 20;
