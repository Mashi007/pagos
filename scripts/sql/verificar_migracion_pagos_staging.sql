-- ============================================
-- ✅ VERIFICACIÓN COMPLETA: MIGRACIÓN DE PAGOS_STAGING
-- ============================================
-- Este script verifica si la migración desde pagos_staging a public.pagos está completa
-- Fecha: 2025-01-XX
-- Ejecutar en: DBeaver (Producción)
-- ============================================

-- ============================================
-- 1. RESUMEN GENERAL: PAGOS_STAGING vs PAGOS
-- ============================================
SELECT 
    '📊 RESUMEN GENERAL' AS seccion,
    '' AS detalle;

SELECT 
    (SELECT COUNT(*) FROM public.pagos_staging) AS total_en_staging,
    (SELECT COUNT(*) FROM public.pagos) AS total_en_pagos,
    (SELECT COUNT(*) FROM public.pagos_staging) - (SELECT COUNT(*) FROM public.pagos) AS diferencia;

-- ============================================
-- 2. VERIFICAR ESTRUCTURA DE pagos_staging
-- ============================================
SELECT 
    '📋 ESTRUCTURA DE pagos_staging' AS seccion,
    '' AS detalle;

SELECT 
    column_name,
    data_type,
    character_maximum_length,
    is_nullable,
    ordinal_position
FROM information_schema.columns
WHERE table_schema = 'public' 
  AND table_name = 'pagos_staging'
ORDER BY ordinal_position;

-- ============================================
-- 3. CONTAR REGISTROS EN STAGING (CON VALIDACIONES)
-- ============================================
SELECT 
    '📈 ESTADÍSTICAS DE pagos_staging' AS seccion,
    '' AS detalle;

WITH staging_montos AS (
    SELECT 
        *,
        CASE 
            WHEN monto_pagado IS NULL THEN NULL
            WHEN TRIM(COALESCE(monto_pagado::TEXT, '')) = '' THEN NULL
            WHEN UPPER(TRIM(COALESCE(monto_pagado::TEXT, ''))) IN ('NN', 'N', 'NULL', '0', '0.00') THEN NULL
            WHEN TRIM(REPLACE(REPLACE(COALESCE(monto_pagado::TEXT, ''), ',', ''), ' ', '')) ~ '^-?\d+(\.\d+)?$' THEN
                CAST(REPLACE(REPLACE(monto_pagado::TEXT, ',', ''), ' ', '') AS NUMERIC(12, 2))
            ELSE NULL
        END AS monto_pagado_normalizado
    FROM public.pagos_staging
)
SELECT 
    COUNT(*) AS total_registros_staging,
    COUNT(DISTINCT cedula_cliente) AS clientes_unicos,
    COUNT(CASE WHEN cedula_cliente IS NULL OR TRIM(COALESCE(cedula_cliente, '')) = '' THEN 1 END) AS registros_sin_cedula,
    COUNT(CASE WHEN fecha_pago IS NULL THEN 1 END) AS registros_sin_fecha,
    COUNT(CASE 
        WHEN monto_pagado_normalizado IS NULL THEN 1
        WHEN monto_pagado_normalizado <= 0 THEN 1
        ELSE 0
    END) AS registros_sin_monto_valido,
    COUNT(CASE WHEN numero_documento IS NULL OR TRIM(COALESCE(numero_documento, '')) = '' THEN 1 END) AS registros_sin_numero_documento
FROM staging_montos;

-- ============================================
-- 4. COMPARAR REGISTROS MIGRADOS vs NO MIGRADOS
-- ============================================
SELECT 
    '🔄 COMPARACIÓN: MIGRADOS vs NO MIGRADOS' AS seccion,
    '' AS detalle;

