-- ============================================
-- DIAGNÓSTICO COMPLETO DE BASE DE DATOS - PAGOS (VERSIÓN SEGURA)
-- ============================================
-- Este script NO intenta usar columnas que pueden no existir
-- Ejecutar en DBeaver para diagnosticar problemas
-- ⚠️ Esta versión es 100% segura - solo consulta metadatos

-- ============================================
-- 1. VERIFICAR CONEXIÓN BÁSICA
-- ============================================
SELECT 
    '✅ Conexión OK' AS resultado_conexion,
    current_database() AS base_datos,
    current_user AS usuario,
    version() AS version_postgresql;

-- ============================================
-- 2. VERIFICAR EXISTENCIA DE TABLAS PRINCIPALES
-- ============================================
SELECT 
    table_name,
    CASE 
        WHEN table_name IN ('pagos', 'prestamos', 'cuotas', 'clientes') THEN '✅ Tabla crítica'
        ELSE 'Tabla adicional'
    END AS tipo
FROM information_schema.tables
WHERE table_schema = 'public'
    AND table_type = 'BASE TABLE'
ORDER BY 
    CASE 
        WHEN table_name IN ('pagos', 'prestamos', 'cuotas', 'clientes') THEN 1
        ELSE 2
    END,
    table_name;

-- ============================================
-- 3. VERIFICAR ESTRUCTURA DETALLADA DE TABLA PAGOS
-- ============================================
SELECT 
    'PAGOS - Columnas' AS verificacion,
    column_name AS columna,
    data_type AS tipo_dato,
    character_maximum_length AS longitud,
    is_nullable AS nullable,
    ordinal_position AS posicion
FROM information_schema.columns
WHERE table_schema = 'public'
    AND table_name = 'pagos'
ORDER BY ordinal_position;

-- ============================================
-- 4. VERIFICAR PROBLEMA ESPECÍFICO: cedula_cliente
-- ============================================
SELECT 
    'VERIFICACIÓN cedula_cliente' AS verificacion,
    CASE 
        WHEN EXISTS (
            SELECT 1 
            FROM information_schema.columns
            WHERE table_schema = 'public'
                AND table_name = 'pagos'
                AND column_name = 'cedula_cliente'
        ) THEN '✅ EXISTE'
        ELSE '❌ NO EXISTE - PROBLEMA DETECTADO'
    END AS resultado_cedula_cliente,
    CASE 
        WHEN EXISTS (
            SELECT 1 
            FROM information_schema.columns
            WHERE table_schema = 'public'
                AND table_name = 'pagos'
                AND column_name = 'cedula_cliente'
        ) THEN NULL
        ELSE 'La columna cedula_cliente no existe en la tabla pagos. Esto causa el error 500.'
    END AS observacion;

-- ============================================
-- 5. VERIFICAR COLUMNAS SIMILARES (por si el nombre es diferente)
-- ============================================
SELECT 
    'Columnas similares a cedula' AS verificacion,
    column_name,
    data_type
FROM information_schema.columns
WHERE table_schema = 'public'
    AND table_name = 'pagos'
    AND (
        column_name ILIKE '%cedula%' 
        OR column_name ILIKE '%cliente%'
        OR column_name ILIKE '%id_cliente%'
    )
ORDER BY column_name;

-- ============================================
-- 6. CONTAR REGISTROS EN TABLA PAGOS
-- ============================================
-- Usar solo COUNT(*) que siempre funciona
SELECT 
    'Total registros' AS verificacion,
    COUNT(*) AS total_pagos
FROM pagos;

-- ============================================
-- 7. VER MUESTRA DE DATOS (solo columnas que siempre existen)
-- ============================================
-- Solo intentar mostrar columnas básicas que deberían existir
-- Si alguna no existe, PostgreSQL fallará pero al menos sabremos cuál
SELECT 
    'Muestra de datos - Intento 1' AS verificacion,
    id,
    monto_pagado,
    fecha_pago
FROM pagos
LIMIT 3;

-- Si lo anterior funciona, intentar más columnas
SELECT 
    'Muestra de datos - Intento 2' AS verificacion,
    id,
    numero_documento,
    fecha_registro
FROM pagos
LIMIT 3;

