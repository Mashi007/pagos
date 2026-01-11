-- ============================================================================
-- VERIFICACIÓN Y POBLADO DE TABLA abono_2026
-- ============================================================================
-- Este script verifica el estado de la tabla abono_2026 y la pobla con
-- los datos de abonos (cantidad total pagada) calculados desde la BD.
-- 
-- La columna 'abonos' (integer) contiene la cantidad total pagada por cada cédula,
-- calculada como la suma de cuotas.total_pagado agrupada por cédula.
-- ============================================================================

-- ----------------------------------------------------------------------------
-- PASO 1: VERIFICAR ESTADO ACTUAL DE abono_2026
-- ----------------------------------------------------------------------------

SELECT 
    '=== ESTADO ACTUAL DE abono_2026 ===' AS info;

-- Verificar estructura y datos
SELECT 
    COUNT(*) AS total_registros,
    COUNT(DISTINCT cedula) AS cedulas_unicas,
    COUNT(abono) AS registros_con_abono_numeric,
    COUNT(abonos) AS registros_con_abonos_integer,
    SUM(abono) AS total_abono_numeric,
    SUM(abonos) AS total_abonos_integer,
    MIN(abono) AS min_abono,
    MAX(abono) AS max_abono
FROM abono_2026;

-- Ver algunos registros de ejemplo
SELECT 
    '=== EJEMPLOS DE REGISTROS ===' AS info;

SELECT 
    cedula,
    abono AS abono_numeric,
    abonos AS abonos_integer,
    fecha_creacion
FROM abono_2026
WHERE cedula IS NOT NULL
ORDER BY cedula
LIMIT 10;

-- ----------------------------------------------------------------------------
-- PASO 2: CALCULAR ABONOS DESDE BD (cuotas.total_pagado)
-- ----------------------------------------------------------------------------

SELECT 
    '=== ABONOS CALCULADOS DESDE BD ===' AS info;

SELECT 
    p.cedula,
    COALESCE(SUM(c.total_pagado), 0) AS total_abonos_bd,
    COUNT(c.id) AS total_cuotas
FROM prestamos p
LEFT JOIN cuotas c ON p.id = c.prestamo_id
WHERE p.cedula IS NOT NULL
  AND p.cedula != ''
GROUP BY p.cedula
ORDER BY p.cedula
LIMIT 10;

-- ----------------------------------------------------------------------------
-- PASO 3: COMPARAR BD vs abono_2026
-- ----------------------------------------------------------------------------

SELECT 
    '=== COMPARACIÓN BD vs abono_2026 ===' AS info;

WITH abonos_bd AS (
    SELECT 
        p.cedula,
        COALESCE(SUM(c.total_pagado), 0) AS total_abonos
    FROM prestamos p
    LEFT JOIN cuotas c ON p.id = c.prestamo_id
    WHERE p.cedula IS NOT NULL
      AND p.cedula != ''
    GROUP BY p.cedula
),
abonos_tabla AS (
    SELECT 
        cedula,
        COALESCE(abonos::numeric, 0) AS total_abonos
    FROM abono_2026
    WHERE cedula IS NOT NULL
)
SELECT 
    COALESCE(bd.cedula, t.cedula) AS cedula,
    COALESCE(bd.total_abonos, 0) AS abono_bd,
    COALESCE(t.total_abonos, 0) AS abono_tabla,
    ABS(COALESCE(bd.total_abonos, 0) - COALESCE(t.total_abonos, 0)) AS diferencia,
    CASE 
        WHEN bd.cedula IS NULL THEN 'Solo en tabla'
        WHEN t.cedula IS NULL THEN 'Solo en BD'
        WHEN ABS(COALESCE(bd.total_abonos, 0) - COALESCE(t.total_abonos, 0)) > 0.01 THEN 'Diferencia'
        ELSE 'Coincide'
    END AS estado
FROM abonos_bd bd
FULL OUTER JOIN abonos_tabla t ON bd.cedula = t.cedula
WHERE ABS(COALESCE(bd.total_abonos, 0) - COALESCE(t.total_abonos, 0)) > 0.01
   OR bd.cedula IS NULL
   OR t.cedula IS NULL
ORDER BY diferencia DESC
LIMIT 20;

-- ----------------------------------------------------------------------------
-- PASO 4: POBLAR abono_2026 DESDE BD (OPCIONAL - DESCOMENTAR PARA EJECUTAR)
-- ----------------------------------------------------------------------------

-- ⚠️ ADVERTENCIA: Este paso actualizará la tabla abono_2026
-- Descomenta las siguientes líneas solo si deseas poblar la tabla

/*
-- Opción 1: INSERT o UPDATE usando UPSERT (usando columna abonos)
INSERT INTO abono_2026 (cedula, abonos, fecha_actualizacion)
SELECT 
    p.cedula,
    COALESCE(SUM(c.total_pagado), 0)::integer AS total_abonos,
    CURRENT_TIMESTAMP AS fecha_actualizacion
FROM prestamos p
LEFT JOIN cuotas c ON p.id = c.prestamo_id
WHERE p.cedula IS NOT NULL
  AND p.cedula != ''
GROUP BY p.cedula
ON CONFLICT (cedula) DO UPDATE SET
    abonos = EXCLUDED.abonos,
    fecha_actualizacion = EXCLUDED.fecha_actualizacion;

-- Opción 2: Si no hay constraint UNIQUE en cedula, usar UPDATE primero, luego INSERT
-- UPDATE registros existentes (usando columna abonos)
UPDATE abono_2026 a
SET 
    abonos = subquery.total_abonos::integer,
    fecha_actualizacion = CURRENT_TIMESTAMP
FROM (
    SELECT 
        p.cedula,
        COALESCE(SUM(c.total_pagado), 0) AS total_abonos
    FROM prestamos p
    LEFT JOIN cuotas c ON p.id = c.prestamo_id
    WHERE p.cedula IS NOT NULL
      AND p.cedula != ''
    GROUP BY p.cedula
) AS subquery
WHERE a.cedula = subquery.cedula;

-- INSERT nuevos registros (usando columna abonos)
INSERT INTO abono_2026 (cedula, abonos, fecha_creacion, fecha_actualizacion)
SELECT 
    p.cedula,
    COALESCE(SUM(c.total_pagado), 0)::integer AS total_abonos,
    CURRENT_TIMESTAMP AS fecha_creacion,
    CURRENT_TIMESTAMP AS fecha_actualizacion
FROM prestamos p
LEFT JOIN cuotas c ON p.id = c.prestamo_id
WHERE p.cedula IS NOT NULL
  AND p.cedula != ''
  AND p.cedula NOT IN (SELECT cedula FROM abono_2026 WHERE cedula IS NOT NULL)
GROUP BY p.cedula;
*/

-- ----------------------------------------------------------------------------
-- PASO 5: VERIFICACIÓN POST-POBLADO (ejecutar después de poblar)
-- ----------------------------------------------------------------------------

SELECT 
    '=== VERIFICACIÓN POST-POBLADO ===' AS info;

SELECT 
    COUNT(*) AS total_registros,
    COUNT(DISTINCT cedula) AS cedulas_unicas,
    COUNT(abonos) AS registros_con_abonos,
    SUM(abonos) AS total_abonos,
    MIN(abonos) AS min_abonos,
    MAX(abonos) AS max_abonos,
    AVG(abonos) AS promedio_abonos
FROM abono_2026
WHERE cedula IS NOT NULL;
