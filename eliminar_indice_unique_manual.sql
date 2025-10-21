-- ============================================
-- ELIMINACIÓN MANUAL DEL ÍNDICE UNIQUE
-- ============================================

-- 1. Eliminar el índice único problemático
DROP INDEX IF EXISTS ix_clientes_cedula;

-- 2. Verificar que se eliminó
SELECT 
    indexname,
    indexdef,
    tablename
FROM pg_indexes 
WHERE tablename = 'clientes' 
    AND indexname LIKE '%cedula%';

-- 3. Crear índice no-unique para performance (opcional)
CREATE INDEX IF NOT EXISTS idx_clientes_cedula_performance 
ON clientes (cedula);

-- 4. Verificar resultado final
SELECT 
    indexname,
    indexdef,
    tablename
FROM pg_indexes 
WHERE tablename = 'clientes' 
    AND indexname LIKE '%cedula%';
