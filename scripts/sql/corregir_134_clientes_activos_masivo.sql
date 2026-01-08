-- ======================================================================
-- SCRIPT PARA CORREGIR 134 CLIENTES: CAMBIAR A ACTIVO (PRESTAMOS VIGENTES)
-- ======================================================================
-- Análisis detectó: 134 clientes en estado FINALIZADO con saldo pendiente
-- Regla: Clientes con préstamos aprobados y saldo pendiente = ACTIVOS
-- ======================================================================

-- ======================================================================
-- 1. VERIFICAR CLIENTES QUE SERAN CORREGIDOS (ANTES)
-- ======================================================================

SELECT 
    'ANTES' AS momento,
    c.id AS cliente_id,
    c.cedula,
    c.nombres,
    c.estado AS estado_actual,
    c.activo,
    COUNT(p.id) AS total_prestamos_aprobados,
    COALESCE(SUM(cu.capital_pendiente), 0) AS capital_pendiente,
    COALESCE(SUM(cu.interes_pendiente), 0) AS interes_pendiente,
    COALESCE(SUM(cu.capital_pendiente), 0) + COALESCE(SUM(cu.interes_pendiente), 0) AS saldo_total_pendiente
FROM clientes c
INNER JOIN prestamos p ON c.cedula = p.cedula
LEFT JOIN cuotas cu ON p.id = cu.prestamo_id
WHERE c.activo = FALSE
  AND p.estado = 'APROBADO'
GROUP BY c.id, c.cedula, c.nombres, c.estado, c.activo
HAVING COALESCE(SUM(cu.capital_pendiente), 0) > 0 
    OR COALESCE(SUM(cu.interes_pendiente), 0) > 0
ORDER BY saldo_total_pendiente DESC;

-- ======================================================================
-- 2. RESUMEN ANTES DE LA CORRECCION
-- ======================================================================

SELECT 
    'ANTES' AS momento,
    COUNT(DISTINCT c.id) AS total_clientes_a_corregir,
    SUM(COALESCE(cu.capital_pendiente, 0)) AS total_capital_pendiente,
    SUM(COALESCE(cu.interes_pendiente, 0)) AS total_interes_pendiente
FROM clientes c
INNER JOIN prestamos p ON c.cedula = p.cedula
LEFT JOIN cuotas cu ON p.id = cu.prestamo_id
WHERE c.activo = FALSE
  AND p.estado = 'APROBADO'
  AND EXISTS (
      SELECT 1 
      FROM cuotas cu2 
      WHERE cu2.prestamo_id = p.id 
      AND (cu2.capital_pendiente > 0 OR cu2.interes_pendiente > 0)
  );

-- ======================================================================
-- 3. ACTUALIZAR CLIENTES A ESTADO 'ACTIVO'
-- ======================================================================
-- Actualiza todos los clientes que tienen préstamos aprobados con saldo pendiente
-- ======================================================================

UPDATE clientes 
SET estado = 'ACTIVO',
    activo = TRUE,
    fecha_actualizacion = CURRENT_TIMESTAMP
WHERE id IN (
    SELECT DISTINCT c.id
    FROM clientes c
    INNER JOIN prestamos p ON c.cedula = p.cedula
    INNER JOIN cuotas cu ON p.id = cu.prestamo_id
    WHERE c.activo = FALSE
      AND p.estado = 'APROBADO'
      AND (cu.capital_pendiente > 0 OR cu.interes_pendiente > 0)
);

-- ======================================================================
-- 4. VERIFICAR CLIENTES DESPUES DE LA CORRECCION
-- ======================================================================

SELECT 
    'DESPUES' AS momento,
    c.id AS cliente_id,
    c.cedula,
    c.nombres,
    c.estado AS estado_actual,
    c.activo,
    COUNT(p.id) AS total_prestamos_aprobados,
    COALESCE(SUM(cu.capital_pendiente), 0) AS capital_pendiente,
    COALESCE(SUM(cu.interes_pendiente), 0) AS interes_pendiente,
    COALESCE(SUM(cu.capital_pendiente), 0) + COALESCE(SUM(cu.interes_pendiente), 0) AS saldo_total_pendiente
