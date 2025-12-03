-- =====================================================
-- SCRIPT DE CORRECCIÓN DE DATOS INVÁLIDOS
-- Ejecutar en DBeaver DESPUÉS de validar y ANTES de aplicar migraciones
-- =====================================================

-- IMPORTANTE: Revisar cada corrección antes de ejecutar
-- Hacer BACKUP de la base de datos antes de ejecutar estos scripts

-- 1. CORREGIR pagos con prestamo_id inválido - Establecer a NULL
-- Revisar primero con: SELECT * FROM pagos WHERE prestamo_id IS NOT NULL AND prestamo_id NOT IN (SELECT id FROM prestamos);
UPDATE pagos
SET prestamo_id = NULL
WHERE prestamo_id IS NOT NULL 
  AND prestamo_id NOT IN (SELECT id FROM prestamos);

-- 2. CORREGIR pagos con cédulas inválidas - Opción 1: Crear clientes temporales
-- Opción 2: Establecer a NULL (si el campo permite NULL)
-- Revisar primero con: SELECT DISTINCT cedula FROM pagos WHERE cedula NOT IN (SELECT cedula FROM clientes);

-- Si decidimos crear clientes temporales para cédulas que no existen:
-- INSERT INTO clientes (cedula, nombres, telefono, email, direccion, fecha_nacimiento, ocupacion, estado, activo, fecha_registro, usuario_registro, notas)
-- SELECT DISTINCT 
--     p.cedula,
--     'CLIENTE TEMPORAL - REVISAR' as nombres,
--     '' as telefono,
--     '' as email,
--     '' as direccion,
--     '1900-01-01'::date as fecha_nacimiento,
--     'REVISAR' as ocupacion,
--     'ACTIVO' as estado,
--     true as activo,
--     NOW() as fecha_registro,
--     'SISTEMA' as usuario_registro,
--     'Cliente creado automáticamente para corregir integridad referencial' as notas
-- FROM pagos p
-- WHERE p.cedula NOT IN (SELECT cedula FROM clientes)
-- ON CONFLICT DO NOTHING;

-- 3. CORREGIR evaluaciones con prestamo_id inválido - Eliminar evaluaciones huérfanas
-- Revisar primero con: SELECT * FROM prestamos_evaluacion WHERE prestamo_id NOT IN (SELECT id FROM prestamos);
-- DECISION: Eliminar evaluaciones huérfanas (o establecer prestamo_id a NULL si es nullable)
DELETE FROM prestamos_evaluacion
WHERE prestamo_id NOT IN (SELECT id FROM prestamos);

-- 4. CORREGIR auditorías de pagos con pago_id inválido - Eliminar auditorías huérfanas
-- ⚠️ NOTA: Esta tabla puede no existir. Si no existe, se creará con la migración.
-- Revisar primero con: SELECT * FROM pagos_auditoria WHERE pago_id NOT IN (SELECT id FROM pagos);
DO $$
BEGIN
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'pagos_auditoria') THEN
        DELETE FROM pagos_auditoria
        WHERE pago_id NOT IN (SELECT id FROM pagos);
        RAISE NOTICE '✅ Auditorías de pagos huérfanas eliminadas';
    ELSE
        RAISE NOTICE '⚠️ Tabla pagos_auditoria no existe - se creará con la migración';
    END IF;
END $$;

-- 5. CORREGIR auditorías de préstamos con prestamo_id inválido - Eliminar auditorías huérfanas
-- ⚠️ NOTA: Esta tabla puede no existir. Si no existe, se creará con la migración.
-- Revisar primero con: SELECT * FROM prestamos_auditoria WHERE prestamo_id NOT IN (SELECT id FROM prestamos);
DO $$
BEGIN
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'prestamos_auditoria') THEN
        DELETE FROM prestamos_auditoria
        WHERE prestamo_id NOT IN (SELECT id FROM prestamos);
        RAISE NOTICE '✅ Auditorías de préstamos huérfanas eliminadas';
    ELSE
        RAISE NOTICE '⚠️ Tabla prestamos_auditoria no existe - se creará con la migración';
    END IF;
END $$;

-- 6. CORREGIR prestamos.concesionario - Crear concesionarios faltantes o establecer a NULL
-- Revisar primero con: SELECT DISTINCT concesionario FROM prestamos WHERE concesionario IS NOT NULL AND concesionario NOT IN (SELECT nombre FROM concesionarios);

-- Opción 1: Crear concesionarios faltantes
INSERT INTO concesionarios (nombre, activo, created_at, updated_at)
SELECT DISTINCT 
    p.concesionario,
    true as activo,
    NOW() as created_at,
    NOW() as updated_at
FROM prestamos p
WHERE p.concesionario IS NOT NULL 
  AND p.concesionario NOT IN (SELECT nombre FROM concesionarios)
ON CONFLICT (nombre) DO NOTHING;

-- 7. CORREGIR prestamos.analista - Crear analistas faltantes o establecer a NULL
-- Revisar primero con: SELECT DISTINCT analista FROM prestamos WHERE analista IS NOT NULL AND analista NOT IN (SELECT nombre FROM analistas);

-- Opción 1: Crear analistas faltantes
INSERT INTO analistas (nombre, activo, created_at, updated_at)
SELECT DISTINCT 
    p.analista,
    true as activo,
    NOW() as created_at,
    NOW() as updated_at
FROM prestamos p
WHERE p.analista IS NOT NULL 
  AND p.analista NOT IN (SELECT nombre FROM analistas)
ON CONFLICT DO NOTHING;

-- 8. CORREGIR prestamos.modelo_vehiculo - Crear modelos faltantes o establecer a NULL
-- Revisar primero con: SELECT DISTINCT modelo_vehiculo FROM prestamos WHERE modelo_vehiculo IS NOT NULL AND modelo_vehiculo NOT IN (SELECT modelo FROM modelos_vehiculos);

-- Opción 1: Crear modelos faltantes
INSERT INTO modelos_vehiculos (modelo, activo, created_at, updated_at)
SELECT DISTINCT 
    p.modelo_vehiculo,
    true as activo,
    NOW() as created_at,
    NOW() as updated_at
FROM prestamos p
WHERE p.modelo_vehiculo IS NOT NULL 
  AND p.modelo_vehiculo NOT IN (SELECT modelo FROM modelos_vehiculos)
ON CONFLICT (modelo) DO NOTHING;

-- =====================================================
-- VERIFICAR CORRECCIONES
-- =====================================================
-- Ejecutar nuevamente el script 01_validar_datos_antes_migracion.sql
-- para verificar que todos los datos están corregidos

