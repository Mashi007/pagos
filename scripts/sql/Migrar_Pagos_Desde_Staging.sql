-- ============================================
-- SCRIPT DE MIGRACIÓN: PAGOS DESDE STAGING
-- ============================================
-- Fecha: 2025-10-31
-- Descripción: Migra datos desde pagos_staging a public.pagos
-- Ejecutar en: DBeaver (Producción)
-- ============================================
-- IMPORTANTE: Este script asume que pagos_staging tiene las columnas:
--   - cedula (o cedula_cliente) - REQUERIDO
--   - fecha_pago - REQUERIDO
--   - monto_pagado - REQUERIDO
--   - numero_documento - REQUERIDO
--
-- PASOS ANTES DE EJECUTAR:
-- 1. Verificar que la tabla pagos_staging existe
-- 2. Verificar que tiene datos cargados (ver PASO 1)
-- 3. Verificar que los clientes existen en public.clientes
-- 4. Si los nombres de columnas son diferentes, ajustar el script
-- ============================================

-- ============================================
-- PASO 1: VERIFICAR DATOS EN STAGING
-- ============================================
SELECT 
    COUNT(*) AS total_registros_staging,
    COUNT(DISTINCT cedula_cliente) AS clientes_unicos,
    COUNT(CASE WHEN cedula_cliente IS NULL OR TRIM(cedula_cliente) = '' THEN 1 END) AS registros_sin_cedula
FROM public.pagos_staging;

-- ============================================
-- PASO 2: VERIFICAR ESTRUCTURA DE pagos_staging
-- ============================================
SELECT 
    column_name,
    data_type,
    character_maximum_length,
    is_nullable
FROM information_schema.columns
WHERE table_schema = 'public' 
  AND table_name = 'pagos_staging'
ORDER BY ordinal_position;

-- ============================================
-- PASO 3: MIGRAR DATOS DE pagos_staging A public.pagos
-- ============================================
-- Este INSERT normaliza datos y valida:
-- 1. Normaliza 'nn'/'NN' → NULL o valores por defecto
-- 2. Convierte fechas de varios formatos (DD/MM/YYYY, MM/DD/YYYY, YYYY-MM-DD)
-- 3. Valida que el cliente existe en public.clientes
-- 4. Asigna valores por defecto para campos requeridos

WITH datos_limpios AS (
    SELECT 
        -- Normalizar cédula: quitar espacios, convertir 'nn' a NULL
        CASE 
            WHEN TRIM(COALESCE(cedula_cliente, '')) = '' OR UPPER(TRIM(COALESCE(cedula_cliente, ''))) IN ('NN', 'N', 'NULL') THEN NULL
            ELSE UPPER(TRIM(cedula_cliente))
        END AS cedula_cliente_normalizada,
        
        -- Normalizar fecha_pago: convertir varios formatos
        CASE 
            WHEN fecha_pago IS NULL OR TRIM(COALESCE(fecha_pago::TEXT, '')) = '' 
                 OR UPPER(TRIM(COALESCE(fecha_pago::TEXT, ''))) IN ('NN', 'N', 'NULL') THEN NULL
            WHEN fecha_pago::TEXT ~ '^\d{4}-\d{2}-\d{2}' THEN 
                fecha_pago::DATE  -- Ya está en formato YYYY-MM-DD
            WHEN fecha_pago::TEXT ~ '^\d{1,2}/\d{1,2}/\d{4}' THEN
                -- Intentar DD/MM/YYYY primero
                CASE 
                    WHEN (SPLIT_PART(fecha_pago::TEXT, '/', 1)::INTEGER) > 12 THEN
                        -- Es DD/MM/YYYY
                        MAKE_DATE(
                            SPLIT_PART(fecha_pago::TEXT, '/', 3)::INTEGER,
                            SPLIT_PART(fecha_pago::TEXT, '/', 2)::INTEGER,
                            SPLIT_PART(fecha_pago::TEXT, '/', 1)::INTEGER
                        )
                    ELSE
                        -- Puede ser MM/DD/YYYY o DD/MM/YYYY, intentar MM/DD/YYYY
                        MAKE_DATE(
                            SPLIT_PART(fecha_pago::TEXT, '/', 3)::INTEGER,
                            SPLIT_PART(fecha_pago::TEXT, '/', 1)::INTEGER,
                            SPLIT_PART(fecha_pago::TEXT, '/', 2)::INTEGER
                        )
                END
            ELSE 
                fecha_pago::DATE  -- Intentar conversión directa
        END AS fecha_pago_normalizada,
        
        -- Normalizar monto_pagado: convertir 'nn' a NULL, luego a NUMERIC
        CASE 
            WHEN monto_pagado IS NULL 
                 OR TRIM(COALESCE(monto_pagado::TEXT, '')) = '' 
                 OR UPPER(TRIM(COALESCE(monto_pagado::TEXT, ''))) IN ('NN', 'N', 'NULL', '0', '0.00') THEN NULL
            ELSE 
                CAST(REPLACE(REPLACE(monto_pagado::TEXT, ',', ''), ' ', '') AS NUMERIC(12, 2))
        END AS monto_pagado_normalizado,
        
        -- Normalizar numero_documento: quitar espacios, convertir 'nn' a NULL
        CASE 
            WHEN numero_documento IS NULL 
                 OR TRIM(COALESCE(numero_documento, '')) = '' 
                 OR UPPER(TRIM(COALESCE(numero_documento, ''))) IN ('NN', 'N', 'NULL') THEN NULL
            ELSE 
                TRIM(numero_documento)
        END AS numero_documento_normalizado
        
    FROM public.pagos_staging
),
datos_validados AS (
    SELECT 
        dc.cedula_cliente_normalizada AS cedula_cliente,
        dc.fecha_pago_normalizada,
        dc.monto_pagado_normalizado,
        dc.numero_documento_normalizado,
        -- Validar que el cliente existe
        c.id AS cliente_existe
    FROM datos_limpios dc
    LEFT JOIN public.clientes c ON c.cedula = dc.cedula_cliente_normalizada
    WHERE 
        -- Solo incluir registros válidos
        dc.cedula_cliente_normalizada IS NOT NULL
        AND dc.fecha_pago_normalizada IS NOT NULL
        AND dc.monto_pagado_normalizado IS NOT NULL
        AND dc.monto_pagado_normalizado > 0
        AND dc.numero_documento_normalizado IS NOT NULL
        AND c.id IS NOT NULL  -- Cliente debe existir
)
INSERT INTO public.pagos (
    cedula_cliente,
    prestamo_id,  -- NULL por ahora, se puede vincular después
    fecha_pago,
    fecha_registro,
    monto_pagado,
    numero_documento,
    estado,
    usuario_registro,
    activo,
    conciliado
)
SELECT 
    dv.cedula_cliente,
    NULL AS prestamo_id,  -- Se puede vincular después con base a cédula y fecha
    dv.fecha_pago_normalizada,
    CURRENT_TIMESTAMP AS fecha_registro,
    dv.monto_pagado_normalizado,
    dv.numero_documento_normalizado,
    'PAGADO' AS estado,  -- Por defecto, todos los pagos importados están como PAGADO
    'itmaster@rapicreditca.com' AS usuario_registro,  -- Cambiar si es necesario
    TRUE AS activo,
    FALSE AS conciliado
