-- Migración: añadir total_financiamiento y dias_mora a clientes (si faltan).
-- Ejecutar en la BD de Render si aparece: column clientes.total_financiamiento does not exist
-- Ejemplo: psql $DATABASE_URL -f backend/sql/migrate_clientes_add_columns.sql

ALTER TABLE clientes ADD COLUMN IF NOT EXISTS total_financiamiento NUMERIC(14, 2) NULL;
ALTER TABLE clientes ADD COLUMN IF NOT EXISTS dias_mora INTEGER NULL DEFAULT 0;
