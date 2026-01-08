-- ======================================================================
-- CORRECCION MASIVA: activo según pago de cuotas
-- ======================================================================
-- Regla: activo = TRUE mientras tenga cuotas pendientes
--        activo = FALSE cuando terminó de pagar TODAS las cuotas
-- ======================================================================

-- ======================================================================
-- 1. VERIFICAR ESTADO ACTUAL (ANTES)
-- ======================================================================

SELECT 
    'ANTES' AS momento,
    COUNT(DISTINCT CASE WHEN c.activo = TRUE THEN c.id END) AS clientes_activos_true,
    COUNT(DISTINCT CASE WHEN c.activo = FALSE THEN c.id END) AS clientes_activos_false,
    COUNT(DISTINCT CASE WHEN c.activo = FALSE 
                         AND EXISTS (
                             SELECT 1 FROM prestamos p 
                             INNER JOIN cuotas cu ON p.id = cu.prestamo_id
                             WHERE p.cedula = c.cedula 
                             AND p.estado = 'APROBADO'
                             AND (cu.capital_pendiente > 0 OR cu.interes_pendiente > 0)
                         ) THEN c.id END) AS anomalia_1,
    COUNT(DISTINCT CASE WHEN c.activo = TRUE 
                         AND EXISTS (
                             SELECT 1 FROM prestamos p 
                             INNER JOIN cuotas cu ON p.id = cu.prestamo_id
                             WHERE p.cedula = c.cedula 
                             AND p.estado = 'APROBADO'
                             GROUP BY p.cedula
                             HAVING COALESCE(SUM(cu.capital_pendiente), 0) = 0 
                                AND COALESCE(SUM(cu.interes_pendiente), 0) = 0
                                AND COUNT(cu.id) > 0
                         ) THEN c.id END) AS anomalia_2
FROM clientes c;

-- ======================================================================
-- 2. CORREGIR: activo = TRUE para clientes con cuotas pendientes
-- ======================================================================
-- Clientes que tienen préstamos aprobados con cuotas que tienen saldo pendiente
-- ======================================================================

UPDATE clientes 
SET activo = TRUE,
    estado = CASE 
        WHEN estado = 'INACTIVO' THEN 'ACTIVO'
        WHEN estado = 'FINALIZADO' THEN 'ACTIVO'
        ELSE estado
    END,
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
-- 3. CORREGIR: activo = FALSE para clientes que pagaron todas las cuotas
-- ======================================================================
-- Clientes que tienen préstamos aprobados pero TODAS las cuotas están pagadas
-- ======================================================================

UPDATE clientes 
SET activo = FALSE,
    estado = 'FINALIZADO',
    fecha_actualizacion = CURRENT_TIMESTAMP
WHERE activo = TRUE
  AND EXISTS (
      SELECT 1 
      FROM prestamos p 
      INNER JOIN cuotas cu ON p.id = cu.prestamo_id
      WHERE p.cedula = clientes.cedula 
      AND p.estado = 'APROBADO'
      GROUP BY p.cedula
      HAVING COALESCE(SUM(cu.capital_pendiente), 0) = 0 
         AND COALESCE(SUM(cu.interes_pendiente), 0) = 0
         AND COUNT(cu.id) > 0
  )
  AND NOT EXISTS (
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
    COUNT(DISTINCT CASE WHEN c.activo = TRUE THEN c.id END) AS clientes_activos_true,
    COUNT(DISTINCT CASE WHEN c.activo = FALSE THEN c.id END) AS clientes_activos_false,
    COUNT(DISTINCT CASE WHEN c.activo = FALSE 
                         AND EXISTS (
                             SELECT 1 FROM prestamos p 
                             INNER JOIN cuotas cu ON p.id = cu.prestamo_id
                             WHERE p.cedula = c.cedula 
                             AND p.estado = 'APROBADO'
                             AND (cu.capital_pendiente > 0 OR cu.interes_pendiente > 0)
                         ) THEN c.id END) AS anomalia_1_restante,
    COUNT(DISTINCT CASE WHEN c.activo = TRUE 
                         AND EXISTS (
                             SELECT 1 FROM prestamos p 
                             INNER JOIN cuotas cu ON p.id = cu.prestamo_id
                             WHERE p.cedula = c.cedula 
                             AND p.estado = 'APROBADO'
                             GROUP BY p.cedula
                             HAVING COALESCE(SUM(cu.capital_pendiente), 0) = 0 
                                AND COALESCE(SUM(cu.interes_pendiente), 0) = 0
                                AND COUNT(cu.id) > 0
                         ) THEN c.id END) AS anomalia_2_restante
FROM clientes c;

-- ======================================================================
-- 5. VERIFICAR REGLA DE NEGOCIO FINAL
-- ======================================================================

SELECT 
    'Verificacion final' AS tipo,
    COUNT(*) AS total_clientes,
    COUNT(CASE WHEN activo = TRUE 
               AND EXISTS (
                   SELECT 1 FROM prestamos p 
                   INNER JOIN cuotas cu ON p.id = cu.prestamo_id
                   WHERE p.cedula = c.cedula 
                   AND p.estado = 'APROBADO'
                   AND (cu.capital_pendiente > 0 OR cu.interes_pendiente > 0)
               ) THEN 1 END) AS correctos_activos,
    COUNT(CASE WHEN activo = FALSE 
               AND EXISTS (
                   SELECT 1 FROM prestamos p 
                   INNER JOIN cuotas cu ON p.id = cu.prestamo_id
                   WHERE p.cedula = c.cedula 
                   AND p.estado = 'APROBADO'
                   GROUP BY p.cedula
                   HAVING COALESCE(SUM(cu.capital_pendiente), 0) = 0 
                      AND COALESCE(SUM(cu.interes_pendiente), 0) = 0
                      AND COUNT(cu.id) > 0
               )
               AND NOT EXISTS (
                   SELECT 1 FROM prestamos p 
                   INNER JOIN cuotas cu ON p.id = cu.prestamo_id
                   WHERE p.cedula = c.cedula 
                   AND p.estado = 'APROBADO'
                   AND (cu.capital_pendiente > 0 OR cu.interes_pendiente > 0)
               ) THEN 1 END) AS correctos_finalizados,
    COUNT(CASE WHEN activo = FALSE 
               AND EXISTS (
                   SELECT 1 FROM prestamos p 
                   INNER JOIN cuotas cu ON p.id = cu.prestamo_id
                   WHERE p.cedula = c.cedula 
                   AND p.estado = 'APROBADO'
                   AND (cu.capital_pendiente > 0 OR cu.interes_pendiente > 0)
               ) THEN 1 END) AS anomalias_restantes
FROM clientes c;

-- ======================================================================
-- RESUMEN:
-- ======================================================================
-- Este script corrige masivamente el campo 'activo' según la regla:
-- 
-- activo = TRUE: Mientras tenga cuotas pendientes (capital_pendiente > 0 o interes_pendiente > 0)
-- activo = FALSE: Cuando terminó de pagar TODAS las cuotas (capital_pendiente = 0 e interes_pendiente = 0)
-- ======================================================================
-- IMPORTANTE: Hacer backup antes de ejecutar
-- ======================================================================
