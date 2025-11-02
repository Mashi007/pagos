    -- ============================================
    -- DIAGNÓSTICO COMPLETO DE BASE DE DATOS - PAGOS
    -- ============================================
    -- Este script verifica la conexión y estructura de la BD
    -- Ejecutar en DBeaver para diagnosticar problemas

    -- ============================================
    -- 1. VERIFICAR CONEXIÓN BÁSICA
    -- ============================================
    SELECT 
        '✅ Conexión OK' AS estado,
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
        END AS estado,
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
    SELECT 
        'Total registros' AS verificacion,
        COUNT(*) AS total_pagos
    FROM pagos;

    -- ============================================
    -- 7. VER MUESTRA DE DATOS (solo columnas básicas)
    -- ============================================
    -- Solo mostrar columnas que deberían existir siempre
    SELECT 
        'Muestra de datos' AS verificacion,
        id,
        monto_pagado,
        fecha_pago,
        numero_documento
    FROM pagos
    LIMIT 5;

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
    DO $$
    BEGIN
        IF EXISTS (
            SELECT 1 
            FROM information_schema.tables
            WHERE table_schema = 'public'
                AND table_name = 'alembic_version'
        ) THEN
            -- Si la tabla existe, ejecutar el SELECT
            PERFORM version_num FROM alembic_version LIMIT 1;
            RAISE NOTICE 'Tabla alembic_version existe. Ejecuta manualmente: SELECT version_num FROM alembic_version LIMIT 1;';
        ELSE
            RAISE NOTICE 'Tabla alembic_version NO existe. Las migraciones de Alembic no están configuradas.';
        END IF;
    END $$;

    -- Alternativa: Intentar SELECT solo si existe (puede fallar si no existe, pero es informativo)
    -- Comentar esta sección si prefieres evitar el error
    -- SELECT 
    --     'Última migración aplicada' AS verificacion,
    --     version_num AS ultima_migracion
    -- FROM alembic_version
    -- LIMIT 1;

    -- ============================================
    -- 9. COMPARACIÓN: MODELO vs BASE DE DATOS
    -- ============================================
    -- Columnas que el modelo Python espera pero que pueden no existir en BD
    WITH modelo_python AS (
        SELECT unnest(ARRAY[
            'id',
            'cedula_cliente',  -- ⚠️ ESTA ES LA QUE FALTA
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
            'estado',
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
        21 AS columnas_esperadas_por_modelo,
        CASE 
            WHEN (SELECT COUNT(*) FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'pagos') >= 21 THEN '✅ Número de columnas OK'
            ELSE '⚠️ Pueden faltar columnas'
        END AS verificacion_columnas;

