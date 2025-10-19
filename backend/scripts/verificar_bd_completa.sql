-- ==================================================
-- SCRIPT SQL PARA DBEAVER - VERIFICACIÓN COMPLETA
-- ==================================================

-- 1. VERIFICAR ESTRUCTURA DE TABLA CLIENTES
SELECT 
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns 
WHERE table_name = 'clientes' 
ORDER BY ordinal_position;

-- 2. VERIFICAR TABLAS DE CONFIGURACIÓN
SELECT 'modelos_vehiculos' as tabla, count(*) as registros FROM modelos_vehiculos
UNION ALL
SELECT 'concesionarios' as tabla, count(*) as registros FROM concesionarios  
UNION ALL
SELECT 'analistas' as tabla, count(*) as registros FROM analistas;

-- 3. VERIFICAR VALIDADORES DISPONIBLES
SELECT 
    nombre,
    tipo,
    activo,
    configuracion
FROM validadores 
WHERE activo = true
ORDER BY tipo, nombre;

-- 4. VERIFICAR FOREIGN KEYS EN CLIENTES
SELECT 
    tc.constraint_name,
    tc.table_name,
    kcu.column_name,
    ccu.table_name AS foreign_table_name,
    ccu.column_name AS foreign_column_name
FROM information_schema.table_constraints AS tc 
JOIN information_schema.key_column_usage AS kcu
    ON tc.constraint_name = kcu.constraint_name
    AND tc.table_schema = kcu.table_schema
JOIN information_schema.constraint_column_usage AS ccu
    ON ccu.constraint_name = tc.constraint_name
    AND ccu.table_schema = tc.table_schema
WHERE tc.constraint_type = 'FOREIGN KEY' 
    AND tc.table_name = 'clientes';

-- 5. VERIFICAR ÍNDICES EN CLIENTES
SELECT 
    indexname,
    indexdef
FROM pg_indexes 
WHERE tablename = 'clientes';

-- 6. VERIFICAR DATOS DE PRUEBA (si existen)
SELECT 
    id,
    cedula,
    nombres,
    apellidos,
    telefono,
    email,
    modelo_vehiculo,
    concesionario,
    estado,
    fecha_registro
FROM clientes 
ORDER BY id DESC 
LIMIT 5;