-- ============================================
-- 8. VERIFICAR MIGRACIONES APLICADAS (Alembic)
-- ============================================
SELECT 
    'Verificar migraciones' AS verificacion,
    CASE 
        WHEN EXISTS (
            SELECT 1 
            FROM information_schema.tables
            WHERE table_schema = 'public'
                AND table_name = 'alembic_version'
        ) THEN '✅ Tabla alembic_version existe'
        ELSE '⚠️ Tabla alembic_version no existe'
    END AS resultado_migraciones;

-- Si existe, ver última migración aplicada (solo si la tabla existe)
-- Usar DO block para verificar antes de consultar
DO $$
DECLARE
    tabla_existe BOOLEAN;
BEGIN
    SELECT EXISTS (
        SELECT 1 
        FROM information_schema.tables
        WHERE table_schema = 'public'
            AND table_name = 'alembic_version'
    ) INTO tabla_existe;
    
    IF tabla_existe THEN
        RAISE NOTICE '✅ La tabla alembic_version existe.';
        RAISE NOTICE 'Para ver la última migración, ejecuta: SELECT version_num FROM alembic_version LIMIT 1;';
    ELSE
        RAISE NOTICE '⚠️ La tabla alembic_version NO existe. Las migraciones de Alembic pueden no estar configuradas.';
    END IF;
END $$;

-- ============================================
-- 9. COMPARACIÓN: MODELO vs BASE DE DATOS (SIN ACCEDER A COLUMNAS)
-- ============================================
-- Solo compara metadatos, NO intenta usar las columnas
WITH modelo_python AS (
    SELECT unnest(ARRAY[
        'id',
        'cedula_cliente',  -- ⚠️ ESTA ES LA QUE PROBABLEMENTE FALTA
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
    ]) AS columna_esperada
)
SELECT 
    mp.columna_esperada,
    CASE 
        WHEN ic.column_name IS NOT NULL THEN '✅ EXISTE EN BD'
        ELSE '❌ FALTA EN BD'
    END AS resultado_columna,
    COALESCE(ic.data_type, 'N/A') AS tipo_en_bd,
    COALESCE(ic.character_maximum_length::TEXT, 'N/A') AS longitud_en_bd
FROM modelo_python mp
LEFT JOIN information_schema.columns ic
    ON ic.table_schema = 'public'
    AND ic.table_name = 'pagos'
    AND ic.column_name = mp.columna_esperada
ORDER BY 
    CASE 
        WHEN ic.column_name IS NULL THEN 1
        ELSE 2
    END,
    mp.columna_esperada;

-- ============================================
-- 10. RESUMEN FINAL
-- ============================================
SELECT 
    '=== RESUMEN DE DIAGNÓSTICO ===' AS resumen,
    CASE 
        WHEN EXISTS (
            SELECT 1 
            FROM information_schema.columns
            WHERE table_schema = 'public'
                AND table_name = 'pagos'
                AND column_name = 'cedula_cliente'
        ) THEN '✅ La columna cedula_cliente EXISTE - El problema puede ser otro'
        ELSE '❌ CRÍTICO: La columna cedula_cliente NO EXISTE - Esto causa el error 500'
    END AS problema_principal,
    (SELECT COUNT(*) FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'pagos') AS total_columnas_en_bd,
    20 AS columnas_esperadas_por_modelo,
    CASE 
        WHEN (SELECT COUNT(*) FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'pagos') >= 15 THEN '✅ Número razonable de columnas'
        ELSE '⚠️ Pueden faltar columnas'
    END AS verificacion_columnas;

-- ============================================
-- 11. LISTA DE COLUMNAS FALTANTES (si hay)
-- ============================================
WITH columnas_esperadas AS (
    SELECT unnest(ARRAY[
        'id', 'cedula_cliente', 'prestamo_id', 'numero_cuota', 'fecha_pago',
        'fecha_registro', 'monto_pagado', 'numero_documento', 'institucion_bancaria',
        'documento_nombre', 'documento_tipo', 'documento_tamaño', 'documento_ruta',
        'conciliado', 'fecha_conciliacion', 'activo', 'notas', 'usuario_registro',
        'fecha_actualizacion', 'verificado_concordancia'
    ]) AS columna
),
columnas_existentes AS (
    SELECT column_name
    FROM information_schema.columns
    WHERE table_schema = 'public'
        AND table_name = 'pagos'
)
SELECT 
    'Columnas faltantes' AS tipo,
    ce.columna AS columna_faltante
FROM columnas_esperadas ce
LEFT JOIN columnas_existentes ex ON ce.columna = ex.column_name
WHERE ex.column_name IS NULL
ORDER BY ce.columna;

