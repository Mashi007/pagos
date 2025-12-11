-- =====================================================
-- ANÁLISIS COMPLETO DE LA TABLA: clientes
-- Variables (Columnas) y todas las condiciones/restricciones
-- =====================================================
-- Fecha: 2025-01-27
-- Compatible con DBeaver, pgAdmin y otros clientes SQL estándar
-- =====================================================

-- =====================================================
-- 1. ESTRUCTURA DE COLUMNAS (VARIABLES)
-- =====================================================
-- Ejecutar esta consulta para ver todas las columnas con sus características

SELECT 
    c.column_name as columna,
    c.data_type as tipo_dato,
    CASE 
        WHEN c.character_maximum_length IS NOT NULL 
        THEN c.data_type || '(' || c.character_maximum_length || ')'
        WHEN c.numeric_precision IS NOT NULL 
        THEN c.data_type || '(' || c.numeric_precision || ',' || COALESCE(c.numeric_scale, 0) || ')'
        ELSE c.data_type
    END as tipo_completo,
    c.is_nullable as permite_null,
    c.column_default as valor_por_defecto,
    CASE 
        WHEN c.column_default LIKE 'nextval%' THEN 'AUTOINCREMENTO'
        WHEN c.column_default LIKE '%now()%' OR c.column_default LIKE '%CURRENT_TIMESTAMP%' THEN 'FECHA ACTUAL'
        WHEN c.column_default IS NOT NULL THEN 'VALOR FIJO'
        ELSE 'SIN DEFAULT'
    END as tipo_default,
    c.ordinal_position as posicion
FROM information_schema.columns c
WHERE c.table_schema = 'public' 
  AND c.table_name = 'clientes'
ORDER BY c.ordinal_position;

-- =====================================================
-- 2. RESTRICCIONES (CONSTRAINTS) DE LA TABLA
-- =====================================================
-- Ejecutar esta consulta para ver todas las restricciones

SELECT 
    tc.constraint_name as nombre_constraint,
    tc.constraint_type as tipo_constraint,
    kcu.column_name as columna,
    CASE tc.constraint_type
        WHEN 'PRIMARY KEY' THEN 'Clave primaria - Identificador único'
        WHEN 'FOREIGN KEY' THEN 'Clave foránea - Referencia a otra tabla'
        WHEN 'UNIQUE' THEN 'Valor único - No permite duplicados'
        WHEN 'CHECK' THEN 'Validación - Condición que debe cumplirse'
        WHEN 'NOT NULL' THEN 'Obligatorio - No puede ser NULL'
        ELSE 'Otro tipo de restricción'
    END as descripcion
FROM information_schema.table_constraints tc
LEFT JOIN information_schema.key_column_usage kcu 
    ON tc.constraint_name = kcu.constraint_name
    AND tc.table_schema = kcu.table_schema
WHERE tc.table_schema = 'public' 
  AND tc.table_name = 'clientes'
ORDER BY tc.constraint_type, kcu.ordinal_position;

-- =====================================================
-- 3. PRIMARY KEY
-- =====================================================
-- Ejecutar esta consulta para ver la clave primaria

SELECT 
    kcu.column_name as columna_pk,
    kcu.ordinal_position as posicion,
    tc.constraint_name as nombre_constraint
FROM information_schema.table_constraints tc
JOIN information_schema.key_column_usage kcu 
    ON tc.constraint_name = kcu.constraint_name
WHERE tc.table_schema = 'public' 
  AND tc.table_name = 'clientes'
  AND tc.constraint_type = 'PRIMARY KEY'
ORDER BY kcu.ordinal_position;

-- =====================================================
-- 4. FOREIGN KEYS (Claves Foráneas)
-- =====================================================
-- Ejecutar esta consulta para ver las relaciones con otras tablas

