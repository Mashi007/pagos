-- ============================================================================
-- Paso 1: Crear columna cedula si no existe
-- ============================================================================

-- Agregar columna cedula
ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS cedula VARCHAR(50);

-- Crear índice único para cedula
CREATE UNIQUE INDEX IF NOT EXISTS ix_usuarios_cedula ON usuarios(cedula);

-- Hacer cedula NOT NULL y UNIQUE
ALTER TABLE usuarios 
ALTER COLUMN cedula SET NOT NULL;

-- ============================================================================
-- Paso 2: Crear usuario Daniel Casañas
-- ============================================================================

BEGIN;

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
SELECT id, email, nombre, cedula, rol, is_active FROM usuarios WHERE email = 'itmaster@rapicreditca.com';

COMMIT;
