-- Migración: columna numero_deposito en pagos_informes (referencia/depósito del OCR).
-- Soluciona: column "numero_deposito" of relation "pagos_informes" does not exist
-- Ejecutar en la BD (Render u otra). Idempotente.

ALTER TABLE pagos_informes ADD COLUMN IF NOT EXISTS numero_deposito VARCHAR(100);
