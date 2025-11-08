-- ============================================================================
-- SCRIPT PARA VERIFICAR TRIGGERS EN LA TABLA USERS
-- ============================================================================
-- Este script verifica si hay triggers en la base de datos que puedan estar
-- afectando el campo 'cargo' de la tabla 'users'
-- ============================================================================

-- 1. Verificar todos los triggers relacionados con la tabla 'users'
SELECT 
    trigger_name,
    event_manipulation,
    event_object_table,
    action_statement,
    action_timing,
    action_orientation
FROM information_schema.triggers
WHERE event_object_table = 'users'
ORDER BY trigger_name;

-- 2. Verificar funciones que puedan estar relacionadas con users
SELECT 
    routine_name,
    routine_type,
    routine_definition
FROM information_schema.routines
WHERE routine_definition LIKE '%users%'
   OR routine_definition LIKE '%cargo%'
ORDER BY routine_name;

-- 3. Verificar si hay constraints o defaults en la columna cargo
SELECT 
    column_name,
    column_default,
    is_nullable,
    data_type
FROM information_schema.columns
WHERE table_name = 'users' 
  AND column_name = 'cargo';

-- 4. Verificar si hay algún valor por defecto o constraint que pueda estar afectando
SELECT 
    conname AS constraint_name,
    contype AS constraint_type,
    pg_get_constraintdef(oid) AS constraint_definition
FROM pg_constraint
WHERE conrelid = 'users'::regclass
  AND (pg_get_constraintdef(oid) LIKE '%cargo%' OR conname LIKE '%cargo%');

