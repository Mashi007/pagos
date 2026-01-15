-- ============================================================================
-- VERIFICACIÓN Y CREACIÓN DE ÍNDICES PARA TABLA configuracion_sistema
-- ============================================================================
-- Fecha: 2025-01-27
-- Propósito: Verificar y crear índices necesarios para optimizar consultas
--            según las mejoras implementadas en el endpoint /configuracion
-- ============================================================================

-- ============================================================================
-- VERIFICACIÓN DE ÍNDICES EXISTENTES
-- ============================================================================

-- Verificar índices actuales en la tabla configuracion_sistema
-- Usar información del catálogo de sistema para mayor compatibilidad
SELECT
    n.nspname AS schemaname,
    t.relname AS tablename,
    i.relname AS indexname,
    pg_get_indexdef(i.oid) AS indexdef
FROM pg_class t
JOIN pg_index ix ON t.oid = ix.indrelid
JOIN pg_class i ON i.oid = ix.indexrelid
JOIN pg_namespace n ON n.oid = t.relnamespace
WHERE t.relname = 'configuracion_sistema'
  AND t.relkind = 'r'
ORDER BY i.relname;

-- ============================================================================
-- CREACIÓN DE ÍNDICES NECESARIOS
-- ============================================================================

-- 1. Índice compuesto para consultas por categoria y clave (usado en optimización N+1)
-- Mejora: Consultas optimizadas en actualizar_configuracion_email/whatsapp/ai
-- Impacto: Reducción significativa de tiempo en bulk operations
CREATE INDEX IF NOT EXISTS idx_configuracion_sistema_categoria_clave
ON configuracion_sistema (categoria, clave)
WHERE categoria IS NOT NULL AND clave IS NOT NULL;

-- 2. Índice compuesto para consultas frecuentes por categoria (ya existe index=True en modelo)
-- Verificar que existe, si no, crearlo
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 
        FROM pg_class t
        JOIN pg_index ix ON t.oid = ix.indrelid
        JOIN pg_class i ON i.oid = ix.indexrelid
        WHERE t.relname = 'configuracion_sistema'
          AND i.relname = 'ix_configuracion_sistema_categoria'
    ) THEN
        CREATE INDEX ix_configuracion_sistema_categoria 
        ON configuracion_sistema (categoria);
        RAISE NOTICE 'Índice ix_configuracion_sistema_categoria creado';
    ELSE
        RAISE NOTICE 'Índice ix_configuracion_sistema_categoria ya existe';
    END IF;
END $$;

-- 3. Índice para clave (ya existe index=True en modelo)
-- Verificar que existe, si no, crearlo
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 
        FROM pg_class t
        JOIN pg_index ix ON t.oid = ix.indrelid
        JOIN pg_class i ON i.oid = ix.indexrelid
        WHERE t.relname = 'configuracion_sistema'
          AND i.relname = 'ix_configuracion_sistema_clave'
    ) THEN
        CREATE INDEX ix_configuracion_sistema_clave 
        ON configuracion_sistema (clave);
        RAISE NOTICE 'Índice ix_configuracion_sistema_clave creado';
    ELSE
        RAISE NOTICE 'Índice ix_configuracion_sistema_clave ya existe';
    END IF;
END $$;

-- 4. Índice para subcategoria (ya existe index=True en modelo)
-- Verificar que existe, si no, crearlo
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 
        FROM pg_class t
        JOIN pg_index ix ON t.oid = ix.indrelid
        JOIN pg_class i ON i.oid = ix.indexrelid
        WHERE t.relname = 'configuracion_sistema'
          AND i.relname = 'ix_configuracion_sistema_subcategoria'
    ) THEN
        CREATE INDEX ix_configuracion_sistema_subcategoria 
        ON configuracion_sistema (subcategoria)
        WHERE subcategoria IS NOT NULL;
        RAISE NOTICE 'Índice ix_configuracion_sistema_subcategoria creado';
    ELSE
        RAISE NOTICE 'Índice ix_configuracion_sistema_subcategoria ya existe';
    END IF;
END $$;

-- ============================================================================
-- VERIFICACIÓN FINAL DE ÍNDICES
-- ============================================================================

-- Mostrar todos los índices después de la creación
SELECT
    n.nspname AS schemaname,
    t.relname AS tablename,
    i.relname AS indexname,
    pg_get_indexdef(i.oid) AS indexdef,
    CASE 
        WHEN i.relname LIKE 'idx_%' THEN '✅ Optimización'
        WHEN i.relname LIKE 'ix_%' THEN '✅ Modelo SQLAlchemy'
        ELSE 'ℹ️ Otro'
    END as tipo
FROM pg_class t
JOIN pg_index ix ON t.oid = ix.indrelid
JOIN pg_class i ON i.oid = ix.indexrelid
JOIN pg_namespace n ON n.oid = t.relnamespace
WHERE t.relname = 'configuracion_sistema'
  AND t.relkind = 'r'
ORDER BY tipo, i.relname;

-- ============================================================================
-- ESTADÍSTICAS DE LA TABLA
-- ============================================================================

-- Actualizar estadísticas para optimizar el planificador de consultas
ANALYZE configuracion_sistema;

-- Mostrar estadísticas de la tabla
SELECT
    schemaname,
    relname AS tablename,
    n_live_tup as registros,
    n_dead_tup as registros_muertos,
    last_vacuum,
    last_autovacuum,
    last_analyze,
    last_autoanalyze
FROM pg_stat_user_tables
WHERE relname = 'configuracion_sistema';

-- ============================================================================
-- VERIFICACIÓN DE RENDIMIENTO
-- ============================================================================

-- Ejemplo de consulta optimizada que debería usar el índice compuesto
EXPLAIN ANALYZE
SELECT *
FROM configuracion_sistema
WHERE categoria = 'EMAIL'
  AND clave IN ('smtp_host', 'smtp_port', 'smtp_user', 'smtp_password');

-- ============================================================================
-- NOTAS
-- ============================================================================
-- 1. Los índices con index=True en el modelo SQLAlchemy se crean automáticamente
--    al ejecutar las migraciones de Alembic
-- 2. El índice compuesto idx_configuracion_sistema_categoria_clave es adicional
--    para optimizar las consultas bulk implementadas
-- 3. Ejecutar ANALYZE después de crear índices para actualizar estadísticas
-- ============================================================================
