-- ============================================
-- VERIFICAR: ¿Cuántos registros YA ESTÁN migrados?
-- ============================================

WITH datos_limpios AS (
    SELECT 
        CASE 
            WHEN TRIM(COALESCE(cedula_cliente, '')) = '' OR UPPER(TRIM(COALESCE(cedula_cliente, ''))) IN ('NN', 'N', 'NULL') THEN NULL
            ELSE UPPER(REPLACE(TRIM(cedula_cliente), '-', ''))
        END AS cedula_cliente_normalizada,
        CASE 
            WHEN fecha_pago IS NULL 
                 OR TRIM(COALESCE(fecha_pago::TEXT, '')) = '' 
                 OR UPPER(TRIM(COALESCE(fecha_pago::TEXT, ''))) IN ('NN', 'N', 'NULL', 'ERROR', 'ERR')
                 OR fecha_pago::TEXT ~ '[^0-9/\-]' THEN 
                MAKE_DATE(2025, 10, 31)
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
            ELSE MAKE_DATE(2025, 10, 31)
        END AS fecha_pago_normalizada,
        CASE 
            WHEN monto_pagado IS NULL 
                 OR TRIM(COALESCE(monto_pagado::TEXT, '')) = '' 
                 OR UPPER(TRIM(COALESCE(monto_pagado::TEXT, ''))) IN ('NN', 'N', 'NULL') THEN NULL
            WHEN UPPER(TRIM(COALESCE(monto_pagado::TEXT, ''))) IN ('ERROR', 'ERR') THEN 0.00
            WHEN TRIM(COALESCE(monto_pagado::TEXT, '')) IN ('0', '0.00') THEN NULL
            ELSE 
                CAST(REPLACE(REPLACE(monto_pagado::TEXT, ',', ''), ' ', '') AS NUMERIC(12, 2))
        END AS monto_pagado_normalizado,
        CASE 
            WHEN numero_documento IS NULL 
                 OR TRIM(COALESCE(numero_documento, '')) = '' 
                 OR UPPER(TRIM(COALESCE(numero_documento, ''))) IN ('NN', 'N', 'NULL') THEN NULL
            ELSE TRIM(numero_documento)
        END AS numero_documento_normalizado
    FROM public.pagos_staging
),
datos_validados AS (
    SELECT 
        dc.cedula_cliente_normalizada AS cedula_cliente,
        dc.fecha_pago_normalizada,
        dc.monto_pagado_normalizado,
        dc.numero_documento_normalizado,
        c.id AS cliente_existe
    FROM datos_limpios dc
    LEFT JOIN public.clientes c ON c.cedula = dc.cedula_cliente_normalizada
    WHERE 
        dc.cedula_cliente_normalizada IS NOT NULL
        AND dc.monto_pagado_normalizado IS NOT NULL
        AND dc.monto_pagado_normalizado >= 0
        AND dc.numero_documento_normalizado IS NOT NULL
        AND c.id IS NOT NULL
)
SELECT 
    COUNT(*) AS total_validos,
    COUNT(CASE WHEN ya_existe = 1 THEN 1 END) AS ya_migrados_duplicados,
    COUNT(CASE WHEN ya_existe = 0 THEN 1 END) AS listos_para_migrar
FROM (
    SELECT 
        dv.*,
        CASE WHEN p.id IS NOT NULL THEN 1 ELSE 0 END AS ya_existe
    FROM datos_validados dv
    LEFT JOIN public.pagos p ON 
        UPPER(REPLACE(TRIM(p.cedula_cliente), '-', '')) = dv.cedula_cliente
        AND p.fecha_pago = dv.fecha_pago_normalizada
        AND p.numero_documento = dv.numero_documento_normalizado
) AS con_check_duplicado;

