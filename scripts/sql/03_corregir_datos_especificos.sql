-- =====================================================
-- SCRIPT DE CORRECCIÓN DE DATOS ESPECÍFICOS ENCONTRADOS
-- Basado en los resultados de la validación
-- Ejecutar en DBeaver ANTES de aplicar las migraciones
-- =====================================================

-- IMPORTANTE: Revisar cada corrección antes de ejecutar
-- Hacer BACKUP de la base de datos antes de ejecutar

BEGIN;

-- =====================================================
-- 1. CORREGIR PAGOS CON CÉDULA "NO DEFINIDA"
-- =====================================================
-- Opción A: Establecer cliente_id a NULL (si el campo permite NULL)
-- Opción B: Crear un cliente temporal "NO DEFINIDA" para estos pagos

-- Opción A: Establecer a NULL (recomendado si no hay relación con cliente)
-- UPDATE pagos
-- SET cliente_id = NULL
-- WHERE cedula = 'NO DEFINIDA';

-- Opción B: Crear cliente temporal (si necesitas mantener la relación)
INSERT INTO clientes (
    cedula, 
    nombres, 
    telefono, 
    email, 
    direccion, 
    fecha_nacimiento, 
    ocupacion, 
    estado, 
    activo, 
    fecha_registro, 
    usuario_registro, 
    notas
)
SELECT DISTINCT
    'NO DEFINIDA' as cedula,
    'CLIENTE TEMPORAL - REVISAR' as nombres,
    '' as telefono,
    '' as email,
    '' as direccion,
    '1900-01-01'::date as fecha_nacimiento,
    'REVISAR' as ocupacion,
    'ACTIVO' as estado,
    true as activo,
    NOW() as fecha_registro,
    'SISTEMA' as usuario_registro,
    'Cliente creado automáticamente para corregir integridad referencial - Revisar y corregir manualmente' as notas
WHERE NOT EXISTS (
    SELECT 1 FROM clientes WHERE cedula = 'NO DEFINIDA'
)
ON CONFLICT DO NOTHING;

-- =====================================================
-- 2. CREAR CONCESIONARIOS FALTANTES (35 concesionarios)
-- =====================================================
INSERT INTO concesionarios (nombre, activo, created_at, updated_at)
SELECT DISTINCT 
    p.concesionario,
    true as activo,
    NOW() as created_at,
    NOW() as updated_at
FROM prestamos p
WHERE p.concesionario IS NOT NULL 
  AND p.concesionario != ''
  AND p.concesionario NOT IN (SELECT nombre FROM concesionarios)
  AND p.concesionario != 'NO DEFINIDO'
ON CONFLICT (nombre) DO NOTHING;

-- Crear también "NO DEFINIDO" si existe en prestamos
INSERT INTO concesionarios (nombre, activo, created_at, updated_at)
SELECT 
    'NO DEFINIDO' as nombre,
    true as activo,
    NOW() as created_at,
    NOW() as updated_at
WHERE EXISTS (
    SELECT 1 FROM prestamos WHERE concesionario = 'NO DEFINIDO'
)
AND NOT EXISTS (
    SELECT 1 FROM concesionarios WHERE nombre = 'NO DEFINIDO'
)
ON CONFLICT (nombre) DO NOTHING;

-- =====================================================
-- 3. CREAR ANALISTAS FALTANTES (15 analistas)
-- =====================================================
INSERT INTO analistas (nombre, activo, created_at, updated_at)
SELECT DISTINCT 
    p.analista,
    true as activo,
    NOW() as created_at,
    NOW() as updated_at
FROM prestamos p
WHERE p.analista IS NOT NULL 
  AND p.analista != ''
  AND p.analista NOT IN (SELECT nombre FROM analistas)
ON CONFLICT DO NOTHING;

-- =====================================================
-- 4. CREAR MODELOS DE VEHÍCULOS FALTANTES (14 modelos)
-- =====================================================
INSERT INTO modelos_vehiculos (modelo, activo, created_at, updated_at)
SELECT DISTINCT 
    p.modelo_vehiculo,
    true as activo,
    NOW() as created_at,
    NOW() as updated_at
FROM prestamos p
WHERE p.modelo_vehiculo IS NOT NULL 
  AND p.modelo_vehiculo != ''
  AND p.modelo_vehiculo NOT IN (SELECT modelo FROM modelos_vehiculos)
ON CONFLICT (modelo) DO NOTHING;

-- =====================================================
-- VERIFICAR CORRECCIONES
-- =====================================================
-- Verificar que se crearon los registros
SELECT 'Concesionarios creados' as tipo, COUNT(*) as cantidad
FROM concesionarios
WHERE created_at >= NOW() - INTERVAL '1 minute'

UNION ALL

SELECT 'Analistas creados' as tipo, COUNT(*) as cantidad
FROM analistas
WHERE created_at >= NOW() - INTERVAL '1 minute'

UNION ALL

SELECT 'Modelos creados' as tipo, COUNT(*) as cantidad
FROM modelos_vehiculos
WHERE created_at >= NOW() - INTERVAL '1 minute';

-- Verificar que ya no hay datos inválidos
SELECT 
    'Pagos con cédula inválida' as tipo,
    COUNT(*) as cantidad
FROM pagos p
WHERE p.cedula NOT IN (SELECT cedula FROM clientes)

UNION ALL

SELECT 
    'Concesionarios inválidos' as tipo,
    COUNT(DISTINCT concesionario) as cantidad
FROM prestamos p
WHERE p.concesionario IS NOT NULL 
  AND p.concesionario NOT IN (SELECT nombre FROM concesionarios)

UNION ALL

SELECT 
    'Analistas inválidos' as tipo,
    COUNT(DISTINCT analista) as cantidad
FROM prestamos p
WHERE p.analista IS NOT NULL 
  AND p.analista NOT IN (SELECT nombre FROM analistas)

UNION ALL

SELECT 
    'Modelos inválidos' as tipo,
    COUNT(DISTINCT modelo_vehiculo) as cantidad
FROM prestamos p
WHERE p.modelo_vehiculo IS NOT NULL 
  AND p.modelo_vehiculo NOT IN (SELECT modelo FROM modelos_vehiculos);

-- Si todo está bien, hacer COMMIT, si no, hacer ROLLBACK
-- COMMIT;
-- ROLLBACK;

