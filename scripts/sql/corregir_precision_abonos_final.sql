-- ============================================================================
-- CORREGIR PRECISIÓN DE abonos - VALORES MUY GRANDES
-- ============================================================================
-- Error: SQL Error [22003]: numeric field overflow
-- Problema: NUMERIC(15,2) permite máximo 13 dígitos antes del punto
--           Valor problemático: 740087000000000 (15 dígitos)
-- Solución: Aumentar a NUMERIC(18,2) que permite 16 dígitos antes del punto
-- ============================================================================

-- PASO 1: Verificar estructura actual
SELECT 
    'ESTRUCTURA ACTUAL' AS verificacion,
    column_name,
    data_type,
    numeric_precision,
    numeric_scale,
    CASE 
        WHEN numeric_precision = 15 THEN '⚠️ INSUFICIENTE - Necesita NUMERIC(18,2)'
        WHEN numeric_precision = 18 THEN '✅ CORRECTO'
        ELSE '❌ VERIFICAR'
    END AS estado
FROM information_schema.columns
WHERE table_name = 'tabla_comparacion_externa'
    AND column_name = 'abonos';

-- PASO 2: Modificar precisión de abonos a NUMERIC(18,2)
ALTER TABLE tabla_comparacion_externa 
ALTER COLUMN abonos TYPE NUMERIC(18,2);

-- PASO 3: Verificar cambio aplicado
SELECT 
    'ESTRUCTURA FINAL' AS verificacion,
    column_name,
    data_type,
    numeric_precision,
    numeric_scale,
    CASE 
        WHEN numeric_precision = 18 THEN '✅ CORREGIDO - Listo para valores grandes'
        ELSE '❌ AÚN NECESITA CORRECCIÓN'
    END AS estado
FROM information_schema.columns
WHERE table_name = 'tabla_comparacion_externa'
    AND column_name = 'abonos';

-- PASO 4: Verificar límites nuevos
SELECT 
    'LÍMITES NUEVOS' AS verificacion,
    'NUMERIC(18,2) permite valores hasta:' AS descripcion,
    '999,999,999,999,999,999.99' AS valor_maximo,
    '16 dígitos antes del punto decimal' AS precision_info,
    'Valor problemático: 740087000000000 (15 dígitos) - ✅ CABE' AS verificacion_valor;

-- ============================================================================
-- COMPARACIÓN DE PRECISIONES:
-- ============================================================================
-- NUMERIC(12,2): máximo 9,999,999,999.99 (10 dígitos antes del punto)
-- NUMERIC(15,2): máximo 999,999,999,999.99 (13 dígitos antes del punto)
-- NUMERIC(18,2): máximo 99,999,999,999,999,999.99 (16 dígitos antes del punto) ✅
-- 
-- Valor problemático: 740087000000000 tiene 15 dígitos
-- Con NUMERIC(18,2) podrá almacenarse correctamente
-- ============================================================================

COMMENT ON COLUMN tabla_comparacion_externa.abonos IS 'Suma de pagos por cédula. Precisión aumentada a NUMERIC(18,2) para manejar valores muy grandes (hasta 16 dígitos antes del punto decimal).';
