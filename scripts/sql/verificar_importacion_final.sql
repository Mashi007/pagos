-- =====================================================
-- VERIFICAR IMPORTACIÓN FINAL
-- Ejecutar después de importar CSV
-- =====================================================

-- Total de registros importados
SELECT 
    'Total de registros en clientes_temp' as verificacion,
    COUNT(*) as cantidad
FROM clientes_temp;

-- Verificar que hay datos
SELECT 
    CASE 
        WHEN COUNT(*) > 0 THEN '✅ Importación exitosa'
        ELSE '❌ No hay datos importados'
    END as estado,
    COUNT(*) as cantidad
FROM clientes_temp;

-- Muestra de los primeros 5 registros
SELECT 
    id,
    cedula,
    nombres,
    telefono,
    email,
    estado
FROM clientes_temp
LIMIT 5;