FROM datos_validados dv
WHERE NOT EXISTS (
    -- Evitar duplicados: verificar si ya existe un pago con la misma cédula, fecha y número de documento
    SELECT 1 
    FROM public.pagos p
    WHERE p.cedula_cliente = dv.cedula_cliente
      AND p.fecha_pago = dv.fecha_pago_normalizada
      AND p.numero_documento = dv.numero_documento_normalizado
)
RETURNING id, cedula_cliente, fecha_pago, monto_pagado, numero_documento;

-- ============================================
-- PASO 4: VERIFICAR RESULTADOS DE LA MIGRACIÓN
-- ============================================
SELECT 
    'Pagos migrados' AS descripcion,
    COUNT(*) AS total
FROM public.pagos
WHERE usuario_registro = 'itmaster@rapicreditca.com'
  AND fecha_registro >= CURRENT_DATE;

-- ============================================
-- PASO 5: REPORTE DE REGISTROS NO MIGRADOS
-- ============================================
-- Este query muestra registros de staging que NO se migraron (por validaciones)
SELECT 
    COUNT(*) AS registros_no_migrados,
    COUNT(CASE WHEN cedula_cliente IS NULL THEN 1 END) AS sin_cedula,
    COUNT(CASE WHEN fecha_pago_normalizada IS NULL THEN 1 END) AS sin_fecha,
    COUNT(CASE WHEN monto_pagado_normalizado IS NULL OR monto_pagado_normalizado <= 0 THEN 1 END) AS sin_monto_valido,
    COUNT(CASE WHEN numero_documento_normalizado IS NULL THEN 1 END) AS sin_numero_documento,
    COUNT(CASE WHEN cliente_existe IS NULL THEN 1 END) AS cliente_no_existe
