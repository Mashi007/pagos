-- =====================================================
-- SCRIPT PARA IMPORTAR CLIENTES DESDE CSV EN DBEAVER
-- Versión que NO requiere privilegios especiales
-- =====================================================
-- 
-- Este script usa INSERT directo en lugar de COPY
-- Funciona en DBeaver sin necesidad de privilegios especiales
--
-- IMPORTANTE: 
-- 1. Usar la herramienta de importación de DBeaver para cargar CSV
-- 2. O usar el script Python alternativo
-- =====================================================

BEGIN;

-- =====================================================
-- PASO 1: BACKUP DE LA TABLA ACTUAL
-- =====================================================

DROP TABLE IF EXISTS clientes_backup_antes_importacion;
CREATE TABLE clientes_backup_antes_importacion AS 
SELECT * FROM clientes;

SELECT 
    'Backup creado' as estado,
    COUNT(*) as registros_respaldados
FROM clientes_backup_antes_importacion;

-- =====================================================
-- PASO 2: BACKUP DE TABLAS DEPENDIENTES
-- =====================================================

-- Backup de préstamos
DROP TABLE IF EXISTS prestamos_backup_antes_importacion;
CREATE TABLE prestamos_backup_antes_importacion AS 
SELECT * FROM prestamos;

-- Backup de pagos (si existe)
DROP TABLE IF EXISTS pagos_backup_antes_importacion;
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'pagos') THEN
        CREATE TABLE pagos_backup_antes_importacion AS 
        SELECT * FROM pagos;
    END IF;
END $$;

-- Backup de tickets (si existe)
DROP TABLE IF EXISTS tickets_backup_antes_importacion;
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'tickets') THEN
        CREATE TABLE tickets_backup_antes_importacion AS 
        SELECT * FROM tickets;
    END IF;
END $$;

-- Backup de notificaciones (si existe)
DROP TABLE IF EXISTS notificaciones_backup_antes_importacion;
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'notificaciones') THEN
        CREATE TABLE notificaciones_backup_antes_importacion AS 
        SELECT * FROM notificaciones;
    END IF;
END $$;

-- Verificar backups
SELECT 
    'Backups creados' as estado,
    (SELECT COUNT(*) FROM prestamos_backup_antes_importacion) as prestamos,
    COALESCE((SELECT COUNT(*) FROM pagos_backup_antes_importacion), 0) as pagos,
    COALESCE((SELECT COUNT(*) FROM tickets_backup_antes_importacion), 0) as tickets,
    COALESCE((SELECT COUNT(*) FROM notificaciones_backup_antes_importacion), 0) as notificaciones;

-- =====================================================
-- PASO 3: VERIFICAR DEPENDENCIAS
-- =====================================================

SELECT 
    'Préstamos que referencian clientes' as advertencia,
    COUNT(*) as cantidad
FROM prestamos
WHERE cliente_id IS NOT NULL

UNION ALL

SELECT 
    'Tickets que referencian clientes' as advertencia,
    COUNT(*) as cantidad
FROM tickets
WHERE cliente_id IS NOT NULL
AND EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'tickets')

UNION ALL

SELECT 
    'Notificaciones que referencian clientes' as advertencia,
    COUNT(*) as cantidad
FROM notificaciones
WHERE cliente_id IS NOT NULL
AND EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'notificaciones');

-- =====================================================
-- PASO 4: ELIMINAR DATOS EN ORDEN (RESPETANDO FOREIGN KEYS)
-- =====================================================

-- 4.1. Eliminar préstamos que referencian clientes
DELETE FROM prestamos
WHERE cliente_id IS NOT NULL;

-- 4.2. Eliminar tickets que referencian clientes (si existe)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'tickets') THEN
        DELETE FROM tickets WHERE cliente_id IS NOT NULL;
    END IF;
END $$;

-- 4.3. Eliminar notificaciones que referencian clientes (si existe)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'notificaciones') THEN
        DELETE FROM notificaciones WHERE cliente_id IS NOT NULL;
    END IF;
END $$;

-- 4.4. Eliminar conversaciones_whatsapp que referencian clientes (si existe)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'conversaciones_whatsapp') THEN
        DELETE FROM conversaciones_whatsapp WHERE cliente_id IS NOT NULL;
    END IF;