-- 4.1. Foreign Keys SALIENTES (clientes referencia a otras tablas)
SELECT 
    tc.constraint_name as nombre_fk,
    kcu.column_name as columna_en_clientes,
    ccu.table_name as tabla_referenciada,
    ccu.column_name as columna_referenciada,
    CASE 
        WHEN rc.update_rule = 'CASCADE' THEN 'CASCADE'
        WHEN rc.update_rule = 'RESTRICT' THEN 'RESTRICT'
        WHEN rc.update_rule = 'SET NULL' THEN 'SET NULL'
        ELSE rc.update_rule
    END as on_update,
    CASE 
        WHEN rc.delete_rule = 'CASCADE' THEN 'CASCADE'
        WHEN rc.delete_rule = 'RESTRICT' THEN 'RESTRICT'
        WHEN rc.delete_rule = 'SET NULL' THEN 'SET NULL'
        ELSE rc.delete_rule
    END as on_delete
FROM information_schema.table_constraints tc
JOIN information_schema.key_column_usage kcu 
    ON tc.constraint_name = kcu.constraint_name
JOIN information_schema.constraint_column_usage ccu 
    ON ccu.constraint_name = tc.constraint_name
LEFT JOIN information_schema.referential_constraints rc 
    ON rc.constraint_name = tc.constraint_name
WHERE tc.table_schema = 'public' 
  AND tc.table_name = 'clientes'
  AND tc.constraint_type = 'FOREIGN KEY'
ORDER BY kcu.ordinal_position;

-- 4.2. Foreign Keys ENTRANTES (otras tablas referencian a clientes)
SELECT 
    tc.table_name as tabla_origen,
    kcu.column_name as columna_fk,
    tc.constraint_name as nombre_fk,
    CASE 
        WHEN rc.update_rule = 'CASCADE' THEN 'CASCADE'
        WHEN rc.update_rule = 'RESTRICT' THEN 'RESTRICT'
        WHEN rc.update_rule = 'SET NULL' THEN 'SET NULL'
        ELSE rc.update_rule
    END as on_update,
    CASE 
        WHEN rc.delete_rule = 'CASCADE' THEN 'CASCADE'
        WHEN rc.delete_rule = 'RESTRICT' THEN 'RESTRICT'
        WHEN rc.delete_rule = 'SET NULL' THEN 'SET NULL'
        ELSE rc.delete_rule
    END as on_delete
FROM information_schema.table_constraints tc
JOIN information_schema.key_column_usage kcu 
    ON tc.constraint_name = kcu.constraint_name
JOIN information_schema.constraint_column_usage ccu 
    ON ccu.constraint_name = tc.constraint_name
LEFT JOIN information_schema.referential_constraints rc 
    ON rc.constraint_name = tc.constraint_name
WHERE ccu.table_schema = 'public' 
  AND ccu.table_name = 'clientes'
  AND tc.constraint_type = 'FOREIGN KEY'
ORDER BY tc.table_name, kcu.ordinal_position;

-- =====================================================
-- 5. ÍNDICES EN LA TABLA
-- =====================================================
-- Ejecutar esta consulta para ver todos los índices

SELECT 
    i.indexname as nombre_indice,
    i.indexdef as definicion,
    CASE 
        WHEN i.indexdef LIKE '%UNIQUE%' THEN 'UNIQUE'
        WHEN i.indexdef LIKE '%PRIMARY%' THEN 'PRIMARY KEY'
        ELSE 'NORMAL'
    END as tipo_indice,
    CASE 
        WHEN i.indexdef LIKE '%WHERE%' THEN 'PARCIAL (con condición)'
        ELSE 'COMPLETO'
    END as alcance
FROM pg_indexes i
WHERE i.schemaname = 'public' 
  AND i.tablename = 'clientes'
ORDER BY 
    CASE 
        WHEN i.indexdef LIKE '%PRIMARY%' THEN 1
        WHEN i.indexdef LIKE '%UNIQUE%' THEN 2
        ELSE 3
    END,
    i.indexname;

-- =====================================================
-- 6. VALORES ÚNICOS Y DISTINTOS EN CAMPOS IMPORTANTES
-- =====================================================
-- Ejecutar estas consultas para ver valores únicos

