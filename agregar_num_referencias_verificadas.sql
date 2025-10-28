-- ============================================
-- AGREGAR COLUMNA num_referencias_verificadas
-- ============================================

-- Agregar la columna si no existe
ALTER TABLE prestamos_evaluacion
ADD COLUMN IF NOT EXISTS num_referencias_verificadas INTEGER;

-- Verificar que se agregó
SELECT 
    column_name, 
    data_type, 
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = 'prestamos_evaluacion'
  AND column_name = 'num_referencias_verificadas';