END $$;

-- 4.5. Eliminar comunicaciones_email que referencian clientes (si existe)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'comunicaciones_email') THEN
        DELETE FROM comunicaciones_email WHERE cliente_id IS NOT NULL;
    END IF;
END $$;

-- 4.6. Eliminar conversaciones_ai que referencian clientes (si existe)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'conversaciones_ai') THEN
        DELETE FROM conversaciones_ai WHERE cliente_id IS NOT NULL;
    END IF;
END $$;

-- 4.7. Ahora sí, eliminar todos los registros de clientes
DELETE FROM clientes;

-- Verificar que se eliminaron
SELECT 
    'Registros restantes en clientes' as verificacion,
    COUNT(*) as cantidad
FROM clientes;
-- Debe ser 0

-- =====================================================
-- PASO 5: CREAR TABLA TEMPORAL
-- =====================================================

DROP TABLE IF EXISTS clientes_temp;
CREATE TABLE clientes_temp (
    id INTEGER,
    cedula VARCHAR(20),
    nombres VARCHAR(100),
    telefono VARCHAR(15),
    email VARCHAR(100),
    direccion TEXT,
    fecha_nacimiento DATE,
    ocupacion VARCHAR(100),
    estado VARCHAR(20),
    activo BOOLEAN,
    fecha_registro TIMESTAMP,
    fecha_actualizacion TIMESTAMP,
    usuario_registro VARCHAR(100),
    notas TEXT
);

-- =====================================================
-- PASO 6: IMPORTAR DATOS DESDE CSV (USANDO DBEAVER)
-- =====================================================
-- 
-- OPCIÓN A: Usar herramienta de importación de DBeaver
-- 1. Click derecho en tabla clientes_temp → Import Data
-- 2. Seleccionar archivo CSV
-- 3. Configurar mapeo de columnas
-- 4. Ejecutar importación
--
-- OPCIÓN B: Usar script Python (ver scripts/python/importar_clientes_csv.py)
--
-- OPCIÓN C: Insertar manualmente usando INSERT (ver abajo)

-- =====================================================
-- OPCIÓN C: INSERT MANUAL (si tienes pocos registros)
-- =====================================================
-- Descomenta y ajusta según tus datos:

/*
INSERT INTO clientes_temp (
    id, cedula, nombres, telefono, email, direccion,
    fecha_nacimiento, ocupacion, estado, activo,
    fecha_registro, fecha_actualizacion, usuario_registro, notas
) VALUES
(1, 'V12345678', 'Juan Pérez García', '+581234567890', 'juan.perez@email.com', 'Av. Principal 123', '1990-05-15', 'Ingeniero', 'ACTIVO', true, '2025-01-27 10:00:00', '2025-01-27 10:00:00', 'admin@rapicreditca.com', 'Cliente nuevo'),
(2, 'V87654321', 'María González López', '+581234567891', 'maria.gonzalez@email.com', 'Calle Secundaria 456', '1985-08-20', 'Doctora', 'ACTIVO', true, '2025-01-27 10:00:00', '2025-01-27 10:00:00', 'admin@rapicreditca.com', 'Cliente nuevo');
-- Agregar más filas según necesites
*/

-- =====================================================
-- PASO 7: VERIFICAR DATOS IMPORTADOS EN TABLA TEMPORAL
-- =====================================================

SELECT 
    'Registros en tabla temporal' as estado,
    COUNT(*) as cantidad
FROM clientes_temp;

-- Verificar problemas en los datos
SELECT 
    'Cédulas NULL o vacías' as problema,
    COUNT(*) as cantidad
FROM clientes_temp
WHERE cedula IS NULL OR TRIM(cedula) = ''

UNION ALL

SELECT 
    'Nombres NULL o vacíos' as problema,
    COUNT(*) as cantidad
FROM clientes_temp
WHERE nombres IS NULL OR TRIM(nombres) = ''

UNION ALL

SELECT 
    'Cédulas con guiones' as problema,
    COUNT(*) as cantidad
FROM clientes_temp
WHERE cedula LIKE '%-%'

