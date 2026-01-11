-- ============================================================================
-- FASE 3: AUDITORÍA DE COLUMNAS SINCRONIZADAS EN USO REAL
-- ============================================================================
-- Este script verifica qué columnas sincronizadas en FASE 3 están siendo
-- realmente utilizadas en la base de datos (valores no nulos, índices, etc.)
-- ============================================================================

-- ============================================================================
-- PASO 1: Verificar existencia de columnas sincronizadas en PAGOS
-- ============================================================================
SELECT 
    'PASO 1: Columnas Pago sincronizadas' AS paso,
    column_name AS columna,
    data_type,
    character_maximum_length AS longitud_maxima,
    is_nullable,
    column_default AS valor_por_defecto
FROM information_schema.columns
WHERE table_schema = 'public'
AND table_name = 'pagos'
AND column_name IN (
    'banco', 'codigo_pago', 'comprobante', 'creado_en', 'descuento',
    'dias_mora', 'documento', 'fecha_vencimiento', 'hora_pago', 'metodo_pago',
    'monto', 'monto_capital', 'monto_cuota_programado', 'monto_interes',
    'monto_mora', 'monto_total', 'numero_operacion', 'observaciones',
    'referencia_pago', 'tasa_mora', 'tipo_pago'
)
ORDER BY column_name;

-- ============================================================================
-- PASO 2: Verificar uso real de columnas PAGOS (valores no nulos)
-- ============================================================================
SELECT 
    'PASO 2: Uso real columnas Pago' AS paso,
    'banco' AS columna,
    COUNT(*) AS total_registros,
    COUNT(banco) AS registros_con_valor,
    COUNT(*) - COUNT(banco) AS registros_nulos,
    ROUND(100.0 * COUNT(banco) / COUNT(*), 2) AS porcentaje_uso
FROM pagos
UNION ALL
SELECT 
    'PASO 2: Uso real columnas Pago',
    'codigo_pago',
    COUNT(*),
    COUNT(codigo_pago),
    COUNT(*) - COUNT(codigo_pago),
    ROUND(100.0 * COUNT(codigo_pago) / COUNT(*), 2)
FROM pagos
UNION ALL
SELECT 
    'PASO 2: Uso real columnas Pago',
    'comprobante',
    COUNT(*),
    COUNT(comprobante),
    COUNT(*) - COUNT(comprobante),
    ROUND(100.0 * COUNT(comprobante) / COUNT(*), 2)
FROM pagos
UNION ALL
SELECT 
    'PASO 2: Uso real columnas Pago',
    'creado_en',
    COUNT(*),
    COUNT(creado_en),
    COUNT(*) - COUNT(creado_en),
    ROUND(100.0 * COUNT(creado_en) / COUNT(*), 2)
FROM pagos
UNION ALL
SELECT 
    'PASO 2: Uso real columnas Pago',
    'descuento',
    COUNT(*),
    COUNT(descuento),
    COUNT(*) - COUNT(descuento),
    ROUND(100.0 * COUNT(descuento) / COUNT(*), 2)
FROM pagos
UNION ALL
SELECT 
    'PASO 2: Uso real columnas Pago',
    'dias_mora',
    COUNT(*),
    COUNT(dias_mora),
    COUNT(*) - COUNT(dias_mora),
    ROUND(100.0 * COUNT(dias_mora) / COUNT(*), 2)
FROM pagos
UNION ALL
SELECT 
    'PASO 2: Uso real columnas Pago',
    'documento',
    COUNT(*),
    COUNT(documento),
    COUNT(*) - COUNT(documento),
    ROUND(100.0 * COUNT(documento) / COUNT(*), 2)
FROM pagos
UNION ALL
SELECT 
    'PASO 2: Uso real columnas Pago',
    'fecha_vencimiento',
    COUNT(*),
    COUNT(fecha_vencimiento),
    COUNT(*) - COUNT(fecha_vencimiento),
    ROUND(100.0 * COUNT(fecha_vencimiento) / COUNT(*), 2)
FROM pagos
UNION ALL
SELECT 
    'PASO 2: Uso real columnas Pago',
    'hora_pago',
    COUNT(*),
    COUNT(hora_pago),
    COUNT(*) - COUNT(hora_pago),
    ROUND(100.0 * COUNT(hora_pago) / COUNT(*), 2)
FROM pagos
UNION ALL
SELECT 
    'PASO 2: Uso real columnas Pago',
    'metodo_pago',
    COUNT(*),
    COUNT(metodo_pago),
    COUNT(*) - COUNT(metodo_pago),
    ROUND(100.0 * COUNT(metodo_pago) / COUNT(*), 2)
FROM pagos
UNION ALL
SELECT 
    'PASO 2: Uso real columnas Pago',
    'monto',
    COUNT(*),
    COUNT(monto),
    COUNT(*) - COUNT(monto),
    ROUND(100.0 * COUNT(monto) / COUNT(*), 2)
