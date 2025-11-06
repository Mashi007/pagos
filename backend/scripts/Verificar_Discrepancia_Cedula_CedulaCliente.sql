-- ============================================
-- VERIFICAR DISCREPANCIA: cedula vs cedula_cliente
-- ============================================
-- Este script verifica si existen ambas columnas y sus datos

-- 1. Verificar existencia de ambas columnas
SELECT 
    'Verificación de columnas' AS paso,
    CASE 
        WHEN EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = 'pagos' AND column_name = 'cedula'
        ) THEN '✅ Columna "cedula" EXISTE'
        ELSE '❌ Columna "cedula" NO existe'
    END AS estado_cedula,
    CASE 
        WHEN EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = 'pagos' AND column_name = 'cedula_cliente'
        ) THEN '✅ Columna "cedula_cliente" EXISTE'
        ELSE '❌ Columna "cedula_cliente" NO existe'
    END AS estado_cedula_cliente;

-- 2. Si ambas existen, comparar datos
SELECT 
    'Comparación de datos (si ambas columnas existen)' AS paso,
    COUNT(*) AS total_registros,
    COUNT(cedula) AS registros_con_cedula,
    COUNT(cedula_cliente) AS registros_con_cedula_cliente,
    COUNT(CASE WHEN cedula IS NOT NULL AND cedula_cliente IS NULL THEN 1 END) AS solo_cedula,
    COUNT(CASE WHEN cedula IS NULL AND cedula_cliente IS NOT NULL THEN 1 END) AS solo_cedula_cliente,
    COUNT(CASE WHEN cedula = cedula_cliente THEN 1 END) AS coinciden,
    COUNT(CASE WHEN cedula IS NOT NULL AND cedula_cliente IS NOT NULL AND cedula != cedula_cliente THEN 1 END) AS diferentes
FROM pagos;

-- 3. Muestra de registros con diferencias (si ambas columnas existen)
SELECT 
    'Muestra de registros (primeros 10)' AS paso,
    id,
    cedula,
    cedula_cliente,
    CASE 
        WHEN cedula IS NULL AND cedula_cliente IS NULL THEN 'Ambas NULL'
        WHEN cedula IS NULL THEN 'Solo cedula_cliente'
        WHEN cedula_cliente IS NULL THEN 'Solo cedula'
        WHEN cedula = cedula_cliente THEN 'Coinciden'
        ELSE 'Diferentes'
    END AS estado_comparacion
FROM pagos
LIMIT 10;

