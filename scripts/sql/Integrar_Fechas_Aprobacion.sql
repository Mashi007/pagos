-- ============================================================================
-- INTEGRAR FECHAS DE APROBACIÓN A LA TABLA prestamos
-- Actualiza fecha_aprobacion y fecha_base_calculo usando la tabla temporal
-- ============================================================================

-- ============================================================================
-- PASO 1: Verificar antes de actualizar
-- ============================================================================

-- Total de préstamos que se actualizarán
SELECT 
    'Préstamos que se actualizarán' AS metrica,
    COUNT(DISTINCT p.id) AS cantidad
FROM prestamos p
INNER JOIN fechas_aprobacion_temp f ON p.cedula = f.cedula
WHERE p.estado = 'APROBADO';

-- Ejemplo de préstamos que se actualizarán (primeros 5)
SELECT 
    p.id,
    p.cedula,
    p.nombres,
    p.fecha_aprobacion AS fecha_aprobacion_actual,
    p.fecha_base_calculo AS fecha_base_calculo_actual,
    f.fecha_aprobacion AS nueva_fecha_aprobacion,
    f.fecha_aprobacion AS nueva_fecha_base_calculo
FROM prestamos p
INNER JOIN fechas_aprobacion_temp f ON p.cedula = f.cedula
WHERE p.estado = 'APROBADO'
ORDER BY p.id
LIMIT 5;

-- ============================================================================
-- PASO 2: ACTUALIZAR fecha_aprobacion (TIMESTAMP)
-- ============================================================================

-- Actualizar fecha_aprobacion (convertir DATE a TIMESTAMP)
-- ⚠️ EJECUTAR ESTE UPDATE DESPUÉS DE VERIFICAR EL PASO 1
UPDATE prestamos p
SET 
    fecha_aprobacion = f.fecha_aprobacion::TIMESTAMP,
    fecha_actualizacion = CURRENT_TIMESTAMP
FROM fechas_aprobacion_temp f
WHERE p.cedula = f.cedula
    AND p.estado = 'APROBADO'
    AND p.fecha_aprobacion IS NULL;

-- Verificar cuántos se actualizaron
SELECT 
    'Préstamos actualizados con fecha_aprobacion' AS resultado,
    COUNT(*) AS cantidad
FROM prestamos
WHERE estado = 'APROBADO' 
    AND fecha_aprobacion IS NOT NULL
    AND DATE(fecha_aprobacion) IN (SELECT fecha_aprobacion FROM fechas_aprobacion_temp);

-- ============================================================================
-- PASO 3: ACTUALIZAR fecha_base_calculo (DATE)
-- ============================================================================

-- Actualizar fecha_base_calculo (usar la misma fecha de aprobación)
UPDATE prestamos p
SET 
    fecha_base_calculo = f.fecha_aprobacion,
    fecha_actualizacion = CURRENT_TIMESTAMP
FROM fechas_aprobacion_temp f
WHERE p.cedula = f.cedula
    AND p.estado = 'APROBADO'
    AND (p.fecha_base_calculo IS NULL OR p.fecha_base_calculo != f.fecha_aprobacion);

-- Verificar cuántos se actualizaron
SELECT 
    'Préstamos actualizados con fecha_base_calculo' AS resultado,
    COUNT(*) AS cantidad
FROM prestamos p
INNER JOIN fechas_aprobacion_temp f ON p.cedula = f.cedula
WHERE p.estado = 'APROBADO'
    AND p.fecha_base_calculo = f.fecha_aprobacion;

-- ============================================================================
-- PASO 4: ACTUALIZAR usuario_aprobador (si aplica)
-- ============================================================================

-- Si tienes información del usuario que aprobó, puedes actualizarlo también
-- Descomenta y ajusta según tus necesidades:
/*
UPDATE prestamos p
SET 
    usuario_aprobador = 'admin@ejemplo.com', -- O el usuario correspondiente
    fecha_actualizacion = CURRENT_TIMESTAMP
FROM fechas_aprobacion_temp f
WHERE p.cedula = f.cedula
    AND p.estado = 'APROBADO'
    AND p.usuario_aprobador IS NULL;
*/

-- ============================================================================
-- PASO 5: VERIFICACIÓN FINAL
-- ============================================================================

-- Verificar que las fechas se actualizaron correctamente
SELECT 
    'Préstamos con fecha_aprobacion actualizada' AS metrica,
    COUNT(*) AS cantidad
FROM prestamos p
INNER JOIN fechas_aprobacion_temp f ON p.cedula = f.cedula
WHERE p.estado = 'APROBADO'
    AND DATE(p.fecha_aprobacion) = f.fecha_aprobacion;

-- Verificar que fecha_base_calculo se actualizó correctamente
SELECT 
    'Préstamos con fecha_base_calculo actualizada' AS metrica,
    COUNT(*) AS cantidad
FROM prestamos p
INNER JOIN fechas_aprobacion_temp f ON p.cedula = f.cedula
WHERE p.estado = 'APROBADO'
    AND p.fecha_base_calculo = f.fecha_aprobacion;

-- Verificar coincidencia entre fecha_aprobacion y fecha_base_calculo
SELECT 
    'Préstamos donde fecha_base_calculo = fecha_aprobacion' AS metrica,
    COUNT(*) AS cantidad
FROM prestamos
WHERE estado = 'APROBADO'
    AND fecha_aprobacion IS NOT NULL
    AND fecha_base_calculo IS NOT NULL
    AND DATE(fecha_aprobacion) = fecha_base_calculo;

-- Ejemplo de préstamos actualizados (primeros 10)
SELECT 
    p.id,
    p.cedula,
    p.nombres,
    DATE(p.fecha_aprobacion) AS fecha_aprobacion_date,
    p.fecha_base_calculo,
    CASE 
        WHEN DATE(p.fecha_aprobacion) = p.fecha_base_calculo THEN '✅ COINCIDEN'
        ELSE '❌ NO COINCIDEN'
    END AS verificacion
FROM prestamos p
INNER JOIN fechas_aprobacion_temp f ON p.cedula = f.cedula
WHERE p.estado = 'APROBADO'
ORDER BY p.id
LIMIT 10;

-- ============================================================================
-- PASO 6: LIMPIEZA (Opcional)
-- ============================================================================

-- Después de verificar que todo está correcto, puedes eliminar la tabla temporal
-- ⚠️ SOLO EJECUTAR DESPUÉS DE VERIFICAR QUE TODO ESTÁ CORRECTO
/*
DROP TABLE IF EXISTS fechas_aprobacion_temp;
*/

-- ============================================================================
-- RESUMEN FINAL
-- ============================================================================

-- Resumen de estado final
SELECT 
    'Total préstamos aprobados' AS metrica,
    COUNT(*) AS cantidad
FROM prestamos
WHERE estado = 'APROBADO'

UNION ALL

SELECT 
    'Con fecha_aprobacion' AS metrica,
    COUNT(*) AS cantidad
FROM prestamos
WHERE estado = 'APROBADO' 
    AND fecha_aprobacion IS NOT NULL

UNION ALL

SELECT 
    'Con fecha_base_calculo' AS metrica,
    COUNT(*) AS cantidad
FROM prestamos
WHERE estado = 'APROBADO' 
    AND fecha_base_calculo IS NOT NULL

UNION ALL

SELECT 
    'Con ambas fechas y coinciden' AS metrica,
    COUNT(*) AS cantidad
FROM prestamos
WHERE estado = 'APROBADO'
    AND fecha_aprobacion IS NOT NULL
    AND fecha_base_calculo IS NOT NULL
    AND DATE(fecha_aprobacion) = fecha_base_calculo;

