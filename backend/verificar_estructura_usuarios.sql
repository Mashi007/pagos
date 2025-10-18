-- ============================================
-- VERIFICAR ESTRUCTURA REAL DE LA TABLA USUARIOS
-- ============================================

-- 1. Verificar estructura de la tabla usuarios
SELECT 
    column_name,
    data_type,
    is_nullable,
    column_default,
    character_maximum_length
FROM information_schema.columns 
WHERE table_name = 'usuarios' 
ORDER BY ordinal_position;

-- 2. Verificar datos existentes
SELECT 
    id,
    email,
    -- Verificar qué campos existen realmente
    CASE 
        WHEN EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'usuarios' AND column_name = 'nombre') 
        THEN nombre 
        ELSE NULL 
    END as nombre,
    CASE 
        WHEN EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'usuarios' AND column_name = 'apellido') 
        THEN apellido 
        ELSE NULL 
    END as apellido,
    CASE 
        WHEN EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'usuarios' AND column_name = 'full_name') 
        THEN full_name 
        ELSE NULL 
    END as full_name,
    CASE 
        WHEN EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'usuarios' AND column_name = 'cargo') 
        THEN cargo 
        ELSE NULL 
    END as cargo,
    rol,
    is_active,
    created_at
FROM usuarios 
LIMIT 5;

-- 3. Verificar todos los campos disponibles
SELECT column_name 
FROM information_schema.columns 
WHERE table_name = 'usuarios' 
ORDER BY ordinal_position;

-- 4. Verificar si hay datos en la tabla
SELECT COUNT(*) as total_usuarios FROM usuarios;

-- 5. Verificar usuario Daniel específicamente
SELECT * FROM usuarios WHERE email = 'itmaster@rapicreditca.com';
