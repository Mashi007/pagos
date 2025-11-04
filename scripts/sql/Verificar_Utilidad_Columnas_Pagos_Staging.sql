-- ============================================
-- VERIFICACIÓN DE UTILIDAD DE COLUMNAS EN PAGOS_STAGING
-- ============================================
-- Este script verifica:
-- 1. Todas las columnas que existen en pagos_staging
-- 2. Si tienen datos (no NULL, no vacíos)
-- 3. Porcentaje de uso de cada columna
-- 4. Recomendación sobre su utilidad
-- ============================================

-- PASO 1: Ver TODAS las columnas de pagos_staging con sus tipos
SELECT 
    column_name,
    data_type,
    is_nullable,
    column_default,
    character_maximum_length
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'pagos_staging'
ORDER BY ordinal_position;

-- PASO 2: Verificar cuántos registros hay en total
SELECT 
    COUNT(*) AS total_registros
FROM pagos_staging;

-- PASO 3: Verificar utilidad de cada columna (conteo de valores no NULL y no vacíos)
SELECT 
    'id_stg' AS columna,
    COUNT(*) AS total_registros,
    COUNT(id_stg) AS registros_con_valor,
    COUNT(*) - COUNT(id_stg) AS registros_null,
    ROUND((COUNT(id_stg)::numeric / COUNT(*)::numeric) * 100, 2) AS porcentaje_uso
FROM pagos_staging
UNION ALL
SELECT 
    'cedula_cliente' AS columna,
    COUNT(*) AS total_registros,
    COUNT(CASE WHEN cedula_cliente IS NOT NULL AND TRIM(cedula_cliente) != '' THEN 1 END) AS registros_con_valor,
    COUNT(*) - COUNT(CASE WHEN cedula_cliente IS NOT NULL AND TRIM(cedula_cliente) != '' THEN 1 END) AS registros_null,
    ROUND((COUNT(CASE WHEN cedula_cliente IS NOT NULL AND TRIM(cedula_cliente) != '' THEN 1 END)::numeric / COUNT(*)::numeric) * 100, 2) AS porcentaje_uso
FROM pagos_staging
UNION ALL
SELECT 
    'fecha_pago' AS columna,
    COUNT(*) AS total_registros,
    COUNT(CASE WHEN fecha_pago IS NOT NULL AND TRIM(fecha_pago) != '' THEN 1 END) AS registros_con_valor,
    COUNT(*) - COUNT(CASE WHEN fecha_pago IS NOT NULL AND TRIM(fecha_pago) != '' THEN 1 END) AS registros_null,
    ROUND((COUNT(CASE WHEN fecha_pago IS NOT NULL AND TRIM(fecha_pago) != '' THEN 1 END)::numeric / COUNT(*)::numeric) * 100, 2) AS porcentaje_uso
FROM pagos_staging
UNION ALL
SELECT 
    'monto_pagado' AS columna,
    COUNT(*) AS total_registros,
    COUNT(CASE WHEN monto_pagado IS NOT NULL AND TRIM(monto_pagado) != '' THEN 1 END) AS registros_con_valor,
    COUNT(*) - COUNT(CASE WHEN monto_pagado IS NOT NULL AND TRIM(monto_pagado) != '' THEN 1 END) AS registros_null,
    ROUND((COUNT(CASE WHEN monto_pagado IS NOT NULL AND TRIM(monto_pagado) != '' THEN 1 END)::numeric / COUNT(*)::numeric) * 100, 2) AS porcentaje_uso
FROM pagos_staging
UNION ALL
SELECT 
    'numero_documento' AS columna,
    COUNT(*) AS total_registros,
    COUNT(CASE WHEN numero_documento IS NOT NULL AND TRIM(numero_documento) != '' THEN 1 END) AS registros_con_valor,
    COUNT(*) - COUNT(CASE WHEN numero_documento IS NOT NULL AND TRIM(numero_documento) != '' THEN 1 END) AS registros_null,
    ROUND((COUNT(CASE WHEN numero_documento IS NOT NULL AND TRIM(numero_documento) != '' THEN 1 END)::numeric / COUNT(*)::numeric) * 100, 2) AS porcentaje_uso
FROM pagos_staging;

