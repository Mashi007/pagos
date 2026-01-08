-- =====================================================
-- SCRIPT DE DIAGNÓSTICO: Importación de Clientes
-- Ejecutar para identificar problemas
-- =====================================================

-- =====================================================
-- 1. VERIFICAR SI HAY DATOS EN TEMPORAL
-- =====================================================

SELECT 
    'Total en clientes_temp' as verificacion,
    COUNT(*) as cantidad
FROM clientes_temp;

-- =====================================================
-- 2. VER EJEMPLO DE DATOS EN TEMPORAL
-- =====================================================

SELECT 
    id,
    cedula,
    nombres,
    email,
    estado,
    telefono,
    fecha_nacimiento,
    activo
FROM clientes_temp 
LIMIT 10;

-- =====================================================
-- 3. VERIFICAR CONDICIONES DEL WHERE
-- =====================================================

SELECT 
    'Total registros' as tipo,
    COUNT(*) as cantidad
FROM clientes_temp

UNION ALL

SELECT 
    'Con cédula no NULL' as tipo,
    COUNT(*) as cantidad
FROM clientes_temp
WHERE cedula IS NOT NULL

UNION ALL

SELECT 
    'Con cédula no vacía' as tipo,
    COUNT(*) as cantidad
FROM clientes_temp
WHERE cedula IS NOT NULL AND TRIM(cedula) != ''

UNION ALL

SELECT 
    'Con nombres no NULL' as tipo,
    COUNT(*) as cantidad
FROM clientes_temp
WHERE nombres IS NOT NULL

UNION ALL

SELECT 
    'Con nombres no vacíos' as tipo,
    COUNT(*) as cantidad
FROM clientes_temp
WHERE nombres IS NOT NULL AND TRIM(nombres) != ''

UNION ALL

SELECT 
    'Cumplen condiciones WHERE' as tipo,
    COUNT(*) as cantidad
FROM clientes_temp
WHERE cedula IS NOT NULL 
  AND TRIM(cedula) != ''
  AND nombres IS NOT NULL 
  AND TRIM(nombres) != '';

-- =====================================================
-- 4. VER REGISTROS QUE NO CUMPLEN CONDICIONES
-- =====================================================

SELECT 
    'Registros con problemas' as tipo,
    COUNT(*) as cantidad
FROM clientes_temp
WHERE cedula IS NULL 
   OR TRIM(cedula) = ''
   OR nombres IS NULL 
   OR TRIM(nombres) = '';

-- Ver ejemplos de registros con problemas
SELECT 
    id,
    CASE 
        WHEN cedula IS NULL THEN 'Cédula NULL'
        WHEN TRIM(cedula) = '' THEN 'Cédula vacía'
        ELSE 'OK'
    END as problema_cedula,
    CASE 
        WHEN nombres IS NULL THEN 'Nombres NULL'
        WHEN TRIM(nombres) = '' THEN 'Nombres vacíos'
        ELSE 'OK'
    END as problema_nombres,
    cedula,
    nombres
FROM clientes_temp
WHERE cedula IS NULL 
   OR TRIM(cedula) = ''
   OR nombres IS NULL 
   OR TRIM(nombres) = ''
LIMIT 10;

-- =====================================================
-- 5. PROBAR INSERT MANUAL CON UN REGISTRO
-- =====================================================

-- Descomenta para probar insertar un solo registro
/*
INSERT INTO clientes (
    cedula, nombres, telefono, email, direccion,
    fecha_nacimiento, ocupacion, estado, activo,
    fecha_registro, fecha_actualizacion, usuario_registro, notas
)
SELECT 
    REPLACE(REPLACE(TRIM(COALESCE(cedula, '')), '-', ''), ' ', '') as cedula,
    TRIM(COALESCE(nombres, '')) as nombres,
    TRIM(COALESCE(telefono, '+589999999999')) as telefono,
    LOWER(TRIM(COALESCE(email, 'buscaremail@noemail.com'))) as email,
    TRIM(COALESCE(direccion, 'Actualizar dirección')) as direccion,
    COALESCE(fecha_nacimiento, '2000-01-01'::date) as fecha_nacimiento,
    TRIM(COALESCE(ocupacion, 'Actualizar ocupación')) as ocupacion,
    CASE 
        WHEN UPPER(TRIM(COALESCE(estado, ''))) IN ('ACTIVO', 'INACTIVO', 'FINALIZADO') 
        THEN UPPER(TRIM(estado))
        ELSE 'ACTIVO'
    END as estado,
    COALESCE(activo, true) as activo,
    COALESCE(fecha_registro, CURRENT_TIMESTAMP) as fecha_registro,
    CURRENT_TIMESTAMP as fecha_actualizacion,
    COALESCE(usuario_registro, 'SISTEMA') as usuario_registro,
    COALESCE(notas, 'No hay observaciones') as notas
FROM clientes_temp
WHERE cedula IS NOT NULL 
  AND TRIM(cedula) != ''
  AND nombres IS NOT NULL 
  AND TRIM(nombres) != ''
LIMIT 1;

-- Verificar si se insertó
SELECT COUNT(*) as registros_insertados FROM clientes;
*/