-- Primero, contar cuántos registros de staging tienen match en pagos (migrados)
WITH staging_normalizado AS (
    SELECT 
        CASE 
            WHEN TRIM(COALESCE(cedula_cliente, '')) = '' OR UPPER(TRIM(COALESCE(cedula_cliente, ''))) IN ('NN', 'N', 'NULL') THEN NULL
            ELSE UPPER(TRIM(cedula_cliente))
        END AS cedula_cliente_norm,
        
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
        END AS fecha_pago_norm,
        
        CASE 
            WHEN numero_documento IS NULL 
                 OR TRIM(COALESCE(numero_documento, '')) = '' 
                 OR UPPER(TRIM(COALESCE(numero_documento, ''))) IN ('NN', 'N', 'NULL') THEN NULL
            ELSE TRIM(numero_documento)
        END AS numero_documento_norm
    FROM public.pagos_staging
)
SELECT 
    COUNT(*) AS total_staging,
    COUNT(CASE WHEN EXISTS (
        SELECT 1 
        FROM public.pagos p
        WHERE p.cedula_cliente = sn.cedula_cliente_norm
          AND p.fecha_pago = sn.fecha_pago_norm
          AND p.numero_documento = sn.numero_documento_norm
    ) THEN 1 END) AS registros_migrados,
    COUNT(CASE WHEN NOT EXISTS (
        SELECT 1 
        FROM public.pagos p
        WHERE p.cedula_cliente = sn.cedula_cliente_norm
          AND p.fecha_pago = sn.fecha_pago_norm
          AND p.numero_documento = sn.numero_documento_norm
    ) THEN 1 END) AS registros_no_migrados,
    ROUND(
        COUNT(CASE WHEN EXISTS (
            SELECT 1 
            FROM public.pagos p
            WHERE p.cedula_cliente = sn.cedula_cliente_norm
              AND p.fecha_pago = sn.fecha_pago_norm
              AND p.numero_documento = sn.numero_documento_norm
        ) THEN 1 END) * 100.0 / COUNT(*), 2
    ) AS porcentaje_migrado
FROM staging_normalizado sn;

-- ============================================
-- 5. DETALLAR REGISTROS NO MIGRADOS Y RAZONES
-- ============================================
SELECT 
    '❌ REGISTROS NO MIGRADOS Y SUS RAZONES' AS seccion,
    '' AS detalle;

WITH staging_datos AS (
    SELECT 
        ps.*,
        CASE 
            WHEN TRIM(COALESCE(ps.cedula_cliente, '')) = '' OR UPPER(TRIM(COALESCE(ps.cedula_cliente, ''))) IN ('NN', 'N', 'NULL') THEN NULL
            ELSE UPPER(TRIM(ps.cedula_cliente))
        END AS cedula_cliente_norm,
        
        CASE 
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
        END AS fecha_pago_norm,
        
        CASE 
            WHEN ps.monto_pagado IS NULL 
                 OR TRIM(COALESCE(ps.monto_pagado::TEXT, '')) = '' 
                 OR UPPER(TRIM(COALESCE(ps.monto_pagado::TEXT, ''))) IN ('NN', 'N', 'NULL', '0', '0.00') THEN NULL
            ELSE 
                CAST(REPLACE(REPLACE(ps.monto_pagado::TEXT, ',', ''), ' ', '') AS NUMERIC(12, 2))
        END AS monto_pagado_norm,
        
        CASE 
            WHEN ps.numero_documento IS NULL 
                 OR TRIM(COALESCE(ps.numero_documento, '')) = '' 
                 OR UPPER(TRIM(COALESCE(ps.numero_documento, ''))) IN ('NN', 'N', 'NULL') THEN NULL
            ELSE TRIM(ps.numero_documento)
        END AS numero_documento_norm,
        
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
)
SELECT 
    COUNT(*) AS total_no_migrados,
    COUNT(CASE WHEN cedula_cliente_norm IS NULL THEN 1 END) AS sin_cedula_valida,
    COUNT(CASE WHEN fecha_pago_norm IS NULL THEN 1 END) AS sin_fecha_valida,
    COUNT(CASE WHEN monto_pagado_norm IS NULL OR monto_pagado_norm <= 0 THEN 1 END) AS sin_monto_valido,
    COUNT(CASE WHEN numero_documento_norm IS NULL THEN 1 END) AS sin_numero_documento_valido,
    COUNT(CASE WHEN cliente_existe IS NULL THEN 1 END) AS cliente_no_existe_en_bd
FROM staging_datos
WHERE 
    cedula_cliente_norm IS NULL
    OR fecha_pago_norm IS NULL
    OR monto_pagado_norm IS NULL
    OR monto_pagado_norm <= 0
    OR numero_documento_norm IS NULL
    OR cliente_existe IS NULL;

-- ============================================
-- 6. MOSTRAR EJEMPLOS DE REGISTROS NO MIGRADOS
-- ============================================
SELECT 
    '📝 EJEMPLOS DE REGISTROS NO MIGRADOS (Primeros 10)' AS seccion,
    '' AS detalle;

