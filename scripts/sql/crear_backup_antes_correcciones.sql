-- ======================================================================
-- CREAR BACKUP ANTES DE CORRECCIONES
-- ======================================================================
-- Objetivo: Crear backups de todas las tablas relevantes antes de
--           ejecutar correcciones de inconsistencias en cuotas
-- ======================================================================
-- IMPORTANTE: Cambiar la fecha en el nombre de las tablas de backup
-- ======================================================================

-- ======================================================================
-- CONFIGURACION: FECHA DEL BACKUP
-- ======================================================================
-- Cambiar esta fecha según el día que se ejecute
-- ======================================================================

DO $$
DECLARE
    fecha_backup TEXT := TO_CHAR(CURRENT_DATE, 'YYYYMMDD');
BEGIN
    RAISE NOTICE 'Creando backups con fecha: %', fecha_backup;
END $$;

-- ======================================================================
-- 1. BACKUP DE TABLA CUOTAS (PRINCIPAL)
-- ======================================================================
-- Esta es la tabla más crítica para las correcciones
-- ======================================================================

CREATE TABLE cuotas_backup_202501XX AS 
SELECT * FROM cuotas;

-- Verificar que el backup se creó correctamente
SELECT 
    'cuotas_backup_202501XX' AS tabla_backup,
    COUNT(*) AS total_registros,
    (SELECT COUNT(*) FROM cuotas) AS total_original,
    CASE 
        WHEN COUNT(*) = (SELECT COUNT(*) FROM cuotas) THEN 'OK: Backup completo'
        ELSE 'ERROR: Diferencia en registros'
    END AS verificacion
FROM cuotas_backup_202501XX;

-- ======================================================================
-- 2. BACKUP DE TABLA PRESTAMOS
-- ======================================================================
-- Importante porque contiene numero_cuotas y fecha_base_calculo
-- ======================================================================

CREATE TABLE prestamos_backup_202501XX AS 
SELECT * FROM prestamos;

-- Verificar backup
SELECT 
    'prestamos_backup_202501XX' AS tabla_backup,
    COUNT(*) AS total_registros,
    (SELECT COUNT(*) FROM prestamos) AS total_original,
    CASE 
        WHEN COUNT(*) = (SELECT COUNT(*) FROM prestamos) THEN 'OK: Backup completo'
        ELSE 'ERROR: Diferencia en registros'
    END AS verificacion
FROM prestamos_backup_202501XX;

-- ======================================================================
-- 3. BACKUP DE TABLA PAGOS
-- ======================================================================
-- Importante para verificar si hay pagos en cuotas que se eliminarán
-- ======================================================================

CREATE TABLE pagos_backup_202501XX AS 
SELECT * FROM pagos;

-- Verificar backup
SELECT 
    'pagos_backup_202501XX' AS tabla_backup,
    COUNT(*) AS total_registros,
    (SELECT COUNT(*) FROM pagos) AS total_original,
    CASE 
        WHEN COUNT(*) = (SELECT COUNT(*) FROM pagos) THEN 'OK: Backup completo'
        ELSE 'ERROR: Diferencia en registros'
    END AS verificacion
FROM pagos_backup_202501XX;

-- ======================================================================
-- 4. BACKUP DE TABLA CLIENTES
-- ======================================================================
-- Por si acaso se necesita restaurar información de clientes
-- ======================================================================

CREATE TABLE clientes_backup_202501XX AS 
SELECT * FROM clientes;

-- Verificar backup
SELECT 
    'clientes_backup_202501XX' AS tabla_backup,
    COUNT(*) AS total_registros,
    (SELECT COUNT(*) FROM clientes) AS total_original,
    CASE 
        WHEN COUNT(*) = (SELECT COUNT(*) FROM clientes) THEN 'OK: Backup completo'
        ELSE 'ERROR: Diferencia en registros'
    END AS verificacion
FROM clientes_backup_202501XX;