UNION ALL

SELECT 
    'Emails no en minúsculas' as problema,
    COUNT(*) as cantidad
FROM clientes_temp
WHERE email IS NOT NULL AND email != LOWER(email)

UNION ALL

SELECT 
    'Estados inválidos' as problema,
    COUNT(*) as cantidad
FROM clientes_temp
WHERE estado IS NOT NULL 
  AND UPPER(TRIM(estado)) NOT IN ('ACTIVO', 'INACTIVO', 'FINALIZADO');

-- =====================================================
-- PASO 8: VERIFICAR CUÁNTOS REGISTROS SE VAN A INSERTAR
-- =====================================================

-- Verificar cuántos registros cumplen las condiciones
SELECT 
    'Registros que se insertarán' as verificacion,
    COUNT(*) as cantidad
FROM clientes_temp
WHERE cedula IS NOT NULL 
  AND TRIM(cedula) != ''
  AND nombres IS NOT NULL 
  AND TRIM(nombres) != '';

-- Si la cantidad es 0, ver qué está pasando
SELECT 
    'Total en temporal' as diagnostico,
    COUNT(*) as cantidad
FROM clientes_temp

UNION ALL

SELECT 
    'Con cédula válida' as diagnostico,
    COUNT(*) as cantidad
FROM clientes_temp
WHERE cedula IS NOT NULL AND TRIM(cedula) != ''

UNION ALL

SELECT 
    'Con nombres válidos' as diagnostico,
    COUNT(*) as cantidad
FROM clientes_temp
WHERE nombres IS NOT NULL AND TRIM(nombres) != ''

UNION ALL

SELECT 
    'Cumplen todas las condiciones' as diagnostico,
    COUNT(*) as cantidad
FROM clientes_temp
WHERE cedula IS NOT NULL 
  AND TRIM(cedula) != ''
  AND nombres IS NOT NULL 
  AND TRIM(nombres) != '';

-- =====================================================
-- PASO 8.1: INSERTAR DATOS EN TABLA clientes
-- =====================================================

-- Insertar registros válidos
INSERT INTO clientes (
    cedula, nombres, telefono, email, direccion,
    fecha_nacimiento, ocupacion, estado, activo,
    fecha_registro, fecha_actualizacion, usuario_registro, notas
)
SELECT 
    -- Cédula: normalizar (eliminar guiones y espacios)
    REPLACE(REPLACE(TRIM(COALESCE(cedula, '')), '-', ''), ' ', '') as cedula,
    
    -- Nombres: trim
    TRIM(COALESCE(nombres, '')) as nombres,
    
    -- Teléfono: trim, default si está vacío
    TRIM(COALESCE(telefono, '+589999999999')) as telefono,
    
    -- Email: minúsculas y trim, default si está vacío
    LOWER(TRIM(COALESCE(email, 'buscaremail@noemail.com'))) as email,
    
    -- Dirección: trim, default si está vacío
    TRIM(COALESCE(direccion, 'Actualizar dirección')) as direccion,
    
    -- Fecha nacimiento: default si es NULL
    COALESCE(fecha_nacimiento, '2000-01-01'::date) as fecha_nacimiento,
    
    -- Ocupación: trim, default si está vacío
    TRIM(COALESCE(ocupacion, 'Actualizar ocupación')) as ocupacion,
    
    -- Estado: default ACTIVO si es NULL o inválido
    CASE 
        WHEN UPPER(TRIM(COALESCE(estado, ''))) IN ('ACTIVO', 'INACTIVO', 'FINALIZADO') 
        THEN UPPER(TRIM(estado))
        ELSE 'ACTIVO'
    END as estado,
    
    -- Activo: default true si es NULL
    COALESCE(activo, true) as activo,
    
    -- Fecha registro: usar del CSV o actual
    COALESCE(fecha_registro, CURRENT_TIMESTAMP) as fecha_registro,
    
    -- Fecha actualización: siempre actual
    CURRENT_TIMESTAMP as fecha_actualizacion,
    
    -- Usuario registro: usar del CSV o 'SISTEMA'
    COALESCE(usuario_registro, 'SISTEMA') as usuario_registro,
    
    -- Notas: default si está vacío
    COALESCE(notas, 'No hay observaciones') as notas

