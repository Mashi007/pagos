-- ======================================================================
-- CORRECCION MASIVA: 134 CLIENTES CON CUOTAS PENDIENTES
-- ======================================================================
-- Regla: activo = TRUE mientras tenga cuotas pendientes
--        activo = FALSE cuando terminó de pagar TODAS las cuotas
-- ======================================================================

-- ======================================================================
-- 1. VERIFICAR ESTADO ACTUAL (ANTES)
-- ======================================================================

SELECT 
    'ANTES' AS momento,
    COUNT(DISTINCT c.id) AS total_clientes_a_corregir,
    SUM(COALESCE(cu.capital_pendiente, 0)) AS total_capital_pendiente,
    SUM(COALESCE(cu.interes_pendiente, 0)) AS total_interes_pendiente
FROM clientes c
INNER JOIN prestamos p ON c.cedula = p.cedula
INNER JOIN cuotas cu ON p.id = cu.prestamo_id
WHERE c.activo = FALSE
  AND p.estado = 'APROBADO'
  AND (cu.capital_pendiente > 0 OR cu.interes_pendiente > 0);

-- ======================================================================
-- 2. LISTA DE CLIENTES QUE SERAN CORREGIDOS
-- ======================================================================

SELECT 
    c.id AS cliente_id,
    c.cedula,
    c.nombres,
    c.estado AS estado_actual,
    c.activo AS activo_actual,
    COUNT(DISTINCT p.id) AS prestamos_aprobados,
    COUNT(DISTINCT cu.id) AS total_cuotas,
    COUNT(DISTINCT CASE WHEN cu.capital_pendiente > 0 OR cu.interes_pendiente > 0 THEN cu.id END) AS cuotas_pendientes,
    COALESCE(SUM(cu.capital_pendiente), 0) AS capital_pendiente_total,
    COALESCE(SUM(cu.interes_pendiente), 0) AS interes_pendiente_total
FROM clientes c
INNER JOIN prestamos p ON c.cedula = p.cedula
INNER JOIN cuotas cu ON p.id = cu.prestamo_id
WHERE c.activo = FALSE
  AND p.estado = 'APROBADO'
  AND (cu.capital_pendiente > 0 OR cu.interes_pendiente > 0)
GROUP BY c.id, c.cedula, c.nombres, c.estado, c.activo
ORDER BY capital_pendiente_total DESC;

-- ======================================================================
-- 3. ACTUALIZAR: activo = TRUE para clientes con cuotas pendientes
-- ======================================================================
-- Cambia a activo = TRUE y estado = 'ACTIVO' para clientes que tienen
-- cuotas con saldo pendiente (capital_pendiente > 0 o interes_pendiente > 0)
-- ======================================================================

UPDATE clientes 
SET activo = TRUE,
    estado = 'ACTIVO',
    fecha_actualizacion = CURRENT_TIMESTAMP
WHERE activo = FALSE
  AND EXISTS (
      SELECT 1 
      FROM prestamos p 
      INNER JOIN cuotas cu ON p.id = cu.prestamo_id
      WHERE p.cedula = clientes.cedula 
      AND p.estado = 'APROBADO'
      AND (cu.capital_pendiente > 0 OR cu.interes_pendiente > 0)
  );

-- ======================================================================
-- 4. VERIFICAR ESTADO DESPUES (DESPUES)
-- ======================================================================

SELECT 
    'DESPUES' AS momento,
    COUNT(DISTINCT c.id) AS total_clientes_corregidos,
    SUM(COALESCE(cu.capital_pendiente, 0)) AS total_capital_pendiente,
    SUM(COALESCE(cu.interes_pendiente, 0)) AS total_interes_pendiente
FROM clientes c
INNER JOIN prestamos p ON c.cedula = p.cedula
INNER JOIN cuotas cu ON p.id = cu.prestamo_id
WHERE c.activo = TRUE
  AND c.estado = 'ACTIVO'
  AND p.estado = 'APROBADO'
  AND (cu.capital_pendiente > 0 OR cu.interes_pendiente > 0);

-- ======================================================================
-- 5. VERIFICAR REGLA DE NEGOCIO: NO DEBE HABER CLIENTES CON CUOTAS PENDIENTES Y activo = FALSE
-- ======================================================================

SELECT 
    'Verificacion regla de negocio' AS tipo_verificacion,
    COUNT(DISTINCT c.id) AS clientes_con_cuotas_pendientes_y_activo_false
FROM clientes c
INNER JOIN prestamos p ON c.cedula = p.cedula
INNER JOIN cuotas cu ON p.id = cu.prestamo_id
WHERE c.activo = FALSE
  AND p.estado = 'APROBADO'
  AND (cu.capital_pendiente > 0 OR cu.interes_pendiente > 0);

-- ======================================================================
-- 6. ESTADISTICAS FINALES
-- ======================================================================

SELECT 
    c.activo,
    c.estado,
    COUNT(DISTINCT c.id) AS total_clientes,
    COUNT(DISTINCT p.id) AS total_prestamos_aprobados,
    COUNT(DISTINCT CASE WHEN cu.capital_pendiente > 0 OR cu.interes_pendiente > 0 THEN c.id END) AS clientes_con_cuotas_pendientes,
    SUM(COALESCE(cu.capital_pendiente, 0)) AS total_capital_pendiente,
    SUM(COALESCE(cu.interes_pendiente, 0)) AS total_interes_pendiente
FROM clientes c
INNER JOIN prestamos p ON c.cedula = p.cedula
LEFT JOIN cuotas cu ON p.id = cu.prestamo_id
WHERE p.estado = 'APROBADO'
GROUP BY c.activo, c.estado
ORDER BY c.activo, c.estado;

-- ======================================================================
-- RESUMEN:
-- ======================================================================
-- Este script corrige 134 clientes que tienen cuotas pendientes
-- pero estaban marcados como activo = FALSE.
-- 
-- Regla aplicada:
-- - activo = TRUE: Mientras tenga cuotas pendientes
-- - activo = FALSE: Cuando terminó de pagar TODAS las cuotas
-- ======================================================================
-- IMPORTANTE: Hacer backup de la base de datos antes de ejecutar
-- ======================================================================
