-- Script para agregar columna created_at a modelos_vehiculos
-- Ejecutar en DBeaver

ALTER TABLE modelos_vehiculos 
ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITH TIME ZONE DEFAULT '2025-10-01 00:00:00+00'::timestamptz;

-- Actualizar registros existentes sin created_at con fecha por defecto
UPDATE modelos_vehiculos 
SET created_at = '2025-10-01 00:00:00+00'::timestamptz 
WHERE created_at IS NULL;

