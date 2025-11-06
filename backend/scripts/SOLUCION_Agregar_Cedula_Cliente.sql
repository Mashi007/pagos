-- ============================================
-- SOLUCIÓN: AGREGAR COLUMNA cedula_cliente
-- ============================================
-- ⚠️ EJECUTAR SOLO SI LA COLUMNA NO EXISTE
-- Primero ejecutar: Verificar_Estructura_Tabla_Pagos.sql
-- para confirmar que la columna falta

-- ============================================
-- PASO 1: VERIFICAR QUE LA COLUMNA NO EXISTE
-- ============================================
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 
        FROM information_schema.columns
        WHERE table_schema = 'public'
            AND table_name = 'pagos'
            AND column_name = 'cedula_cliente'
    ) THEN
        RAISE NOTICE '⚠️ La columna cedula_cliente YA EXISTE. No es necesario ejecutar este script.';
    ELSE
        RAISE NOTICE '✅ La columna cedula_cliente NO existe. Procediendo a crearla...';
    END IF;
END $$;

-- ============================================
-- PASO 2: AGREGAR LA COLUMNA cedula_cliente
-- ============================================
-- Solo se ejecutará si no existe
ALTER TABLE pagos 
ADD COLUMN IF NOT EXISTS cedula_cliente VARCHAR(20);

-- ============================================
-- PASO 3: AGREGAR ÍNDICE PARA MEJOR RENDIMIENTO
-- ============================================
CREATE INDEX IF NOT EXISTS idx_pagos_cedula_cliente 
ON pagos(cedula_cliente);

-- ============================================
-- PASO 4: VERIFICAR QUE SE CREÓ CORRECTAMENTE
-- ============================================
SELECT 
    'Verificación post-creación' AS paso,
    column_name,
    data_type,
    character_maximum_length,
    is_nullable
FROM information_schema.columns
WHERE table_schema = 'public'
    AND table_name = 'pagos'
    AND column_name = 'cedula_cliente';

-- ============================================
-- PASO 5: SI HAY DATOS EXISTENTES, MIGRAR VALORES
-- ============================================
-- Si hay una columna alternativa con la cédula, migrar los datos
-- Por ejemplo, si existe 'id_cliente' o similar:

-- OPCIÓN A: Si existe relación con tabla clientes
/*
UPDATE pagos p
SET cedula_cliente = c.cedula
FROM clientes c
WHERE p.cliente_id = c.id
  AND p.cedula_cliente IS NULL;
*/

-- OPCIÓN B: Si hay otra columna en pagos que tenga la cédula
-- (Ajustar según la estructura real de tu BD)
/*
UPDATE pagos
SET cedula_cliente = otra_columna_con_cedula
WHERE cedula_cliente IS NULL
  AND otra_columna_con_cedula IS NOT NULL;
*/

-- ============================================
-- PASO 6: HACER LA COLUMNA NOT NULL (OPCIONAL)
-- ============================================
-- ⚠️ SOLO ejecutar si todos los registros tienen cedula_cliente
-- Primero verificar:
SELECT 
    COUNT(*) AS total_pagos,
    COUNT(cedula_cliente) AS pagos_con_cedula,
    COUNT(*) - COUNT(cedula_cliente) AS pagos_sin_cedula
FROM pagos;

-- Si pagos_sin_cedula = 0, entonces puedes hacer:
-- ALTER TABLE pagos ALTER COLUMN cedula_cliente SET NOT NULL;

-- ============================================
-- PASO 7: VERIFICACIÓN FINAL
-- ============================================
SELECT 
    '=== VERIFICACIÓN FINAL ===' AS resumen,
    CASE 
        WHEN EXISTS (
            SELECT 1 
            FROM information_schema.columns
            WHERE table_schema = 'public'
                AND table_name = 'pagos'
                AND column_name = 'cedula_cliente'
        ) THEN '✅ La columna cedula_cliente fue creada exitosamente'
        ELSE '❌ ERROR: La columna no se creó'
    END AS estado,
    (SELECT COUNT(*) FROM pagos WHERE cedula_cliente IS NOT NULL) AS registros_con_cedula,
    (SELECT COUNT(*) FROM pagos WHERE cedula_cliente IS NULL) AS registros_sin_cedula;

