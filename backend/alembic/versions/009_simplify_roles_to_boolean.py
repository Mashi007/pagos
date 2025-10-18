-- Migración para simplificar roles: rol → is_admin
-- Fecha: 2024-10-18
-- Descripción: Cambiar de sistema de roles múltiples a boolean is_admin

-- Paso 1: Agregar columna is_admin
ALTER TABLE usuarios ADD COLUMN is_admin BOOLEAN DEFAULT FALSE;

-- Paso 2: Migrar datos existentes
-- Los usuarios con rol 'ADMIN' serán is_admin = true
UPDATE usuarios SET is_admin = TRUE WHERE rol = 'ADMIN';

-- Paso 3: Hacer is_admin NOT NULL
ALTER TABLE usuarios ALTER COLUMN is_admin SET NOT NULL;

-- Paso 4: Eliminar columna rol (opcional, comentado por seguridad)
-- ALTER TABLE usuarios DROP COLUMN rol;

-- Verificar migración
SELECT id, email, nombre, apellido, rol, is_admin, is_active 
FROM usuarios 
ORDER BY id;
