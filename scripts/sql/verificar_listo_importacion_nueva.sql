-- ============================================================================
-- VERIFICACIÓN FINAL: LISTO PARA NUEVA IMPORTACIÓN COMPLETA
-- ============================================================================

-- 1. Verificar que tabla está vacía
SELECT 
    'TABLA VACÍA' AS verificacion,
    COUNT(*) AS total_filas,
    CASE 
        WHEN COUNT(*) = 0 THEN '✅ LISTA PARA IMPORTAR'
        ELSE '⚠️ AÚN TIENE DATOS'
    END AS estado
FROM tabla_comparacion_externa;

-- 2. Verificar estructura de columna abonos (debe ser NUMERIC(18,2))
SELECT 
    'ESTRUCTURA abonos' AS verificacion,
    column_name,
    data_type,
    numeric_precision,
    numeric_scale,
    CASE 
        WHEN numeric_precision = 18 THEN '✅ CORRECTO - Listo para valores grandes'
        ELSE '❌ NECESITA CORRECCIÓN'
    END AS estado
FROM information_schema.columns
WHERE table_name = 'tabla_comparacion_externa'
    AND column_name = 'abonos';

-- 3. Verificar Primary Key en id
SELECT 
    'PRIMARY KEY' AS verificacion,
    tc.constraint_name,
    kcu.column_name,
    CASE 
        WHEN kcu.column_name = 'id' THEN '✅ CORRECTO - Permite múltiples préstamos por cliente'
        ELSE '⚠️ VERIFICAR'
    END AS estado
FROM information_schema.table_constraints tc
JOIN information_schema.key_column_usage kcu 
    ON tc.constraint_name = kcu.constraint_name
WHERE tc.table_name = 'tabla_comparacion_externa'
    AND tc.constraint_type = 'PRIMARY KEY';

-- 4. Verificar índice en cedula (no único)
SELECT 
    'ÍNDICE cedula' AS verificacion,
    indexname AS nombre_indice,
    indexdef AS definicion,
    CASE 
        WHEN indexdef LIKE '%UNIQUE%' THEN '⚠️ ES ÚNICO - Debe ser NO ÚNICO'
        ELSE '✅ NO ÚNICO - Permite múltiples préstamos por cliente'
    END AS estado
FROM pg_indexes
WHERE tablename = 'tabla_comparacion_externa'
    AND indexname LIKE '%cedula%';

-- 5. Resumen final
SELECT 
    '✅ RESUMEN' AS verificacion,
    'Si tabla está vacía, abonos es NUMERIC(18,2), y PK está en id, puedes proceder con la importación completa de 4,800 filas' AS estado;
