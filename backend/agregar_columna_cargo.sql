-- Script SQL para agregar columna cargo a tabla usuarios
-- Ejecutar directamente en la base de datos PostgreSQL

-- Verificar si la columna ya existe
DO $$
BEGIN
    -- Verificar si la columna cargo existe
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'usuarios' 
        AND column_name = 'cargo'
    ) THEN
        -- Agregar la columna cargo
        ALTER TABLE usuarios ADD COLUMN cargo VARCHAR(100);
        
        -- Crear índice en la columna cargo
        CREATE INDEX IF NOT EXISTS ix_usuarios_cargo ON usuarios(cargo);
        
        RAISE NOTICE 'Columna cargo agregada exitosamente a tabla usuarios';
    ELSE
        RAISE NOTICE 'Columna cargo ya existe en tabla usuarios';
    END IF;
END $$;

-- Verificar la estructura de la tabla usuarios
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns 
WHERE table_name = 'usuarios' 
ORDER BY ordinal_position;
