-- ============================================================================
-- EJECUTAR CORRECCIÓN DE MORA EN CUOTAS
-- ============================================================================
-- Script listo para ejecutar - Corrige todas las cuotas con mora > 0
-- ⚠️ Este script modificará 15,185 cuotas
-- ============================================================================

BEGIN;

-- ============================================================================
-- CORRECCIÓN COMPLETA DE MORA
-- ============================================================================

-- 1. Corregir monto_mora en todas las cuotas
UPDATE cuotas 
SET monto_mora = 0.00
WHERE monto_mora > 0;

-- 2. Corregir tasa_mora en todas las cuotas
UPDATE cuotas 
SET tasa_mora = 0.00
WHERE tasa_mora > 0;

-- 3. Corregir dias_mora en todas las cuotas (solo las que tienen mora registrada)
UPDATE cuotas 
SET dias_mora = 0
WHERE dias_mora > 0 
  AND (monto_mora > 0 OR tasa_mora > 0);

-- ============================================================================
-- VERIFICACIÓN POST-CORRECCIÓN
-- ============================================================================

SELECT 
    '=== VERIFICACIÓN POST-CORRECCIÓN ===' AS info;

SELECT 
    COUNT(*) AS total_cuotas,
    COUNT(CASE WHEN monto_mora = 0 THEN 1 END) AS con_mora_0,
    COUNT(CASE WHEN monto_mora > 0 THEN 1 END) AS con_mora_mayor_0,
    COUNT(CASE WHEN tasa_mora = 0 THEN 1 END) AS con_tasa_mora_0,
    COUNT(CASE WHEN tasa_mora > 0 THEN 1 END) AS con_tasa_mora_mayor_0,
    COUNT(CASE WHEN dias_mora = 0 THEN 1 END) AS con_dias_mora_0,
    COUNT(CASE WHEN dias_mora > 0 THEN 1 END) AS con_dias_mora_mayor_0
FROM cuotas;

-- Verificar que no queden cuotas con mora
SELECT 
    (SELECT COUNT(*) FROM cuotas WHERE monto_mora > 0) AS cuotas_con_mora_restantes,
    (SELECT COUNT(*) FROM cuotas WHERE tasa_mora > 0) AS cuotas_con_tasa_mora_restantes,
    (SELECT COUNT(*) FROM cuotas WHERE dias_mora > 0 AND estado != 'PAGADO') AS cuotas_con_dias_mora_restantes;

-- Si todo está correcto (todos los valores deben ser 0), hacer COMMIT
-- Si hay problemas, hacer ROLLBACK antes de COMMIT
COMMIT;
-- ROLLBACK;  -- Descomentar solo si hay problemas y quieres revertir
