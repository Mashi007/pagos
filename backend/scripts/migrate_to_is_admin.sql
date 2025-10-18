-- ============================================
-- MIGRACIÓN MANUAL: rol → is_admin
-- ============================================
-- Este script ejecuta la migración de la columna 'rol' a 'is_admin'
-- Equivale a las migraciones 009_simplify_roles_to_boolean.py y 010_fix_roles_final.py

-- PASO 1: Verificar estructura actual
SELECT 
    column_name, 
    data_type, 
    is_nullable, 
    column_default 
FROM 
    information_schema.columns 
WHERE 
    table_name = 'usuarios' 
    AND column_name IN ('rol', 'is_admin')
ORDER BY 
    ordinal_position;

-- PASO 2: Agregar la nueva columna is_admin
ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS is_admin BOOLEAN DEFAULT FALSE;

-- PASO 3: Migrar datos de la columna 'rol' a 'is_admin'
-- Establecer is_admin = TRUE para los usuarios que eran 'ADMIN'
UPDATE usuarios SET is_admin = TRUE WHERE rol = 'ADMIN';

-- Para los demás roles ('USER', 'GERENTE', 'COBRANZAS'), is_admin ya es FALSE por defecto
UPDATE usuarios SET is_admin = FALSE WHERE rol IN ('USER', 'GERENTE', 'COBRANZAS');

-- PASO 4: Hacer la columna is_admin NOT NULL
ALTER TABLE usuarios ALTER COLUMN is_admin SET NOT NULL;

-- PASO 5: Eliminar la columna 'rol' y el tipo ENUM
ALTER TABLE usuarios DROP COLUMN IF EXISTS rol;

-- Eliminar el tipo ENUM 'userrole' si existe
DROP TYPE IF EXISTS userrole;

-- PASO 6: Verificar resultado
SELECT 
    column_name, 
    data_type, 
    is_nullable, 
    column_default 
FROM 
    information_schema.columns 
WHERE 
    table_name = 'usuarios' 
    AND column_name IN ('id', 'email', 'nombre', 'apellido', 'hashed_password', 'is_admin', 'cargo', 'is_active', 'created_at', 'updated_at', 'last_login')
ORDER BY 
    ordinal_position;

-- PASO 7: Mostrar usuarios con sus nuevos roles
SELECT 
    id, 
    email, 
    nombre, 
    apellido, 
    is_admin, 
    is_active, 
    created_at 
FROM 
    usuarios 
ORDER BY 
    id;

-- PASO 8: Verificar que al menos un usuario sea administrador
SELECT 
    COUNT(*) as total_administradores 
FROM 
    usuarios 
WHERE 
    is_admin = TRUE;

-- Si no hay administradores, crear uno por defecto
-- (Descomentar si es necesario)
-- UPDATE usuarios SET is_admin = TRUE WHERE id = 1;
