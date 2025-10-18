-- ============================================
-- CONSULTAR ESTRUCTURA REAL DE LA TABLA USUARIOS
-- ============================================

-- 1. Ver todas las columnas de la tabla usuarios
SELECT 
    column_name as "Campo",
    data_type as "Tipo",
    is_nullable as "Permite NULL",
    column_default as "Valor por defecto",
    character_maximum_length as "Longitud máxima"
FROM information_schema.columns 
WHERE table_name = 'usuarios' 
ORDER BY ordinal_position;

-- 2. Ver solo los nombres de las columnas
SELECT column_name 
FROM information_schema.columns 
WHERE table_name = 'usuarios' 
ORDER BY ordinal_position;

-- 3. Verificar si existen campos específicos
SELECT 
    CASE WHEN EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'usuarios' AND column_name = 'nombre'
    ) THEN 'SÍ' ELSE 'NO' END as "Existe campo 'nombre'",
    
    CASE WHEN EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'usuarios' AND column_name = 'apellido'
    ) THEN 'SÍ' ELSE 'NO' END as "Existe campo 'apellido'",
    
    CASE WHEN EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'usuarios' AND column_name = 'full_name'
    ) THEN 'SÍ' ELSE 'NO' END as "Existe campo 'full_name'",
    
    CASE WHEN EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'usuarios' AND column_name = 'cargo'
    ) THEN 'SÍ' ELSE 'NO' END as "Existe campo 'cargo'";

-- 4. Ver datos de ejemplo (si existen)
SELECT * FROM usuarios LIMIT 1;

-- 5. Contar total de usuarios
SELECT COUNT(*) as total_usuarios FROM usuarios;
