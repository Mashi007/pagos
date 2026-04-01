-- ============================================================================
-- Paso 1: ROLLBACK si hay transacción pendiente
-- ============================================================================
ROLLBACK;

-- ============================================================================
-- Paso 2: Verificar estructura actual de la tabla usuarios
-- ============================================================================

-- Ver todas las columnas de usuarios
SELECT column_name, data_type, is_nullable 
FROM information_schema.columns 
WHERE table_name = 'usuarios'
ORDER BY ordinal_position;