FROM clientes_temp
WHERE cedula IS NOT NULL 
  AND TRIM(cedula) != ''
  AND nombres IS NOT NULL 
  AND TRIM(nombres) != '';

-- =====================================================
-- PASO 8.2: VERIFICAR CUÁNTOS SE INSERTARON
-- =====================================================

SELECT 
    'Registros insertados' as resultado,
    COUNT(*) as cantidad
FROM clientes;

-- =====================================================
-- PASO 9: VERIFICAR RESULTADOS
-- =====================================================

-- 9.1. Total de registros insertados
SELECT 
    'Registros en clientes después de importar' as resultado,
    COUNT(*) as cantidad
FROM clientes;

-- 9.2. Verificar normalización
SELECT 
    'Cédulas sin guiones' as verificacion,
    COUNT(*) as cantidad
FROM clientes
WHERE cedula !~ '-'

UNION ALL

SELECT 
    'Emails en minúsculas' as verificacion,
    COUNT(*) as cantidad
FROM clientes
WHERE email = LOWER(email)

UNION ALL

SELECT 
    'Estados válidos' as verificacion,
    COUNT(*) as cantidad
FROM clientes
WHERE estado IN ('ACTIVO', 'INACTIVO', 'FINALIZADO')

UNION ALL

SELECT 
    'Estados NULL (debe ser 0)' as verificacion,
    COUNT(*) as cantidad
FROM clientes
WHERE estado IS NULL;

-- 9.3. Verificar duplicados
SELECT 
    'Cédulas duplicadas' as problema,
    COUNT(*) as cantidad
FROM (
    SELECT cedula, COUNT(*) 
    FROM clientes 
    GROUP BY cedula 
    HAVING COUNT(*) > 1
) duplicados;

-- =====================================================
-- PASO 10: COMPARAR BASE ACTUAL CON NUEVA
-- =====================================================

-- Comparar totales
SELECT 
    'Base actual (backup)' as origen,
    COUNT(*) as total_clientes
FROM clientes_backup_antes_importacion

UNION ALL

SELECT 
    'Base nueva (importada)' as origen,
    COUNT(*) as total_clientes
FROM clientes;

-- Comparar por estado
SELECT 
    'Base actual' as origen,
    estado,
    COUNT(*) as cantidad
FROM clientes_backup_antes_importacion
GROUP BY estado

UNION ALL

SELECT 
    'Base nueva' as origen,
    estado,
    COUNT(*) as cantidad
FROM clientes
GROUP BY estado
ORDER BY origen, estado;

-- =====================================================
-- PASO 11: LIMPIAR TABLA TEMPORAL
-- =====================================================

DROP TABLE IF EXISTS clientes_temp;

-- =====================================================
-- FIN DEL SCRIPT
-- =====================================================

-- Si todo está bien, hacer COMMIT
-- Si hay errores, hacer ROLLBACK

-- COMMIT;
-- ROLLBACK;

-- =====================================================
-- ROLLBACK COMPLETO (Si necesitas revertir)
-- =====================================================

-- Si necesitas restaurar desde backup:
/*
-- Restaurar clientes
DELETE FROM clientes;
INSERT INTO clientes 
SELECT * FROM clientes_backup_antes_importacion;

-- Restaurar préstamos
DELETE FROM prestamos;
INSERT INTO prestamos 
SELECT * FROM prestamos_backup_antes_importacion;

-- Restaurar pagos (si existe)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'pagos') THEN
        DELETE FROM pagos;
        INSERT INTO pagos SELECT * FROM pagos_backup_antes_importacion;
    END IF;
END $$;

-- Restaurar tickets (si existe)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'tickets') THEN
        DELETE FROM tickets;
        INSERT INTO tickets SELECT * FROM tickets_backup_antes_importacion;
    END IF;
END $$;

-- Restaurar notificaciones (si existe)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'notificaciones') THEN
        DELETE FROM notificaciones;
        INSERT INTO notificaciones SELECT * FROM notificaciones_backup_antes_importacion;
    END IF;
END $$;
*/

