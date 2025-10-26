-- Script para agregar columna created_at a analistas y concesionarios
-- Ejecutar en DBeaver

-- =====================================================
-- TABLA: analistas
-- =====================================================
ALTER TABLE analistas 
ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITH TIME ZONE DEFAULT '2025-10-01 00:00:00+00'::timestamptz;

ALTER TABLE analistas 
ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;

-- Actualizar registros existentes sin created_at con fecha por defecto
UPDATE analistas 
SET created_at = '2025-10-01 00:00:00+00'::timestamptz 
WHERE created_at IS NULL;

-- =====================================================
-- TABLA: concesionarios
-- =====================================================
ALTER TABLE concesionarios 
ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITH TIME ZONE DEFAULT '2025-10-01 00:00:00+00'::timestamptz;

-- Actualizar registros existentes sin created_at con fecha por defecto
UPDATE concesionarios 
SET created_at = '2025-10-01 00:00:00+00'::timestamptz 
WHERE created_at IS NULL;

-- =====================================================
-- VERIFICACIÓN
-- =====================================================
-- Verificar que las columnas se agregaron correctamente
-- SELECT column_name, data_type, column_default
-- FROM information_schema.columns 
-- WHERE table_name IN ('analistas', 'concesionarios')
-- ORDER BY table_name, ordinal_position;

