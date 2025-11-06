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
-- VERIFICAR QUE SE ACTUALIZARON (CORREGIDO)
-- ============================================================================

SELECT 
    schemaname,
    relname AS tablename,
    last_analyze,
    last_autoanalyze
FROM pg_stat_user_tables
WHERE relname IN ('prestamos', 'cuotas', 'pagos')
ORDER BY relname;