-- 6.1. Valores únicos en campo 'estado'
SELECT 
    'estado' as campo,
    estado as valor,
    COUNT(*) as cantidad_registros,
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM clientes), 2) as porcentaje
FROM clientes
GROUP BY estado
ORDER BY cantidad_registros DESC;

-- 6.2. Valores únicos en campo 'activo'
SELECT 
    'activo' as campo,
    activo as valor,
    COUNT(*) as cantidad_registros,
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM clientes), 2) as porcentaje
FROM clientes
GROUP BY activo
ORDER BY activo DESC;

-- 6.3. Top 10 ocupaciones más comunes
SELECT 
    'ocupacion' as campo,
    ocupacion as valor,
    COUNT(*) as cantidad_registros
FROM clientes
GROUP BY ocupacion
ORDER BY cantidad_registros DESC
LIMIT 10;

-- 6.4. Estadísticas de cédulas (duplicados permitidos)
SELECT 
    'cedula' as campo,
    COUNT(*) as total_registros,
    COUNT(DISTINCT cedula) as cedulas_unicas,
    COUNT(*) - COUNT(DISTINCT cedula) as cedulas_duplicadas,
    CASE 
        WHEN COUNT(*) > 0 
        THEN ROUND((COUNT(*) - COUNT(DISTINCT cedula)) * 100.0 / COUNT(*), 2)
        ELSE 0
    END as porcentaje_duplicados
FROM clientes;

-- 6.5. Cédulas con más de un registro (duplicados)
SELECT 
    cedula,
    COUNT(*) as cantidad_registros,
    STRING_AGG(id::text, ', ' ORDER BY id) as ids_registros
FROM clientes
GROUP BY cedula
HAVING COUNT(*) > 1
ORDER BY cantidad_registros DESC
LIMIT 20;

-- =====================================================
-- 7. RESTRICCIONES CHECK (Validaciones)
-- =====================================================
-- Ejecutar esta consulta para ver validaciones CHECK

SELECT 
    tc.constraint_name as nombre_check,
    cc.check_clause as condicion,
    kcu.column_name as columna_afectada
FROM information_schema.table_constraints tc
JOIN information_schema.check_constraints cc 
    ON tc.constraint_name = cc.constraint_name
LEFT JOIN information_schema.key_column_usage kcu 
    ON tc.constraint_name = kcu.constraint_name
WHERE tc.table_schema = 'public' 
  AND tc.table_name = 'clientes'
  AND tc.constraint_type = 'CHECK'
ORDER BY tc.constraint_name;

-- =====================================================
-- 8. ESTADÍSTICAS GENERALES DE LA TABLA
-- =====================================================
-- Ejecutar esta consulta para ver estadísticas generales

SELECT 
    'Total de registros' as metrica,
    COUNT(*)::text as valor
FROM clientes

UNION ALL

SELECT 
    'Registros activos (activo = true)' as metrica,
    COUNT(*)::text as valor
FROM clientes
WHERE activo = true

UNION ALL

SELECT 
    'Registros inactivos (activo = false)' as metrica,
    COUNT(*)::text as valor
FROM clientes
WHERE activo = false

UNION ALL

SELECT 
    'Estado ACTIVO' as metrica,
    COUNT(*)::text as valor
FROM clientes
WHERE estado = 'ACTIVO'

UNION ALL

SELECT 
    'Estado INACTIVO' as metrica,
    COUNT(*)::text as valor
FROM clientes
WHERE estado = 'INACTIVO'

UNION ALL

SELECT 
    'Estado FINALIZADO' as metrica,
    COUNT(*)::text as valor
FROM clientes
WHERE estado = 'FINALIZADO'

UNION ALL

SELECT 
    'Registros con email por defecto' as metrica,
    COUNT(*)::text as valor
FROM clientes
WHERE email LIKE '%noemail%' OR email LIKE '%@noemail%'

