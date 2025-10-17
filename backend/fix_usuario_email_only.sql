-- Script SQL para agregar SOLO la columna usuario_email faltante
-- Ejecutar en DBeaver

DO $$
BEGIN
    -- Verificar y agregar usuario_email si no existe
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'auditorias' AND column_name = 'usuario_email'
    ) THEN
        ALTER TABLE auditorias ADD COLUMN usuario_email VARCHAR(255);
        CREATE INDEX IF NOT EXISTS ix_auditorias_usuario_email ON auditorias(usuario_email);
        RAISE NOTICE 'Columna "usuario_email" agregada a la tabla "auditorias".';
    ELSE
        RAISE NOTICE 'La columna "usuario_email" ya existe en la tabla "auditorias".';
    END IF;
END
$$;

-- Verificar que la columna se agregó
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'auditorias' AND column_name = 'usuario_email';
