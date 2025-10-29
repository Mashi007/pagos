-- ============================================
-- VERIFICAR TODAS LAS COLUMNAS DE EVALUACION
-- ============================================

SELECT 
    column_name, 
    data_type, 
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = 'prestamos_evaluacion'
ORDER BY column_name;

