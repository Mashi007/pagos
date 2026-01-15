-- ============================================================================
-- SCRIPT PARA VERIFICAR ÍNDICES CRÍTICOS EN BASE DE DATOS
-- ============================================================================
-- Fecha: 2026-01-15
-- Propósito: Verificar existencia de índices críticos identificados en auditoría
-- ============================================================================

-- ============================================================================
-- VERIFICAR ÍNDICES CRÍTICOS POR TABLA
-- ============================================================================

-- 1. ÍNDICES EN TABLA clientes
SELECT 
    schemaname,
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE tablename = 'clientes'
  AND (
    indexname LIKE '%cedula%' 
    OR indexname LIKE '%idx_clientes_cedula%'
    OR indexdef LIKE '%cedula%'
  )
ORDER BY indexname;

-- 2. ÍNDICES EN TABLA prestamos
SELECT 
    schemaname,
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE tablename = 'prestamos'
  AND (
    indexname LIKE '%cliente_id%' 
    OR indexname LIKE '%idx_prestamos_cliente_id%'
    OR indexdef LIKE '%cliente_id%'
  )
ORDER BY indexname;

-- 3. ÍNDICES EN TABLA cuotas
SELECT 
    schemaname,
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE tablename = 'cuotas'
  AND (
    indexname LIKE '%prestamo_id%' 
    OR indexname LIKE '%idx_cuotas_prestamo_id%'
    OR indexdef LIKE '%prestamo_id%'
  )
ORDER BY indexname;

-- 4. ÍNDICES EN TABLA pagos
SELECT 
    schemaname,
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE tablename = 'pagos'
  AND (
    indexname LIKE '%prestamo_id%' 
    OR indexname LIKE '%idx_pagos_prestamo_id%'
    OR indexdef LIKE '%prestamo_id%'
  )
ORDER BY indexname;

-- ============================================================================
-- RESUMEN: VERIFICAR TODOS LOS ÍNDICES CRÍTICOS ESPERADOS
-- ============================================================================

SELECT 
    'INDICES_CRITICOS' as categoria,
    tablename,
    indexname,
    CASE 
        WHEN indexname LIKE '%cedula%' AND tablename = 'clientes' THEN 'OK'
        WHEN indexname LIKE '%cliente_id%' AND tablename = 'prestamos' THEN 'OK'
        WHEN indexname LIKE '%prestamo_id%' AND tablename = 'cuotas' THEN 'OK'
        WHEN indexname LIKE '%prestamo_id%' AND tablename = 'pagos' THEN 'OK'
        ELSE 'REVISAR'
    END as estado
FROM pg_indexes
WHERE tablename IN ('clientes', 'prestamos', 'cuotas', 'pagos')
  AND (
    (tablename = 'clientes' AND (indexname LIKE '%cedula%' OR indexdef LIKE '%cedula%'))
    OR (tablename = 'prestamos' AND (indexname LIKE '%cliente_id%' OR indexdef LIKE '%cliente_id%'))
    OR (tablename = 'cuotas' AND (indexname LIKE '%prestamo_id%' OR indexdef LIKE '%prestamo_id%'))
    OR (tablename = 'pagos' AND (indexname LIKE '%prestamo_id%' OR indexdef LIKE '%prestamo_id%'))
  )
ORDER BY tablename, indexname;

-- ============================================================================
-- VERIFICAR ÍNDICES FUNCIONALES PARA GROUP BY (Optimización Chat AI)
-- ============================================================================

SELECT 
    'INDICES_FUNCIONALES' as categoria,
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE indexname IN (
    'idx_cuotas_extract_year_month_vencimiento',
    'idx_prestamos_extract_year_month_registro',
    'idx_pagos_extract_year_month',
    'idx_cuotas_prestamo_estado_fecha_vencimiento',
    'idx_prestamos_estado_analista_cedula',
    'idx_pagos_fecha_activo_prestamo',
    'idx_prestamos_analista_trgm'
)
ORDER BY tablename, indexname;

-- ============================================================================
-- VERIFICAR ÍNDICES COMPUESTOS CRÍTICOS
-- ============================================================================

SELECT 
    'INDICES_COMPUESTOS' as categoria,
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE tablename IN ('cuotas', 'prestamos', 'pagos')
  AND indexdef LIKE '%,%'  -- Índices con múltiples columnas
ORDER BY tablename, indexname;

-- ============================================================================
-- REPORTE FINAL: ESTADO DE ÍNDICES CRÍTICOS
-- ============================================================================

WITH indices_esperados AS (
    SELECT 'clientes' as tabla, 'idx_clientes_cedula' as indice_esperado, 'cedula' as columna
    UNION ALL SELECT 'prestamos', 'idx_prestamos_cliente_id', 'cliente_id'
    UNION ALL SELECT 'cuotas', 'idx_cuotas_prestamo_id', 'prestamo_id'
    UNION ALL SELECT 'pagos', 'idx_pagos_prestamo_id', 'prestamo_id'
),
indices_existentes AS (
    SELECT tablename, indexname, indexdef
    FROM pg_indexes
    WHERE tablename IN ('clientes', 'prestamos', 'cuotas', 'pagos')
)
SELECT 
    ie.tabla,
    ie.indice_esperado,
    ie.columna,
    CASE 
        WHEN EXISTS (
            SELECT 1 FROM indices_existentes ie2 
            WHERE ie2.tablename = ie.tabla 
            AND (ie2.indexname = ie.indice_esperado OR ie2.indexdef LIKE '%' || ie.columna || '%')
        ) THEN 'EXISTE'
        ELSE 'FALTA'
    END as estado
FROM indices_esperados ie
ORDER BY 
    CASE WHEN estado = 'FALTA' THEN 0 ELSE 1 END,
    ie.tabla;
