-- ============================================
-- CREAR COLUMNA cedula_cliente EN TABLA pagos
-- ============================================
-- Este script crea la columna cedula_cliente que falta
-- y migra los datos desde la columna 'cedula' existente

-- ============================================
-- PASO 1: Verificar que la columna NO existe
-- ============================================
SELECT 
    'PASO 1: Verificación pre-creación' AS paso,
    CASE 
        WHEN EXISTS (
            SELECT 1 
            FROM information_schema.columns
            WHERE table_schema = 'public'
                AND table_name = 'pagos'
                AND column_name = 'cedula_cliente'
        ) THEN '⚠️ La columna cedula_cliente YA EXISTE - No es necesario ejecutar este script'
        ELSE '✅ La columna cedula_cliente NO existe - Procediendo a crearla'
    END AS estado;

-- ============================================
-- PASO 2: Crear la columna cedula_cliente
-- ============================================
-- Solo se ejecutará si no existe
ALTER TABLE pagos 
ADD COLUMN IF NOT EXISTS cedula_cliente VARCHAR(20);

-- ============================================
-- PASO 3: Migrar datos desde columna 'cedula' a 'cedula_cliente'
-- ============================================
-- Si existe la columna 'cedula', copiar sus valores a 'cedula_cliente'
UPDATE pagos
SET cedula_cliente = cedula
WHERE cedula_cliente IS NULL
  AND cedula IS NOT NULL;

-- ============================================
-- PASO 4: Crear índice en cedula_cliente
-- ============================================
-- El índice ix_pagos_cedula_cliente debería existir si la columna existía antes
-- Si no existe, crearlo
CREATE INDEX IF NOT EXISTS ix_pagos_cedula_cliente 
ON pagos(cedula_cliente);

-- ============================================
-- PASO 5: Verificar que se creó correctamente
-- ============================================
SELECT 
    'PASO 5: Verificación post-creación' AS paso,
    column_name,
    data_type,
    character_maximum_length,
    is_nullable
FROM information_schema.columns
WHERE table_schema = 'public'
    AND table_name = 'pagos'
    AND column_name = 'cedula_cliente';

-- ============================================
-- PASO 6: Estadísticas de migración
-- ============================================
SELECT 
    'PASO 6: Estadísticas de migración' AS paso,
    COUNT(*) AS total_registros,
    COUNT(cedula_cliente) AS registros_con_cedula_cliente,
    COUNT(cedula) AS registros_con_cedula,
    COUNT(CASE WHEN cedula_cliente IS NULL AND cedula IS NOT NULL THEN 1 END) AS pendientes_de_migrar
FROM pagos;

-- ============================================
-- PASO 7: Verificar índices
-- ============================================
SELECT 
    'PASO 7: Verificación de índices' AS paso,
    indexname,
    indexdef
FROM pg_indexes
WHERE schemaname = 'public'
    AND tablename = 'pagos'
    AND indexname LIKE '%cedula%'
ORDER BY indexname;

-- ============================================
-- RESUMEN FINAL
-- ============================================
SELECT 
    '=== RESUMEN FINAL ===' AS resumen,
    CASE 
        WHEN EXISTS (
            SELECT 1 
            FROM information_schema.columns
            WHERE table_schema = 'public'
                AND table_name = 'pagos'
                AND column_name = 'cedula_cliente'
        ) THEN '✅ La columna cedula_cliente fue creada exitosamente'
        ELSE '❌ ERROR: La columna no se creó'
    END AS resultado,
    (SELECT COUNT(*) FROM pagos WHERE cedula_cliente IS NOT NULL) AS registros_con_datos,
    (SELECT COUNT(*) FROM pagos WHERE cedula_cliente IS NULL) AS registros_sin_datos;