WITH staging_datos AS (
    SELECT 
        ps.*,
        CASE 
            WHEN TRIM(COALESCE(ps.cedula_cliente, '')) = '' OR UPPER(TRIM(COALESCE(ps.cedula_cliente, ''))) IN ('NN', 'N', 'NULL') THEN NULL
            ELSE UPPER(TRIM(ps.cedula_cliente))
        END AS cedula_cliente_norm,
        
        CASE 
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
        END AS fecha_pago_norm,
        
        CASE 
            WHEN ps.monto_pagado IS NULL 
                 OR TRIM(COALESCE(ps.monto_pagado::TEXT, '')) = '' 
                 OR UPPER(TRIM(COALESCE(ps.monto_pagado::TEXT, ''))) IN ('NN', 'N', 'NULL', '0', '0.00') THEN NULL
            ELSE 
                CAST(REPLACE(REPLACE(ps.monto_pagado::TEXT, ',', ''), ' ', '') AS NUMERIC(12, 2))
        END AS monto_pagado_norm,
        
        CASE 
            WHEN ps.numero_documento IS NULL 
                 OR TRIM(COALESCE(ps.numero_documento, '')) = '' 
                 OR UPPER(TRIM(COALESCE(ps.numero_documento, ''))) IN ('NN', 'N', 'NULL') THEN NULL
            ELSE TRIM(ps.numero_documento)
        END AS numero_documento_norm,
        
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
)
SELECT 
    id_stg,
    cedula_cliente AS cedula_original,
    cedula_cliente_norm AS cedula_normalizada,
    fecha_pago AS fecha_original,
    fecha_pago_norm AS fecha_normalizada,
    monto_pagado AS monto_original,
    monto_pagado_norm AS monto_normalizado,
    numero_documento AS numero_documento_original,
    numero_documento_norm AS numero_documento_normalizado,
    CASE 
        WHEN cedula_cliente_norm IS NULL THEN 'Sin cédula válida'
        WHEN fecha_pago_norm IS NULL THEN 'Sin fecha válida'
        WHEN monto_pagado_norm IS NULL OR monto_pagado_norm <= 0 THEN 'Sin monto válido'
        WHEN numero_documento_norm IS NULL THEN 'Sin número de documento'
        WHEN cliente_existe IS NULL THEN 'Cliente no existe en BD'
        ELSE 'Otra razón'
    END AS razon_no_migrado
FROM staging_datos
WHERE 
    cedula_cliente_norm IS NULL
    OR fecha_pago_norm IS NULL
    OR monto_pagado_norm IS NULL
    OR monto_pagado_norm <= 0
    OR numero_documento_norm IS NULL
    OR cliente_existe IS NULL
ORDER BY id_stg
LIMIT 10;

-- ============================================
-- 7. VERIFICAR REGISTROS MIGRADOS RECIENTEMENTE
-- ============================================
SELECT 
    '✅ REGISTROS MIGRADOS RECIENTEMENTE' AS seccion,
    '' AS detalle;

SELECT 
    COUNT(*) AS total_migrados_hoy,
    MIN(fecha_registro) AS primer_registro,
    MAX(fecha_registro) AS ultimo_registro,
    COUNT(DISTINCT cedula_cliente) AS clientes_unicos_migrados,
    SUM(monto_pagado) AS monto_total_migrado
FROM public.pagos
WHERE usuario_registro = 'itmaster@rapicreditca.com'
  AND fecha_registro >= CURRENT_DATE - INTERVAL '7 days';

-- ============================================
-- 8. CONCLUSIÓN: ESTADO DE LA MIGRACIÓN
-- ============================================
SELECT 
    '🎯 CONCLUSIÓN: ESTADO DE LA MIGRACIÓN' AS seccion,
    '' AS detalle;

WITH staging_count AS (
    SELECT COUNT(*) AS total FROM public.pagos_staging
),
pagos_count AS (
    SELECT COUNT(*) AS total FROM public.pagos
),
migrados_count AS (
    SELECT COUNT(*) AS total
    FROM public.pagos
    WHERE usuario_registro = 'itmaster@rapicreditca.com'
      AND fecha_registro >= CURRENT_DATE - INTERVAL '30 days'
)
SELECT 
    sc.total AS total_en_staging,
    pc.total AS total_en_pagos,
    mc.total AS migrados_recientemente,
    CASE 
        WHEN sc.total <= pc.total THEN '✅ COMPLETA - Todos los registros válidos fueron migrados'
        WHEN sc.total > pc.total THEN '⚠️ PENDIENTE - Hay registros en staging que no fueron migrados'
        ELSE '❌ ERROR - No se puede determinar el estado'
    END AS estado_migracion,
    ROUND((pc.total * 100.0 / NULLIF(sc.total, 0)), 2) AS porcentaje_completado
FROM staging_count sc, pagos_count pc, migrados_count mc;

-- ============================================
-- FIN DEL SCRIPT DE VERIFICACIÓN
-- ============================================

