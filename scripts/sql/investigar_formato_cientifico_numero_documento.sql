-- ============================================================================
-- INVESTIGACIÓN: FORMATO CIENTÍFICO EN NUMERO_DOCUMENTO
-- ============================================================================
-- Este script investiga el alcance del problema de formato científico
-- en el campo numero_documento de la tabla pagos
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1. RESUMEN GENERAL
-- ----------------------------------------------------------------------------
SELECT 
    'RESUMEN GENERAL' as tipo_reporte,
    COUNT(*) FILTER (WHERE activo = true) as total_pagos_activos,
    COUNT(*) FILTER (WHERE activo = true AND numero_documento IS NOT NULL AND numero_documento != '') as pagos_con_documento,
    COUNT(*) FILTER (WHERE activo = true AND (
        numero_documento ~* '^[0-9]+\.[0-9]+E\+[0-9]+$'
        OR numero_documento ~* '^[0-9]+\.[0-9]+e\+[0-9]+$'
        OR numero_documento ~* '^[0-9]+\.[0-9]+E-[0-9]+$'
        OR numero_documento ~* '^[0-9]+\.[0-9]+e-[0-9]+$'
    )) as pagos_con_formato_cientifico,
    COUNT(DISTINCT numero_documento) FILTER (WHERE activo = true AND (
        numero_documento ~* '^[0-9]+\.[0-9]+E\+[0-9]+$'
        OR numero_documento ~* '^[0-9]+\.[0-9]+e\+[0-9]+$'
        OR numero_documento ~* '^[0-9]+\.[0-9]+E-[0-9]+$'
        OR numero_documento ~* '^[0-9]+\.[0-9]+e-[0-9]+$'
    )) as documentos_unicos_cientificos,
    SUM(monto_pagado) FILTER (WHERE activo = true AND (
        numero_documento ~* '^[0-9]+\.[0-9]+E\+[0-9]+$'
        OR numero_documento ~* '^[0-9]+\.[0-9]+e\+[0-9]+$'
        OR numero_documento ~* '^[0-9]+\.[0-9]+E-[0-9]+$'
        OR numero_documento ~* '^[0-9]+\.[0-9]+e-[0-9]+$'
    )) as monto_total_afectado
FROM pagos;

-- ----------------------------------------------------------------------------
-- 2. DISTRIBUCIÓN POR TIPO DE FORMATO CIENTÍFICO
-- ----------------------------------------------------------------------------
SELECT 
    'DISTRIBUCION POR TIPO' as tipo_reporte,
    CASE 
        WHEN numero_documento ~* '^[0-9]+\.[0-9]+E\+[0-9]+$' THEN 'E+ (mayúscula)'
        WHEN numero_documento ~* '^[0-9]+\.[0-9]+e\+[0-9]+$' THEN 'e+ (minúscula)'
        WHEN numero_documento ~* '^[0-9]+\.[0-9]+E-[0-9]+$' THEN 'E- (mayúscula negativo)'
        WHEN numero_documento ~* '^[0-9]+\.[0-9]+e-[0-9]+$' THEN 'e- (minúscula negativo)'
        ELSE 'Otro formato'
    END as tipo_formato,
    COUNT(*) as cantidad_pagos,
    COUNT(DISTINCT numero_documento) as documentos_unicos,
    SUM(monto_pagado) as monto_total,
    MIN(monto_pagado) as monto_minimo,
    MAX(monto_pagado) as monto_maximo,
    AVG(monto_pagado) as monto_promedio
FROM pagos
WHERE activo = true
  AND (
    numero_documento ~* '^[0-9]+\.[0-9]+E\+[0-9]+$'
    OR numero_documento ~* '^[0-9]+\.[0-9]+e\+[0-9]+$'
    OR numero_documento ~* '^[0-9]+\.[0-9]+E-[0-9]+$'
    OR numero_documento ~* '^[0-9]+\.[0-9]+e-[0-9]+$'
  )
GROUP BY tipo_formato
ORDER BY cantidad_pagos DESC;

