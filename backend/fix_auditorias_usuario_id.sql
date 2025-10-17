-- Script SQL para agregar la columna 'usuario_id' a la tabla 'auditorias'
-- Solo ejecuta si la columna no existe para evitar errores.

DO $$
BEGIN
    -- Verificar si la columna ya existe
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'auditorias' AND column_name = 'usuario_id'
    ) THEN
        -- Agregar la columna
        ALTER TABLE auditorias ADD COLUMN usuario_id INTEGER;
        
        -- Crear índice
        CREATE INDEX IF NOT EXISTS ix_auditorias_usuario_id ON auditorias(usuario_id);
        
        -- Intentar agregar foreign key constraint
        BEGIN
            ALTER TABLE auditorias 
            ADD CONSTRAINT fk_auditorias_usuario_id 
            FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE SET NULL;
        EXCEPTION
            WHEN OTHERS THEN
                -- Si no se puede crear la FK, continuar sin ella
                RAISE NOTICE 'No se pudo crear la foreign key constraint: %', SQLERRM;
        END;
        
        RAISE NOTICE 'Columna "usuario_id" agregada a la tabla "auditorias".';
    ELSE
        RAISE NOTICE 'La columna "usuario_id" ya existe en la tabla "auditorias".';
    END IF;
END
$$;

-- Verificar la estructura de la tabla después de la operación
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_name = 'auditorias'
ORDER BY ordinal_position;
