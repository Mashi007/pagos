-- ======================================================================
-- REGLA DE NEGOCIO: activo según pago de cuotas
-- ======================================================================
-- activo = TRUE: Hasta que NO pague la totalidad de cuotas (tiene cuotas pendientes)
-- activo = FALSE / estado = FINALIZADO: Cuando termine el pago de TODAS las cuotas
-- ======================================================================

-- ======================================================================
-- activo = TRUE
-- ======================================================================
-- Se marca activo = TRUE cuando:
-- 1. El cliente tiene préstamos APROBADOS
-- 2. Existe AL MENOS UNA cuota con saldo pendiente
--    (capital_pendiente > 0 OR interes_pendiente > 0)
-- 
-- IMPORTANTE: Mientras tenga cuotas pendientes, está ACTIVO
-- ======================================================================

-- Ver clientes que DEBEN tener activo = TRUE (tienen cuotas pendientes)
SELECT 
    'DEBEN TENER activo = TRUE' AS regla,
    c.id AS cliente_id,
    c.cedula,
    c.nombres,
    c.estado AS estado_cliente,
    c.activo AS activo_actual,
    COUNT(DISTINCT p.id) AS prestamos_aprobados,
    COUNT(DISTINCT cu.id) AS total_cuotas,
    COUNT(DISTINCT CASE WHEN cu.capital_pendiente > 0 OR cu.interes_pendiente > 0 THEN cu.id END) AS cuotas_pendientes,
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
-- activo = FALSE / estado = FINALIZADO
-- ======================================================================
-- Se marca activo = FALSE cuando:
-- 1. El cliente tiene préstamos APROBADOS
-- 2. TODAS las cuotas están completamente pagadas
--    (capital_pendiente = 0 AND interes_pendiente = 0 para TODAS las cuotas)
-- 3. El estado debe ser 'FINALIZADO'
-- 
-- IMPORTANTE: Solo cuando terminó el pago de TODAS las cuotas
-- ======================================================================

-- Ver clientes que DEBEN tener activo = FALSE (todas las cuotas pagadas)
SELECT 
    'DEBEN TENER activo = FALSE (FINALIZADO)' AS regla,
    c.id AS cliente_id,
    c.cedula,
    c.nombres,
    c.estado AS estado_cliente,
    c.activo AS activo_actual,
    COUNT(DISTINCT p.id) AS prestamos_aprobados,
    COUNT(DISTINCT cu.id) AS total_cuotas,
    COUNT(DISTINCT CASE WHEN cu.capital_pendiente = 0 AND cu.interes_pendiente = 0 THEN cu.id END) AS cuotas_pagadas,
    COALESCE(SUM(cu.capital_pendiente), 0) AS capital_pendiente_total,
    COALESCE(SUM(cu.interes_pendiente), 0) AS interes_pendiente_total,
    COALESCE(SUM(cu.total_pagado), 0) AS total_pagado,
    CASE 
        WHEN c.activo = FALSE 
             AND c.estado = 'FINALIZADO' 
             AND COALESCE(SUM(cu.capital_pendiente), 0) = 0 
             AND COALESCE(SUM(cu.interes_pendiente), 0) = 0
             AND COUNT(DISTINCT cu.id) > 0
        THEN 'YA ESTA CORRECTO'
        WHEN COALESCE(SUM(cu.capital_pendiente), 0) > 0 
             OR COALESCE(SUM(cu.interes_pendiente), 0) > 0
        THEN 'ERROR: Tiene cuotas pendientes, debe estar ACTIVO'
        WHEN c.activo = TRUE 
        THEN 'DEBE CAMBIARSE A FALSE'
        WHEN c.estado != 'FINALIZADO' 
        THEN 'DEBE CAMBIARSE estado A FINALIZADO'
        ELSE 'REVISAR'
    END AS accion_requerida
FROM clientes c
INNER JOIN prestamos p ON c.cedula = p.cedula
INNER JOIN cuotas cu ON p.id = cu.prestamo_id
WHERE p.estado = 'APROBADO'
GROUP BY c.id, c.cedula, c.nombres, c.estado, c.activo
HAVING COALESCE(SUM(cu.capital_pendiente), 0) = 0 
    AND COALESCE(SUM(cu.interes_pendiente), 0) = 0
    AND COUNT(DISTINCT cu.id) > 0
ORDER BY accion_requerida, c.cedula
LIMIT 30;

-- ======================================================================
-- FLUJO DEL PROCESO
-- ======================================================================

SELECT 
    'ETAPA 1' AS etapa,
    'Se inicia proceso de análisis de préstamo' AS descripcion,
    'activo = TRUE' AS activo,
    'estado = ACTIVO' AS estado,
    'Cliente en evaluación o aprobado' AS detalle
UNION ALL
SELECT 
    'ETAPA 2',
    'Préstamo aprobado, cuotas generadas',
    'activo = TRUE',
    'estado = ACTIVO',
    'Cliente tiene cuotas pendientes'
