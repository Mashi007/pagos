-- Script SQL para agregar TODAS las columnas faltantes a la tabla 'auditorias'
-- Ejecutar en DBeaver para resolver definitivamente el problema

DO $$
BEGIN
    -- Verificar y agregar usuario_email si no existe
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'auditorias' AND column_name = 'usuario_email'
    ) THEN
        ALTER TABLE auditorias ADD COLUMN usuario_email VARCHAR(255);
        RAISE NOTICE 'Columna "usuario_email" agregada a la tabla "auditorias".';
    ELSE
        RAISE NOTICE 'La columna "usuario_email" ya existe en la tabla "auditorias".';
    END IF;

    -- Verificar y agregar usuario_id si no existe
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'auditorias' AND column_name = 'usuario_id'
    ) THEN
        ALTER TABLE auditorias ADD COLUMN usuario_id INTEGER;
        RAISE NOTICE 'Columna "usuario_id" agregada a la tabla "auditorias".';
    ELSE
        RAISE NOTICE 'La columna "usuario_id" ya existe en la tabla "auditorias".';
    END IF;

    -- Crear índices si no existen
    CREATE INDEX IF NOT EXISTS ix_auditorias_usuario_email ON auditorias(usuario_email);
    CREATE INDEX IF NOT EXISTS ix_auditorias_usuario_id ON auditorias(usuario_id);
    
    -- Intentar agregar foreign key constraint
    BEGIN
        ALTER TABLE auditorias 
        ADD CONSTRAINT fk_auditorias_usuario_id 
        FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE SET NULL;
        RAISE NOTICE 'Foreign key constraint agregada.';
    EXCEPTION
        WHEN OTHERS THEN
            RAISE NOTICE 'No se pudo crear la foreign key constraint: %', SQLERRM;
    END;
END
$$;

-- Verificar la estructura final de la tabla
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'auditorias'
ORDER BY ordinal_position;