-- PASO 4: Verificar si existen columnas adicionales (que no deberían estar)
-- Este query muestra columnas que NO son las 5 básicas esperadas
SELECT 
    column_name,
    data_type,
    is_nullable,
    column_default,
    CASE 
        WHEN column_name IN ('id_stg', 'cedula_cliente', 'fecha_pago', 'monto_pagado', 'numero_documento') 
        THEN '✅ COLUMNA BÁSICA ESPERADA'
        ELSE '⚠️ COLUMNA ADICIONAL - VERIFICAR SI ES NECESARIA'
    END AS estado
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'pagos_staging'
ORDER BY 
    CASE 
        WHEN column_name IN ('id_stg', 'cedula_cliente', 'fecha_pago', 'monto_pagado', 'numero_documento') 
        THEN 0 
        ELSE 1 
    END,
    ordinal_position;

-- PASO 5: Verificar TODAS las columnas adicionales con datos (verificación dinámica)
-- Este query verifica automáticamente si las columnas adicionales tienen datos
-- Ejecuta este query después de ver el PASO 4 para identificar los nombres de las columnas adicionales
-- Luego ajusta los nombres en el query de abajo

-- IMPORTANTE: Reemplaza 'column5', 'column6', 'column7', 'column8' con los nombres reales que veas en PASO 4
-- Si no hay columnas adicionales, este query no es necesario

-- Ejemplo genérico (ajusta los nombres según PASO 4):
/*
SELECT 
    COUNT(*) AS total_registros,
    COUNT(CASE WHEN column5 IS NOT NULL AND TRIM(CAST(column5 AS TEXT)) != '' THEN 1 END) AS column5_con_datos,
    COUNT(CASE WHEN column6 IS NOT NULL AND TRIM(CAST(column6 AS TEXT)) != '' THEN 1 END) AS column6_con_datos,
    COUNT(CASE WHEN column7 IS NOT NULL AND TRIM(CAST(column7 AS TEXT)) != '' THEN 1 END) AS column7_con_datos,
    COUNT(CASE WHEN column8 IS NOT NULL AND TRIM(CAST(column8 AS TEXT)) != '' THEN 1 END) AS column8_con_datos,
    ROUND((COUNT(CASE WHEN column5 IS NOT NULL AND TRIM(CAST(column5 AS TEXT)) != '' THEN 1 END)::numeric / COUNT(*)::numeric) * 100, 2) AS column5_porcentaje,
    ROUND((COUNT(CASE WHEN column6 IS NOT NULL AND TRIM(CAST(column6 AS TEXT)) != '' THEN 1 END)::numeric / COUNT(*)::numeric) * 100, 2) AS column6_porcentaje,
    ROUND((COUNT(CASE WHEN column7 IS NOT NULL AND TRIM(CAST(column7 AS TEXT)) != '' THEN 1 END)::numeric / COUNT(*)::numeric) * 100, 2) AS column7_porcentaje,
    ROUND((COUNT(CASE WHEN column8 IS NOT NULL AND TRIM(CAST(column8 AS TEXT)) != '' THEN 1 END)::numeric / COUNT(*)::numeric) * 100, 2) AS column8_porcentaje
FROM pagos_staging;
*/

-- PASO 5B: Verificación automática de columnas adicionales (más completo)
-- Este query genera un resumen de utilidad para cada columna adicional
-- Ejecuta este query después de identificar los nombres de las columnas en PASO 4
-- Reemplaza los nombres de columnas según lo que veas en PASO 4

