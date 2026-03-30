-- Fix: Agregar columna metadata_tecnica a tabla envios_notificacion
-- Error: psycopg2.errors.UndefinedColumn: column "metadata_tecnica" of relation "envios_notificacion" does not exist
-- Causa: El modelo define la columna pero la BD no la tiene

ALTER TABLE envios_notificacion
ADD COLUMN IF NOT EXISTS metadata_tecnica JSON NULL;

-- Verificación
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'envios_notificacion' AND column_name = 'metadata_tecnica';
