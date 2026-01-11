-- ============================================================================
-- VERIFICAR COLUMNAS SIMILARES A LAS DE LA IMAGEN
-- ============================================================================
-- Este script muestra todas las columnas en la BD que se relacionan con:
-- - cedula
-- - TOTAL FINANCIAMIENTO
-- - ABONOS
-- ============================================================================

-- ============================================================================
-- 1. COLUMNAS RELACIONADAS CON "cedula"
-- ============================================================================

SELECT 
    '=== COLUMNAS CON "cedula" ===' AS info;

SELECT 
    table_name,
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE column_name ILIKE '%cedula%'
  AND table_schema = 'public'
ORDER BY table_name, column_name;

-- ============================================================================
-- 2. COLUMNAS RELACIONADAS CON "financiamiento" o "total"
-- ============================================================================

SELECT 
    '=== COLUMNAS CON "financiamiento" o "total" ===' AS info;

SELECT 
    table_name,
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE (column_name ILIKE '%financiamiento%' 
    OR column_name ILIKE '%total%')
  AND table_schema = 'public'
ORDER BY table_name, column_name;

-- ============================================================================
-- 3. COLUMNAS RELACIONADAS CON "abono" o "pago"
-- ============================================================================

SELECT 
    '=== COLUMNAS CON "abono" o "pago" ===' AS info;

SELECT 
    table_name,
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE (column_name ILIKE '%abono%' 
    OR column_name ILIKE '%pago%')
  AND table_schema = 'public'
ORDER BY table_name, column_name;

-- ============================================================================
-- 4. ESTRUCTURA COMPLETA DE TABLAS PRINCIPALES
-- ============================================================================

-- Tabla prestamos
SELECT 
    '=== ESTRUCTURA: prestamos ===' AS info;

SELECT 
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = 'prestamos'
  AND table_schema = 'public'
ORDER BY ordinal_position;

-- Tabla cuotas
SELECT 
    '=== ESTRUCTURA: cuotas ===' AS info;

SELECT 
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = 'cuotas'
  AND table_schema = 'public'
ORDER BY ordinal_position;

-- Tabla abono_2026
SELECT 
    '=== ESTRUCTURA: abono_2026 ===' AS info;

SELECT 
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = 'abono_2026'
  AND table_schema = 'public'
ORDER BY ordinal_position;

-- ============================================================================
-- 5. CORRESPONDENCIA DIRECTA: Imagen → BD
-- ============================================================================

SELECT 
    '=== CORRESPONDENCIA IMAGEN → BD ===' AS info;

-- Mostrar ejemplo de datos con todas las columnas relacionadas
SELECT 
    p.cedula AS cedula_imagen,
    p.total_financiamiento AS total_financiamiento_imagen,
    COALESCE(SUM(c.total_pagado), 0) AS abonos_bd,
    a.abonos AS abonos_imagen,
    ABS(COALESCE(SUM(c.total_pagado), 0) - COALESCE(a.abonos::numeric, 0)) AS diferencia
FROM prestamos p
LEFT JOIN cuotas c ON p.id = c.prestamo_id
LEFT JOIN abono_2026 a ON p.cedula = a.cedula
WHERE p.cedula IN ('V14406409', 'V27223265', 'V23681759', 'V23107415')
GROUP BY p.cedula, p.total_financiamiento, a.abonos
ORDER BY p.cedula;
