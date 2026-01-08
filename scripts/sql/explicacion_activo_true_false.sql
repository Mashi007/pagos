-- ======================================================================
-- EXPLICACION: CUANDO ES activo = TRUE Y CUANDO ES activo = FALSE
-- ======================================================================
-- Regla de negocio para el campo 'activo' en la tabla clientes
-- ======================================================================

-- ======================================================================
-- activo = TRUE
-- ======================================================================
-- Se aplica cuando:
-- 1. El cliente tiene préstamos APROBADOS (vigentes)
-- 2. El cliente tiene saldo pendiente (capital_pendiente > 0 o interes_pendiente > 0)
-- 3. El estado debe ser 'ACTIVO'
-- 
-- Ejemplo: Cliente con préstamo aprobado de $1,000 y aún debe $500
-- ======================================================================

-- Ver clientes que DEBEN tener activo = TRUE
SELECT 
    'DEBEN TENER activo = TRUE' AS regla,
    c.id AS cliente_id,
    c.cedula,
    c.nombres,
    c.estado AS estado_actual,
    c.activo AS activo_actual,
    COUNT(p.id) AS prestamos_aprobados,
    COALESCE(SUM(cu.capital_pendiente), 0) AS capital_pendiente,
    COALESCE(SUM(cu.interes_pendiente), 0) AS interes_pendiente,
    CASE 
        WHEN c.activo = TRUE AND c.estado = 'ACTIVO' THEN 'CORRECTO'
        ELSE 'DEBE CORREGIRSE'
    END AS estado_correccion
FROM clientes c
INNER JOIN prestamos p ON c.cedula = p.cedula
LEFT JOIN cuotas cu ON p.id = cu.prestamo_id
WHERE p.estado = 'APROBADO'
GROUP BY c.id, c.cedula, c.nombres, c.estado, c.activo
HAVING COALESCE(SUM(cu.capital_pendiente), 0) > 0 
    OR COALESCE(SUM(cu.interes_pendiente), 0) > 0
ORDER BY estado_correccion, c.cedula
LIMIT 20;

-- ======================================================================
-- activo = FALSE
-- ======================================================================
-- Se aplica cuando:
-- 1. El cliente NO tiene préstamos aprobados (pasivo)
-- 2. El cliente completó su ciclo (sin saldo pendiente)
-- 3. El estado puede ser 'INACTIVO' o 'FINALIZADO'
-- 
-- Ejemplo 1: Cliente que nunca concretó préstamo → estado = 'INACTIVO', activo = FALSE
-- Ejemplo 2: Cliente que pagó todo su préstamo → estado = 'FINALIZADO', activo = FALSE
-- ======================================================================

-- Ver clientes que DEBEN tener activo = FALSE (INACTIVOS - pasivos)
SELECT 
    'DEBEN TENER activo = FALSE (INACTIVOS)' AS regla,
    c.id AS cliente_id,
    c.cedula,
    c.nombres,
    c.estado AS estado_actual,
    c.activo AS activo_actual,
    COUNT(p.id) AS prestamos_aprobados,
    CASE 
        WHEN c.activo = FALSE AND c.estado = 'INACTIVO' AND COUNT(p.id) = 0 THEN 'CORRECTO'
        WHEN c.activo = FALSE AND c.estado = 'INACTIVO' AND COUNT(p.id) > 0 THEN 'ERROR: Tiene prestamos aprobados'
        ELSE 'REVISAR'
    END AS estado_correccion
FROM clientes c
LEFT JOIN prestamos p ON c.cedula = p.cedula AND p.estado = 'APROBADO'
WHERE c.estado = 'INACTIVO'
GROUP BY c.id, c.cedula, c.nombres, c.estado, c.activo
ORDER BY estado_correccion, COUNT(p.id) DESC
LIMIT 20;

-- Ver clientes que DEBEN tener activo = FALSE (FINALIZADOS - sin saldo)
SELECT 
    'DEBEN TENER activo = FALSE (FINALIZADOS)' AS regla,
    c.id AS cliente_id,
    c.cedula,
    c.nombres,
    c.estado AS estado_actual,
    c.activo AS activo_actual,
    COUNT(p.id) AS prestamos_aprobados,
    COALESCE(SUM(cu.capital_pendiente), 0) AS capital_pendiente,
    COALESCE(SUM(cu.interes_pendiente), 0) AS interes_pendiente,
    COALESCE(SUM(cu.total_pagado), 0) AS total_pagado,
    CASE 
        WHEN c.activo = FALSE 
             AND c.estado = 'FINALIZADO' 
             AND COALESCE(SUM(cu.capital_pendiente), 0) = 0 
             AND COALESCE(SUM(cu.interes_pendiente), 0) = 0
             AND COALESCE(SUM(cu.total_pagado), 0) > 0
        THEN 'CORRECTO'
        WHEN c.activo = FALSE 
             AND c.estado = 'FINALIZADO' 
             AND (COALESCE(SUM(cu.capital_pendiente), 0) > 0 
                  OR COALESCE(SUM(cu.interes_pendiente), 0) > 0)
        THEN 'ERROR: Tiene saldo pendiente, debe estar ACTIVO'
        ELSE 'REVISAR'
    END AS estado_correccion
