-- ============================================================================
-- Script SQL para actualizar contraseña del usuario itmaster@rapicreditca.com
-- Nueva contraseña: Casa1803+
-- ============================================================================
-- 
-- INSTRUCCIONES:
-- 1. Ejecuta este script en tu base de datos PostgreSQL
-- 2. Verifica que el usuario existe antes de actualizar
-- 3. Confirma los cambios con COMMIT
--
-- Para ejecutar desde línea de comandos:
--   psql -U tu_usuario -d tu_base_de_datos -f UPDATE_PASSWORD_itmaster.sql
--
-- O copia y pega este contenido en pgAdmin, DBeaver, o tu cliente SQL favorito
-- ============================================================================

-- Paso 1: Verificar que el usuario existe
SELECT 
    id,
    email,
    nombre,
    apellido,
    is_admin,
    is_active,
    created_at,
    updated_at
FROM users
WHERE email = 'itmaster@rapicreditca.com';

-- Paso 2: Actualizar contraseña
-- NOTA: El hash se generará automáticamente cuando ejecutes el script Python
--       o puedes usar el script Python para obtener el hash correcto
UPDATE users
SET 
    hashed_password = 'REEMPLAZAR_CON_HASH_GENERADO',
    updated_at = NOW()
WHERE email = 'itmaster@rapicreditca.com';

-- Paso 3: Verificar que se actualizó correctamente
SELECT 
    id,
    email,
    nombre,
    apellido,
    is_admin,
    is_active,
    updated_at,
    'Verificar que updated_at cambió' as verificacion
FROM users
WHERE email = 'itmaster@rapicreditca.com';

-- Paso 4: Confirmar cambios (descomentar para ejecutar)
-- COMMIT;

-- ============================================================================
-- IMPORTANTE: 
-- Este script es una plantilla. Para obtener el hash correcto, ejecuta:
--   python scripts/actualizar_password_sql.py itmaster@rapicreditca.com Casa1803+
-- ============================================================================