-- ----------------------------------------------------------------------------
-- 3. TOP 20 NÚMEROS DE DOCUMENTO MÁS FRECUENTES (formato científico)
-- ----------------------------------------------------------------------------
SELECT 
    'TOP DOCUMENTOS CIENTIFICOS' as tipo_reporte,
    numero_documento as numero_documento_original,
    COUNT(*) as cantidad_pagos,
    COUNT(DISTINCT cedula) as cedulas_distintas,
    COUNT(DISTINCT prestamo_id) FILTER (WHERE prestamo_id IS NOT NULL) as prestamos_distintos,
    SUM(monto_pagado) as monto_total,
    MIN(fecha_pago) as fecha_pago_mas_antigua,
    MAX(fecha_pago) as fecha_pago_mas_reciente,
    COUNT(*) FILTER (WHERE conciliado = true) as pagos_conciliados,
    COUNT(*) FILTER (WHERE conciliado = false) as pagos_no_conciliados
FROM pagos
WHERE activo = true
  AND (
    numero_documento ~* '^[0-9]+\.[0-9]+E\+[0-9]+$'
    OR numero_documento ~* '^[0-9]+\.[0-9]+e\+[0-9]+$'
    OR numero_documento ~* '^[0-9]+\.[0-9]+E-[0-9]+$'
    OR numero_documento ~* '^[0-9]+\.[0-9]+e-[0-9]+$'
  )
GROUP BY numero_documento
ORDER BY cantidad_pagos DESC
LIMIT 20;

-- ----------------------------------------------------------------------------
-- 4. ANÁLISIS DE DUPLICADOS POTENCIALES DESPUÉS DE NORMALIZACIÓN
-- ----------------------------------------------------------------------------
-- Nota: Esta query simula la normalización para detectar posibles duplicados
-- después de convertir formato científico a número completo
WITH pagos_cientificos AS (
    SELECT 
        id,
        cedula,
        prestamo_id,
        numero_documento as numero_original,
        monto_pagado,
        fecha_pago,
        conciliado,
        -- Simular normalización: convertir científico a int
        CASE 
            WHEN numero_documento ~* '^[0-9]+\.[0-9]+[Ee][+-][0-9]+$' THEN
                CAST(FLOOR(CAST(numero_documento AS FLOAT)) AS TEXT)
            ELSE numero_documento
        END as numero_normalizado
    FROM pagos
    WHERE activo = true
      AND (
        numero_documento ~* '^[0-9]+\.[0-9]+E\+[0-9]+$'
        OR numero_documento ~* '^[0-9]+\.[0-9]+e\+[0-9]+$'
        OR numero_documento ~* '^[0-9]+\.[0-9]+E-[0-9]+$'
        OR numero_documento ~* '^[0-9]+\.[0-9]+e-[0-9]+$'
      )
),
duplicados_potenciales AS (
    SELECT 
        numero_normalizado,
        COUNT(*) as cantidad_pagos_cientificos,
        COUNT(DISTINCT numero_original) as numeros_originales_distintos,
        STRING_AGG(DISTINCT numero_original, ', ' ORDER BY numero_original) as numeros_originales,
        SUM(monto_pagado) as monto_total
    FROM pagos_cientificos
    GROUP BY numero_normalizado
    HAVING COUNT(*) > 1
)
SELECT 
    'DUPLICADOS POTENCIALES' as tipo_reporte,
    numero_normalizado,
    cantidad_pagos_cientificos,
    numeros_originales_distintos,
    numeros_originales,
    monto_total
FROM duplicados_potenciales
ORDER BY cantidad_pagos_cientificos DESC
LIMIT 20;

