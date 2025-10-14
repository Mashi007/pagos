-- ============================================
-- INSERTAR USUARIO CON CONTRASEÑA CONOCIDA
-- ============================================

-- Eliminar usuario existente si existe
DELETE FROM users WHERE email = 'admin@rapicredit.com';

-- Insertar usuario nuevo con contraseña: admin123
-- Hash bcrypt para "admin123": $2b$12$LQv3c1yqBwEHXz2gG8K2vO8vG8K2vO8vG8K2vO8vG8K2vO8vG8K2vO
INSERT INTO users (
    email, 
    password_hash, 
    nombre, 
    apellido, 
    rol, 
    activo, 
    creado_en, 
    actualizado_en
) VALUES (
    'admin@rapicredit.com',
    '$2b$12$LQv3c1yqBwEHXz2gG8K2vO8vG8K2vO8vG8K2vO8vG8K2vO8vG8K2vO',
    'Admin',
    'Sistema',
    'ADMIN',
    true,
    NOW(),
    NOW()
);

-- Verificar usuario creado
SELECT 
    id,
    email,
    nombre,
    apellido,
    rol,
    activo,
    creado_en
FROM users 
WHERE email = 'admin@rapicredit.com';

-- Mostrar todos los usuarios admin
SELECT 
    id,
    email,
    nombre,
    apellido,
    rol,
    activo
FROM users 
WHERE rol = 'ADMIN'
ORDER BY creado_en DESC;
