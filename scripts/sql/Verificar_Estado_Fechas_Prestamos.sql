-- ============================================================================
-- VERIFICAR ESTADO DE FECHAS EN PRÉSTAMOS
-- Para entender por qué el UPDATE no actualizó filas
-- ============================================================================

-- Verificar si los préstamos ya tienen fecha_aprobacion
SELECT 
    'Préstamos con fecha_aprobacion' AS metrica,
    COUNT(*) AS cantidad
FROM prestamos p
INNER JOIN fechas_aprobacion_temp f ON p.cedula = f.cedula
WHERE p.estado = 'APROBADO'
    AND p.fecha_aprobacion IS NOT NULL;

-- Verificar préstamos sin fecha_aprobacion (que sí se actualizarían)
SELECT 
    'Préstamos SIN fecha_aprobacion (se actualizarían)' AS metrica,
    COUNT(*) AS cantidad
FROM prestamos p
INNER JOIN fechas_aprobacion_temp f ON p.cedula = f.cedula
WHERE p.estado = 'APROBADO'
    AND p.fecha_aprobacion IS NULL;

-- Ver ejemplo de préstamos que coinciden
SELECT 
    p.id,
    p.cedula,
    p.estado,
    p.fecha_aprobacion,
    p.fecha_base_calculo,
    f.fecha_aprobacion AS fecha_en_temp,
    CASE 
        WHEN p.fecha_aprobacion IS NULL THEN '✅ Se actualizaría'
        WHEN DATE(p.fecha_aprobacion) = f.fecha_aprobacion THEN '⚠️ Ya tiene la misma fecha'
        ELSE '⚠️ Tiene fecha diferente'
    END AS estado
FROM prestamos p
INNER JOIN fechas_aprobacion_temp f ON p.cedula = f.cedula
WHERE p.estado = 'APROBADO'
ORDER BY p.id
LIMIT 10;

