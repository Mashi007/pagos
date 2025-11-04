-- ============================================
-- ELIMINAR COLUMNAS ADICIONALES DE PAGOS_STAGING
-- ============================================
-- Este script elimina las columnas adicionales que NO tienen utilidad:
-- - column5, column6, column7, column8
-- 
-- ⚠️ IMPORTANTE: 
-- 1. Verifica primero que estas columnas estén vacías (0% de uso)
-- 2. Haz un backup de la base de datos antes de ejecutar
-- 3. Ejecuta en un entorno de prueba primero
-- 4. Las columnas básicas (id_stg, cedula_cliente, fecha_pago, monto_pagado, numero_documento) NO se eliminarán
-- ============================================

-- PASO 1: Verificar que las columnas existen antes de eliminarlas
SELECT 
    column_name,
    data_type,
    CASE 
        WHEN column_name IN ('column5', 'column6', 'column7', 'column8') THEN '⚠️ SERÁ ELIMINADA'
        ELSE '✅ SE MANTIENE'
    END AS accion
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'pagos_staging'
  AND column_name IN ('column5', 'column6', 'column7', 'column8')
ORDER BY column_name;

-- PASO 2: Verificar que las columnas están vacías (seguridad adicional)
SELECT 
    COUNT(*) AS total_registros,
    COUNT(CASE WHEN column5 IS NOT NULL AND TRIM(CAST(column5 AS TEXT)) != '' THEN 1 END) AS column5_con_datos,
    COUNT(CASE WHEN column6 IS NOT NULL AND TRIM(CAST(column6 AS TEXT)) != '' THEN 1 END) AS column6_con_datos,
    COUNT(CASE WHEN column7 IS NOT NULL AND TRIM(CAST(column7 AS TEXT)) != '' THEN 1 END) AS column7_con_datos,
    COUNT(CASE WHEN column8 IS NOT NULL AND TRIM(CAST(column8 AS TEXT)) != '' THEN 1 END) AS column8_con_datos
FROM pagos_staging;

-- Si los valores anteriores son todos 0, es seguro eliminar las columnas

-- PASO 3: ELIMINAR COLUMNAS ADICIONALES
-- ⚠️ EJECUTA ESTOS COMANDOS UNO POR UNO Y VERIFICA QUE NO HAY ERRORES

-- Eliminar column5
ALTER TABLE pagos_staging DROP COLUMN IF EXISTS column5;
-- Verificar que se eliminó
SELECT '✅ column5 eliminada' AS resultado;

-- Eliminar column6
ALTER TABLE pagos_staging DROP COLUMN IF EXISTS column6;
-- Verificar que se eliminó
SELECT '✅ column6 eliminada' AS resultado;

-- Eliminar column7
ALTER TABLE pagos_staging DROP COLUMN IF EXISTS column7;
-- Verificar que se eliminó
SELECT '✅ column7 eliminada' AS resultado;

-- Eliminar column8
ALTER TABLE pagos_staging DROP COLUMN IF EXISTS column8;
-- Verificar que se eliminó
SELECT '✅ column8 eliminada' AS resultado;

-- PASO 4: Verificar que las columnas fueron eliminadas correctamente
SELECT 
    column_name,
    data_type,
    is_nullable,
    CASE 
        WHEN column_name IN ('id_stg', 'cedula_cliente', 'fecha_pago', 'monto_pagado', 'numero_documento') 
        THEN '✅ COLUMNA BÁSICA (SE MANTIENE)'
        ELSE '⚠️ COLUMNA ADICIONAL (VERIFICAR)'
    END AS estado
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'pagos_staging'
ORDER BY ordinal_position;

-- PASO 5: Verificar que la tabla sigue funcionando correctamente
-- Contar registros (debe ser el mismo número que antes)
SELECT 
    COUNT(*) AS total_registros,
    COUNT(CASE WHEN cedula_cliente IS NOT NULL AND TRIM(cedula_cliente) != '' THEN 1 END) AS registros_con_cedula,
    COUNT(CASE WHEN fecha_pago IS NOT NULL AND TRIM(fecha_pago) != '' THEN 1 END) AS registros_con_fecha,
    COUNT(CASE WHEN monto_pagado IS NOT NULL AND TRIM(monto_pagado) != '' THEN 1 END) AS registros_con_monto
FROM pagos_staging;

-- PASO 6: Mostrar estructura final de la tabla
SELECT 
    '✅ ESTRUCTURA FINAL DE PAGOS_STAGING' AS mensaje,
    COUNT(*) AS total_columnas
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'pagos_staging';

SELECT 
    column_name,
    data_type,
    is_nullable,
    '✅ COLUMNA BÁSICA' AS tipo
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'pagos_staging'
ORDER BY ordinal_position;

-- ============================================
-- RESUMEN DE OPERACIONES:
-- ============================================
-- ✅ column5 eliminada
-- ✅ column6 eliminada
-- ✅ column7 eliminada
-- ✅ column8 eliminada
-- ✅ Columnas básicas mantenidas: id_stg, cedula_cliente, fecha_pago, monto_pagado, numero_documento
-- ============================================

