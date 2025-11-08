-- ============================================================================
-- SCRIPT SQL PARA ACTUALIZAR CONTRASEÑA EN BASE DE DATOS
-- Usuario: itmaster@rapicreditca.com
-- Nueva contraseña: Casa1803+
-- ============================================================================
--
-- INSTRUCCIONES:
-- 1. Primero ejecuta el script Python para obtener el hash correcto:
--    python scripts/actualizar_password_sql.py itmaster@rapicreditca.com Casa1803+
--
-- 2. Copia el hash generado y reemplázalo en la línea del UPDATE
--
-- 3. Ejecuta este script en tu base de datos PostgreSQL
--
-- ============================================================================

BEGIN;

-- Verificar que el usuario existe antes de actualizar
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

-- Si el usuario existe, actualizar la contraseña
-- IMPORTANTE: Reemplaza 'HASH_AQUI' con el hash generado por el script Python
UPDATE users
SET 
    hashed_password = 'HASH_AQUI',  -- ⚠️ REEMPLAZAR con hash generado por Python
    updated_at = NOW()
WHERE email = 'itmaster@rapicreditca.com';

-- Verificar que se actualizó correctamente
SELECT 
    id,
    email,
    nombre,
    apellido,
    is_admin,
    is_active,
    updated_at,
    CASE 
        WHEN updated_at > NOW() - INTERVAL '1 minute' THEN '✅ Contraseña actualizada correctamente'
        ELSE '⚠️ Verificar actualización'
    END as estado
FROM users
WHERE email = 'itmaster@rapicreditca.com';

-- Confirmar cambios
COMMIT;

-- ============================================================================
-- MÉTODO ALTERNATIVO: Usar script Python directo (RECOMENDADO)
-- ============================================================================
-- En lugar de ejecutar SQL manualmente, puedes usar:
--
--   python scripts/cambiar_password_usuario.py itmaster@rapicreditca.com Casa1803+
--
-- Este script actualiza directamente en la BD sin necesidad de SQL manual
-- ============================================================================

