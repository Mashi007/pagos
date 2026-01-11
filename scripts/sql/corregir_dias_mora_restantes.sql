-- ============================================================================
-- CORREGIR DÍAS DE MORA RESTANTES
-- ============================================================================
-- Script para corregir las 896 cuotas que aún tienen dias_mora > 0
-- ============================================================================

BEGIN;

-- Corregir dias_mora en todas las cuotas que aún lo tengan > 0
UPDATE cuotas 
SET dias_mora = 0
WHERE dias_mora > 0;

-- Verificación
SELECT 
    '=== VERIFICACIÓN FINAL ===' AS info;

SELECT 
    COUNT(*) AS total_cuotas,
    COUNT(CASE WHEN dias_mora = 0 THEN 1 END) AS con_dias_mora_0,
    COUNT(CASE WHEN dias_mora > 0 THEN 1 END) AS con_dias_mora_mayor_0,
    COUNT(CASE WHEN monto_mora = 0 THEN 1 END) AS con_mora_0,
    COUNT(CASE WHEN tasa_mora = 0 THEN 1 END) AS con_tasa_mora_0
FROM cuotas;

-- Verificar que no queden cuotas con mora o dias_mora
SELECT 
    (SELECT COUNT(*) FROM cuotas WHERE monto_mora > 0) AS cuotas_con_mora,
    (SELECT COUNT(*) FROM cuotas WHERE tasa_mora > 0) AS cuotas_con_tasa_mora,
    (SELECT COUNT(*) FROM cuotas WHERE dias_mora > 0) AS cuotas_con_dias_mora;

COMMIT;
