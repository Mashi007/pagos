-- ============================================
-- AGREGAR COLUMNA 'canal' A TABLA 'notificaciones'
-- ============================================
-- Este script es seguro y puede ejecutarse múltiples veces
-- Verifica si la columna existe antes de agregarla

DO $$
BEGIN
    -- Verificar si la columna ya existe
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'notificaciones'
          AND column_name = 'canal'
    ) THEN
        -- Agregar columna
        ALTER TABLE notificaciones 
        ADD COLUMN canal VARCHAR(20);
        
        RAISE NOTICE '✅ Columna canal agregada exitosamente';
    ELSE
        RAISE NOTICE 'ℹ️ Columna canal ya existe';
    END IF;
    
    -- Verificar si el índice existe
    IF NOT EXISTS (
        SELECT 1 
        FROM pg_indexes
        WHERE schemaname = 'public'
          AND tablename = 'notificaciones'
          AND indexname = 'ix_notificaciones_canal'
    ) THEN
        -- Crear índice
        CREATE INDEX ix_notificaciones_canal 
        ON notificaciones(canal);
        
        RAISE NOTICE '✅ Índice ix_notificaciones_canal creado exitosamente';
    ELSE
        RAISE NOTICE 'ℹ️ Índice ix_notificaciones_canal ya existe';
    END IF;
END $$;

-- Verificar que se agregó correctamente
SELECT 
    column_name,
    data_type,
    character_maximum_length,
    is_nullable
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'notificaciones'
  AND column_name = 'canal';

-- Verificar índice
SELECT 
    indexname,
    indexdef
FROM pg_indexes
WHERE schemaname = 'public'
  AND tablename = 'notificaciones'
  AND indexname = 'ix_notificaciones_canal';