-- Si tienes columnas adicionales con nombres específicos, usa este formato:
/*
WITH columnas_adicionales AS (
    SELECT 
        COUNT(*) AS total,
        COUNT(CASE WHEN column5 IS NOT NULL AND TRIM(CAST(column5 AS TEXT)) != '' THEN 1 END) AS col5_con_datos,
        COUNT(CASE WHEN column6 IS NOT NULL AND TRIM(CAST(column6 AS TEXT)) != '' THEN 1 END) AS col6_con_datos,
        COUNT(CASE WHEN column7 IS NOT NULL AND TRIM(CAST(column7 AS TEXT)) != '' THEN 1 END) AS col7_con_datos,
        COUNT(CASE WHEN column8 IS NOT NULL AND TRIM(CAST(column8 AS TEXT)) != '' THEN 1 END) AS col8_con_datos
    FROM pagos_staging
)
SELECT 
    'column5' AS columna,
    total AS total_registros,
    col5_con_datos AS registros_con_datos,
    total - col5_con_datos AS registros_vacios,
    CASE 
        WHEN col5_con_datos = 0 THEN '❌ SIN UTILIDAD - Todos NULL/vacíos'
        WHEN col5_con_datos < total * 0.1 THEN '⚠️ POCO ÚTIL - Menos del 10% tiene datos'
        WHEN col5_con_datos < total * 0.5 THEN '⚠️ PARCIALMENTE ÚTIL - Menos del 50% tiene datos'
        ELSE '✅ ÚTIL - Más del 50% tiene datos'
    END AS utilidad
FROM columnas_adicionales
UNION ALL
SELECT 
    'column6' AS columna,
    total AS total_registros,
    col6_con_datos AS registros_con_datos,
    total - col6_con_datos AS registros_vacios,
    CASE 
        WHEN col6_con_datos = 0 THEN '❌ SIN UTILIDAD - Todos NULL/vacíos'
        WHEN col6_con_datos < total * 0.1 THEN '⚠️ POCO ÚTIL - Menos del 10% tiene datos'
        WHEN col6_con_datos < total * 0.5 THEN '⚠️ PARCIALMENTE ÚTIL - Menos del 50% tiene datos'
        ELSE '✅ ÚTIL - Más del 50% tiene datos'
    END AS utilidad
FROM columnas_adicionales
UNION ALL
SELECT 
    'column7' AS columna,
    total AS total_registros,
    col7_con_datos AS registros_con_datos,
    total - col7_con_datos AS registros_vacios,
    CASE 
        WHEN col7_con_datos = 0 THEN '❌ SIN UTILIDAD - Todos NULL/vacíos'
        WHEN col7_con_datos < total * 0.1 THEN '⚠️ POCO ÚTIL - Menos del 10% tiene datos'
        WHEN col7_con_datos < total * 0.5 THEN '⚠️ PARCIALMENTE ÚTIL - Menos del 50% tiene datos'
        ELSE '✅ ÚTIL - Más del 50% tiene datos'
    END AS utilidad
FROM columnas_adicionales
UNION ALL
SELECT 
    'column8' AS columna,
    total AS total_registros,
    col8_con_datos AS registros_con_datos,
    total - col8_con_datos AS registros_vacios,
    CASE 
        WHEN col8_con_datos = 0 THEN '❌ SIN UTILIDAD - Todos NULL/vacíos'
        WHEN col8_con_datos < total * 0.1 THEN '⚠️ POCO ÚTIL - Menos del 10% tiene datos'
        WHEN col8_con_datos < total * 0.5 THEN '⚠️ PARCIALMENTE ÚTIL - Menos del 50% tiene datos'
        ELSE '✅ ÚTIL - Más del 50% tiene datos'
    END AS utilidad
FROM columnas_adicionales;
*/

-- PASO 6: Muestra ejemplos de registros para ver qué columnas tienen datos
SELECT 
    id_stg,
    cedula_cliente,
    fecha_pago,
    monto_pagado,
    numero_documento
FROM pagos_staging
WHERE id_stg IS NOT NULL
ORDER BY id_stg DESC
LIMIT 10;

-- PASO 7: Comparar con tabla pagos para ver qué columnas faltan en staging
SELECT 
    'pagos' AS tabla,
    column_name,
    data_type
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'pagos'
  AND column_name IN ('conciliado', 'estado', 'fecha_registro', 'prestamo_id', 'institucion_bancaria', 'notas', 'activo', 'usuario_registro', 'verificado_concordancia')
UNION ALL
SELECT 
    'pagos_staging' AS tabla,
    column_name,
    data_type
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'pagos_staging'
  AND column_name IN ('conciliado', 'estado', 'fecha_registro', 'prestamo_id', 'institucion_bancaria', 'notas', 'activo', 'usuario_registro', 'verificado_concordancia')
ORDER BY column_name, tabla;

-- ============================================
-- INTERPRETACIÓN DE RESULTADOS:
-- ============================================
-- 1. PASO 1: Muestra todas las columnas. Si ves column5, column6, etc., son columnas adicionales
-- 2. PASO 2: Total de registros en la tabla
-- 3. PASO 3: Porcentaje de uso de cada columna básica esperada
-- 4. PASO 4: Identifica columnas adicionales que no deberían estar
-- 5. PASO 5: Si hay columnas adicionales, verifica si tienen datos (descomenta y ajusta nombres)
-- 6. PASO 6: Muestra ejemplos de registros reales
-- 7. PASO 7: Compara qué columnas importantes faltan en staging vs pagos
--
-- CONCLUSIÓN:
-- - Si column5, column6, column7, column8 tienen 0% de uso (todos NULL), NO son útiles y pueden eliminarse
-- - Solo las 5 columnas básicas (id_stg, cedula_cliente, fecha_pago, monto_pagado, numero_documento) son necesarias
-- - La columna 'conciliado' NO existe en pagos_staging (es correcto, solo está en tabla 'pagos')
-- ============================================

