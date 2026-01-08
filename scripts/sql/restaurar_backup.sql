-- ======================================================================
-- RESTAURAR BACKUP (SI ES NECESARIO)
-- ======================================================================
-- Objetivo: Restaurar tablas desde backups en caso de problemas
-- ======================================================================
-- IMPORTANTE: Cambiar la fecha según el backup que se quiera restaurar
-- ======================================================================

-- ======================================================================
-- CONFIGURACION: FECHA DEL BACKUP A RESTAURAR
-- ======================================================================
-- Cambiar esta fecha según el backup que se quiera restaurar
-- ======================================================================

-- Fecha del backup (ejemplo: 20250115)
-- Cambiar según la fecha del backup que se creó

-- ======================================================================
-- ADVERTENCIA: ESTE SCRIPT ELIMINA DATOS ACTUALES
-- ======================================================================
-- Solo ejecutar si es absolutamente necesario restaurar
-- ======================================================================

-- ======================================================================
-- 1. VERIFICAR QUE EXISTEN LOS BACKUPS
-- ======================================================================

SELECT 
    tablename,
    CASE 
        WHEN EXISTS (
            SELECT 1 FROM information_schema.tables 
            WHERE table_name = tablename
        ) THEN 'EXISTE'
        ELSE 'NO EXISTE'
    END AS estado
FROM (
    VALUES 
        ('cuotas_backup_202501XX'),
        ('prestamos_backup_202501XX'),
        ('pagos_backup_202501XX'),
        ('clientes_backup_202501XX')
) AS backups(tablename);

-- ======================================================================
-- 2. COMPARAR REGISTROS: ORIGINAL VS BACKUP
-- ======================================================================

SELECT 
    'cuotas' AS tabla,
    (SELECT COUNT(*) FROM cuotas) AS registros_actuales,
    (SELECT COUNT(*) FROM cuotas_backup_202501XX) AS registros_backup,
    (SELECT COUNT(*) FROM cuotas_backup_202501XX) - (SELECT COUNT(*) FROM cuotas) AS diferencia
WHERE EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'cuotas_backup_202501XX')

UNION ALL

SELECT 
    'prestamos' AS tabla,
    (SELECT COUNT(*) FROM prestamos) AS registros_actuales,
    (SELECT COUNT(*) FROM prestamos_backup_202501XX) AS registros_backup,
    (SELECT COUNT(*) FROM prestamos_backup_202501XX) - (SELECT COUNT(*) FROM prestamos) AS diferencia
WHERE EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'prestamos_backup_202501XX')

UNION ALL

SELECT 
    'pagos' AS tabla,
    (SELECT COUNT(*) FROM pagos) AS registros_actuales,
    (SELECT COUNT(*) FROM pagos_backup_202501XX) AS registros_backup,
    (SELECT COUNT(*) FROM pagos_backup_202501XX) - (SELECT COUNT(*) FROM pagos) AS diferencia
WHERE EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'pagos_backup_202501XX')

UNION ALL

SELECT 
    'clientes' AS tabla,
    (SELECT COUNT(*) FROM clientes) AS registros_actuales,
    (SELECT COUNT(*) FROM clientes_backup_202501XX) AS registros_backup,
    (SELECT COUNT(*) FROM clientes_backup_202501XX) - (SELECT COUNT(*) FROM clientes) AS diferencia
WHERE EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'clientes_backup_202501XX');

-- ======================================================================
-- 3. RESTAURAR TABLA CUOTAS
-- ======================================================================
-- ⚠️ ADVERTENCIA: Esto elimina todos los datos actuales de cuotas
-- ======================================================================

-- DESCOMENTAR SOLO SI ES NECESARIO RESTAURAR
/*
TRUNCATE TABLE cuotas;

INSERT INTO cuotas 
SELECT * FROM cuotas_backup_202501XX;

-- Verificar restauración
SELECT 
    'RESTAURACION CUOTAS' AS operacion,
    COUNT(*) AS total_registros_restaurados,
    (SELECT COUNT(*) FROM cuotas_backup_202501XX) AS total_backup,
    CASE 
        WHEN COUNT(*) = (SELECT COUNT(*) FROM cuotas_backup_202501XX) 
        THEN 'OK: Restauracion completa'
        ELSE 'ERROR: Diferencia en registros'
    END AS verificacion
FROM cuotas;
*/

