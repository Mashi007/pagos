-- =====================================================
-- SCRIPT PARA COMPARAR BASE ACTUAL CON NUEVA
-- Ejecutar después de importar para verificar diferencias
-- =====================================================

-- =====================================================
-- 1. COMPARAR TOTALES
-- =====================================================

SELECT 
    'Base actual (backup)' as origen,
    COUNT(*) as total_clientes,
    COUNT(DISTINCT cedula) as cedulas_unicas
FROM clientes_backup_antes_importacion

UNION ALL

SELECT 
    'Base nueva (importada)' as origen,
    COUNT(*) as total_clientes,
    COUNT(DISTINCT cedula) as cedulas_unicas
FROM clientes;

-- =====================================================
-- 2. COMPARAR POR ESTADO
-- =====================================================

SELECT 
    'Base actual' as origen,
    estado,
    COUNT(*) as cantidad
FROM clientes_backup_antes_importacion
GROUP BY estado

UNION ALL

SELECT 
    'Base nueva' as origen,
    estado,
    COUNT(*) as cantidad
FROM clientes
GROUP BY estado
ORDER BY origen, estado;

-- =====================================================
-- 3. CLIENTES QUE ESTABAN Y YA NO ESTÁN
-- =====================================================

SELECT 
    'Clientes eliminados' as tipo,
    COUNT(*) as cantidad
FROM clientes_backup_antes_importacion c_antes
LEFT JOIN clientes c_nueva ON c_antes.cedula = c_nueva.cedula
WHERE c_nueva.id IS NULL;

-- Ver ejemplos de clientes eliminados
SELECT 
    c_antes.id,
    c_antes.cedula,
    c_antes.nombres,
    c_antes.estado,
    'Eliminado' as cambio
FROM clientes_backup_antes_importacion c_antes
LEFT JOIN clientes c_nueva ON c_antes.cedula = c_nueva.cedula
WHERE c_nueva.id IS NULL
ORDER BY c_antes.id
LIMIT 20;

-- =====================================================
-- 4. CLIENTES NUEVOS (que no estaban antes)
-- =====================================================

SELECT 
    'Clientes nuevos' as tipo,
    COUNT(*) as cantidad
FROM clientes c_nueva
LEFT JOIN clientes_backup_antes_importacion c_antes ON c_nueva.cedula = c_antes.cedula
WHERE c_antes.id IS NULL;

-- Ver ejemplos de clientes nuevos
SELECT 
    c_nueva.id,
    c_nueva.cedula,
    c_nueva.nombres,
    c_nueva.estado,
    'Nuevo' as cambio
FROM clientes c_nueva
LEFT JOIN clientes_backup_antes_importacion c_antes ON c_nueva.cedula = c_antes.cedula
WHERE c_antes.id IS NULL
ORDER BY c_nueva.id
LIMIT 20;

-- =====================================================
-- 5. CLIENTES QUE CAMBIARON
-- =====================================================

-- Clientes que existen en ambas pero con datos diferentes
SELECT 
    'Clientes modificados' as tipo,
    COUNT(*) as cantidad
FROM clientes c_nueva
INNER JOIN clientes_backup_antes_importacion c_antes ON c_nueva.cedula = c_antes.cedula
WHERE c_nueva.nombres != c_antes.nombres
   OR c_nueva.email != c_antes.email
   OR c_nueva.telefono != c_antes.telefono
   OR c_nueva.estado != c_antes.estado;

-- Ver ejemplos de cambios
SELECT 
    c_nueva.cedula,
    c_nueva.nombres as nombres_nuevo,
    c_antes.nombres as nombres_antes,
    c_nueva.email as email_nuevo,
    c_antes.email as email_antes,
    c_nueva.estado as estado_nuevo,
    c_antes.estado as estado_antes
FROM clientes c_nueva
INNER JOIN clientes_backup_antes_importacion c_antes ON c_nueva.cedula = c_antes.cedula
WHERE c_nueva.nombres != c_antes.nombres
   OR c_nueva.email != c_antes.email
   OR c_nueva.estado != c_antes.estado
LIMIT 20;

-- =====================================================
-- 6. RESUMEN DE CAMBIOS
-- =====================================================

SELECT 
    'Total en base anterior' as metrica,
    COUNT(*)::text as valor
FROM clientes_backup_antes_importacion

UNION ALL

SELECT 
    'Total en base nueva' as metrica,
    COUNT(*)::text as valor
FROM clientes

UNION ALL

SELECT 
    'Clientes eliminados' as metrica,
    COUNT(*)::text as valor
FROM clientes_backup_antes_importacion c_antes
LEFT JOIN clientes c_nueva ON c_antes.cedula = c_nueva.cedula
WHERE c_nueva.id IS NULL

UNION ALL

SELECT 
    'Clientes nuevos' as metrica,
    COUNT(*)::text as valor
FROM clientes c_nueva
LEFT JOIN clientes_backup_antes_importacion c_antes ON c_nueva.cedula = c_antes.cedula
WHERE c_antes.id IS NULL

UNION ALL

SELECT 
    'Clientes que se mantienen' as metrica,
    COUNT(*)::text as valor
FROM clientes c_nueva
INNER JOIN clientes_backup_antes_importacion c_antes ON c_nueva.cedula = c_antes.cedula;

-- =====================================================
-- FIN DEL SCRIPT
-- =====================================================

