-- ============================================================================
-- CORREGIR INTERÉS Y MORA EN PRÉSTAMOS EXISTENTES
-- ============================================================================
-- Script para corregir todos los préstamos y cuotas que tengan interés o mora > 0
-- ⚠️ EJECUTAR CON PRECAUCIÓN - Este script modifica datos existentes
-- ============================================================================

-- ============================================================================
-- PASO 1: VERIFICAR ANTES DE CORREGIR (EJECUTAR PRIMERO)
-- ============================================================================

SELECT 
    '=== VERIFICACIÓN PREVIA ===' AS info;

SELECT 
    COUNT(*) AS prestamos_a_corregir_interes,
    (SELECT COUNT(*) FROM cuotas WHERE monto_mora > 0 OR tasa_mora > 0) AS cuotas_a_corregir_mora
FROM prestamos
WHERE tasa_interes > 0 OR tasa_interes IS NULL;

-- ============================================================================
-- PASO 2: CORREGIR TASA DE INTERÉS EN PRÉSTAMOS
-- ============================================================================

-- ⚠️ DESCOMENTAR PARA EJECUTAR LA CORRECCIÓN
/*
BEGIN;

-- Actualizar tasa_interes a 0.00 en todos los préstamos
UPDATE prestamos 
SET tasa_interes = 0.00
WHERE tasa_interes > 0 OR tasa_interes IS NULL;

-- Verificar cambios
SELECT 
    COUNT(*) AS total_prestamos,
    COUNT(CASE WHEN tasa_interes = 0 THEN 1 END) AS con_interes_0,
    COUNT(CASE WHEN tasa_interes > 0 THEN 1 END) AS con_interes_mayor_0
FROM prestamos;

COMMIT;
*/

-- ============================================================================
-- PASO 3: CORREGIR MORA EN CUOTAS
-- ============================================================================

-- ⚠️ DESCOMENTAR PARA EJECUTAR LA CORRECCIÓN
/*
BEGIN;

-- Actualizar monto_mora a 0.00 en todas las cuotas
UPDATE cuotas 
SET monto_mora = 0.00
WHERE monto_mora > 0;

-- Actualizar tasa_mora a 0.00 en todas las cuotas
UPDATE cuotas 
SET tasa_mora = 0.00
WHERE tasa_mora > 0;

-- Actualizar dias_mora a 0 en cuotas no pagadas (solo si tienen mora)
UPDATE cuotas 
SET dias_mora = 0
WHERE dias_mora > 0 
  AND estado != 'PAGADO'
  AND monto_mora > 0;

-- Verificar cambios
SELECT 
    COUNT(*) AS total_cuotas,
    COUNT(CASE WHEN monto_mora = 0 THEN 1 END) AS con_mora_0,
    COUNT(CASE WHEN monto_mora > 0 THEN 1 END) AS con_mora_mayor_0,
    COUNT(CASE WHEN tasa_mora = 0 THEN 1 END) AS con_tasa_mora_0,
    COUNT(CASE WHEN tasa_mora > 0 THEN 1 END) AS con_tasa_mora_mayor_0
FROM cuotas;

COMMIT;
*/

-- ============================================================================
-- PASO 4: CORRECCIÓN COMPLETA (EJECUTAR TODO EN UNA TRANSACCIÓN)
-- ============================================================================

-- ⚠️ DESCOMENTAR PARA EJECUTAR LA CORRECCIÓN COMPLETA
/*
BEGIN;

-- 1. Corregir tasa_interes en préstamos
UPDATE prestamos 
SET tasa_interes = 0.00
WHERE tasa_interes > 0 OR tasa_interes IS NULL;

-- 2. Corregir monto_mora en cuotas
UPDATE cuotas 
SET monto_mora = 0.00
WHERE monto_mora > 0;

-- 3. Corregir tasa_mora en cuotas
UPDATE cuotas 
SET tasa_mora = 0.00
WHERE tasa_mora > 0;

-- 4. Corregir dias_mora en cuotas no pagadas (solo si tienen mora)
UPDATE cuotas 
SET dias_mora = 0
WHERE dias_mora > 0 
  AND estado != 'PAGADO'
  AND monto_mora > 0;

-- 5. Verificación final
SELECT 
    '=== VERIFICACIÓN POST-CORRECCIÓN ===' AS info;

SELECT 
    (SELECT COUNT(*) FROM prestamos WHERE tasa_interes > 0) AS prestamos_con_interes_restantes,
    (SELECT COUNT(*) FROM cuotas WHERE monto_mora > 0) AS cuotas_con_mora_restantes,
    (SELECT COUNT(*) FROM cuotas WHERE tasa_mora > 0) AS cuotas_con_tasa_mora_restantes;

-- Si todo está correcto, hacer COMMIT. Si hay problemas, hacer ROLLBACK.
COMMIT;
-- ROLLBACK;  -- Descomentar si hay problemas
*/