UNION ALL

SELECT 
    'Registros con teléfono por defecto' as metrica,
    COUNT(*)::text as valor
FROM clientes
WHERE telefono LIKE '%999999999%'

UNION ALL

SELECT 
    'Registros con dirección por defecto' as metrica,
    COUNT(*)::text as valor
FROM clientes
WHERE direccion LIKE '%Actualizar%'

UNION ALL

SELECT 
    'Registros con ocupación por defecto' as metrica,
    COUNT(*)::text as valor
FROM clientes
WHERE ocupacion LIKE '%Actualizar%'

UNION ALL

SELECT 
    'Registros creados en último mes' as metrica,
    COUNT(*)::text as valor
FROM clientes
WHERE fecha_registro >= NOW() - INTERVAL '30 days'

UNION ALL

SELECT 
    'Registros actualizados en último mes' as metrica,
    COUNT(*)::text as valor
FROM clientes
WHERE fecha_actualizacion >= NOW() - INTERVAL '30 days';

-- =====================================================
-- 9. VALORES POR DEFECTO Y NULLS
-- =====================================================
-- Ejecutar esta consulta para ver campos con valores NULL o por defecto

SELECT 
    'Campos con valores NULL' as tipo,
    COUNT(*) as cantidad
FROM clientes
WHERE id IS NULL
   OR cedula IS NULL
   OR nombres IS NULL
   OR telefono IS NULL
   OR email IS NULL
   OR direccion IS NULL
   OR fecha_nacimiento IS NULL
   OR ocupacion IS NULL
   OR estado IS NULL
   OR activo IS NULL
   OR fecha_registro IS NULL
   OR fecha_actualizacion IS NULL
   OR usuario_registro IS NULL
   OR notas IS NULL

UNION ALL

SELECT 
    'Campos con valores por defecto (email)' as tipo,
    COUNT(*) as cantidad
FROM clientes
WHERE email LIKE '%noemail%' OR email LIKE '%@noemail%'

UNION ALL

SELECT 
    'Campos con valores por defecto (teléfono)' as tipo,
    COUNT(*) as cantidad
FROM clientes
WHERE telefono LIKE '%999999999%'

UNION ALL

SELECT 
    'Campos con valores por defecto (dirección)' as tipo,
    COUNT(*) as cantidad
FROM clientes
WHERE direccion LIKE '%Actualizar%'

UNION ALL

SELECT 
    'Campos con valores por defecto (ocupación)' as tipo,
    COUNT(*) as cantidad
FROM clientes
WHERE ocupacion LIKE '%Actualizar%';

-- =====================================================
-- 10. LONGITUDES Y FORMATOS
-- =====================================================
-- Ejecutar esta consulta para ver estadísticas de longitudes

SELECT 
    'cedula' as campo,
    MIN(LENGTH(cedula)) as longitud_minima,
    MAX(LENGTH(cedula)) as longitud_maxima,
    AVG(LENGTH(cedula))::numeric(10,2) as longitud_promedio,
    COUNT(*) as total_registros
FROM clientes

UNION ALL

SELECT 
    'nombres' as campo,
    MIN(LENGTH(nombres)) as longitud_minima,
    MAX(LENGTH(nombres)) as longitud_maxima,
    AVG(LENGTH(nombres))::numeric(10,2) as longitud_promedio,
    COUNT(*) as total_registros
FROM clientes

UNION ALL

SELECT 
    'telefono' as campo,
    MIN(LENGTH(telefono)) as longitud_minima,
    MAX(LENGTH(telefono)) as longitud_maxima,
    AVG(LENGTH(telefono))::numeric(10,2) as longitud_promedio,
    COUNT(*) as total_registros
FROM clientes

UNION ALL

SELECT 
    'email' as campo,
    MIN(LENGTH(email)) as longitud_minima,
    MAX(LENGTH(email)) as longitud_maxima,
    AVG(LENGTH(email))::numeric(10,2) as longitud_promedio,
    COUNT(*) as total_registros
