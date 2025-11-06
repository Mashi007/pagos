-- ============================================
-- VERIFICAR COLUMNA 'canal' EN TABLA 'notificaciones'
-- ============================================

-- 1. Verificar si la columna existe
SELECT 
    CASE 
        WHEN EXISTS (
            SELECT 1 
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = 'notificaciones'
              AND column_name = 'canal'
        ) THEN '✅ Columna canal EXISTE'
        ELSE '❌ Columna canal NO EXISTE'
    END AS estado_columna;

-- 2. Ver detalles de la columna si existe
SELECT 
    column_name,
    data_type,
    character_maximum_length,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'notificaciones'
  AND column_name = 'canal';

-- 3. Verificar índice asociado
SELECT 
    CASE 
        WHEN EXISTS (
            SELECT 1 
            FROM pg_indexes
            WHERE schemaname = 'public'
              AND tablename = 'notificaciones'
              AND indexname = 'ix_notificaciones_canal'
        ) THEN '✅ Índice ix_notificaciones_canal EXISTE'
        ELSE '❌ Índice ix_notificaciones_canal NO EXISTE'
    END AS estado_indice;

-- 4. Ver todas las columnas de la tabla (para referencia)
SELECT 
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'notificaciones'
ORDER BY ordinal_position;

-- 5. Si la columna NO existe, ejecutar esto para agregarla:
/*
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'notificaciones'
          AND column_name = 'canal'
    ) THEN
        -- Agregar columna
        ALTER TABLE notificaciones 
        ADD COLUMN canal VARCHAR(20);
        
        -- Crear índice
        CREATE INDEX IF NOT EXISTS ix_notificaciones_canal 
        ON notificaciones(canal);
        
        RAISE NOTICE '✅ Columna canal agregada exitosamente';
    ELSE
        RAISE NOTICE 'ℹ️ Columna canal ya existe';
    END IF;
END $$;
*/

