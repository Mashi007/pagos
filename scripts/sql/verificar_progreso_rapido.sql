-- ============================================================================
-- VERIFICACIÓN RÁPIDA DE PROGRESO DE IMPORTACIÓN
-- ============================================================================
-- Ejecuta este script mientras la importación está en proceso
-- ============================================================================

-- VERIFICACIÓN RÁPIDA: Cuántas filas se han importado hasta ahora
SELECT 
    COUNT(*) AS filas_importadas,
    ROUND(COUNT(*) * 100.0 / 4800, 1) AS porcentaje_completado,
    CASE 
        WHEN COUNT(*) = 0 THEN '⏳ Esperando inicio...'
        WHEN COUNT(*) < 4800 THEN CONCAT('⏳ En progreso: ', COUNT(*)::text, ' de 4,800 (', ROUND(COUNT(*) * 100.0 / 4800, 1)::text, '%)')
        WHEN COUNT(*) = 4800 THEN '✅ IMPORTACIÓN COMPLETA'
        ELSE CONCAT('⚠️ ', COUNT(*)::text, ' filas (más de lo esperado)')
    END AS estado
FROM tabla_comparacion_externa;
