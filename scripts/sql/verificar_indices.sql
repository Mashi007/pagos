-- ============================================================================
-- SCRIPT DE VERIFICACIÓN DE ÍNDICES
-- ============================================================================
-- Este script verifica que los índices estén creados y funcionando correctamente
-- ============================================================================

-- ============================================================================
-- 1. VERIFICAR ÍNDICES DEL SCRIPT
-- ============================================================================

SELECT 
    'Índices del Script' AS categoria,
    tablename,
    indexname,
    CASE 
        WHEN indexname IN (
            'idx_prestamos_fecha_aprobacion_ym',
            'idx_prestamos_cedula_estado',
            'idx_prestamos_aprobacion_estado_analista',
            'idx_prestamos_concesionario_estado',
            'idx_prestamos_modelo_estado',
            'idx_cuotas_fecha_vencimiento_ym',
            'idx_cuotas_prestamo_fecha_vencimiento',
            'idx_pagos_fecha_pago_activo',
            'idx_pagos_prestamo_fecha'
        ) THEN '✅ Del Script'
        ELSE 'Otro Índice'
    END AS origen
FROM pg_indexes
WHERE schemaname = 'public'
  AND tablename IN ('prestamos', 'cuotas', 'pagos')
  AND (
      indexname LIKE 'idx_prestamos_%' 
      OR indexname LIKE 'idx_cuotas_%'
      OR indexname LIKE 'idx_pagos_%'
  )
ORDER BY tablename, indexname;

-- ============================================================================
-- 2. VERIFICAR ESTADO DE LOS ÍNDICES
-- ============================================================================

SELECT 
    i.indexrelid::regclass AS index_name,
    t.relname AS table_name,
    i.indisvalid AS es_valido,
    i.indisready AS esta_listo,
    i.indislive AS esta_activo,
    CASE 
        WHEN i.indisvalid AND i.indisready AND i.indislive THEN '✅ OK'
        ELSE '⚠️ PROBLEMA'
    END AS estado
FROM pg_index i
JOIN pg_class t ON i.indrelid = t.oid
WHERE t.relname IN ('prestamos', 'cuotas', 'pagos')
  AND i.indexrelid::regclass::text LIKE 'idx_%'
ORDER BY t.relname, i.indexrelid::regclass;

-- ============================================================================
-- 3. TAMAÑO DE TABLAS E ÍNDICES
-- ============================================================================

SELECT 
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS tamaño_total,
    pg_size_pretty(pg_relation_size(schemaname||'.'||tablename)) AS tamaño_tabla,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename) - 
                   pg_relation_size(schemaname||'.'||tablename)) AS tamaño_indices,
    (SELECT COUNT(*) FROM information_schema.columns 
     WHERE table_schema = schemaname AND table_name = tablename) AS num_columnas
FROM pg_tables
WHERE schemaname = 'public'
  AND tablename IN ('prestamos', 'cuotas', 'pagos')
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- ============================================================================
-- 4. ESTADÍSTICAS DE TABLAS
-- ============================================================================

SELECT 
    schemaname,
    tablename,
    last_analyze,
    last_autoanalyze,
    CASE 
        WHEN last_analyze IS NULL AND last_autoanalyze IS NULL THEN '⚠️ Nunca analizada'
        WHEN last_analyze > NOW() - INTERVAL '7 days' THEN '✅ Reciente'
        WHEN last_autoanalyze > NOW() - INTERVAL '7 days' THEN '✅ Reciente (auto)'
        ELSE '⚠️ Desactualizada'
    END AS estado_estadisticas
FROM pg_stat_user_tables
WHERE tablename IN ('prestamos', 'cuotas', 'pagos')
ORDER BY tablename;

-- ============================================================================
-- 5. RECOMENDACIÓN: ACTUALIZAR ESTADÍSTICAS
-- ============================================================================

-- Descomentar para ejecutar:
-- ANALYZE prestamos;
-- ANALYZE cuotas;
-- ANALYZE pagos;

-- ============================================================================
-- 6. VERIFICAR USO DE ÍNDICES (Requiere ejecutar queries primero)
-- ============================================================================

SELECT 
    schemaname,
    tablename,
    indexrelname AS index_name,
    idx_scan AS veces_usado,
    idx_tup_read AS tuplas_leidas,
    idx_tup_fetch AS tuplas_obtenidas,
    CASE 
        WHEN idx_scan = 0 THEN '⚠️ Nunca usado'
        WHEN idx_scan < 10 THEN '🟡 Poco usado'
        ELSE '✅ Usado'
    END AS estado_uso
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
  AND tablename IN ('prestamos', 'cuotas', 'pagos')
  AND indexrelname LIKE 'idx_%'
ORDER BY tablename, idx_scan DESC;

-- ============================================================================
-- NOTAS
-- ============================================================================
-- 1. Si un índice muestra "Nunca usado", puede ser porque:
--    - La tabla es pequeña y PostgreSQL prefiere Seq Scan
--    - Las queries no coinciden con el índice
--    - Las estadísticas están desactualizadas
--
-- 2. Para forzar actualización de estadísticas:
--    ANALYZE prestamos;
--    ANALYZE cuotas;
--    ANALYZE pagos;
--
-- 3. Para verificar uso de índice en una query específica:
--    EXPLAIN ANALYZE SELECT ... FROM prestamos WHERE ...;
-- ============================================================================

