-- ============================================
-- VERIFICACIÓN DE MIGRACIONES APLICADAS
-- ============================================

-- 1. Ver todas las migraciones aplicadas
SELECT 
    version_num,
    is_current,
    created_at
FROM alembic_version
ORDER BY version_num DESC;

-- 2. Verificar si la migración 014 está aplicada
SELECT 
    version_num,
    is_current,
    created_at
FROM alembic_version
WHERE version_num = '014_remove_unique_constraint_cedula';

-- 3. Verificar si la migración 015 está aplicada
SELECT 
    version_num,
    is_current,
    created_at
FROM alembic_version
WHERE version_num = '015_remove_unique_constraint_cedula_fixed';

-- 4. Ver el historial completo de migraciones
SELECT 
    version_num,
    is_current,
    created_at,
    CASE 
        WHEN is_current = true THEN '← ACTUAL'
        ELSE ''
    END as estado
FROM alembic_version
ORDER BY created_at DESC;
