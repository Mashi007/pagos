-- ============================================
-- VERIFICACIÓN: DATOS EN TABLA pagos_staging
-- ============================================
-- Verifica qué datos existen en la tabla de staging (pagos temporales/pre-procesamiento)

-- ============================================
-- PARTE 1: VERIFICAR SI LA TABLA EXISTE
-- ============================================
SELECT 
    '=== VERIFICACIÓN: EXISTENCIA DE TABLA ===' AS verificacion,
    CASE 
        WHEN EXISTS (
            SELECT 1 FROM information_schema.tables 
            WHERE table_schema = 'public' AND table_name = 'pagos_staging'
        ) THEN '✅ Tabla pagos_staging EXISTE'
        ELSE '❌ Tabla pagos_staging NO EXISTE'
    END AS estado_tabla;

-- ============================================
-- PARTE 2: ESTRUCTURA DE LA TABLA (si existe)
-- ============================================
SELECT 
    '=== ESTRUCTURA: TABLA pagos_staging ===' AS verificacion,
    column_name AS columna,
    data_type AS tipo_dato,
    COALESCE(
        CASE 
            WHEN character_maximum_length IS NOT NULL THEN character_maximum_length::text
            WHEN numeric_precision IS NOT NULL THEN numeric_precision::text || ',' || COALESCE(numeric_scale::text, '0')
            ELSE NULL
        END,
        ''
    ) AS longitud_precision,
    CASE 
        WHEN is_nullable = 'YES' THEN 'Sí'
        ELSE 'No'
    END AS nullable,
    COALESCE(column_default, 'Sin default') AS valor_default,
    ordinal_position AS posicion
FROM information_schema.columns
WHERE table_schema = 'public'
    AND table_name = 'pagos_staging'
ORDER BY ordinal_position;

-- ============================================
-- PARTE 3: CANTIDAD DE REGISTROS
-- ============================================
SELECT 
    '=== CANTIDAD DE REGISTROS ===' AS verificacion,
    COUNT(*) AS total_registros,
    COUNT(CASE WHEN cedula_cliente IS NOT NULL THEN 1 END) AS registros_con_cedula,
    COUNT(CASE WHEN prestamo_id IS NOT NULL THEN 1 END) AS registros_con_prestamo_id,
    COUNT(CASE WHEN fecha_pago IS NOT NULL THEN 1 END) AS registros_con_fecha_pago,
    COUNT(CASE WHEN monto_pagado IS NOT NULL THEN 1 END) AS registros_con_monto
FROM pagos_staging;

-- ============================================
-- PARTE 4: RESUMEN POR ESTADO
-- ============================================
SELECT 
    '=== RESUMEN POR ESTADO ===' AS verificacion,
    estado,
    COUNT(*) AS cantidad,
    SUM(monto_pagado) AS total_monto
FROM pagos_staging
WHERE estado IS NOT NULL
GROUP BY estado
ORDER BY cantidad DESC;

-- ============================================
-- PARTE 5: RESUMEN POR FECHA
-- ============================================
SELECT 
    '=== RESUMEN POR FECHA DE PAGO ===' AS verificacion,
    DATE(fecha_pago) AS fecha,
    COUNT(*) AS cantidad_pagos,
    SUM(monto_pagado) AS total_monto
FROM pagos_staging
WHERE fecha_pago IS NOT NULL
GROUP BY DATE(fecha_pago)
ORDER BY fecha DESC
LIMIT 10;

-- ============================================
-- PARTE 6: REGISTROS RECIENTES
-- ============================================
SELECT 
    '=== MUESTRA: ÚLTIMOS 10 REGISTROS ===' AS verificacion,
    id,
    cedula_cliente,
    prestamo_id,
    fecha_pago,
    monto_pagado,
    numero_documento,
    estado,
    fecha_registro
FROM pagos_staging
ORDER BY fecha_registro DESC NULLS LAST, id DESC
LIMIT 10;

-- ============================================
-- PARTE 7: VERIFICAR PROBLEMAS
-- ============================================
-- Registros con datos faltantes críticos
SELECT 
    '=== PROBLEMAS: DATOS FALTANTES ===' AS verificacion,
    COUNT(CASE WHEN cedula_cliente IS NULL THEN 1 END) AS sin_cedula_cliente,
    COUNT(CASE WHEN fecha_pago IS NULL THEN 1 END) AS sin_fecha_pago,
    COUNT(CASE WHEN monto_pagado IS NULL OR monto_pagado <= 0 THEN 1 END) AS sin_monto_valido,
    COUNT(CASE WHEN numero_documento IS NULL THEN 1 END) AS sin_numero_documento
