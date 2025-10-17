-- Script SQL para hacer nullable la columna entidad
-- Ejecutar en DBeaver

DO $$
BEGIN
    -- Hacer nullable la columna entidad
    ALTER TABLE auditorias ALTER COLUMN entidad DROP NOT NULL;
    RAISE NOTICE 'Columna "entidad" ahora es nullable.';
END
$$;

-- Verificar que la columna entidad es nullable
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'auditorias' AND column_name = 'entidad';
