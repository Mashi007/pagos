-- ============================================================================
-- Script para crear usuario en Render
-- Usuario: Daniel Casañas (Analista IT)
-- ============================================================================

BEGIN;

-- Insertar usuario admin
INSERT INTO usuarios (
    email,
    cedula,
    password_hash,
    nombre,
    cargo,
    rol,
    is_active,
    created_at,
    updated_at
) VALUES (
    'itmaster@rapicreditca.com',
    'V12345678',
    '$2b$12$51290debb83a53b1b1c3bd476311fccc',
    'Daniel Casañas',
    'Analista IT',
    'admin',
    true,
    NOW(),
    NOW()
);

-- Verificar que se creó
SELECT id, email, nombre, rol, is_active FROM usuarios WHERE email = 'itmaster@rapicreditca.com';

COMMIT;