FROM (
    SELECT 
        CASE 
            WHEN TRIM(COALESCE(cedula_cliente, '')) = '' OR UPPER(TRIM(COALESCE(cedula_cliente, ''))) IN ('NN', 'N', 'NULL') THEN NULL
            ELSE UPPER(TRIM(cedula_cliente))
        END AS cedula_cliente,
        CASE 
            WHEN fecha_pago IS NULL OR TRIM(COALESCE(fecha_pago::TEXT, '')) = '' 
                 OR UPPER(TRIM(COALESCE(fecha_pago::TEXT, ''))) IN ('NN', 'N', 'NULL') THEN NULL
            WHEN fecha_pago::TEXT ~ '^\d{4}-\d{2}-\d{2}' THEN fecha_pago::DATE
            WHEN fecha_pago::TEXT ~ '^\d{1,2}/\d{1,2}/\d{4}' THEN
                CASE 
                    WHEN (SPLIT_PART(fecha_pago::TEXT, '/', 1)::INTEGER) > 12 THEN
                        MAKE_DATE(
                            SPLIT_PART(fecha_pago::TEXT, '/', 3)::INTEGER,
                            SPLIT_PART(fecha_pago::TEXT, '/', 2)::INTEGER,
                            SPLIT_PART(fecha_pago::TEXT, '/', 1)::INTEGER
                        )
                    ELSE
                        MAKE_DATE(
                            SPLIT_PART(fecha_pago::TEXT, '/', 3)::INTEGER,
                            SPLIT_PART(fecha_pago::TEXT, '/', 1)::INTEGER,
                            SPLIT_PART(fecha_pago::TEXT, '/', 2)::INTEGER
                        )
                END
            ELSE fecha_pago::DATE
        END AS fecha_pago_normalizada,
        CASE 
            WHEN monto_pagado IS NULL 
                 OR TRIM(COALESCE(monto_pagado::TEXT, '')) = '' 
                 OR UPPER(TRIM(COALESCE(monto_pagado::TEXT, ''))) IN ('NN', 'N', 'NULL', '0', '0.00') THEN NULL
            ELSE 
                CAST(REPLACE(REPLACE(monto_pagado::TEXT, ',', ''), ' ', '') AS NUMERIC(12, 2))
        END AS monto_pagado_normalizado,
        CASE 
            WHEN numero_documento IS NULL 
                 OR TRIM(COALESCE(numero_documento, '')) = '' 
                 OR UPPER(TRIM(COALESCE(numero_documento, ''))) IN ('NN', 'N', 'NULL') THEN NULL
            ELSE TRIM(numero_documento)
        END AS numero_documento_normalizado,
        c.id AS cliente_existe
    FROM public.pagos_staging ps
    LEFT JOIN public.clientes c ON c.cedula = CASE 
        WHEN TRIM(COALESCE(ps.cedula_cliente, '')) = '' OR UPPER(TRIM(COALESCE(ps.cedula_cliente, ''))) IN ('NN', 'N', 'NULL') THEN NULL
        ELSE UPPER(TRIM(ps.cedula_cliente))
    END
    WHERE NOT EXISTS (
        SELECT 1 
        FROM public.pagos p
        WHERE p.cedula_cliente = CASE 
            WHEN TRIM(COALESCE(ps.cedula_cliente, '')) = '' OR UPPER(TRIM(COALESCE(ps.cedula_cliente, ''))) IN ('NN', 'N', 'NULL') THEN NULL
            ELSE UPPER(TRIM(ps.cedula_cliente))
        END
        AND p.fecha_pago = CASE 
            WHEN ps.fecha_pago IS NULL OR TRIM(COALESCE(ps.fecha_pago::TEXT, '')) = '' 
                 OR UPPER(TRIM(COALESCE(ps.fecha_pago::TEXT, ''))) IN ('NN', 'N', 'NULL') THEN NULL
            WHEN ps.fecha_pago::TEXT ~ '^\d{4}-\d{2}-\d{2}' THEN ps.fecha_pago::DATE
            WHEN ps.fecha_pago::TEXT ~ '^\d{1,2}/\d{1,2}/\d{4}' THEN
                CASE 
                    WHEN (SPLIT_PART(ps.fecha_pago::TEXT, '/', 1)::INTEGER) > 12 THEN
                        MAKE_DATE(
                            SPLIT_PART(ps.fecha_pago::TEXT, '/', 3)::INTEGER,
                            SPLIT_PART(ps.fecha_pago::TEXT, '/', 2)::INTEGER,
                            SPLIT_PART(ps.fecha_pago::TEXT, '/', 1)::INTEGER
                        )
                    ELSE
                        MAKE_DATE(
                            SPLIT_PART(ps.fecha_pago::TEXT, '/', 3)::INTEGER,
                            SPLIT_PART(ps.fecha_pago::TEXT, '/', 1)::INTEGER,
                            SPLIT_PART(ps.fecha_pago::TEXT, '/', 2)::INTEGER
                        )
                END
            ELSE ps.fecha_pago::DATE
        END
        AND p.numero_documento = CASE 
            WHEN ps.numero_documento IS NULL 
                 OR TRIM(COALESCE(ps.numero_documento, '')) = '' 
                 OR UPPER(TRIM(COALESCE(ps.numero_documento, ''))) IN ('NN', 'N', 'NULL') THEN NULL
            ELSE TRIM(ps.numero_documento)
        END
    )
) AS no_migrados
WHERE 
    cedula_cliente IS NULL
    OR fecha_pago_normalizada IS NULL
    OR monto_pagado_normalizado IS NULL
    OR monto_pagado_normalizado <= 0
    OR numero_documento_normalizado IS NULL
    OR cliente_existe IS NULL;

-- ============================================
-- FIN DEL SCRIPT
-- ============================================
-- NOTA: Si necesitas vincular los pagos a préstamos, puedes ejecutar
-- un UPDATE posterior basado en cedula_cliente y fecha_pago.

