-- ======================================================================
-- CORRECCION: ELIMINAR CUOTAS DUPLICADAS/EXTRA
-- ======================================================================
-- Objetivo: Eliminar cuotas extra en préstamos con regeneraciones múltiples
-- Estrategia: Mantener solo las primeras N cuotas (donde N = numero_cuotas)
-- ======================================================================

-- ======================================================================
-- 1. VERIFICACION ANTES DE CORRECCION
-- ======================================================================

SELECT 
    'ANTES' AS momento,
    COUNT(DISTINCT p.id) AS prestamos_con_cuotas_extra,
    SUM(COUNT(cu.id) - p.numero_cuotas) AS total_cuotas_extra
FROM prestamos p
INNER JOIN cuotas cu ON p.id = cu.prestamo_id
WHERE p.estado = 'APROBADO'
GROUP BY p.id, p.numero_cuotas
HAVING COUNT(cu.id) > p.numero_cuotas;

-- ======================================================================
-- 2. LISTAR PRESTAMOS QUE SERAN CORREGIDOS
-- ======================================================================

SELECT 
    p.id AS prestamo_id,
    p.cedula,
    c.nombres AS nombre_cliente,
    p.numero_cuotas AS cuotas_planificadas,
    COUNT(cu.id) AS cuotas_actuales,
    COUNT(cu.id) - p.numero_cuotas AS cuotas_a_eliminar
FROM prestamos p
LEFT JOIN clientes c ON p.cedula = c.cedula
INNER JOIN cuotas cu ON p.id = cu.prestamo_id
WHERE p.estado = 'APROBADO'
GROUP BY p.id, p.cedula, c.nombres, p.numero_cuotas
HAVING COUNT(cu.id) > p.numero_cuotas
ORDER BY p.id;

-- ======================================================================
-- 3. CORRECCION: ELIMINAR CUOTAS EXTRA
-- ======================================================================
-- Estrategia: Eliminar las cuotas con IDs más altos, manteniendo solo
-- las primeras numero_cuotas cuotas (ordenadas por numero_cuota y fecha_vencimiento)
-- ======================================================================

-- IMPORTANTE: Hacer backup antes de ejecutar
-- CREATE TABLE cuotas_backup_YYYYMMDD AS SELECT * FROM cuotas;

-- Eliminar cuotas extra manteniendo solo las primeras N cuotas
DELETE FROM cuotas
WHERE id IN (
    SELECT cu.id
    FROM cuotas cu
    INNER JOIN prestamos p ON cu.prestamo_id = p.id
    WHERE p.estado = 'APROBADO'
      AND cu.id NOT IN (
          -- Mantener solo las primeras numero_cuotas cuotas
          SELECT cu2.id
          FROM cuotas cu2
          WHERE cu2.prestamo_id = cu.prestamo_id
          ORDER BY cu2.numero_cuota, cu2.fecha_vencimiento, cu2.id
          LIMIT (SELECT p2.numero_cuotas FROM prestamos p2 WHERE p2.id = cu.prestamo_id)
      )
);

-- ======================================================================
-- 4. VERIFICACION DESPUES DE CORRECCION
-- ======================================================================

SELECT 
    'DESPUES' AS momento,
    COUNT(DISTINCT p.id) AS prestamos_con_cuotas_extra,
    SUM(COUNT(cu.id) - p.numero_cuotas) AS total_cuotas_extra
FROM prestamos p
INNER JOIN cuotas cu ON p.id = cu.prestamo_id
WHERE p.estado = 'APROBADO'
GROUP BY p.id, p.numero_cuotas
HAVING COUNT(cu.id) > p.numero_cuotas;

-- ======================================================================
-- 5. VERIFICAR QUE NO QUEDARON CUOTAS DUPLICADAS (MISMO numero_cuota)
-- ======================================================================

SELECT 
    p.id AS prestamo_id,
    p.cedula,
    cu.numero_cuota,
    COUNT(*) AS veces_duplicada
FROM prestamos p
INNER JOIN cuotas cu ON p.id = cu.prestamo_id
WHERE p.estado = 'APROBADO'
GROUP BY p.id, p.cedula, cu.numero_cuota
HAVING COUNT(*) > 1
ORDER BY p.id, cu.numero_cuota;

-- ======================================================================
-- NOTAS:
-- ======================================================================
-- 1. HACER BACKUP antes de ejecutar: CREATE TABLE cuotas_backup AS SELECT * FROM cuotas;
-- 2. Este script elimina las cuotas con IDs más altos, manteniendo las primeras
-- 3. Si hay cuotas duplicadas con mismo numero_cuota, se mantiene la más antigua
-- 4. Verificar que no haya pagos asociados a las cuotas que se eliminarán
-- ======================================================================