-- ----------------------------------------------------------------------------
-- 5. ANÁLISIS DE CONFLICTOS CON NÚMEROS YA EXISTENTES (normalizados)
-- ----------------------------------------------------------------------------
-- Detecta si al normalizar un número científico, entraría en conflicto
-- con un número que ya existe en la base de datos
WITH pagos_cientificos AS (
    SELECT 
        id,
        numero_documento as numero_original,
        -- Simular normalización
        CAST(FLOOR(CAST(numero_documento AS FLOAT)) AS TEXT) as numero_normalizado
    FROM pagos
    WHERE activo = true
      AND (
        numero_documento ~* '^[0-9]+\.[0-9]+E\+[0-9]+$'
        OR numero_documento ~* '^[0-9]+\.[0-9]+e\+[0-9]+$'
        OR numero_documento ~* '^[0-9]+\.[0-9]+E-[0-9]+$'
        OR numero_documento ~* '^[0-9]+\.[0-9]+e-[0-9]+$'
      )
),
conflictos AS (
    SELECT 
        pc.numero_original,
        pc.numero_normalizado,
        COUNT(p.id) FILTER (WHERE p.numero_documento = pc.numero_normalizado AND p.numero_documento != pc.numero_original) as pagos_existentes_con_numero_normalizado
    FROM pagos_cientificos pc
    LEFT JOIN pagos p ON p.activo = true AND p.numero_documento = pc.numero_normalizado
    GROUP BY pc.numero_original, pc.numero_normalizado
    HAVING COUNT(p.id) FILTER (WHERE p.numero_documento = pc.numero_normalizado AND p.numero_documento != pc.numero_original) > 0
)
SELECT 
    'CONFLICTOS CON NUMEROS EXISTENTES' as tipo_reporte,
    numero_original,
    numero_normalizado,
    pagos_existentes_con_numero_normalizado
FROM conflictos
ORDER BY pagos_existentes_con_numero_normalizado DESC
LIMIT 20;

-- ----------------------------------------------------------------------------
-- 6. DISTRIBUCIÓN POR ESTADO DE CONCILIACIÓN
-- ----------------------------------------------------------------------------
SELECT 
    'DISTRIBUCION POR CONCILIACION' as tipo_reporte,
    CASE 
        WHEN conciliado = true THEN 'Conciliado'
        WHEN conciliado = false THEN 'No conciliado'
        ELSE 'Sin estado'
    END as estado_conciliacion,
    COUNT(*) as cantidad_pagos,
    SUM(monto_pagado) as monto_total,
    COUNT(DISTINCT cedula) as cedulas_distintas,
    COUNT(DISTINCT prestamo_id) FILTER (WHERE prestamo_id IS NOT NULL) as prestamos_distintos
FROM pagos
WHERE activo = true
  AND (
    numero_documento ~* '^[0-9]+\.[0-9]+E\+[0-9]+$'
    OR numero_documento ~* '^[0-9]+\.[0-9]+e\+[0-9]+$'
    OR numero_documento ~* '^[0-9]+\.[0-9]+E-[0-9]+$'
    OR numero_documento ~* '^[0-9]+\.[0-9]+e-[0-9]+$'
  )
GROUP BY estado_conciliacion
ORDER BY cantidad_pagos DESC;

-- ----------------------------------------------------------------------------
-- 7. DISTRIBUCIÓN TEMPORAL (por año y mes)
-- ----------------------------------------------------------------------------
SELECT 
    'DISTRIBUCION TEMPORAL' as tipo_reporte,
    DATE_TRUNC('month', fecha_pago) as mes,
    COUNT(*) as cantidad_pagos,
    SUM(monto_pagado) as monto_total,
    COUNT(DISTINCT numero_documento) as documentos_unicos
FROM pagos
WHERE activo = true
  AND (
    numero_documento ~* '^[0-9]+\.[0-9]+E\+[0-9]+$'
    OR numero_documento ~* '^[0-9]+\.[0-9]+e\+[0-9]+$'
    OR numero_documento ~* '^[0-9]+\.[0-9]+E-[0-9]+$'
    OR numero_documento ~* '^[0-9]+\.[0-9]+e-[0-9]+$'
  )
  AND fecha_pago IS NOT NULL
GROUP BY DATE_TRUNC('month', fecha_pago)
ORDER BY mes DESC;

-- ----------------------------------------------------------------------------
-- 8. MUESTRA DE REGISTROS AFECTADOS (primeros 50)
-- ----------------------------------------------------------------------------
SELECT 
    'MUESTRA DE REGISTROS' as tipo_reporte,
    id,
    cedula,
    prestamo_id,
    numero_documento as numero_documento_original,
    monto_pagado,
    fecha_pago,
    conciliado,
    fecha_registro,
    -- Simular normalización para mostrar cómo quedaría
    CASE 
        WHEN numero_documento ~* '^[0-9]+\.[0-9]+[Ee][+-][0-9]+$' THEN
            CAST(FLOOR(CAST(numero_documento AS FLOAT)) AS TEXT)
        ELSE numero_documento
    END as numero_documento_normalizado
