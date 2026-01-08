-- ============================================================================
-- VERIFICACIÓN DE IMPORTACIÓN COMPLETA
-- ============================================================================

-- 1. Verificar total de filas importadas
SELECT 
    'TOTAL FILAS IMPORTADAS' AS verificacion,
    COUNT(*) AS total_filas,
    CASE 
        WHEN COUNT(*) = 4800 THEN '✅ COMPLETA (4,800 filas)'
        WHEN COUNT(*) > 0 THEN CONCAT('⚠️ PARCIAL (', COUNT(*)::text, ' de 4,800 filas)')
        ELSE '❌ SIN DATOS'
    END AS estado
FROM tabla_comparacion_externa;

-- 2. Verificar cédulas únicas
SELECT 
    'CEDULAS UNICAS' AS verificacion,
    COUNT(DISTINCT cedula) AS cedulas_unicas,
    COUNT(*) AS total_filas,
    CASE 
        WHEN COUNT(DISTINCT cedula) < COUNT(*) THEN CONCAT('✅ Múltiples préstamos por cliente (', (COUNT(*) - COUNT(DISTINCT cedula))::text, ' duplicados)')
        ELSE '⚠️ Una fila por cédula'
    END AS estado
FROM tabla_comparacion_externa;

-- 3. Verificar valores numéricos (sin errores de overflow)
SELECT 
    'VALORES NUMERICOS' AS verificacion,
    COUNT(*) AS total_filas,
    COUNT(CASE WHEN abonos IS NOT NULL THEN 1 END) AS con_abonos,
    COUNT(CASE WHEN total_financiamiento IS NOT NULL THEN 1 END) AS con_financiamiento,
    SUM(total_financiamiento) AS total_financiamiento_sum,
    SUM(abonos) AS total_abonos_sum,
    MAX(abonos) AS max_abonos,
    MIN(abonos) AS min_abonos,
    CASE 
        WHEN MAX(abonos) > 999999999999.99 THEN '✅ Valores grandes manejados correctamente'
        ELSE '⚠️ Verificar valores'
    END AS estado_overflow
FROM tabla_comparacion_externa;

-- 4. Verificar filas con valores NULL críticos
SELECT 
    'VALORES NULL' AS verificacion,
    COUNT(*) AS total_filas,
    COUNT(CASE WHEN cedula IS NULL OR cedula = '' THEN 1 END) AS sin_cedula,
    COUNT(CASE WHEN nombres IS NULL OR nombres = '' THEN 1 END) AS sin_nombres,
    COUNT(CASE WHEN total_financiamiento IS NULL THEN 1 END) AS sin_financiamiento,
    COUNT(CASE WHEN abonos IS NULL THEN 1 END) AS sin_abonos
FROM tabla_comparacion_externa;

-- 5. Verificar distribución por estado
SELECT 
    'DISTRIBUCION POR ESTADO' AS verificacion,
    estado,
    COUNT(*) AS cantidad,
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM tabla_comparacion_externa), 2) AS porcentaje
FROM tabla_comparacion_externa
GROUP BY estado
ORDER BY cantidad DESC;

-- 6. Verificar modalidad de pago
SELECT 
    'MODALIDAD DE PAGO' AS verificacion,
    modalidad_pago,
    COUNT(*) AS cantidad
FROM tabla_comparacion_externa
GROUP BY modalidad_pago
ORDER BY cantidad DESC;

-- 7. Verificar si hay valores problemáticos en abonos
SELECT 
    'VALORES PROBLEMATICOS ABONOS' AS verificacion,
    COUNT(*) AS total_filas,
    COUNT(CASE WHEN abonos > 999999999999999.99 THEN 1 END) AS exceden_limite,
    COUNT(CASE WHEN abonos < 0 THEN 1 END) AS valores_negativos,
    COUNT(CASE WHEN abonos = 0 THEN 1 END) AS valores_cero
FROM tabla_comparacion_externa
WHERE abonos IS NOT NULL;

-- 8. Resumen final
SELECT 
    '✅ RESUMEN FINAL' AS verificacion,
    CONCAT(
        'Total importado: ', COUNT(*)::text, ' filas. ',
        CASE 
            WHEN COUNT(*) = 4800 THEN 'Importación completa.'
            WHEN COUNT(*) > 0 THEN CONCAT('Faltan ', (4800 - COUNT(*)::text), ' filas.')
            ELSE 'Sin datos importados.'
        END
    ) AS estado
FROM tabla_comparacion_externa;