FROM clientes;

-- =====================================================
-- 11. VALIDACIONES DE FORMATO
-- =====================================================
-- Ejecutar estas consultas para verificar formatos

-- 11.1. Emails que no parecen válidos
SELECT 
    'Emails inválidos' as validacion,
    COUNT(*) as cantidad
FROM clientes
WHERE email NOT LIKE '%@%.%'
   OR email LIKE '%noemail%'
   OR email = ''

UNION ALL

-- 11.2. Teléfonos que no parecen válidos
SELECT 
    'Teléfonos inválidos' as validacion,
    COUNT(*) as cantidad
FROM clientes
WHERE telefono LIKE '%999999999%'
   OR LENGTH(telefono) < 10
   OR telefono = ''

UNION ALL

-- 11.3. Fechas de nacimiento futuras o muy antiguas
SELECT 
    'Fechas nacimiento inválidas' as validacion,
    COUNT(*) as cantidad
FROM clientes
WHERE fecha_nacimiento > CURRENT_DATE
   OR fecha_nacimiento < '1900-01-01'
   OR EXTRACT(YEAR FROM fecha_nacimiento) > EXTRACT(YEAR FROM CURRENT_DATE) - 18;

-- =====================================================
-- 12. RESUMEN DE CONDICIONES Y RESTRICCIONES
-- =====================================================
-- Ejecutar esta consulta para ver un resumen completo

SELECT 
    'COLUMNAS' as categoria,
    COUNT(*)::text as cantidad,
    'Total de columnas en la tabla' as descripcion
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'clientes'

UNION ALL

SELECT 
    'PRIMARY KEYS' as categoria,
    COUNT(*)::text as cantidad,
    'Claves primarias (identificadores únicos)' as descripcion
FROM information_schema.table_constraints
WHERE table_schema = 'public' 
  AND table_name = 'clientes'
  AND constraint_type = 'PRIMARY KEY'

UNION ALL

SELECT 
    'FOREIGN KEYS SALIENTES' as categoria,
    COUNT(*)::text as cantidad,
    'Relaciones que clientes tiene con otras tablas' as descripcion
FROM information_schema.table_constraints
WHERE table_schema = 'public' 
  AND table_name = 'clientes'
  AND constraint_type = 'FOREIGN KEY'

UNION ALL

SELECT 
    'FOREIGN KEYS ENTRANTES' as categoria,
    COUNT(*)::text as cantidad,
    'Otras tablas que referencian a clientes' as descripcion
FROM information_schema.table_constraints tc
JOIN information_schema.constraint_column_usage ccu 
    ON ccu.constraint_name = tc.constraint_name
WHERE ccu.table_schema = 'public' 
  AND ccu.table_name = 'clientes'
  AND tc.constraint_type = 'FOREIGN KEY'

UNION ALL

SELECT 
    'ÍNDICES' as categoria,
    COUNT(*)::text as cantidad,
    'Índices para optimización de consultas' as descripcion
FROM pg_indexes
WHERE schemaname = 'public' AND tablename = 'clientes'

UNION ALL

SELECT 
    'CHECK CONSTRAINTS' as categoria,
    COUNT(*)::text as cantidad,
    'Validaciones de datos (CHECK)' as descripcion
FROM information_schema.table_constraints
WHERE table_schema = 'public' 
  AND table_name = 'clientes'
  AND constraint_type = 'CHECK'

UNION ALL

SELECT 
    'COLUMNAS NOT NULL' as categoria,
    COUNT(*)::text as cantidad,
    'Columnas que no permiten valores NULL' as descripcion
FROM information_schema.columns
WHERE table_schema = 'public' 
  AND table_name = 'clientes'
  AND is_nullable = 'NO';

-- =====================================================
-- FIN DEL SCRIPT
-- =====================================================
-- Revisa los resultados de cada sección arriba
-- Cada consulta muestra un aspecto diferente de la tabla clientes

