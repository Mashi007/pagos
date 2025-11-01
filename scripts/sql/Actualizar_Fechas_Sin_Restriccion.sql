-- ============================================================================
-- ACTUALIZAR FECHAS SIN RESTRICCIÓN DE IS NULL
-- Actualiza fecha_aprobacion y fecha_base_calculo usando la tabla temporal
-- ============================================================================

-- ACTUALIZAR fecha_aprobacion (actualiza incluso si ya tiene valor)
UPDATE prestamos p
SET 
    fecha_aprobacion = f.fecha_aprobacion::TIMESTAMP,
    fecha_actualizacion = CURRENT_TIMESTAMP
FROM fechas_aprobacion_temp f
WHERE p.cedula = f.cedula
    AND p.estado = 'APROBADO';

-- Verificar cuántos se actualizaron
SELECT 
    'Préstamos con fecha_aprobacion actualizada' AS resultado,
    COUNT(*) AS cantidad
FROM prestamos p
INNER JOIN fechas_aprobacion_temp f ON p.cedula = f.cedula
WHERE p.estado = 'APROBADO'
    AND DATE(p.fecha_aprobacion) = f.fecha_aprobacion;

-- ACTUALIZAR fecha_base_calculo (más importante para generar cuotas)
UPDATE prestamos p
SET 
    fecha_base_calculo = f.fecha_aprobacion,
    fecha_actualizacion = CURRENT_TIMESTAMP
FROM fechas_aprobacion_temp f
WHERE p.cedula = f.cedula
    AND p.estado = 'APROBADO';

-- Verificar cuántos se actualizaron
SELECT 
    'Préstamos con fecha_base_calculo actualizada' AS resultado,
    COUNT(*) AS cantidad
FROM prestamos p
INNER JOIN fechas_aprobacion_temp f ON p.cedula = f.cedula
WHERE p.estado = 'APROBADO'
    AND p.fecha_base_calculo = f.fecha_aprobacion;

-- VERIFICACIÓN FINAL: Ver ejemplos
SELECT 
    p.id,
    p.cedula,
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

