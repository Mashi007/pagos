-- ============================================================================
-- VERIFICACIÓN FINAL: LISTO PARA IMPORTACIÓN
-- ============================================================================

-- 1. Verificar estructura de columna abonos
SELECT 
    'ESTRUCTURA CORREGIDA' AS verificacion,
    column_name,
    data_type,
    numeric_precision,
    numeric_scale,
    CASE 
        WHEN numeric_precision = 18 THEN '✅ CORRECTO - Listo para valores grandes'
        ELSE '❌ AÚN NECESITA CORRECCIÓN'
    END AS estado
FROM information_schema.columns
WHERE table_name = 'tabla_comparacion_externa'
    AND column_name = 'abonos';

-- 2. Verificar que la tabla está vacía
SELECT 
    'TABLA VACÍA' AS verificacion,
    COUNT(*) AS total_filas,
    CASE 
        WHEN COUNT(*) = 0 THEN '✅ LISTA PARA IMPORTAR'
        ELSE '⚠️ AÚN TIENE DATOS'
    END AS estado
FROM tabla_comparacion_externa;

-- 3. Verificar estructura completa de campos numéricos
SELECT 
    'ESTRUCTURA COMPLETA NUMÉRICOS' AS verificacion,
    column_name,
    data_type,
    numeric_precision,
    numeric_scale,
    CASE 
        WHEN column_name = 'abonos' AND numeric_precision = 18 THEN '✅ CORRECTO'
        WHEN column_name IN ('total_financiamiento', 'cuota_periodo') AND numeric_precision = 15 THEN '✅ CORRECTO'
        ELSE '⚠️ VERIFICAR'
    END AS estado
FROM information_schema.columns
WHERE table_name = 'tabla_comparacion_externa'
    AND data_type = 'numeric'
ORDER BY ordinal_position;

-- 4. Verificar Primary Key
SELECT 
    'PRIMARY KEY' AS verificacion,
    tc.constraint_name,
    kcu.column_name,
    '✅ PRIMARY KEY en id' AS estado
FROM information_schema.table_constraints tc
JOIN information_schema.key_column_usage kcu 
    ON tc.constraint_name = kcu.constraint_name
WHERE tc.table_name = 'tabla_comparacion_externa'
    AND tc.constraint_type = 'PRIMARY KEY';

-- ============================================================================
-- RESUMEN FINAL
-- ============================================================================
SELECT 
    '✅ RESUMEN' AS verificacion,
    'Si abonos es NUMERIC(18,2) y tabla está vacía, puedes proceder con la importación' AS estado;