-- ======================================================================
-- 5. RESUMEN DE BACKUPS CREADOS
-- ======================================================================

SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS tamaño
FROM pg_tables
WHERE tablename LIKE '%_backup_202501XX'
ORDER BY tablename;

-- ======================================================================
-- 6. ESTADISTICAS DE TABLAS ORIGINALES (PARA COMPARACION)
-- ======================================================================

SELECT 
    'cuotas' AS tabla,
    COUNT(*) AS total_registros,
    COUNT(DISTINCT prestamo_id) AS prestamos_con_cuotas,
    MIN(fecha_registro) AS registro_mas_antiguo,
    MAX(fecha_registro) AS registro_mas_reciente
FROM cuotas

UNION ALL

SELECT 
    'prestamos' AS tabla,
    COUNT(*) AS total_registros,
    COUNT(DISTINCT cedula) AS clientes_distintos,
    MIN(fecha_registro) AS registro_mas_antiguo,
    MAX(fecha_registro) AS registro_mas_reciente
FROM prestamos

UNION ALL

SELECT 
    'pagos' AS tabla,
    COUNT(*) AS total_registros,
    COUNT(DISTINCT cedula) AS clientes_distintos,
    MIN(fecha_registro) AS registro_mas_antiguo,
    MAX(fecha_registro) AS registro_mas_reciente
FROM pagos

UNION ALL

SELECT 
    'clientes' AS tabla,
    COUNT(*) AS total_registros,
    COUNT(DISTINCT cedula) AS clientes_distintos,
    MIN(fecha_registro) AS registro_mas_antiguo,
    MAX(fecha_registro) AS registro_mas_reciente
FROM clientes;

-- ======================================================================
-- 7. VERIFICACION DE INTEGRIDAD DE BACKUPS
-- ======================================================================

SELECT 
    'VERIFICACION DE BACKUPS' AS tipo,
    CASE 
        WHEN EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'cuotas_backup_202501XX') 
        THEN 'OK: Tabla cuotas_backup existe'
        ELSE 'ERROR: Tabla cuotas_backup NO existe'
    END AS cuotas_backup,
    CASE 
        WHEN EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'prestamos_backup_202501XX') 
        THEN 'OK: Tabla prestamos_backup existe'
        ELSE 'ERROR: Tabla prestamos_backup NO existe'
    END AS prestamos_backup,
    CASE 
        WHEN EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'pagos_backup_202501XX') 
        THEN 'OK: Tabla pagos_backup existe'
        ELSE 'ERROR: Tabla pagos_backup NO existe'
    END AS pagos_backup,
    CASE 
        WHEN EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'clientes_backup_202501XX') 
        THEN 'OK: Tabla clientes_backup existe'
        ELSE 'ERROR: Tabla clientes_backup NO existe'
    END AS clientes_backup;

-- ======================================================================
-- NOTAS IMPORTANTES:
-- ======================================================================
-- 1. CAMBIAR LA FECHA en todos los nombres de tablas backup:
--    Reemplazar '202501XX' con la fecha actual (ej: '20250115')
--
-- 2. VERIFICAR que todos los backups se crearon correctamente:
--    Revisar los resultados de las verificaciones anteriores
--
-- 3. TAMAÑO DE BACKUPS:
--    Los backups pueden ocupar espacio significativo
--    Considerar eliminarlos después de verificar que las correcciones funcionaron
--
-- 4. RESTAURACION (si es necesario):
--    TRUNCATE TABLE cuotas;
--    INSERT INTO cuotas SELECT * FROM cuotas_backup_202501XX;
--
-- 5. ELIMINAR BACKUPS (después de verificar):
--    DROP TABLE cuotas_backup_202501XX;
--    DROP TABLE prestamos_backup_202501XX;
--    DROP TABLE pagos_backup_202501XX;
--    DROP TABLE clientes_backup_202501XX;
-- ======================================================================
