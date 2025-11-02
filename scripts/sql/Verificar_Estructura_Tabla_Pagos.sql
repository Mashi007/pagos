-- ============================================
-- VERIFICACIÓN DE ESTRUCTURA DE TABLA PAGOS
-- ============================================
-- Ejecutar este script en DBeaver para verificar la estructura
-- de la tabla 'pagos' y compararla con lo que espera el modelo

-- 1. Verificar si la tabla 'pagos' existe
SELECT 
    table_name,
    table_schema
FROM information_schema.tables 
WHERE table_name = 'pagos'
    AND table_schema = 'public';

-- 2. Listar TODAS las columnas de la tabla 'pagos' con sus tipos
SELECT 
    column_name,
    data_type,
    character_maximum_length,
    is_nullable,
    column_default,
    ordinal_position
FROM information_schema.columns
WHERE table_schema = 'public'
    AND table_name = 'pagos'
ORDER BY ordinal_position;

-- 3. Verificar específicamente si existe la columna 'cedula_cliente'
SELECT 
    CASE 
        WHEN EXISTS (
            SELECT 1 
            FROM information_schema.columns
            WHERE table_schema = 'public'
                AND table_name = 'pagos'
                AND column_name = 'cedula_cliente'
        ) THEN '✅ Columna cedula_cliente EXISTE'
        ELSE '❌ Columna cedula_cliente NO EXISTE'
    END AS estado_cedula_cliente;

-- 4. Verificar otras columnas críticas que espera el modelo
SELECT 
    column_name,
    CASE 
        WHEN column_name IN (
            'id',
            'cedula_cliente',
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
            'activo',
            'notas',
            'usuario_registro',
            'fecha_actualizacion',
            'verificado_concordancia'
        ) THEN '✅ Requerida'
        ELSE '⚠️ No requerida'
    END AS importancia
FROM information_schema.columns
WHERE table_schema = 'public'
    AND table_name = 'pagos'
ORDER BY ordinal_position;

-- 5. Comparar columnas esperadas vs existentes
WITH columnas_esperadas AS (
    SELECT unnest(ARRAY[
        'id',
        'cedula_cliente',
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
        'activo',
        'notas',
        'usuario_registro',
        'fecha_actualizacion',
        'verificado_concordancia'
    ]) AS columna
),
columnas_existentes AS (
    SELECT column_name
    FROM information_schema.columns
    WHERE table_schema = 'public'
        AND table_name = 'pagos'
)
SELECT 
    COALESCE(e.columna, '') AS columna_esperada,
    CASE 
        WHEN e.columna IS NULL THEN '❌ FALTA EN MODELO'
        WHEN ex.column_name IS NULL THEN '❌ FALTA EN BD'
        ELSE '✅ OK'
    END AS resultado_verificacion
FROM columnas_esperadas e
FULL OUTER JOIN columnas_existentes ex ON e.columna = ex.column_name
ORDER BY 
    CASE 
        WHEN e.columna IS NULL THEN 2
        WHEN ex.column_name IS NULL THEN 1
        ELSE 3
    END,
    COALESCE(e.columna, ex.column_name);

-- 6. Ver índices en la tabla 'pagos'
SELECT 
    indexname,
    indexdef
FROM pg_indexes
WHERE schemaname = 'public'
    AND tablename = 'pagos'
ORDER BY indexname;

-- 7. Ver constraints (foreign keys, primary keys, etc.)
SELECT
    tc.constraint_name,
    tc.constraint_type,
    kcu.column_name,
    ccu.table_name AS foreign_table_name,
    ccu.column_name AS foreign_column_name
FROM information_schema.table_constraints AS tc
JOIN information_schema.key_column_usage AS kcu
    ON tc.constraint_name = kcu.constraint_name
    AND tc.table_schema = kcu.table_schema
LEFT JOIN information_schema.constraint_column_usage AS ccu
    ON ccu.constraint_name = tc.constraint_name
    AND ccu.table_schema = tc.table_schema
WHERE tc.table_schema = 'public'
    AND tc.table_name = 'pagos'
ORDER BY tc.constraint_type, tc.constraint_name;

-- 8. Verificar tipo de datos de columnas críticas (comparar con modelo)
-- Solo verifica columnas que existen (excluye 'estado' que puede no existir)
SELECT 
    column_name,
    data_type,
    character_maximum_length,
    CASE 
        WHEN column_name = 'cedula_cliente' AND data_type = 'character varying' AND character_maximum_length = 20 THEN '✅ Correcto'
        WHEN column_name = 'cedula_cliente' THEN '⚠️ Tipo diferente o longitud incorrecta'
        WHEN column_name = 'monto_pagado' AND data_type = 'numeric' THEN '✅ Correcto'
        WHEN column_name = 'fecha_pago' AND (data_type LIKE '%timestamp%' OR data_type = 'date') THEN '✅ Correcto'
        WHEN column_name = 'fecha_registro' AND (data_type LIKE '%timestamp%' OR data_type = 'date') THEN '✅ Correcto'
        ELSE 'Verificar'
    END AS verificacion_tipo
FROM information_schema.columns
WHERE table_schema = 'public'
    AND table_name = 'pagos'
    AND column_name IN (
        'cedula_cliente', 
        'monto_pagado', 
        'fecha_pago', 
        'fecha_registro'
    )
ORDER BY column_name;