-- ======================================================================
-- 4. RESTAURAR TABLA PRESTAMOS
-- ======================================================================
-- ⚠️ ADVERTENCIA: Esto elimina todos los datos actuales de prestamos
-- ======================================================================

-- DESCOMENTAR SOLO SI ES NECESARIO RESTAURAR
/*
TRUNCATE TABLE prestamos;

INSERT INTO prestamos 
SELECT * FROM prestamos_backup_202501XX;

-- Verificar restauración
SELECT 
    'RESTAURACION PRESTAMOS' AS operacion,
    COUNT(*) AS total_registros_restaurados,
    (SELECT COUNT(*) FROM prestamos_backup_202501XX) AS total_backup,
    CASE 
        WHEN COUNT(*) = (SELECT COUNT(*) FROM prestamos_backup_202501XX) 
        THEN 'OK: Restauracion completa'
        ELSE 'ERROR: Diferencia en registros'
    END AS verificacion
FROM prestamos;
*/

-- ======================================================================
-- 5. RESTAURAR TABLA PAGOS
-- ======================================================================
-- ⚠️ ADVERTENCIA: Esto elimina todos los datos actuales de pagos
-- ======================================================================

-- DESCOMENTAR SOLO SI ES NECESARIO RESTAURAR
/*
TRUNCATE TABLE pagos;

INSERT INTO pagos 
SELECT * FROM pagos_backup_202501XX;

-- Verificar restauración
SELECT 
    'RESTAURACION PAGOS' AS operacion,
    COUNT(*) AS total_registros_restaurados,
    (SELECT COUNT(*) FROM pagos_backup_202501XX) AS total_backup,
    CASE 
        WHEN COUNT(*) = (SELECT COUNT(*) FROM pagos_backup_202501XX) 
        THEN 'OK: Restauracion completa'
        ELSE 'ERROR: Diferencia en registros'
    END AS verificacion
FROM pagos;
*/

-- ======================================================================
-- 6. RESTAURAR TABLA CLIENTES
-- ======================================================================
-- ⚠️ ADVERTENCIA: Esto elimina todos los datos actuales de clientes
-- ======================================================================

-- DESCOMENTAR SOLO SI ES NECESARIO RESTAURAR
/*
TRUNCATE TABLE clientes;

INSERT INTO clientes 
SELECT * FROM clientes_backup_202501XX;

-- Verificar restauración
SELECT 
    'RESTAURACION CLIENTES' AS operacion,
    COUNT(*) AS total_registros_restaurados,
    (SELECT COUNT(*) FROM clientes_backup_202501XX) AS total_backup,
    CASE 
        WHEN COUNT(*) = (SELECT COUNT(*) FROM clientes_backup_202501XX) 
        THEN 'OK: Restauracion completa'
        ELSE 'ERROR: Diferencia en registros'
    END AS verificacion
FROM clientes;
*/

-- ======================================================================
-- NOTAS IMPORTANTES:
-- ======================================================================
-- 1. CAMBIAR LA FECHA en todos los nombres de tablas backup:
--    Reemplazar '202501XX' con la fecha del backup (ej: '20250115')
--
-- 2. DESCOMENTAR solo las secciones que se necesiten restaurar
--
-- 3. VERIFICAR antes de restaurar:
--    - Que los backups existen
--    - Que realmente se necesita restaurar
--    - Que se entiende que se perderán los datos actuales
--
-- 4. ORDEN DE RESTAURACION (si se restauran todas):
--    - clientes (primero, por dependencias)
--    - prestamos (segundo)
--    - cuotas (tercero)
--    - pagos (último)
--
-- 5. DESPUES DE RESTAURAR:
--    - Verificar integridad de datos
--    - Verificar relaciones entre tablas
--    - Ejecutar scripts de verificación
-- ======================================================================
