-- Fix: Agregar columna payload_snapshot a tabla auditoria_cartera_revision
-- Error: psycopg2.errors.UndefinedColumn: column "payload_snapshot" of relation "auditoria_cartera_revision" does not exist
-- Causa: El modelo define la columna pero la BD no la tiene

ALTER TABLE auditoria_cartera_revision
ADD COLUMN IF NOT EXISTS payload_snapshot JSONB NULL;

-- Verificación
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'auditoria_cartera_revision' AND column_name = 'payload_snapshot';
