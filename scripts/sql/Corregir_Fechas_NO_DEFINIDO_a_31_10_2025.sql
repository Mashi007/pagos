-- ============================================
-- CORREGIR FECHAS "NO DEFINIDO" A 31/10/2025
-- ============================================
-- Este script cambia todos los valores "NO DEFINIDO" en fecha_pago
-- por la fecha 31/10/2025 (formato: 2025-10-31 00:00:00)
-- ============================================

-- PASO 1: Verificar cuántos registros tienen "NO DEFINIDO" en fecha_pago
SELECT 
    COUNT(*) AS total_registros_con_NO_DEFINIDO,
    (SELECT COUNT(*) FROM pagos_staging) AS total_registros,
    ROUND((COUNT(*)::numeric / (SELECT COUNT(*) FROM pagos_staging)::numeric) * 100, 2) AS porcentaje_del_total
FROM pagos_staging
WHERE fecha_pago IS NULL 
   OR TRIM(UPPER(fecha_pago)) = 'NO DEFINIDO'
   OR TRIM(UPPER(fecha_pago)) LIKE '%NO DEFINIDO%';

-- PASO 2: Ver ejemplos de registros con "NO DEFINIDO" antes de corregir
SELECT 
    id_stg,
    cedula_cliente,
    fecha_pago AS fecha_pago_actual,
    monto_pagado,
    numero_documento,
    '2025-10-31 00:00:00' AS fecha_pago_nueva
FROM pagos_staging
WHERE fecha_pago IS NULL 
   OR TRIM(UPPER(fecha_pago)) = 'NO DEFINIDO'
   OR TRIM(UPPER(fecha_pago)) LIKE '%NO DEFINIDO%'
ORDER BY id_stg DESC
LIMIT 20;

-- PASO 3: ACTUALIZAR registros con "NO DEFINIDO" a 31/10/2025
-- ⚠️ IMPORTANTE: Ejecuta primero PASO 1 y PASO 2 para verificar
-- La fecha se guardará en formato: 2025-10-31 00:00:00

UPDATE pagos_staging
SET fecha_pago = '2025-10-31 00:00:00'
WHERE fecha_pago IS NULL 
   OR TRIM(UPPER(fecha_pago)) = 'NO DEFINIDO'
   OR TRIM(UPPER(fecha_pago)) LIKE '%NO DEFINIDO%';

-- Verificar cuántos registros se actualizaron
SELECT 
    '✅ Registros actualizados' AS mensaje,
    COUNT(*) AS registros_actualizados
FROM pagos_staging
WHERE fecha_pago = '2025-10-31 00:00:00';

-- PASO 4: Verificar que la corrección se aplicó correctamente
SELECT 
    id_stg,
    cedula_cliente,
    fecha_pago AS fecha_pago_corregida,
    monto_pagado,
    numero_documento
FROM pagos_staging
WHERE fecha_pago = '2025-10-31 00:00:00'
ORDER BY id_stg DESC
LIMIT 20;

-- PASO 5: Verificar que ya no hay registros con "NO DEFINIDO"
SELECT 
    COUNT(*) AS registros_con_NO_DEFINIDO
FROM pagos_staging
WHERE fecha_pago IS NULL 
   OR TRIM(UPPER(fecha_pago)) = 'NO DEFINIDO'
   OR TRIM(UPPER(fecha_pago)) LIKE '%NO DEFINIDO%';

-- PASO 6: Resumen final de fechas en fecha_pago
SELECT 
    fecha_pago,
    COUNT(*) AS cantidad_registros,
    ROUND((COUNT(*)::numeric / (SELECT COUNT(*) FROM pagos_staging)::numeric) * 100, 2) AS porcentaje
FROM pagos_staging
GROUP BY fecha_pago
ORDER BY cantidad_registros DESC
LIMIT 10;

-- ============================================
-- INSTRUCCIONES:
-- ============================================
-- 1. Ejecuta PASO 1 para ver cuántos registros tienen "NO DEFINIDO"
-- 2. Ejecuta PASO 2 para ver ejemplos de los registros que se corregirán
-- 3. Si estás de acuerdo, ejecuta PASO 3 para actualizar los registros
-- 4. Ejecuta PASO 4 para verificar que se corrigieron correctamente
-- 5. Ejecuta PASO 5 para confirmar que ya no hay "NO DEFINIDO"
-- 6. Ejecuta PASO 6 para ver el resumen de fechas
-- ============================================
-- ⚠️ NOTA: La fecha se guarda como '2025-10-31 00:00:00' (formato estándar)
-- ============================================

