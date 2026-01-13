-- ============================================
-- VERIFICAR SI EXISTE LA TABLA prestamos_temporal
-- ============================================

-- Verificar si la tabla existe
SELECT 
    CASE 
        WHEN EXISTS (
            SELECT 1 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            AND table_name = 'prestamos_temporal'
        ) THEN '✅ La tabla prestamos_temporal EXISTE'
        ELSE '❌ La tabla prestamos_temporal NO EXISTE'
    END as estado_tabla;

-- Si existe, mostrar información detallada
SELECT 
    'prestamos_temporal' as tabla,
    COUNT(*) as total_columnas
FROM information_schema.columns 
WHERE table_schema = 'public'
  AND table_name = 'prestamos_temporal';

-- Mostrar estructura completa si existe
SELECT 
    column_name,
    data_type,
    character_maximum_length,
    is_nullable,
    column_default
FROM information_schema.columns 
WHERE table_schema = 'public'
  AND table_name = 'prestamos_temporal'
ORDER BY ordinal_position;

-- Verificar índices si existe
SELECT 
    indexname,
    indexdef
FROM pg_indexes
WHERE schemaname = 'public'
  AND tablename = 'prestamos_temporal';
