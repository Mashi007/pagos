-- ============================================================================
-- ACTUALIZAR ESTADÍSTICAS DE TABLAS
-- ============================================================================
-- Ejecuta ANALYZE en las tablas principales para que PostgreSQL
-- pueda usar los índices correctamente
-- ============================================================================

ANALYZE prestamos;
ANALYZE cuotas;
ANALYZE pagos;

-- ============================================================================
-- VERIFICAR QUE SE ACTUALIZARON
-- ============================================================================

SELECT 
    schemaname,
    tablename,
    last_analyze,
    last_autoanalyze
FROM pg_stat_user_tables
WHERE tablename IN ('prestamos', 'cuotas', 'pagos')
ORDER BY tablename;