FROM pagos
UNION ALL
SELECT 
    'PASO 2: Uso real columnas Pago',
    'monto_capital',
    COUNT(*),
    COUNT(monto_capital),
    COUNT(*) - COUNT(monto_capital),
    ROUND(100.0 * COUNT(monto_capital) / COUNT(*), 2)
FROM pagos
UNION ALL
SELECT 
    'PASO 2: Uso real columnas Pago',
    'monto_cuota_programado',
    COUNT(*),
    COUNT(monto_cuota_programado),
    COUNT(*) - COUNT(monto_cuota_programado),
    ROUND(100.0 * COUNT(monto_cuota_programado) / COUNT(*), 2)
FROM pagos
UNION ALL
SELECT 
    'PASO 2: Uso real columnas Pago',
    'monto_interes',
    COUNT(*),
    COUNT(monto_interes),
    COUNT(*) - COUNT(monto_interes),
    ROUND(100.0 * COUNT(monto_interes) / COUNT(*), 2)
FROM pagos
UNION ALL
SELECT 
    'PASO 2: Uso real columnas Pago',
    'monto_mora',
    COUNT(*),
    COUNT(monto_mora),
    COUNT(*) - COUNT(monto_mora),
    ROUND(100.0 * COUNT(monto_mora) / COUNT(*), 2)
FROM pagos
UNION ALL
SELECT 
    'PASO 2: Uso real columnas Pago',
    'monto_total',
    COUNT(*),
    COUNT(monto_total),
    COUNT(*) - COUNT(monto_total),
    ROUND(100.0 * COUNT(monto_total) / COUNT(*), 2)
FROM pagos
UNION ALL
SELECT 
    'PASO 2: Uso real columnas Pago',
    'numero_operacion',
    COUNT(*),
    COUNT(numero_operacion),
    COUNT(*) - COUNT(numero_operacion),
    ROUND(100.0 * COUNT(numero_operacion) / COUNT(*), 2)
FROM pagos
UNION ALL
SELECT 
    'PASO 2: Uso real columnas Pago',
    'observaciones',
    COUNT(*),
    COUNT(observaciones),
    COUNT(*) - COUNT(observaciones),
    ROUND(100.0 * COUNT(observaciones) / COUNT(*), 2)
FROM pagos
UNION ALL
SELECT 
    'PASO 2: Uso real columnas Pago',
    'referencia_pago',
    COUNT(*),
    COUNT(referencia_pago),
    COUNT(*) - COUNT(referencia_pago),
    ROUND(100.0 * COUNT(referencia_pago) / COUNT(*), 2)
FROM pagos
UNION ALL
SELECT 
    'PASO 2: Uso real columnas Pago',
    'tasa_mora',
    COUNT(*),
    COUNT(tasa_mora),
    COUNT(*) - COUNT(tasa_mora),
    ROUND(100.0 * COUNT(tasa_mora) / COUNT(*), 2)
FROM pagos
UNION ALL
SELECT 
    'PASO 2: Uso real columnas Pago',
    'tipo_pago',
    COUNT(*),
    COUNT(tipo_pago),
    COUNT(*) - COUNT(tipo_pago),
    ROUND(100.0 * COUNT(tipo_pago) / COUNT(*), 2)
FROM pagos
ORDER BY porcentaje_uso DESC, columna;

-- ============================================================================
-- PASO 3: Verificar uso real de columnas CUOTAS
-- ============================================================================
SELECT 
    'PASO 3: Uso real columnas Cuota' AS paso,
    'creado_en' AS columna,
    COUNT(*) AS total_registros,
    COUNT(creado_en) AS registros_con_valor,
    COUNT(*) - COUNT(creado_en) AS registros_nulos,
    ROUND(100.0 * COUNT(creado_en) / COUNT(*), 2) AS porcentaje_uso
FROM cuotas
UNION ALL
SELECT 
    'PASO 3: Uso real columnas Cuota',
    'actualizado_en',
    COUNT(*),
    COUNT(actualizado_en),
    COUNT(*) - COUNT(actualizado_en),
    ROUND(100.0 * COUNT(actualizado_en) / COUNT(*), 2)
FROM cuotas
ORDER BY porcentaje_uso DESC, columna;

-- ============================================================================
-- PASO 4: Verificar índices en columnas sincronizadas
-- ============================================================================
SELECT 
    'PASO 4: Indices en columnas sincronizadas' AS paso,
    t.tablename AS tabla,
    i.indexname AS indice,
    a.attname AS columna,
    CASE WHEN i.indexdef LIKE '%UNIQUE%' THEN 'UNIQUE' ELSE 'NORMAL' END AS tipo_indice
