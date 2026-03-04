-- Script 023: Verificar constraint UNIQUE en numero_documento
-- Propósito: Confirmar que la BD tiene la restricción para rechazar duplicados

-- 1. Verificar si existe el constraint UNIQUE
SELECT
    constraint_name,
    constraint_type,
    table_name,
    column_name
FROM information_schema.constraint_column_usage
WHERE table_name = 'pagos' AND column_name = 'numero_documento'
UNION ALL
SELECT
    conname as constraint_name,
    'UNIQUE' as constraint_type,
    'pagos' as table_name,
    'numero_documento' as column_name
FROM pg_constraint
WHERE conname LIKE '%numero_documento%' OR (conrelid IN (
    SELECT oid FROM pg_class WHERE relname = 'pagos'
) AND contype = 'u');

-- 2. Listar todos los constraints en tabla pagos
SELECT
    constraint_name,
    constraint_type,
    table_name
FROM information_schema.table_constraints
WHERE table_name = 'pagos'
ORDER BY constraint_type, constraint_name;

-- 3. Contar documentos únicos vs total
SELECT
    COUNT(*) as total_pagos,
    COUNT(DISTINCT numero_documento) as documentos_unicos,
    COUNT(*) - COUNT(DISTINCT numero_documento) as duplicados_existentes
FROM public.pagos
WHERE numero_documento IS NOT NULL;

-- 4. Si hay duplicados, mostrarlos
SELECT
    numero_documento,
    COUNT(*) as cantidad,
    STRING_AGG(id::text, ', ') as ids
FROM public.pagos
WHERE numero_documento IS NOT NULL
GROUP BY numero_documento
HAVING COUNT(*) > 1
ORDER BY cantidad DESC;

-- 5. Probar inserción de documento duplicado (esto debería fallar)
-- COMENTADO PARA SEGURIDAD - descomenta para probar
/*
BEGIN;
INSERT INTO public.pagos (
    cedula, 
    fecha_pago, 
    monto_pagado, 
    numero_documento, 
    estado,
    referencia_pago
) VALUES (
    'V99999999',
    NOW(),
    100.00,
    'TEST_DUPLICADO_VERIFICACION_001',
    'PENDIENTE',
    'TEST'
);

-- Intentar insertar el mismo documento
INSERT INTO public.pagos (
    cedula, 
    fecha_pago, 
    monto_pagado, 
    numero_documento, 
    estado,
    referencia_pago
) VALUES (
    'V88888888',
    NOW(),
    200.00,
    'TEST_DUPLICADO_VERIFICACION_001',  -- DUPLICADO
    'PENDIENTE',
    'TEST'
);
-- Debería fallar con: ERROR: duplicate key value violates unique constraint
ROLLBACK;
*/

-- 6. Ver definición completa del constraint
SELECT
    pg_get_constraintdef(oid)
FROM pg_constraint
WHERE conrelid IN (SELECT oid FROM pg_class WHERE relname = 'pagos')
  AND conname LIKE '%numero%';