FROM clientes c
INNER JOIN prestamos p ON c.cedula = p.cedula
LEFT JOIN cuotas cu ON p.id = cu.prestamo_id
WHERE c.activo = TRUE
  AND p.estado = 'APROBADO'
  AND c.id IN (
      SELECT DISTINCT c2.id
      FROM clientes c2
      INNER JOIN prestamos p2 ON c2.cedula = p2.cedula
      INNER JOIN cuotas cu2 ON p2.id = cu2.prestamo_id
      WHERE (cu2.capital_pendiente > 0 OR cu2.interes_pendiente > 0)
  )
GROUP BY c.id, c.cedula, c.nombres, c.estado, c.activo
ORDER BY saldo_total_pendiente DESC
LIMIT 20;

-- ======================================================================
-- 5. RESUMEN DESPUES DE LA CORRECCION
-- ======================================================================

SELECT 
    'DESPUES' AS momento,
    COUNT(DISTINCT c.id) AS total_clientes_activos_con_saldo,
    SUM(COALESCE(cu.capital_pendiente, 0)) AS total_capital_pendiente,
    SUM(COALESCE(cu.interes_pendiente, 0)) AS total_interes_pendiente
FROM clientes c
INNER JOIN prestamos p ON c.cedula = p.cedula
LEFT JOIN cuotas cu ON p.id = cu.prestamo_id
WHERE c.activo = TRUE
  AND c.estado = 'ACTIVO'
  AND p.estado = 'APROBADO'
  AND EXISTS (
      SELECT 1 
      FROM cuotas cu2 
      WHERE cu2.prestamo_id = p.id 
      AND (cu2.capital_pendiente > 0 OR cu2.interes_pendiente > 0)
  );

-- ======================================================================
-- 6. VERIFICAR REGLA DE NEGOCIO: NO DEBE HABER CLIENTES INACTIVOS CON PRESTAMOS APROBADOS
-- ======================================================================

SELECT 
    'Verificacion regla de negocio' AS tipo_verificacion,
    COUNT(*) AS clientes_inactivos_con_prestamos_aprobados
FROM clientes c
INNER JOIN prestamos p ON c.cedula = p.cedula
WHERE c.activo = FALSE
  AND p.estado = 'APROBADO'
  AND EXISTS (
      SELECT 1 
      FROM cuotas cu 
      WHERE cu.prestamo_id = p.id 
      AND (cu.capital_pendiente > 0 OR cu.interes_pendiente > 0)
  );

-- ======================================================================
-- 7. ESTADISTICAS FINALES
-- ======================================================================

SELECT 
    c.estado,
    c.activo,
    COUNT(DISTINCT c.id) AS total_clientes,
    COUNT(p.id) AS total_prestamos_aprobados,
    COUNT(DISTINCT CASE WHEN cu.capital_pendiente > 0 OR cu.interes_pendiente > 0 THEN c.id END) AS clientes_con_saldo_pendiente,
    SUM(COALESCE(cu.capital_pendiente, 0)) AS total_capital_pendiente,
    SUM(COALESCE(cu.interes_pendiente, 0)) AS total_interes_pendiente
FROM clientes c
INNER JOIN prestamos p ON c.cedula = p.cedula
LEFT JOIN cuotas cu ON p.id = cu.prestamo_id
WHERE p.estado = 'APROBADO'
GROUP BY c.estado, c.activo
ORDER BY c.estado, c.activo;

-- ======================================================================
-- RESUMEN:
-- ======================================================================
-- Este script corrige masivamente 134 clientes que tienen préstamos
-- aprobados con saldo pendiente, cambiándolos de estado FINALIZADO
-- a estado ACTIVO.
-- 
-- Regla de negocio aplicada:
-- - Clientes ACTIVOS = Tienen préstamos aprobados con saldo pendiente (vigentes)
-- - Clientes INACTIVOS = No tienen préstamos aprobados (pasivos)
-- - Clientes FINALIZADOS = Completaron su ciclo (sin saldo pendiente)
-- ======================================================================
-- IMPORTANTE: Hacer backup de la base de datos antes de ejecutar
-- ======================================================================