FROM pagos_staging;

-- Registros con fechas inválidas
SELECT 
    '=== PROBLEMAS: FECHAS INVÁLIDAS ===' AS verificacion,
    COUNT(*) AS registros_con_fecha_invalida
FROM pagos_staging
WHERE fecha_pago IS NOT NULL
  AND (fecha_pago < '2000-01-01' OR fecha_pago > CURRENT_DATE + INTERVAL '1 year');

-- ============================================
-- PARTE 8: COMPARACIÓN CON TABLA pagos
-- ============================================
SELECT 
    '=== COMPARACIÓN: pagos_staging vs pagos ===' AS verificacion,
    (SELECT COUNT(*) FROM pagos_staging) AS total_pagos_staging,
    (SELECT COUNT(*) FROM pagos) AS total_pagos_final,
    CASE 
        WHEN (SELECT COUNT(*) FROM pagos_staging) > (SELECT COUNT(*) FROM pagos) 
        THEN '⚠️ Hay más registros en staging que en pagos - Posible migración pendiente'
        WHEN (SELECT COUNT(*) FROM pagos_staging) = (SELECT COUNT(*) FROM pagos) 
        THEN '✅ Misma cantidad - Posible duplicación o ya migrados'
        WHEN (SELECT COUNT(*) FROM pagos_staging) < (SELECT COUNT(*) FROM pagos) 
        THEN '✅ Staging tiene menos registros - Normal si ya se migraron'
        ELSE '❓ No se puede comparar'
    END AS observacion;

-- ============================================
-- PARTE 9: VERIFICAR DUPLICADOS
-- ============================================
SELECT 
    '=== DUPLICADOS: POR NÚMERO DE DOCUMENTO ===' AS verificacion,
    numero_documento,
    COUNT(*) AS cantidad_duplicados
FROM pagos_staging
WHERE numero_documento IS NOT NULL
GROUP BY numero_documento
HAVING COUNT(*) > 1
ORDER BY cantidad_duplicados DESC
LIMIT 10;

-- ============================================
-- PARTE 10: RESUMEN FINAL
-- ============================================
SELECT 
    '=== RESUMEN FINAL: pagos_staging ===' AS verificacion,
    CASE 
        WHEN EXISTS (
            SELECT 1 FROM information_schema.tables 
            WHERE table_schema = 'public' AND table_name = 'pagos_staging'
        ) THEN '✅ Tabla existe'
        ELSE '❌ Tabla NO existe'
    END AS estado_tabla,
    (SELECT COUNT(*) FROM pagos_staging) AS total_registros,
    CASE 
        WHEN (SELECT COUNT(*) FROM pagos_staging) = 0 THEN '❌ Tabla está vacía'
        WHEN (SELECT COUNT(*) FROM pagos_staging) > 0 AND (SELECT COUNT(*) FROM pagos_staging WHERE cedula_cliente IS NULL AND fecha_pago IS NULL AND monto_pagado IS NULL) = (SELECT COUNT(*) FROM pagos_staging) THEN '⚠️ Tabla tiene registros pero todos están vacíos'
        WHEN (SELECT COUNT(*) FROM pagos_staging WHERE cedula_cliente IS NOT NULL AND fecha_pago IS NOT NULL AND monto_pagado IS NOT NULL) > 0 THEN '✅ Hay registros con datos completos'
        ELSE '⚠️ Hay registros pero algunos con datos incompletos'
    END AS estado_datos,
    CASE 
        WHEN (SELECT COUNT(*) FROM pagos_staging) > 0 THEN 'Los datos están listos para migrar o procesar'
        ELSE 'No hay datos para procesar'
    END AS recomendacion;

-- ============================================
-- FIN DEL VERIFICACIÓN
-- ============================================
-- Este script verifica:
-- 1. Si la tabla pagos_staging existe
-- 2. Su estructura de columnas
-- 3. Cantidad de registros
-- 4. Calidad de los datos
-- 5. Comparación con tabla pagos final
-- 6. Problemas potenciales

