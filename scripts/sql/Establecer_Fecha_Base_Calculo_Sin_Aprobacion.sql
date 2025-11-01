-- ============================================================================
-- ESTABLECER fecha_base_calculo PARA PRÉSTAMOS SIN fecha_aprobacion
-- SOLUCIÓN PARA PRÉSTAMOS CARGADOS MASIVAMENTE
-- ============================================================================

-- ============================================================================
-- PASO 1: DIAGNÓSTICO - Verificar situación actual
-- ============================================================================

-- Total de préstamos aprobados sin fecha_aprobacion
SELECT 
    'Préstamos aprobados SIN fecha_aprobacion' AS metrica,
    COUNT(*) AS cantidad
FROM prestamos
WHERE estado = 'APROBADO' 
    AND fecha_aprobacion IS NULL;

-- Préstamos aprobados con fecha_registro
SELECT 
    'Préstamos aprobados CON fecha_registro' AS metrica,
    COUNT(*) AS cantidad
FROM prestamos
WHERE estado = 'APROBADO' 
    AND fecha_registro IS NOT NULL;

-- Préstamos aprobados sin fecha_base_calculo
SELECT 
    'Préstamos aprobados SIN fecha_base_calculo' AS metrica,
    COUNT(*) AS cantidad
FROM prestamos
WHERE estado = 'APROBADO' 
    AND fecha_base_calculo IS NULL;

-- ============================================================================
-- PASO 2: VERIFICAR fecha_registro DISPONIBLE
-- ============================================================================

-- Ver rango de fechas de registro
SELECT 
    'Rango de fechas de registro' AS metrica,
    MIN(DATE(fecha_registro)) AS fecha_minima,
    MAX(DATE(fecha_registro)) AS fecha_maxima,
    COUNT(*) AS total
FROM prestamos
WHERE estado = 'APROBADO' 
    AND fecha_registro IS NOT NULL;

-- ============================================================================
-- OPCIÓN A: USAR fecha_registro COMO fecha_base_calculo
-- ============================================================================

-- ESTABLECER fecha_base_calculo = fecha_registro (convertir TIMESTAMP a DATE)
-- ⚠️ EJECUTAR ESTE UPDATE SI QUIERES USAR LA FECHA DE REGISTRO
UPDATE prestamos
SET fecha_base_calculo = DATE(fecha_registro)
WHERE estado = 'APROBADO' 
    AND fecha_base_calculo IS NULL
    AND fecha_registro IS NOT NULL;

-- Verificar cuántos se actualizaron
SELECT 
    'Actualizados con fecha_registro' AS resultado,
    COUNT(*) AS cantidad
FROM prestamos
WHERE estado = 'APROBADO' 
    AND fecha_base_calculo IS NOT NULL
    AND DATE(fecha_registro) = fecha_base_calculo;

-- ============================================================================
-- OPCIÓN B: ESTABLECER FECHA ESPECÍFICA (24/05/2025)
-- ============================================================================

-- ESTABLECER fecha_base_calculo = '2025-05-24' (24/05/2025)
-- ⚠️ EJECUTAR ESTE UPDATE SI QUIERES USAR UNA FECHA ESPECÍFICA
-- Descomenta las siguientes líneas si quieres usar esta opción:

/*
UPDATE prestamos
SET fecha_base_calculo = '2025-05-24'
WHERE estado = 'APROBADO' 
    AND fecha_base_calculo IS NULL;

-- Verificar cuántos se actualizaron
SELECT 
    'Actualizados con fecha 24/05/2025' AS resultado,
    COUNT(*) AS cantidad
FROM prestamos
WHERE estado = 'APROBADO' 
    AND fecha_base_calculo = '2025-05-24';
*/

-- ============================================================================
-- OPCIÓN C: ESTABLECER FECHA ACTUAL
-- ============================================================================

-- ESTABLECER fecha_base_calculo = CURRENT_DATE (fecha de hoy)
-- ⚠️ EJECUTAR ESTE UPDATE SI QUIERES USAR LA FECHA ACTUAL
-- Descomenta las siguientes líneas si quieres usar esta opción:

/*
UPDATE prestamos
SET fecha_base_calculo = CURRENT_DATE
WHERE estado = 'APROBADO' 
    AND fecha_base_calculo IS NULL;

-- Verificar cuántos se actualizaron
SELECT 
    'Actualizados con CURRENT_DATE' AS resultado,
    COUNT(*) AS cantidad
FROM prestamos
WHERE estado = 'APROBADO' 
    AND fecha_base_calculo = CURRENT_DATE;
*/

-- ============================================================================
-- PASO 3: VERIFICACIÓN FINAL
-- ============================================================================

-- Verificar que todos los préstamos aprobados ahora tengan fecha_base_calculo
SELECT 
    'Préstamos aprobados CON fecha_base_calculo (final)' AS metrica,
    COUNT(*) AS cantidad
FROM prestamos
WHERE estado = 'APROBADO' 
    AND fecha_base_calculo IS NOT NULL;

-- Verificar si quedan préstamos sin fecha_base_calculo
SELECT 
    'Préstamos aprobados SIN fecha_base_calculo (debe ser 0)' AS metrica,
    COUNT(*) AS cantidad
FROM prestamos
WHERE estado = 'APROBADO' 
    AND fecha_base_calculo IS NULL;

-- Ejemplo de préstamos actualizados (primeros 5)
SELECT 
    id,
    cedula,
    nombres,
    DATE(fecha_registro) AS fecha_registro_date,
    fecha_base_calculo,
    estado
FROM prestamos
WHERE estado = 'APROBADO' 
    AND fecha_base_calculo IS NOT NULL
ORDER BY id
LIMIT 5;

