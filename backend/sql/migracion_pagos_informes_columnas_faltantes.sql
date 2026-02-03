-- Migración: asegurar que pagos_informes tenga todas las columnas del modelo (PagosInforme).
-- Útil cuando la tabla existía con un esquema antiguo (sin nombre_banco, numero_deposito, etc.) y CREATE TABLE IF NOT EXISTS no la alteró.
-- Ejecutar en la BD. Cada ADD COLUMN usa IF NOT EXISTS, así que es idempotente.

ALTER TABLE pagos_informes ADD COLUMN IF NOT EXISTS nombre_banco VARCHAR(255);
ALTER TABLE pagos_informes ADD COLUMN IF NOT EXISTS numero_deposito VARCHAR(100);
ALTER TABLE pagos_informes ADD COLUMN IF NOT EXISTS numero_documento VARCHAR(100);
ALTER TABLE pagos_informes ADD COLUMN IF NOT EXISTS humano VARCHAR(20);
ALTER TABLE pagos_informes ADD COLUMN IF NOT EXISTS observacion TEXT;
