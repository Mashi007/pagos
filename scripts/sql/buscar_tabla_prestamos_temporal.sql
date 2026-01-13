-- ============================================
-- BUSCAR TABLA prestamos_temporal EN TODOS LOS ESQUEMAS
-- ============================================

-- Buscar en todos los esquemas
SELECT 
    table_schema,
    table_name,
    '✅ Encontrada' as estado
FROM information_schema.tables 
WHERE table_name = 'prestamos_temporal'
ORDER BY table_schema;

-- Verificar específicamente en esquema public
SELECT 
    CASE 
        WHEN EXISTS (
            SELECT 1 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            AND table_name = 'prestamos_temporal'
        ) THEN '✅ La tabla EXISTE en esquema PUBLIC'
        ELSE '❌ La tabla NO EXISTE en esquema PUBLIC'
    END as estado_public;

-- Verificar en esquema actual
SELECT 
    current_schema() as esquema_actual,
    CASE 
        WHEN EXISTS (
            SELECT 1 
            FROM information_schema.tables 
            WHERE table_schema = current_schema()
            AND table_name = 'prestamos_temporal'
        ) THEN '✅ La tabla EXISTE en esquema actual'
        ELSE '❌ La tabla NO EXISTE en esquema actual'
    END as estado_esquema_actual;

-- Listar todas las tablas que contienen "prestamos" en el nombre
SELECT 
    table_schema,
    table_name,
    'Tabla relacionada' as tipo
FROM information_schema.tables 
WHERE table_name LIKE '%prestamos%'
  AND table_schema NOT IN ('information_schema', 'pg_catalog')
ORDER BY table_schema, table_name;

-- Verificar permisos de acceso
SELECT 
    has_table_privilege('prestamos_temporal', 'SELECT') as puede_seleccionar,
    has_table_privilege('prestamos_temporal', 'INSERT') as puede_insertar,
    has_table_privilege('prestamos_temporal', 'UPDATE') as puede_actualizar,
    has_table_privilege('prestamos_temporal', 'DELETE') as puede_eliminar;
