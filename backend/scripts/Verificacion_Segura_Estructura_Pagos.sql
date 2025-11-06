-- ============================================
-- VERIFICACIÓN SEGURA DE ESTRUCTURA DE TABLA PAGOS
-- ============================================
-- Este script NO intenta usar columnas que no existen
-- Ejecutar en DBeaver para verificar la estructura

-- ============================================
-- PASO 1: Verificar existencia de la tabla
-- ============================================
SELECT 
    'PASO 1: Verificar tabla' AS paso,
    CASE 
        WHEN EXISTS (
            SELECT 1 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = 'pagos'
        ) THEN '✅ Tabla pagos EXISTE'
        ELSE '❌ Tabla pagos NO EXISTE'
    END AS estado;

-- ============================================
-- PASO 2: Listar TODAS las columnas que existen
-- ============================================
SELECT 
    'PASO 2: Columnas existentes' AS paso,
    column_name AS columna,
    data_type AS tipo_dato,
    character_maximum_length AS longitud_max,
    is_nullable AS permite_null,
    column_default AS valor_por_defecto,
    ordinal_position AS posicion
FROM information_schema.columns
WHERE table_schema = 'public'
    AND table_name = 'pagos'
ORDER BY ordinal_position;

-- ============================================
-- PASO 3: Verificar columnas críticas (sin usar las columnas directamente)
-- ============================================
SELECT 
    'PASO 3: Verificación de columnas críticas' AS paso,
    columna_esperada,
    CASE 
        WHEN columna_existe IS NOT NULL THEN '✅ EXISTE'
        ELSE '❌ NO EXISTE'
    END AS estado,
    CASE 
        WHEN columna_existe IS NOT NULL THEN columna_existe::TEXT
        ELSE 'NO DISPONIBLE'
    END AS tipo_dato
FROM (
    SELECT unnest(ARRAY[
        'id',
        'cedula_cliente',  -- ⚠️ CRÍTICA - Probablemente falta
        'prestamo_id',
        'numero_cuota',
        'fecha_pago',
        'fecha_registro',
        'monto_pagado',
        'numero_documento',
        'institucion_bancaria',
        'documento_nombre',
        'documento_tipo',
        'documento_tamaño',
        'documento_ruta',
        'conciliado',
        'fecha_conciliacion',
        'estado',  -- ⚠️ Puede no existir
        'activo',
        'notas',
        'usuario_registro',
        'fecha_actualizacion',
        'verificado_concordancia'
    ]) AS columna_esperada
) esperadas
LEFT JOIN (
    SELECT 
        column_name,
        data_type || 
        CASE 
            WHEN character_maximum_length IS NOT NULL 
            THEN '(' || character_maximum_length || ')'
            ELSE ''
        END AS tipo_completo
    FROM information_schema.columns
    WHERE table_schema = 'public'
        AND table_name = 'pagos'
) existentes ON existentes.column_name = esperadas.columna_esperada
ORDER BY 
    CASE 
        WHEN columna_existe IS NULL THEN 1
        ELSE 2
    END,
    columna_esperada;

-- ============================================
-- PASO 4: Verificar específicamente cedula_cliente
-- ============================================
SELECT 
    'PASO 4: Verificación cedula_cliente' AS paso,
    CASE 
        WHEN EXISTS (
            SELECT 1 
            FROM information_schema.columns
            WHERE table_schema = 'public'
                AND table_name = 'pagos'
                AND column_name = 'cedula_cliente'
        ) THEN '✅ EXISTE - El modelo debería funcionar'
        ELSE '❌ NO EXISTE - Esto causa el error 500 en listar_pagos'
    END AS estado_cedula_cliente,
    CASE 
        WHEN EXISTS (
            SELECT 1 
            FROM information_schema.columns
            WHERE table_schema = 'public'
                AND table_name = 'pagos'
                AND column_name = 'cedula_cliente'
        ) THEN (
            SELECT 
                'Tipo: ' || data_type || 
                CASE 
                    WHEN character_maximum_length IS NOT NULL 
                    THEN ', Longitud: ' || character_maximum_length
                    ELSE ''
                END
            FROM information_schema.columns
            WHERE table_schema = 'public'
                AND table_name = 'pagos'
                AND column_name = 'cedula_cliente'
        )
        ELSE 'Columna no existe'
    END AS detalles;

-- ============================================
-- PASO 5: Ver columnas similares (por si el nombre es diferente)
-- ============================================
SELECT 
    'PASO 5: Columnas relacionadas con cliente/cedula' AS paso,
    column_name AS columna_encontrada,
    data_type AS tipo_dato
FROM information_schema.columns
WHERE table_schema = 'public'
    AND table_name = 'pagos'
    AND (
        column_name ILIKE '%cedula%' 
        OR column_name ILIKE '%cliente%'
        OR column_name ILIKE '%id_cliente%'
        OR column_name ILIKE '%client_id%'
    )
ORDER BY column_name;

-- ============================================
-- PASO 6: Contar registros (solo si existen columnas básicas)
-- ============================================
SELECT 
    'PASO 6: Conteo de registros' AS paso,
    CASE 
        WHEN EXISTS (
            SELECT 1 
            FROM information_schema.columns
            WHERE table_schema = 'public'
                AND table_name = 'pagos'
                AND column_name = 'id'
        ) THEN (
            SELECT COUNT(*)::TEXT
            FROM pagos
        )
        ELSE 'No se puede contar (columna id no existe)'
    END AS total_registros;

-- ============================================
-- PASO 7: Ver índices
-- ============================================
SELECT 
    'PASO 7: Índices' AS paso,
    indexname AS nombre_indice,
    indexdef AS definicion_indice
FROM pg_indexes
WHERE schemaname = 'public'
    AND tablename = 'pagos'
ORDER BY indexname;

-- ============================================
-- PASO 8: RESUMEN FINAL
-- ============================================
SELECT 
    '=== RESUMEN FINAL ===' AS resumen,
    (SELECT COUNT(*) FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'pagos') AS total_columnas_existentes,
    CASE 
        WHEN EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = 'pagos' AND column_name = 'cedula_cliente'
        ) THEN '✅ cedula_cliente existe'
        ELSE '❌ cedula_cliente NO existe - REQUIERE ACCIÓN'
    END AS problema_principal,
    CASE 
        WHEN EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = 'pagos' AND column_name = 'estado'
        ) THEN '✅ estado existe'
        ELSE '⚠️ estado NO existe'
    END AS estado_columna,
    CASE 
        WHEN (SELECT COUNT(*) FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'pagos') >= 15 
        THEN '✅ Número razonable de columnas'
        ELSE '⚠️ Pocas columnas, pueden faltar más'
    END AS verificacion_general;

