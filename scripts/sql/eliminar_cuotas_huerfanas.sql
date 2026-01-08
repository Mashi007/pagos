-- ======================================================================
-- ELIMINAR CUOTAS HUERFANAS (prestamo_id 1-3784)
-- ======================================================================
-- IMPORTANTE: 
--   1. Hacer backup antes de ejecutar
--   2. Las cuotas huérfanas NO afectan a los préstamos aprobados (3785-7826)
--   3. Se eliminarán 45,335 cuotas huérfanas
-- ======================================================================

-- ======================================================================
-- PASO 1: CREAR BACKUP DE CUOTAS HUERFANAS
-- ======================================================================

CREATE TABLE IF NOT EXISTS cuotas_huerfanas_backup_eliminacion AS
SELECT 
    *,
    CURRENT_TIMESTAMP AS fecha_backup
FROM cuotas
WHERE prestamo_id BETWEEN 1 AND 3784;

-- Verificar backup
SELECT 
    'BACKUP CREADO' AS tipo,
    COUNT(*) AS total_cuotas_backup
FROM cuotas_huerfanas_backup_eliminacion;

-- ======================================================================
-- PASO 2: VERIFICAR CUOTAS A ELIMINAR
-- ======================================================================

SELECT 
    'CUOTAS A ELIMINAR' AS tipo,
    COUNT(*) AS total_cuotas,
    COUNT(DISTINCT prestamo_id) AS prestamos_referenciados,
    COUNT(CASE WHEN total_pagado > 0 THEN 1 END) AS cuotas_con_pagos,
    SUM(total_pagado) AS total_pagado
FROM cuotas
WHERE prestamo_id BETWEEN 1 AND 3784;

-- ======================================================================
-- PASO 3: VERIFICAR QUE LOS PRESTAMOS APROBADOS NO SE AFECTAN
-- ======================================================================

SELECT 
    'VERIFICACION PRESTAMOS APROBADOS' AS tipo,
    COUNT(DISTINCT p.id) AS prestamos_aprobados,
    COUNT(c.id) AS cuotas_propias
FROM prestamos p
INNER JOIN cuotas c ON p.id = c.prestamo_id
WHERE p.estado = 'APROBADO'
  AND c.prestamo_id BETWEEN 3785 AND 7826;

-- Debe retornar: 4,042 préstamos con 48,840 cuotas propias

-- ======================================================================
-- PASO 4: ELIMINAR CUOTAS HUERFANAS
-- ======================================================================
-- OPCION A: Eliminar TODAS las cuotas huérfanas (incluyendo las con pagos)
-- OPCION B: Eliminar solo las cuotas huérfanas SIN pagos (mantener las con pagos)

-- OPCION A: Eliminar TODAS las cuotas huérfanas
-- DESCOMENTAR LA SIGUIENTE LINEA PARA EJECUTAR:
/*
DELETE FROM cuotas
WHERE prestamo_id BETWEEN 1 AND 3784;
*/

-- OPCION B: Eliminar solo cuotas huérfanas SIN pagos (mantener las con pagos)
-- DESCOMENTAR LAS SIGUIENTES LINEAS PARA EJECUTAR:
/*
DELETE FROM cuotas
WHERE prestamo_id BETWEEN 1 AND 3784
  AND total_pagado = 0;
*/

-- ======================================================================
-- PASO 5: VERIFICAR ELIMINACION
-- ======================================================================

-- Verificar cuotas huérfanas restantes
SELECT 
    'CUOTAS HUERFANAS RESTANTES' AS tipo,
    COUNT(*) AS total_cuotas_huerfanas
FROM cuotas
WHERE prestamo_id BETWEEN 1 AND 3784;

-- Debe retornar 0 (si se eliminaron todas) o el número de cuotas con pagos (si se mantuvieron)

-- Verificar que los préstamos aprobados siguen intactos
SELECT 
    'VERIFICACION POST-ELIMINACION' AS tipo,
    COUNT(DISTINCT p.id) AS prestamos_aprobados,
    COUNT(c.id) AS cuotas_propias
FROM prestamos p
INNER JOIN cuotas c ON p.id = c.prestamo_id
WHERE p.estado = 'APROBADO'
  AND c.prestamo_id BETWEEN 3785 AND 7826;

-- Debe seguir retornando: 4,042 préstamos con 48,840 cuotas

-- ======================================================================
-- PASO 6: RESUMEN FINAL
-- ======================================================================

SELECT 
    'RESUMEN FINAL' AS tipo,
    (SELECT COUNT(*) FROM cuotas WHERE prestamo_id BETWEEN 1 AND 3784) AS cuotas_huerfanas_restantes,
    (SELECT COUNT(*) FROM cuotas WHERE prestamo_id BETWEEN 3785 AND 7826) AS cuotas_propias,
    (SELECT COUNT(*) FROM prestamos WHERE estado = 'APROBADO') AS prestamos_aprobados;

-- ======================================================================
-- NOTAS:
-- ======================================================================
-- 1. Backup creado en tabla: cuotas_huerfanas_backup_eliminacion
-- 2. Para restaurar desde backup:
--    INSERT INTO cuotas SELECT * FROM cuotas_huerfanas_backup_eliminacion;
-- 3. Las cuotas huérfanas eliminadas referencian préstamos inexistentes (IDs 1-3784)
-- 4. Los préstamos aprobados (IDs 3785-7826) NO se afectan
-- 5. Si se mantienen cuotas con pagos, estas seguirán siendo huérfanas pero preservan datos históricos
-- ======================================================================
