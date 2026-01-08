-- ============================================================================
-- VERIFICAR PROGRESO DE IMPORTACIÓN
-- ============================================================================

-- 1. Verificar cuántas filas se han importado hasta ahora
SELECT 
    'PROGRESO IMPORTACIÓN' AS verificacion,
    COUNT(*) AS filas_importadas,
    CASE 
        WHEN COUNT(*) = 0 THEN '⏳ Esperando inicio de importación...'
        WHEN COUNT(*) < 4800 THEN CONCAT('⏳ En progreso: ', COUNT(*)::text, ' de 4,800 filas (', ROUND(COUNT(*) * 100.0 / 4800, 1)::text, '%)')
        WHEN COUNT(*) = 4800 THEN '✅ IMPORTACIÓN COMPLETA (4,800 filas)'
        ELSE CONCAT('⚠️ Importadas: ', COUNT(*)::text, ' filas (más de lo esperado)')
    END AS estado
FROM tabla_comparacion_externa;

-- 2. Verificar si hay errores (valores NULL críticos)
SELECT 
    'VERIFICACIÓN DE ERRORES' AS verificacion,
    COUNT(*) AS total_filas,
    COUNT(CASE WHEN cedula IS NULL OR cedula = '' THEN 1 END) AS sin_cedula,
    COUNT(CASE WHEN abonos IS NULL THEN 1 END) AS sin_abonos,
    COUNT(CASE WHEN total_financiamiento IS NULL THEN 1 END) AS sin_financiamiento,
    CASE 
        WHEN COUNT(CASE WHEN cedula IS NULL OR cedula = '' THEN 1 END) > 0 THEN '⚠️ Hay filas sin cédula'
        WHEN COUNT(CASE WHEN abonos IS NULL THEN 1 END) > 0 THEN '⚠️ Hay filas sin abonos'
        ELSE '✅ Sin errores aparentes'
    END AS estado
FROM tabla_comparacion_externa;

-- 3. Verificar valores numéricos (confirmar que no hay overflow)
SELECT 
    'VERIFICACIÓN NUMÉRICA' AS verificacion,
    COUNT(*) AS total_filas,
    MAX(abonos) AS max_abonos,
    MIN(abonos) AS min_abonos,
    SUM(abonos) AS total_abonos_sum,
    CASE 
        WHEN MAX(abonos) > 999999999999.99 THEN '✅ Valores grandes manejados correctamente'
        WHEN MAX(abonos) IS NULL THEN '⏳ Esperando datos...'
        ELSE '✅ Valores normales'
    END AS estado_overflow
FROM tabla_comparacion_externa;

-- 4. Verificar última fecha de importación (si existe columna fecha_importacion)
SELECT 
    'ÚLTIMA IMPORTACIÓN' AS verificacion,
    MAX(fecha_importacion) AS ultima_fecha_importacion,
    COUNT(*) AS filas_importadas
FROM tabla_comparacion_externa
WHERE fecha_importacion IS NOT NULL;

-- 5. Resumen rápido
SELECT 
    '📊 RESUMEN' AS verificacion,
    CONCAT(
        'Filas importadas: ', COUNT(*)::text, ' / 4,800. ',
        CASE 
            WHEN COUNT(*) = 0 THEN 'Esperando inicio...'
            WHEN COUNT(*) < 4800 THEN CONCAT('Progreso: ', ROUND(COUNT(*) * 100.0 / 4800, 1)::text, '%')
            WHEN COUNT(*) = 4800 THEN '✅ COMPLETA'
            ELSE '⚠️ Verificar'
        END
    ) AS estado
FROM tabla_comparacion_externa;
