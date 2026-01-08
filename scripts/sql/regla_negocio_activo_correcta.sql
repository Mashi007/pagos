-- ======================================================================
-- REGLA DE NEGOCIO CORRECTA: activo = TRUE / activo = FALSE
-- ======================================================================
-- Actualizado según aclaración del usuario
-- ======================================================================

-- ======================================================================
-- activo = TRUE
-- ======================================================================
-- Se marca activo = TRUE cuando:
-- 1. Se le INICIA un proceso de análisis de préstamo al cliente
-- 2. El cliente está en evaluación, aprobación, o tiene préstamo vigente
-- 3. El cliente NO ha terminado de pagar completamente
-- 
-- IMPORTANTE: Se activa al INICIAR el proceso, no solo cuando tiene saldo pendiente
-- ======================================================================

-- Ver clientes que DEBEN tener activo = TRUE
-- (Clientes con préstamos en cualquier estado excepto FINALIZADO)
SELECT 
    'DEBEN TENER activo = TRUE' AS regla,
    c.id AS cliente_id,
    c.cedula,
    c.nombres,
    c.estado AS estado_cliente,
    c.activo AS activo_actual,
    COUNT(DISTINCT p.id) AS total_prestamos,
    COUNT(DISTINCT CASE WHEN p.estado = 'APROBADO' THEN p.id END) AS prestamos_aprobados,
    COUNT(DISTINCT CASE WHEN p.estado = 'FINALIZADO' THEN p.id END) AS prestamos_finalizados,
    CASE 
        WHEN c.activo = TRUE THEN 'YA ESTA CORRECTO'
        ELSE 'DEBE CAMBIARSE A TRUE'
    END AS accion_requerida
FROM clientes c
INNER JOIN prestamos p ON c.cedula = p.cedula
WHERE p.estado != 'FINALIZADO'  -- Cualquier estado excepto FINALIZADO
GROUP BY c.id, c.cedula, c.nombres, c.estado, c.activo
HAVING COUNT(DISTINCT CASE WHEN p.estado = 'FINALIZADO' THEN p.id END) = 0
   OR (COUNT(DISTINCT CASE WHEN p.estado != 'FINALIZADO' THEN p.id END) > 0)
ORDER BY accion_requerida, c.cedula
LIMIT 30;

-- ======================================================================
-- activo = FALSE
-- ======================================================================
-- Se marca activo = FALSE cuando:
-- 1. El cliente TERMINÓ DE PAGAR completamente su préstamo
-- 2. El préstamo se pone en estado 'FINALIZADO'
-- 3. El estado del cliente se pone FALSE (activo = FALSE)
-- 
-- IMPORTANTE: Solo cuando el préstamo está completamente pagado y finalizado
-- ======================================================================

-- Ver clientes que DEBEN tener activo = FALSE
-- (Clientes con préstamos FINALIZADOS y sin préstamos activos)
SELECT 
    'DEBEN TENER activo = FALSE' AS regla,
    c.id AS cliente_id,
    c.cedula,
    c.nombres,
    c.estado AS estado_cliente,
    c.activo AS activo_actual,
    COUNT(DISTINCT CASE WHEN p.estado = 'FINALIZADO' THEN p.id END) AS prestamos_finalizados,
    COUNT(DISTINCT CASE WHEN p.estado != 'FINALIZADO' THEN p.id END) AS prestamos_activos,
    COALESCE(SUM(CASE WHEN p.estado = 'FINALIZADO' THEN cu.total_pagado ELSE 0 END), 0) AS total_pagado,
    CASE 
        WHEN c.activo = FALSE 
             AND COUNT(DISTINCT CASE WHEN p.estado != 'FINALIZADO' THEN p.id END) = 0
             AND COUNT(DISTINCT CASE WHEN p.estado = 'FINALIZADO' THEN p.id END) > 0
        THEN 'YA ESTA CORRECTO'
        WHEN COUNT(DISTINCT CASE WHEN p.estado != 'FINALIZADO' THEN p.id END) > 0
        THEN 'ERROR: Tiene prestamos activos, debe estar TRUE'
        WHEN c.activo = TRUE 
        THEN 'DEBE CAMBIARSE A FALSE'
        ELSE 'REVISAR'
    END AS accion_requerida
FROM clientes c
INNER JOIN prestamos p ON c.cedula = p.cedula
LEFT JOIN cuotas cu ON p.id = cu.prestamo_id
WHERE p.estado = 'FINALIZADO'
GROUP BY c.id, c.cedula, c.nombres, c.estado, c.activo
HAVING COUNT(DISTINCT CASE WHEN p.estado != 'FINALIZADO' THEN p.id END) = 0
ORDER BY accion_requerida, c.cedula
LIMIT 30;