FROM clientes c
INNER JOIN prestamos p ON c.cedula = p.cedula
LEFT JOIN cuotas cu ON p.id = cu.prestamo_id
WHERE c.estado = 'FINALIZADO'
  AND p.estado = 'APROBADO'
GROUP BY c.id, c.cedula, c.nombres, c.estado, c.activo
ORDER BY estado_correccion, capital_pendiente DESC
LIMIT 20;

-- ======================================================================
-- RESUMEN: REGLAS DE NEGOCIO
-- ======================================================================

SELECT 
    'RESUMEN DE REGLAS' AS tipo,
    'activo = TRUE' AS condicion,
    'Cliente con préstamo APROBADO y saldo pendiente' AS cuando_se_aplica,
    'estado = ACTIVO' AS estado_correspondiente
UNION ALL
SELECT 
    'RESUMEN DE REGLAS',
    'activo = FALSE',
    'Cliente INACTIVO (pasivo) - sin préstamos aprobados',
    'estado = INACTIVO'
UNION ALL
SELECT 
    'RESUMEN DE REGLAS',
    'activo = FALSE',
    'Cliente FINALIZADO - completó préstamo (sin saldo pendiente)',
    'estado = FINALIZADO';

-- ======================================================================
-- CASOS ANOMALOS: DETECTAR INCONSISTENCIAS
-- ======================================================================

-- Caso 1: activo = TRUE pero estado != 'ACTIVO'
SELECT 
    'ANOMALIA 1' AS tipo_anomalia,
    'activo = TRUE pero estado != ACTIVO' AS descripcion,
    COUNT(*) AS total_casos
FROM clientes
WHERE activo = TRUE
  AND estado != 'ACTIVO'

UNION ALL

-- Caso 2: activo = FALSE pero tiene préstamos aprobados con saldo pendiente
SELECT 
    'ANOMALIA 2' AS tipo_anomalia,
    'activo = FALSE pero tiene saldo pendiente' AS descripcion,
    COUNT(DISTINCT c.id) AS total_casos
FROM clientes c
INNER JOIN prestamos p ON c.cedula = p.cedula
LEFT JOIN cuotas cu ON p.id = cu.prestamo_id
WHERE c.activo = FALSE
  AND p.estado = 'APROBADO'
GROUP BY c.id
HAVING COALESCE(SUM(cu.capital_pendiente), 0) > 0 
    OR COALESCE(SUM(cu.interes_pendiente), 0) > 0

UNION ALL

-- Caso 3: estado = 'INACTIVO' pero tiene préstamos aprobados
SELECT 
    'ANOMALIA 3' AS tipo_anomalia,
    'estado = INACTIVO pero tiene préstamos aprobados' AS descripcion,
    COUNT(DISTINCT c.id) AS total_casos
FROM clientes c
INNER JOIN prestamos p ON c.cedula = p.cedula
WHERE c.estado = 'INACTIVO'
  AND p.estado = 'APROBADO'

UNION ALL

-- Caso 4: estado = 'ACTIVO' pero activo = FALSE
SELECT 
    'ANOMALIA 4' AS tipo_anomalia,
    'estado = ACTIVO pero activo = FALSE' AS descripcion,
    COUNT(*) AS total_casos
FROM clientes
WHERE estado = 'ACTIVO'
  AND activo = FALSE;

-- ======================================================================
-- TABLA DE DECISION
-- ======================================================================

SELECT 
    'Tiene préstamo APROBADO?' AS condicion_1,
    'Tiene saldo pendiente?' AS condicion_2,
    'activo' AS campo_activo,
    'estado' AS campo_estado,
    'Ejemplo' AS ejemplo
UNION ALL
SELECT 'SI', 'SI', 'TRUE', 'ACTIVO', 'Cliente con préstamo vigente, debe $500'
UNION ALL
SELECT 'SI', 'NO (pero tiene pagos)', 'FALSE', 'FINALIZADO', 'Cliente pagó todo, completó ciclo'
UNION ALL
SELECT 'NO', 'NO', 'FALSE', 'INACTIVO', 'Cliente pasivo, nunca concretó préstamo'
UNION ALL
SELECT 'SI', 'NO (sin pagos)', 'TRUE', 'ACTIVO', 'Cliente con préstamo aprobado pero sin pagos aún';

-- ======================================================================
-- NOTAS IMPORTANTES:
-- ======================================================================
-- 1. activo = TRUE → Cliente tiene préstamo vigente (con saldo pendiente)
-- 2. activo = FALSE → Cliente pasivo o finalizado (sin préstamos vigentes)
-- 3. estado = 'ACTIVO' → DEBE coincidir con activo = TRUE
-- 4. estado = 'INACTIVO' → Cliente pasivo, NO debe tener préstamos aprobados
-- 5. estado = 'FINALIZADO' → Cliente completó ciclo, NO debe tener saldo pendiente
-- ======================================================================
