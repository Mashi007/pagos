-- Script SQL para agregar TODAS las columnas faltantes en auditorias
-- Ejecutar en DBeaver para resolver definitivamente

DO $$
BEGIN
    -- Verificar y agregar modulo si no existe
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'auditorias' AND column_name = 'modulo'
    ) THEN
        ALTER TABLE auditorias ADD COLUMN modulo VARCHAR(50);
        RAISE NOTICE 'Columna "modulo" agregada a la tabla "auditorias".';
    ELSE
        RAISE NOTICE 'La columna "modulo" ya existe en la tabla "auditorias".';
    END IF;

    -- Verificar y agregar tabla si no existe
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'auditorias' AND column_name = 'tabla'
    ) THEN
        ALTER TABLE auditorias ADD COLUMN tabla VARCHAR(50);
        RAISE NOTICE 'Columna "tabla" agregada a la tabla "auditorias".';
    ELSE
        RAISE NOTICE 'La columna "tabla" ya existe en la tabla "auditorias".';
    END IF;

    -- Verificar y agregar registro_id si no existe
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'auditorias' AND column_name = 'registro_id'
    ) THEN
        ALTER TABLE auditorias ADD COLUMN registro_id INTEGER;
        RAISE NOTICE 'Columna "registro_id" agregada a la tabla "auditorias".';
    ELSE
        RAISE NOTICE 'La columna "registro_id" ya existe en la tabla "auditorias".';
    END IF;

    -- Verificar y agregar fecha si no existe
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'auditorias' AND column_name = 'fecha'
    ) THEN
        ALTER TABLE auditorias ADD COLUMN fecha TIMESTAMP WITH TIME ZONE DEFAULT NOW();
        RAISE NOTICE 'Columna "fecha" agregada a la tabla "auditorias".';
    ELSE
        RAISE NOTICE 'La columna "fecha" ya existe en la tabla "auditorias".';
    END IF;

    -- Crear índices si no existen
    CREATE INDEX IF NOT EXISTS ix_auditorias_modulo ON auditorias(modulo);
    CREATE INDEX IF NOT EXISTS ix_auditorias_tabla ON auditorias(tabla);
    CREATE INDEX IF NOT EXISTS ix_auditorias_registro_id ON auditorias(registro_id);
    CREATE INDEX IF NOT EXISTS ix_auditorias_fecha ON auditorias(fecha);
    
END
$$;

-- Verificar la estructura final de la tabla
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'auditorias'
ORDER BY ordinal_position;
