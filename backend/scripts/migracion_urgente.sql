-- =====================================================
-- MIGRACIÓN URGENTE: ROL → IS_ADMIN
-- Ejecutar este código directamente en la base de datos
-- =====================================================

-- PASO 1: Verificar estado actual
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

-- PASO 2: Ver usuarios actuales por rol
SELECT 
    rol, 
    COUNT(*) as cantidad,
    STRING_AGG(email, ', ') as emails
FROM 
    usuarios 
GROUP BY 
    rol;

-- PASO 3: Agregar columna is_admin
ALTER TABLE usuarios ADD COLUMN is_admin BOOLEAN DEFAULT FALSE;

-- PASO 4: Migrar datos de rol a is_admin
-- ADMIN → is_admin = TRUE
UPDATE usuarios SET is_admin = TRUE WHERE rol = 'ADMIN';

-- Otros roles → is_admin = FALSE (ya es FALSE por defecto)
UPDATE usuarios SET is_admin = FALSE WHERE rol IN ('USER', 'GERENTE', 'COBRANZAS');

-- PASO 5: Hacer is_admin NOT NULL
ALTER TABLE usuarios ALTER COLUMN is_admin SET NOT NULL;

-- PASO 6: Eliminar columna rol
ALTER TABLE usuarios DROP COLUMN rol;

-- PASO 7: Eliminar tipo ENUM userrole
DROP TYPE IF EXISTS userrole;

-- PASO 8: Verificar resultado
SELECT 
    column_name, 
    data_type, 
    is_nullable, 
    column_default 
FROM 
    information_schema.columns 
WHERE 
    table_name = 'usuarios' 
    AND column_name = 'is_admin';

-- PASO 9: Verificar usuarios migrados
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

-- PASO 10: Contar administradores
SELECT 
    COUNT(*) as total_administradores 
FROM 
    usuarios 
WHERE 
    is_admin = TRUE;

-- PASO 11: Si no hay administradores, crear uno
-- (Descomenta la siguiente línea si es necesario)
-- UPDATE usuarios SET is_admin = TRUE WHERE id = 1;

-- =====================================================
-- VERIFICACIÓN FINAL
-- =====================================================
SELECT 
    'MIGRACIÓN COMPLETADA' as status,
    COUNT(*) as total_usuarios,
    SUM(CASE WHEN is_admin = TRUE THEN 1 ELSE 0 END) as administradores,
    SUM(CASE WHEN is_admin = FALSE THEN 1 ELSE 0 END) as usuarios_normales
FROM 
    usuarios;
