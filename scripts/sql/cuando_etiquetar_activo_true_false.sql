-- ======================================================================
-- CUANDO ETIQUETAR activo = TRUE O activo = FALSE
-- ======================================================================
-- Criterios específicos para marcar el campo 'activo' en clientes
-- ======================================================================

-- ======================================================================
-- CRITERIO PARA activo = TRUE
-- ======================================================================
-- Se marca activo = TRUE cuando se cumple TODAS estas condiciones:
-- 1. El cliente tiene AL MENOS UN préstamo con estado = 'APROBADO'
-- 2. Ese préstamo aprobado tiene cuotas generadas
-- 3. Existe AL MENOS UNA cuota con saldo pendiente (capital_pendiente > 0 O interes_pendiente > 0)
-- 
-- IMPORTANTE: No importa si el cliente ha pagado algo o no,
-- lo importante es que tenga saldo pendiente en alguna cuota
-- ======================================================================

-- Query para identificar clientes que DEBEN tener activo = TRUE
SELECT 
    'MARCAR activo = TRUE' AS accion,
    c.id AS cliente_id,
    c.cedula,
    c.nombres,
    c.estado AS estado_actual,
    c.activo AS activo_actual,
    COUNT(DISTINCT p.id) AS prestamos_aprobados,
    COUNT(DISTINCT cu.id) AS cuotas_con_saldo_pendiente,
    COALESCE(SUM(cu.capital_pendiente), 0) AS capital_pendiente_total,
    COALESCE(SUM(cu.interes_pendiente), 0) AS interes_pendiente_total,
    CASE 
        WHEN c.activo = TRUE AND c.estado = 'ACTIVO' THEN 'YA ESTA CORRECTO'
        WHEN c.activo = FALSE THEN 'DEBE CAMBIARSE A TRUE'
        WHEN c.estado != 'ACTIVO' THEN 'DEBE CAMBIARSE estado A ACTIVO'
        ELSE 'REVISAR'
    END AS accion_requerida
FROM clientes c
INNER JOIN prestamos p ON c.cedula = p.cedula
INNER JOIN cuotas cu ON p.id = cu.prestamo_id
WHERE p.estado = 'APROBADO'
  AND (cu.capital_pendiente > 0 OR cu.interes_pendiente > 0)
GROUP BY c.id, c.cedula, c.nombres, c.estado, c.activo
ORDER BY accion_requerida, c.cedula
LIMIT 30;

-- ======================================================================
-- CRITERIO PARA activo = FALSE - CASO 1: INACTIVO (PASIVO)
-- ======================================================================
-- Se marca activo = FALSE cuando se cumple TODAS estas condiciones:
-- 1. El cliente NO tiene préstamos con estado = 'APROBADO'
-- 2. El cliente nunca concretó una opción de préstamo
-- 3. El estado debe ser 'INACTIVO'
-- 
-- IMPORTANTE: Cliente pasivo = consultó pero no aprobó préstamo
-- ======================================================================

-- Query para identificar clientes que DEBEN tener activo = FALSE (INACTIVOS)
SELECT 
    'MARCAR activo = FALSE (INACTIVO)' AS accion,
    c.id AS cliente_id,
    c.cedula,
    c.nombres,
    c.estado AS estado_actual,
    c.activo AS activo_actual,
    COUNT(p.id) AS prestamos_aprobados,
    CASE 
        WHEN c.activo = FALSE 
             AND c.estado = 'INACTIVO' 
             AND COUNT(p.id) = 0 
        THEN 'YA ESTA CORRECTO'
        WHEN COUNT(p.id) > 0 
        THEN 'ERROR: Tiene prestamos aprobados, debe estar ACTIVO'
        WHEN c.activo = TRUE 
        THEN 'DEBE CAMBIARSE A FALSE'
        WHEN c.estado != 'INACTIVO' 
        THEN 'DEBE CAMBIARSE estado A INACTIVO'
        ELSE 'REVISAR'
    END AS accion_requerida
FROM clientes c
LEFT JOIN prestamos p ON c.cedula = p.cedula AND p.estado = 'APROBADO'
WHERE c.estado = 'INACTIVO'
GROUP BY c.id, c.cedula, c.nombres, c.estado, c.activo
ORDER BY accion_requerida, COUNT(p.id) DESC
LIMIT 30;

