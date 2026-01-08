-- ======================================================================
-- CORRECCION MASIVA: activo según regla de negocio correcta
-- ======================================================================
-- Regla: activo = TRUE cuando se inicia proceso de análisis
--        activo = FALSE cuando cliente terminó de pagar (préstamo finalizado)
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
                             WHERE p.cedula = c.cedula 
                             AND p.estado != 'FINALIZADO'
                         ) THEN c.id END) AS anomalia_1,
    COUNT(DISTINCT CASE WHEN c.activo = TRUE 
                         AND NOT EXISTS (
                             SELECT 1 FROM prestamos p 
                             WHERE p.cedula = c.cedula 
                             AND p.estado != 'FINALIZADO'
                         )
                         AND EXISTS (
                             SELECT 1 FROM prestamos p 
                             WHERE p.cedula = c.cedula 
                             AND p.estado = 'FINALIZADO'
                         ) THEN c.id END) AS anomalia_2
FROM clientes c;

-- ======================================================================
-- 2. CORREGIR: activo = TRUE para clientes con préstamos activos
-- ======================================================================
-- Clientes que tienen préstamos en cualquier estado excepto FINALIZADO
-- ======================================================================

UPDATE clientes 
SET activo = TRUE,
    estado = CASE 
        WHEN estado = 'INACTIVO' THEN 'ACTIVO'
        ELSE estado
    END,
    fecha_actualizacion = CURRENT_TIMESTAMP
WHERE activo = FALSE
  AND EXISTS (
      SELECT 1 
      FROM prestamos p 
      WHERE p.cedula = clientes.cedula 
      AND p.estado != 'FINALIZADO'
  );

-- ======================================================================
-- 3. CORREGIR: activo = FALSE para clientes que terminaron de pagar
-- ======================================================================
-- Clientes que solo tienen préstamos FINALIZADOS (sin préstamos activos)
-- ======================================================================

UPDATE clientes 
SET activo = FALSE,
    estado = 'FINALIZADO',
    fecha_actualizacion = CURRENT_TIMESTAMP
WHERE activo = TRUE
  AND NOT EXISTS (
      SELECT 1 
      FROM prestamos p 
      WHERE p.cedula = clientes.cedula 
      AND p.estado != 'FINALIZADO'
  )
  AND EXISTS (
      SELECT 1 
      FROM prestamos p 
      WHERE p.cedula = clientes.cedula 
      AND p.estado = 'FINALIZADO'
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
                             WHERE p.cedula = c.cedula 
                             AND p.estado != 'FINALIZADO'
                         ) THEN c.id END) AS anomalia_1_restante,
    COUNT(DISTINCT CASE WHEN c.activo = TRUE 
                         AND NOT EXISTS (
                             SELECT 1 FROM prestamos p 
                             WHERE p.cedula = c.cedula 
                             AND p.estado != 'FINALIZADO'
                         )
                         AND EXISTS (
                             SELECT 1 FROM prestamos p 
                             WHERE p.cedula = c.cedula 
                             AND p.estado = 'FINALIZADO'
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
                   WHERE p.cedula = c.cedula 
                   AND p.estado != 'FINALIZADO'
               ) THEN 1 END) AS correctos_activos,
    COUNT(CASE WHEN activo = FALSE 
               AND NOT EXISTS (
                   SELECT 1 FROM prestamos p 
                   WHERE p.cedula = c.cedula 
                   AND p.estado != 'FINALIZADO'
               )
               AND EXISTS (
                   SELECT 1 FROM prestamos p 
                   WHERE p.cedula = c.cedula 
                   AND p.estado = 'FINALIZADO'
               ) THEN 1 END) AS correctos_inactivos,
    COUNT(CASE WHEN activo = FALSE 
               AND EXISTS (
                   SELECT 1 FROM prestamos p 
                   WHERE p.cedula = c.cedula 
                   AND p.estado != 'FINALIZADO'
               ) THEN 1 END) AS anomalias_restantes
FROM clientes c;

-- ======================================================================
-- RESUMEN:
-- ======================================================================
-- Este script corrige masivamente el campo 'activo' según la regla:
-- 
-- activo = TRUE: Cliente con proceso de préstamo iniciado (tiene préstamos activos)
-- activo = FALSE: Cliente que terminó de pagar (solo tiene préstamos finalizados)
-- ======================================================================
-- IMPORTANTE: Hacer backup antes de ejecutar
-- ======================================================================