FROM pagos
WHERE activo = true
  AND (
    numero_documento ~* '^[0-9]+\.[0-9]+E\+[0-9]+$'
    OR numero_documento ~* '^[0-9]+\.[0-9]+e\+[0-9]+$'
    OR numero_documento ~* '^[0-9]+\.[0-9]+E-[0-9]+$'
    OR numero_documento ~* '^[0-9]+\.[0-9]+e-[0-9]+$'
  )
ORDER BY id
LIMIT 50;

-- ----------------------------------------------------------------------------
-- 9. IMPACTO EN PRÉSTAMOS
-- ----------------------------------------------------------------------------
SELECT 
    'IMPACTO EN PRESTAMOS' as tipo_reporte,
    COUNT(DISTINCT prestamo_id) FILTER (WHERE prestamo_id IS NOT NULL) as prestamos_afectados,
    COUNT(*) FILTER (WHERE prestamo_id IS NOT NULL) as pagos_con_prestamo,
    COUNT(*) FILTER (WHERE prestamo_id IS NULL) as pagos_sin_prestamo,
    SUM(monto_pagado) FILTER (WHERE prestamo_id IS NOT NULL) as monto_en_prestamos,
    SUM(monto_pagado) FILTER (WHERE prestamo_id IS NULL) as monto_sin_prestamo
FROM pagos
WHERE activo = true
  AND (
    numero_documento ~* '^[0-9]+\.[0-9]+E\+[0-9]+$'
    OR numero_documento ~* '^[0-9]+\.[0-9]+e\+[0-9]+$'
    OR numero_documento ~* '^[0-9]+\.[0-9]+E-[0-9]+$'
    OR numero_documento ~* '^[0-9]+\.[0-9]+e-[0-9]+$'
  );

-- ----------------------------------------------------------------------------
-- 10. COMPARACIÓN: NÚMEROS CIENTÍFICOS VS NÚMEROS NORMALIZADOS EXISTENTES
-- ----------------------------------------------------------------------------
-- Detecta si hay números normalizados que ya existen en la BD
-- (para identificar posibles duplicados después de la normalización)
WITH numeros_cientificos_normalizados AS (
    SELECT DISTINCT
        CAST(FLOOR(CAST(numero_documento AS FLOAT)) AS TEXT) as numero_normalizado
    FROM pagos
    WHERE activo = true
      AND (
        numero_documento ~* '^[0-9]+\.[0-9]+E\+[0-9]+$'
        OR numero_documento ~* '^[0-9]+\.[0-9]+e\+[0-9]+$'
        OR numero_documento ~* '^[0-9]+\.[0-9]+E-[0-9]+$'
        OR numero_documento ~* '^[0-9]+\.[0-9]+e-[0-9]+$'
      )
)
SELECT 
    'NUMEROS NORMALIZADOS QUE YA EXISTEN' as tipo_reporte,
    ncn.numero_normalizado,
    COUNT(p.id) as pagos_existentes_con_este_numero,
    SUM(p.monto_pagado) as monto_total_existente,
    COUNT(DISTINCT p.cedula) as cedulas_distintas_existentes
FROM numeros_cientificos_normalizados ncn
INNER JOIN pagos p ON p.activo = true 
    AND p.numero_documento = ncn.numero_normalizado
    AND NOT (
        p.numero_documento ~* '^[0-9]+\.[0-9]+E\+[0-9]+$'
        OR p.numero_documento ~* '^[0-9]+\.[0-9]+e\+[0-9]+$'
        OR p.numero_documento ~* '^[0-9]+\.[0-9]+E-[0-9]+$'
        OR p.numero_documento ~* '^[0-9]+\.[0-9]+e-[0-9]+$'
    )
GROUP BY ncn.numero_normalizado
ORDER BY pagos_existentes_con_este_numero DESC
LIMIT 20;