-- ======================================================================
-- CRITERIO PARA activo = FALSE - CASO 2: FINALIZADO
-- ======================================================================
-- Se marca activo = FALSE cuando se cumple TODAS estas condiciones:
-- 1. El cliente tiene préstamos con estado = 'APROBADO'
-- 2. TODAS las cuotas de TODOS los préstamos tienen saldo pendiente = 0
--    (capital_pendiente = 0 AND interes_pendiente = 0)
-- 3. El cliente tiene AL MENOS UN pago registrado (total_pagado > 0)
-- 4. El estado debe ser 'FINALIZADO'
-- 
-- IMPORTANTE: Cliente completó su ciclo = pagó todo su préstamo
-- ======================================================================

-- Query para identificar clientes que DEBEN tener activo = FALSE (FINALIZADOS)
SELECT 
    'MARCAR activo = FALSE (FINALIZADO)' AS accion,
    c.id AS cliente_id,
    c.cedula,
    c.nombres,
    c.estado AS estado_actual,
    c.activo AS activo_actual,
    COUNT(DISTINCT p.id) AS prestamos_aprobados,
    COALESCE(SUM(cu.capital_pendiente), 0) AS capital_pendiente_total,
    COALESCE(SUM(cu.interes_pendiente), 0) AS interes_pendiente_total,
    COALESCE(SUM(cu.total_pagado), 0) AS total_pagado,
    CASE 
        WHEN c.activo = FALSE 
             AND c.estado = 'FINALIZADO' 
             AND COALESCE(SUM(cu.capital_pendiente), 0) = 0 
             AND COALESCE(SUM(cu.interes_pendiente), 0) = 0
             AND COALESCE(SUM(cu.total_pagado), 0) > 0
        THEN 'YA ESTA CORRECTO'
        WHEN COALESCE(SUM(cu.capital_pendiente), 0) > 0 
             OR COALESCE(SUM(cu.interes_pendiente), 0) > 0
        THEN 'ERROR: Tiene saldo pendiente, debe estar ACTIVO'
        WHEN c.activo = TRUE 
        THEN 'DEBE CAMBIARSE A FALSE'
        WHEN c.estado != 'FINALIZADO' 
        THEN 'DEBE CAMBIARSE estado A FINALIZADO'
        ELSE 'REVISAR'
    END AS accion_requerida
FROM clientes c
INNER JOIN prestamos p ON c.cedula = p.cedula
LEFT JOIN cuotas cu ON p.id = cu.prestamo_id
WHERE p.estado = 'APROBADO'
GROUP BY c.id, c.cedula, c.nombres, c.estado, c.activo
HAVING COALESCE(SUM(cu.capital_pendiente), 0) = 0 
    AND COALESCE(SUM(cu.interes_pendiente), 0) = 0
    AND COALESCE(SUM(cu.total_pagado), 0) > 0
ORDER BY accion_requerida, c.cedula
LIMIT 30;

-- ======================================================================
-- ALGORITMO DE DECISION: PASO A PASO
-- ======================================================================

SELECT 
    'PASO 1' AS paso,
    '¿Tiene préstamos con estado = APROBADO?' AS pregunta,
    'SI' AS respuesta_si,
    'NO' AS respuesta_no,
    'Ir a PASO 2' AS siguiente_si,
    'MARCAR: activo = FALSE, estado = INACTIVO' AS siguiente_no
UNION ALL
SELECT 
    'PASO 2',
    '¿Tiene cuotas con saldo pendiente? (capital_pendiente > 0 OR interes_pendiente > 0)',
    'SI',
    'NO',
    'MARCAR: activo = TRUE, estado = ACTIVO',
    'Ir a PASO 3'
UNION ALL
SELECT 
    'PASO 3',
    '¿Tiene pagos registrados? (total_pagado > 0)',
    'SI',
    'NO',
    'MARCAR: activo = FALSE, estado = FINALIZADO',
    'MARCAR: activo = TRUE, estado = ACTIVO (préstamo aprobado pero sin pagos aún)';

-- ======================================================================
-- EJEMPLOS CONCRETOS
-- ======================================================================

-- Ejemplo 1: Cliente con préstamo aprobado y saldo pendiente
SELECT 
    'EJEMPLO 1' AS ejemplo,
    'Cliente: Juan Pérez' AS descripcion,
    'Préstamo: $1,000 aprobado' AS detalle_1,
    'Cuotas: 12 cuotas generadas' AS detalle_2,
    'Saldo pendiente: $500 (capital_pendiente)' AS detalle_3,
    'DECISION: activo = TRUE, estado = ACTIVO' AS decision
UNION ALL