FROM pg_indexes i
JOIN pg_class c ON c.relname = i.indexname
JOIN pg_index idx ON idx.indexrelid = c.oid
JOIN pg_attribute a ON a.attrelid = idx.indrelid AND a.attnum = ANY(idx.indkey)
JOIN pg_class t ON t.oid = idx.indrelid
WHERE i.schemaname = 'public'
AND t.tablename IN ('pagos', 'cuotas')
AND a.attname IN (
    -- Columnas Pago
    'banco', 'codigo_pago', 'comprobante', 'creado_en', 'descuento',
    'dias_mora', 'documento', 'fecha_vencimiento', 'hora_pago', 'metodo_pago',
    'monto', 'monto_capital', 'monto_cuota_programado', 'monto_interes',
    'monto_mora', 'monto_total', 'numero_operacion', 'observaciones',
    'referencia_pago', 'tasa_mora', 'tipo_pago',
    -- Columnas Cuota
    'creado_en', 'actualizado_en'
)
ORDER BY t.tablename, a.attname, i.indexname;

-- ============================================================================
-- PASO 5: Resumen de columnas más usadas vs menos usadas
-- ============================================================================
WITH uso_pagos AS (
    SELECT 'banco' AS columna, COUNT(banco) AS con_valor, COUNT(*) AS total FROM pagos
    UNION ALL SELECT 'codigo_pago', COUNT(codigo_pago), COUNT(*) FROM pagos
    UNION ALL SELECT 'comprobante', COUNT(comprobante), COUNT(*) FROM pagos
    UNION ALL SELECT 'creado_en', COUNT(creado_en), COUNT(*) FROM pagos
    UNION ALL SELECT 'descuento', COUNT(descuento), COUNT(*) FROM pagos
    UNION ALL SELECT 'dias_mora', COUNT(dias_mora), COUNT(*) FROM pagos
    UNION ALL SELECT 'documento', COUNT(documento), COUNT(*) FROM pagos
    UNION ALL SELECT 'fecha_vencimiento', COUNT(fecha_vencimiento), COUNT(*) FROM pagos
    UNION ALL SELECT 'hora_pago', COUNT(hora_pago), COUNT(*) FROM pagos
    UNION ALL SELECT 'metodo_pago', COUNT(metodo_pago), COUNT(*) FROM pagos
    UNION ALL SELECT 'monto', COUNT(monto), COUNT(*) FROM pagos
    UNION ALL SELECT 'monto_capital', COUNT(monto_capital), COUNT(*) FROM pagos
    UNION ALL SELECT 'monto_cuota_programado', COUNT(monto_cuota_programado), COUNT(*) FROM pagos
    UNION ALL SELECT 'monto_interes', COUNT(monto_interes), COUNT(*) FROM pagos
    UNION ALL SELECT 'monto_mora', COUNT(monto_mora), COUNT(*) FROM pagos
    UNION ALL SELECT 'monto_total', COUNT(monto_total), COUNT(*) FROM pagos
    UNION ALL SELECT 'numero_operacion', COUNT(numero_operacion), COUNT(*) FROM pagos
    UNION ALL SELECT 'observaciones', COUNT(observaciones), COUNT(*) FROM pagos
    UNION ALL SELECT 'referencia_pago', COUNT(referencia_pago), COUNT(*) FROM pagos
    UNION ALL SELECT 'tasa_mora', COUNT(tasa_mora), COUNT(*) FROM pagos
    UNION ALL SELECT 'tipo_pago', COUNT(tipo_pago), COUNT(*) FROM pagos
),
uso_cuotas AS (
    SELECT 'creado_en' AS columna, COUNT(creado_en) AS con_valor, COUNT(*) AS total FROM cuotas
    UNION ALL SELECT 'actualizado_en', COUNT(actualizado_en), COUNT(*) FROM cuotas
)
SELECT 
    'PASO 5: Resumen uso columnas' AS paso,
    'pagos' AS tabla,
    columna,
    con_valor,
    total,
    ROUND(100.0 * con_valor / total, 2) AS porcentaje_uso,
    CASE 
        WHEN ROUND(100.0 * con_valor / total, 2) >= 50 THEN 'ALTO USO'
        WHEN ROUND(100.0 * con_valor / total, 2) >= 10 THEN 'MEDIO USO'
        WHEN ROUND(100.0 * con_valor / total, 2) > 0 THEN 'BAJO USO'
        ELSE 'SIN USO'
    END AS categoria
FROM uso_pagos
UNION ALL
SELECT 
    'PASO 5: Resumen uso columnas',
    'cuotas',
    columna,
    con_valor,
    total,
    ROUND(100.0 * con_valor / total, 2),
    CASE 
        WHEN ROUND(100.0 * con_valor / total, 2) >= 50 THEN 'ALTO USO'
        WHEN ROUND(100.0 * con_valor / total, 2) >= 10 THEN 'MEDIO USO'
        WHEN ROUND(100.0 * con_valor / total, 2) > 0 THEN 'BAJO USO'
        ELSE 'SIN USO'
    END
FROM uso_cuotas
ORDER BY tabla, porcentaje_uso DESC;
