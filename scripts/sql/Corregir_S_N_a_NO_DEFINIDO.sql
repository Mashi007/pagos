-- ============================================
-- CORREGIR "s/n" Y "S/N" A "NO DEFINIDO"
-- ============================================
-- Este script cambia todos los valores "s/n" y "S/N" (y variaciones) en numero_documento
-- por "NO DEFINIDO"
-- ============================================

-- PASO 1: Verificar cuántos registros tienen "s/n" o "S/N" en numero_documento
SELECT 
    COUNT(*) AS total_registros_con_S_N,
    (SELECT COUNT(*) FROM pagos_staging) AS total_registros,
    ROUND((COUNT(*)::numeric / (SELECT COUNT(*) FROM pagos_staging)::numeric) * 100, 2) AS porcentaje_del_total
FROM pagos_staging
WHERE numero_documento IS NOT NULL 
   AND (TRIM(UPPER(numero_documento)) = 'S/N'
   OR TRIM(UPPER(numero_documento)) = 'S\\N'
   OR TRIM(UPPER(numero_documento)) = 'SN'
   OR TRIM(UPPER(numero_documento)) LIKE '%S/N%'
   OR TRIM(UPPER(numero_documento)) LIKE '%S\\N%'
   OR TRIM(UPPER(numero_documento)) LIKE '%SN%'
   OR TRIM(UPPER(numero_documento)) = 'S/N'
   OR TRIM(LOWER(numero_documento)) = 's/n'
   OR TRIM(LOWER(numero_documento)) = 's\\n'
   OR TRIM(LOWER(numero_documento)) = 'sn');

-- PASO 2: Ver ejemplos de registros con "s/n" o "S/N" antes de corregir
SELECT 
    id_stg,
    cedula_cliente,
    fecha_pago,
    monto_pagado,
    numero_documento AS numero_documento_actual,
    'NO DEFINIDO' AS numero_documento_nuevo
FROM pagos_staging
WHERE numero_documento IS NOT NULL 
   AND (TRIM(UPPER(numero_documento)) = 'S/N'
   OR TRIM(UPPER(numero_documento)) = 'S\\N'
   OR TRIM(UPPER(numero_documento)) = 'SN'
   OR TRIM(UPPER(numero_documento)) LIKE '%S/N%'
   OR TRIM(UPPER(numero_documento)) LIKE '%S\\N%'
   OR TRIM(UPPER(numero_documento)) LIKE '%SN%'
   OR TRIM(UPPER(numero_documento)) = 'S/N'
   OR TRIM(LOWER(numero_documento)) = 's/n'
   OR TRIM(LOWER(numero_documento)) = 's\\n'
   OR TRIM(LOWER(numero_documento)) = 'sn')
ORDER BY id_stg DESC
LIMIT 20;

-- PASO 3: ACTUALIZAR registros con "s/n" o "S/N" a "NO DEFINIDO"
-- ⚠️ IMPORTANTE: Ejecuta primero PASO 1 y PASO 2 para verificar

UPDATE pagos_staging
SET numero_documento = 'NO DEFINIDO'
WHERE numero_documento IS NOT NULL 
   AND (TRIM(UPPER(numero_documento)) = 'S/N'
   OR TRIM(UPPER(numero_documento)) = 'S\\N'
   OR TRIM(UPPER(numero_documento)) = 'SN'
   OR TRIM(UPPER(numero_documento)) LIKE '%S/N%'
   OR TRIM(UPPER(numero_documento)) LIKE '%S\\N%'
   OR TRIM(UPPER(numero_documento)) LIKE '%SN%'
   OR TRIM(LOWER(numero_documento)) = 's/n'
   OR TRIM(LOWER(numero_documento)) = 's\\n'
   OR TRIM(LOWER(numero_documento)) = 'sn');

-- Verificar cuántos registros se actualizaron
SELECT 
    '✅ Registros actualizados' AS mensaje,
    COUNT(*) AS registros_actualizados
FROM pagos_staging
WHERE numero_documento = 'NO DEFINIDO';

-- PASO 4: Verificar que la corrección se aplicó correctamente
SELECT 
    id_stg,
    cedula_cliente,
    fecha_pago,
    monto_pagado,
    numero_documento AS numero_documento_corregido
FROM pagos_staging
WHERE numero_documento = 'NO DEFINIDO'
ORDER BY id_stg DESC
LIMIT 20;

-- PASO 5: Verificar que ya no hay registros con "s/n" o "S/N"
SELECT 
    COUNT(*) AS registros_con_S_N
FROM pagos_staging
WHERE numero_documento IS NOT NULL 
   AND (TRIM(UPPER(numero_documento)) = 'S/N'
   OR TRIM(UPPER(numero_documento)) = 'S\\N'
   OR TRIM(UPPER(numero_documento)) = 'SN'
   OR TRIM(UPPER(numero_documento)) LIKE '%S/N%'
   OR TRIM(UPPER(numero_documento)) LIKE '%S\\N%'
   OR TRIM(UPPER(numero_documento)) LIKE '%SN%'
   OR TRIM(LOWER(numero_documento)) = 's/n'
   OR TRIM(LOWER(numero_documento)) = 's\\n'
   OR TRIM(LOWER(numero_documento)) = 'sn');

-- PASO 6: Resumen final de valores en numero_documento
SELECT 
    numero_documento,
    COUNT(*) AS cantidad_registros,
    ROUND((COUNT(*)::numeric / (SELECT COUNT(*) FROM pagos_staging)::numeric) * 100, 2) AS porcentaje
FROM pagos_staging
WHERE numero_documento IS NOT NULL
GROUP BY numero_documento
ORDER BY cantidad_registros DESC
LIMIT 10;

-- ============================================
-- INSTRUCCIONES:
-- ============================================
-- 1. Ejecuta PASO 1 para ver cuántos registros tienen "s/n" o "S/N"
-- 2. Ejecuta PASO 2 para ver ejemplos de los registros que se corregirán
-- 3. Si estás de acuerdo, ejecuta PASO 3 para actualizar los registros
-- 4. Ejecuta PASO 4 para verificar que se corrigieron correctamente
-- 5. Ejecuta PASO 5 para confirmar que ya no hay "s/n" o "S/N"
-- 6. Ejecuta PASO 6 para ver el resumen de valores en numero_documento
-- ============================================
-- ⚠️ NOTA: Este script detecta y corrige las siguientes variaciones:
-- - "S/N", "s/n", "S\N", "s\n", "SN", "sn"
-- - También valores que contengan estas cadenas (ej: "REF: S/N")
-- ============================================