-- Ejemplo 2: Cliente que pagó todo
SELECT 
    'EJEMPLO 2',
    'Cliente: María González',
    'Préstamo: $2,000 aprobado',
    'Cuotas: 24 cuotas generadas',
    'Saldo pendiente: $0.00, Total pagado: $2,000',
    'DECISION: activo = FALSE, estado = FINALIZADO'
UNION ALL

-- Ejemplo 3: Cliente pasivo
SELECT 
    'EJEMPLO 3',
    'Cliente: Pedro Sánchez',
    'Préstamos aprobados: 0',
    'Estado: Consultó pero no aprobó',
    'Nunca concretó préstamo',
    'DECISION: activo = FALSE, estado = INACTIVO'
UNION ALL

-- Ejemplo 4: Cliente con préstamo aprobado pero sin pagos aún
SELECT 
    'EJEMPLO 4',
    'Cliente: Ana López',
    'Préstamo: $500 aprobado',
    'Cuotas: 6 cuotas generadas',
    'Saldo pendiente: $500, Total pagado: $0',
    'DECISION: activo = TRUE, estado = ACTIVO (tiene saldo pendiente)';

-- ======================================================================
-- QUERY PARA APLICAR ETIQUETADO AUTOMATICO
-- ======================================================================
-- Esta query muestra qué clientes necesitan cambio y a qué valor
-- ======================================================================

WITH clasificacion_clientes AS (
    SELECT 
        c.id AS cliente_id,
        c.cedula,
        c.nombres,
        c.estado AS estado_actual,
        c.activo AS activo_actual,
        COUNT(DISTINCT p.id) AS prestamos_aprobados,
        COALESCE(SUM(CASE WHEN cu.capital_pendiente > 0 OR cu.interes_pendiente > 0 THEN 1 ELSE 0 END), 0) AS cuotas_con_saldo,
        COALESCE(SUM(cu.capital_pendiente), 0) AS capital_pendiente,
        COALESCE(SUM(cu.interes_pendiente), 0) AS interes_pendiente,
        COALESCE(SUM(cu.total_pagado), 0) AS total_pagado
    FROM clientes c
    LEFT JOIN prestamos p ON c.cedula = p.cedula AND p.estado = 'APROBADO'
    LEFT JOIN cuotas cu ON p.id = cu.prestamo_id
    GROUP BY c.id, c.cedula, c.nombres, c.estado, c.activo
)
SELECT 
    cliente_id,
    cedula,
    nombres,
    estado_actual,
    activo_actual,
    CASE 
        -- Caso 1: Tiene préstamos aprobados con saldo pendiente
        WHEN prestamos_aprobados > 0 AND (capital_pendiente > 0 OR interes_pendiente > 0)
        THEN 'MARCAR: activo = TRUE, estado = ACTIVO'
        
        -- Caso 2: Tiene préstamos aprobados pero sin saldo pendiente y con pagos
        WHEN prestamos_aprobados > 0 
             AND capital_pendiente = 0 
             AND interes_pendiente = 0 
             AND total_pagado > 0
        THEN 'MARCAR: activo = FALSE, estado = FINALIZADO'
        
        -- Caso 3: No tiene préstamos aprobados
        WHEN prestamos_aprobados = 0
        THEN 'MARCAR: activo = FALSE, estado = INACTIVO'
        
        -- Caso 4: Tiene préstamos pero sin saldo y sin pagos (préstamo recién aprobado)
        WHEN prestamos_aprobados > 0 
             AND capital_pendiente = 0 
             AND interes_pendiente = 0 
             AND total_pagado = 0
        THEN 'MARCAR: activo = TRUE, estado = ACTIVO (préstamo aprobado, cuotas pendientes)'
        
        ELSE 'REVISAR MANUALMENTE'
    END AS etiquetado_requerido,
    prestamos_aprobados,
    capital_pendiente,
    interes_pendiente,
    total_pagado
FROM clasificacion_clientes
WHERE (activo_actual = TRUE AND estado_actual != 'ACTIVO')
   OR (activo_actual = FALSE AND estado_actual = 'ACTIVO')
   OR (activo_actual = FALSE AND prestamos_aprobados > 0 AND (capital_pendiente > 0 OR interes_pendiente > 0))
   OR (activo_actual = TRUE AND prestamos_aprobados = 0)
ORDER BY etiquetado_requerido, cedula
LIMIT 50;

-- ======================================================================
-- RESUMEN: CUANDO ETIQUETAR
-- ======================================================================
-- activo = TRUE: Cliente con préstamo APROBADO que tiene saldo pendiente
-- activo = FALSE: Cliente sin préstamos aprobados (INACTIVO) o que completó pago (FINALIZADO)
-- ======================================================================
