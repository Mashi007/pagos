-- ============================================
-- VERIFICACIÓN DE RESTRICCIONES EN TABLA CLIENTES
-- ============================================

-- 1. Ver todas las restricciones de la tabla clientes
SELECT 
    tc.constraint_name,
    tc.constraint_type,
    kcu.column_name,
    tc.table_name
FROM information_schema.table_constraints tc
JOIN information_schema.key_column_usage kcu 
    ON tc.constraint_name = kcu.constraint_name
WHERE tc.table_name = 'clientes'
ORDER BY tc.constraint_type, tc.constraint_name;

-- 2. Ver índices en la tabla clientes
SELECT 
    indexname,
    indexdef,
    tablename
FROM pg_indexes 
WHERE tablename = 'clientes'
ORDER BY indexname;

-- 3. Verificar específicamente restricciones UNIQUE en cedula
SELECT 
    conname as constraint_name,
    contype as constraint_type,
    pg_get_constraintdef(oid) as constraint_definition
FROM pg_constraint 
WHERE conrelid = 'clientes'::regclass
    AND contype = 'u'
    AND pg_get_constraintdef(oid) LIKE '%cedula%';

-- 4. Verificar si existe el índice ix_clientes_cedula
SELECT 
    schemaname,
    tablename,
    indexname,
    indexdef
FROM pg_indexes 
WHERE tablename = 'clientes' 
    AND indexname LIKE '%cedula%';

-- 5. Contar registros con cédulas duplicadas (debería mostrar duplicados si la corrección funcionó)
SELECT 
    cedula,
    COUNT(*) as cantidad_clientes
FROM clientes 
GROUP BY cedula 
HAVING COUNT(*) > 1
ORDER BY cantidad_clientes DESC
LIMIT 10;
