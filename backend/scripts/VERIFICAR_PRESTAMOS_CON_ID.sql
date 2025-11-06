-- ============================================================================
-- ✅ VERIFICAR QUE TODOS LOS PRÉSTAMOS TIENEN ID
-- ============================================================================
-- Script para DBeaver: Confirma que todos los préstamos tienen ID asignado
-- ============================================================================

-- ============================================================================
-- 1. VERIFICAR PRÉSTAMOS SIN ID (debería ser 0)
-- ============================================================================
SELECT 
    COUNT(*) as prestamos_sin_id
FROM prestamos
WHERE id IS NULL;

-- ============================================================================
-- 2. TOTAL DE PRÉSTAMOS Y RANGO DE IDs
-- ============================================================================
SELECT 
    COUNT(*) as total_prestamos,
    MIN(id) as id_minimo,
    MAX(id) as id_maximo,
    COUNT(DISTINCT id) as ids_unicos,
    CASE 
        WHEN COUNT(*) = COUNT(DISTINCT id) THEN '✅ Todos los IDs son únicos'
        ELSE '⚠️ Hay IDs duplicados'
    END as validacion_unicidad
FROM prestamos;

-- ============================================================================
-- 3. VERIFICAR SI HAY GAPS EN LA SECUENCIA DE IDs
-- ============================================================================
-- Nota: Es normal tener gaps si se eliminaron préstamos
SELECT 
    'Gaps en secuencia de IDs' as tipo_verificacion,
    COUNT(*) as cantidad_gaps
FROM (
    SELECT 
        id,
        LAG(id) OVER (ORDER BY id) as id_anterior,
        id - LAG(id) OVER (ORDER BY id) as diferencia
    FROM prestamos
    ORDER BY id
) subquery
WHERE diferencia > 1;

-- ============================================================================
-- 4. DISTRIBUCIÓN DE PRÉSTAMOS POR ESTADO (con IDs)
-- ============================================================================
SELECT 
    estado,
    COUNT(*) as cantidad,
    MIN(id) as id_minimo,
    MAX(id) as id_maximo
FROM prestamos
GROUP BY estado
ORDER BY estado;

-- ============================================================================
-- 5. PRIMEROS Y ÚLTIMOS PRÉSTAMOS (para verificar secuencia)
-- ============================================================================
SELECT 
    'Primeros 5 préstamos' as tipo,
    id,
    cedula,
    estado,
    fecha_registro,
    fecha_aprobacion
FROM prestamos
ORDER BY id ASC
LIMIT 5

UNION ALL

SELECT 
    'Últimos 5 préstamos' as tipo,
    id,
    cedula,
    estado,
    fecha_registro,
    fecha_aprobacion
FROM prestamos
ORDER BY id DESC
LIMIT 5;

-- ============================================================================
-- 6. RESUMEN FINAL
-- ============================================================================
SELECT 
    'RESUMEN' as verificacion,
    COUNT(*) as total_prestamos,
    COUNT(CASE WHEN id IS NULL THEN 1 END) as prestamos_sin_id,
    COUNT(CASE WHEN id IS NOT NULL THEN 1 END) as prestamos_con_id,
    CASE 
        WHEN COUNT(CASE WHEN id IS NULL THEN 1 END) = 0 THEN '✅ Todos los préstamos tienen ID'
        ELSE '⚠️ Hay préstamos sin ID'
    END as resultado
FROM prestamos;