UNION ALL
SELECT 
    'ETAPA 3',
    'Cliente pagando cuotas',
    'activo = TRUE',
    'estado = ACTIVO',
    'Aún tiene cuotas con saldo pendiente'
UNION ALL
SELECT 
    'ETAPA 4',
    'Cliente terminó de pagar TODAS las cuotas',
    'activo = FALSE',
    'estado = FINALIZADO',
    'Todas las cuotas: capital_pendiente = 0 e interes_pendiente = 0';

-- ======================================================================
-- CASOS ANOMALOS: DETECTAR INCONSISTENCIAS
-- ======================================================================

-- Caso 1: activo = FALSE pero tiene cuotas pendientes
SELECT 
    'ANOMALIA 1' AS tipo_anomalia,
    'activo = FALSE pero tiene cuotas pendientes' AS descripcion,
    COUNT(DISTINCT c.id) AS total_casos
FROM clientes c
INNER JOIN prestamos p ON c.cedula = p.cedula
INNER JOIN cuotas cu ON p.id = cu.prestamo_id
WHERE c.activo = FALSE
  AND p.estado = 'APROBADO'
  AND (cu.capital_pendiente > 0 OR cu.interes_pendiente > 0)

UNION ALL

-- Caso 2: activo = TRUE pero todas las cuotas están pagadas
SELECT 
    'ANOMALIA 2' AS tipo_anomalia,
    'activo = TRUE pero todas las cuotas estan pagadas' AS descripcion,
    COUNT(DISTINCT c.id) AS total_casos
FROM clientes c
INNER JOIN prestamos p ON c.cedula = p.cedula
INNER JOIN cuotas cu ON p.id = cu.prestamo_id
WHERE c.activo = TRUE
  AND p.estado = 'APROBADO'
GROUP BY c.id
HAVING COALESCE(SUM(cu.capital_pendiente), 0) = 0 
    AND COALESCE(SUM(cu.interes_pendiente), 0) = 0
    AND COUNT(DISTINCT cu.id) > 0;

-- ======================================================================
-- QUERY PARA IDENTIFICAR CLIENTES QUE NECESITAN CORRECCION
-- ======================================================================

WITH estado_cuotas AS (
    SELECT 
        c.id AS cliente_id,
        c.cedula,
        c.nombres,
        c.estado AS estado_cliente,
        c.activo AS activo_actual,
        COUNT(DISTINCT p.id) AS prestamos_aprobados,
        COUNT(DISTINCT cu.id) AS total_cuotas,
        COUNT(DISTINCT CASE WHEN cu.capital_pendiente > 0 OR cu.interes_pendiente > 0 THEN cu.id END) AS cuotas_pendientes,
        COALESCE(SUM(cu.capital_pendiente), 0) AS capital_pendiente_total,
        COALESCE(SUM(cu.interes_pendiente), 0) AS interes_pendiente_total,
        COALESCE(SUM(cu.total_pagado), 0) AS total_pagado
    FROM clientes c
    INNER JOIN prestamos p ON c.cedula = p.cedula
    LEFT JOIN cuotas cu ON p.id = cu.prestamo_id
    WHERE p.estado = 'APROBADO'
    GROUP BY c.id, c.cedula, c.nombres, c.estado, c.activo
)
SELECT 
    cliente_id,
    cedula,
    nombres,
    estado_cliente,
    activo_actual,
    prestamos_aprobados,
    total_cuotas,
    cuotas_pendientes,
    capital_pendiente_total,
    interes_pendiente_total,
    total_pagado,
    CASE 
        -- Caso 1: Tiene cuotas pendientes pero activo = FALSE
        WHEN cuotas_pendientes > 0 AND activo_actual = FALSE
        THEN 'CORREGIR: activo = TRUE (tiene cuotas pendientes)'
        
        -- Caso 2: Todas las cuotas pagadas pero activo = TRUE
        WHEN cuotas_pendientes = 0 
             AND total_cuotas > 0 
             AND activo_actual = TRUE
        THEN 'CORREGIR: activo = FALSE, estado = FINALIZADO (todas las cuotas pagadas)'
        
        -- Caso 3: Sin cuotas generadas
        WHEN total_cuotas = 0
        THEN 'REVISAR: Cliente sin cuotas generadas'
        
        ELSE 'OK'
    END AS accion_requerida
FROM estado_cuotas
WHERE (cuotas_pendientes > 0 AND activo_actual = FALSE)
   OR (cuotas_pendientes = 0 AND total_cuotas > 0 AND activo_actual = TRUE)
ORDER BY accion_requerida, cedula
LIMIT 50;

-- ======================================================================
-- RESUMEN: REGLA DE NEGOCIO
-- ======================================================================
-- activo = TRUE: Mientras tenga cuotas pendientes (capital_pendiente > 0 o interes_pendiente > 0)
-- activo = FALSE: Cuando terminó de pagar TODAS las cuotas (capital_pendiente = 0 e interes_pendiente = 0)
-- ======================================================================
