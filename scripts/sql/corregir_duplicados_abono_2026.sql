-- ============================================================================
-- CORRECCIÓN DE DUPLICADOS EN abono_2026
-- ============================================================================
-- Este script identifica y corrige registros duplicados en la tabla abono_2026
-- ============================================================================

-- ----------------------------------------------------------------------------
-- PASO 1: IDENTIFICAR DUPLICADOS
-- ----------------------------------------------------------------------------

SELECT 
    '=== CÉDULAS CON REGISTROS DUPLICADOS ===' AS info;

SELECT 
    cedula,
    COUNT(*) AS total_registros,
    SUM(abonos) AS suma_abonos,
    STRING_AGG(abonos::text, ', ') AS valores_abonos,
    STRING_AGG(id::text, ', ') AS ids_registros
FROM abono_2026
WHERE cedula IS NOT NULL
GROUP BY cedula
HAVING COUNT(*) > 1
ORDER BY COUNT(*) DESC;

-- ----------------------------------------------------------------------------
-- PASO 2: VER DETALLE DE DUPLICADOS
-- ----------------------------------------------------------------------------

SELECT 
    '=== DETALLE DE REGISTROS DUPLICADOS ===' AS info;

SELECT 
    id,
    cedula,
    abonos,
    fecha_creacion,
    fecha_actualizacion
FROM abono_2026
WHERE cedula IN (
    SELECT cedula
    FROM abono_2026
    WHERE cedula IS NOT NULL
    GROUP BY cedula
    HAVING COUNT(*) > 1
)
ORDER BY cedula, id;

-- ----------------------------------------------------------------------------
-- PASO 3: CORREGIR DUPLICADOS (OPCIONAL - DESCOMENTAR PARA EJECUTAR)
-- ----------------------------------------------------------------------------
-- ⚠️ ADVERTENCIA: Este paso eliminará registros duplicados
-- Mantendrá solo el registro con el ID más reciente o el mayor valor de abonos

/*
-- Opción 1: Mantener el registro con el ID más reciente
DELETE FROM abono_2026
WHERE id NOT IN (
    SELECT DISTINCT ON (cedula) id
    FROM abono_2026
    WHERE cedula IS NOT NULL
    ORDER BY cedula, id DESC
);

-- Opción 2: Mantener el registro con el mayor valor de abonos
DELETE FROM abono_2026
WHERE id NOT IN (
    SELECT DISTINCT ON (cedula) id
    FROM abono_2026
    WHERE cedula IS NOT NULL
    ORDER BY cedula, abonos DESC NULLS LAST, id DESC
);

-- Opción 3: Consolidar valores (sumar abonos y mantener un solo registro)
-- Primero actualizar el registro que se mantendrá con la suma
WITH consolidado AS (
    SELECT 
        cedula,
        SUM(abonos) AS total_abonos,
        MIN(id) AS id_a_mantener,
        MAX(fecha_actualizacion) AS ultima_actualizacion
    FROM abono_2026
    WHERE cedula IS NOT NULL
    GROUP BY cedula
    HAVING COUNT(*) > 1
)
UPDATE abono_2026 a
SET 
    abonos = c.total_abonos,
    fecha_actualizacion = c.ultima_actualizacion
FROM consolidado c
WHERE a.cedula = c.cedula
  AND a.id = c.id_a_mantener;

-- Luego eliminar los duplicados restantes
DELETE FROM abono_2026
WHERE id NOT IN (
    SELECT DISTINCT ON (cedula) id
    FROM abono_2026
    WHERE cedula IS NOT NULL
    ORDER BY cedula, id
);
*/

-- ----------------------------------------------------------------------------
-- PASO 4: VERIFICAR QUE NO QUEDEN DUPLICADOS
-- ----------------------------------------------------------------------------

SELECT 
    '=== VERIFICACIÓN POST-CORRECCIÓN ===' AS info;

SELECT 
    COUNT(*) AS total_duplicados
FROM (
    SELECT cedula
    FROM abono_2026
    WHERE cedula IS NOT NULL
    GROUP BY cedula
    HAVING COUNT(*) > 1
) AS duplicados;

-- Si el resultado es 0, no hay duplicados

-- ----------------------------------------------------------------------------
-- PASO 5: AGREGAR CONSTRAINT UNIQUE PARA PREVENIR FUTUROS DUPLICADOS
-- ----------------------------------------------------------------------------
-- ⚠️ ADVERTENCIA: Esto fallará si aún hay duplicados
-- Ejecutar solo después de eliminar todos los duplicados

/*
-- Verificar si ya existe el constraint
SELECT 
    constraint_name,
    constraint_type
FROM information_schema.table_constraints
WHERE table_name = 'abono_2026'
  AND constraint_type = 'UNIQUE';

-- Agregar constraint UNIQUE si no existe
ALTER TABLE abono_2026 
ADD CONSTRAINT uk_abono_2026_cedula UNIQUE (cedula);
*/