-- ======================================================================
-- FLUJO DEL PROCESO
-- ======================================================================

SELECT 
    'ETAPA 1' AS etapa,
    'Cliente consulta préstamo' AS descripcion,
    'activo = FALSE' AS activo_inicial,
    'estado = INACTIVO' AS estado_inicial
UNION ALL
SELECT 
    'ETAPA 2',
    'Se INICIA proceso de análisis de préstamo',
    'activo = TRUE',
    'estado = ACTIVO (o en evaluación)'
UNION ALL
SELECT 
    'ETAPA 3',
    'Préstamo aprobado, cliente pagando',
    'activo = TRUE',
    'estado = ACTIVO'
UNION ALL
SELECT 
    'ETAPA 4',
    'Cliente TERMINÓ DE PAGAR completamente',
    'activo = FALSE',
    'estado = FINALIZADO';

-- ======================================================================
-- CASOS ANOMALOS: DETECTAR INCONSISTENCIAS
-- ======================================================================

-- Caso 1: activo = FALSE pero tiene préstamos activos (no finalizados)
SELECT 
    'ANOMALIA 1' AS tipo_anomalia,
    'activo = FALSE pero tiene prestamos activos' AS descripcion,
    COUNT(DISTINCT c.id) AS total_casos
FROM clientes c
INNER JOIN prestamos p ON c.cedula = p.cedula
WHERE c.activo = FALSE
  AND p.estado != 'FINALIZADO'

UNION ALL

-- Caso 2: activo = TRUE pero todos sus préstamos están finalizados
SELECT 
    'ANOMALIA 2' AS tipo_anomalia,
    'activo = TRUE pero todos los prestamos estan finalizados' AS descripcion,
    COUNT(DISTINCT c.id) AS total_casos
FROM clientes c
INNER JOIN prestamos p ON c.cedula = p.cedula
WHERE c.activo = TRUE
GROUP BY c.id
HAVING COUNT(DISTINCT CASE WHEN p.estado != 'FINALIZADO' THEN p.id END) = 0
   AND COUNT(DISTINCT CASE WHEN p.estado = 'FINALIZADO' THEN p.id END) > 0;

-- ======================================================================
-- QUERY PARA IDENTIFICAR CLIENTES QUE NECESITAN CORRECCION
-- ======================================================================

WITH estado_prestamos AS (
    SELECT 
        c.id AS cliente_id,
        c.cedula,
        c.nombres,
        c.estado AS estado_cliente,
        c.activo AS activo_actual,
        COUNT(DISTINCT CASE WHEN p.estado != 'FINALIZADO' THEN p.id END) AS prestamos_activos,
        COUNT(DISTINCT CASE WHEN p.estado = 'FINALIZADO' THEN p.id END) AS prestamos_finalizados
    FROM clientes c
    LEFT JOIN prestamos p ON c.cedula = p.cedula
    GROUP BY c.id, c.cedula, c.nombres, c.estado, c.activo
)
SELECT 
    cliente_id,
    cedula,
    nombres,
    estado_cliente,
    activo_actual,
    prestamos_activos,
    prestamos_finalizados,
    CASE 
        -- Caso 1: Tiene préstamos activos pero activo = FALSE
        WHEN prestamos_activos > 0 AND activo_actual = FALSE
        THEN 'CORREGIR: activo = TRUE (tiene prestamos activos)'
        
        -- Caso 2: Todos los préstamos finalizados pero activo = TRUE
        WHEN prestamos_activos = 0 
             AND prestamos_finalizados > 0 
             AND activo_actual = TRUE
        THEN 'CORREGIR: activo = FALSE (todos los prestamos finalizados)'
        
        -- Caso 3: Sin préstamos (cliente pasivo)
        WHEN prestamos_activos = 0 AND prestamos_finalizados = 0
        THEN 'REVISAR: Cliente sin prestamos (pasivo)'
        
        ELSE 'OK'
    END AS accion_requerida
FROM estado_prestamos
WHERE (prestamos_activos > 0 AND activo_actual = FALSE)
   OR (prestamos_activos = 0 AND prestamos_finalizados > 0 AND activo_actual = TRUE)
ORDER BY accion_requerida, cedula
LIMIT 50;

-- ======================================================================
-- RESUMEN: REGLA DE NEGOCIO CORRECTA
-- ======================================================================
-- activo = TRUE: Se marca cuando se INICIA proceso de análisis de préstamo
--                (cliente en evaluación, aprobado, o pagando)
-- 
-- activo = FALSE: Se marca cuando el cliente TERMINÓ DE PAGAR completamente
--                 (préstamo finalizado, sin préstamos activos)
-- ======================================================================
