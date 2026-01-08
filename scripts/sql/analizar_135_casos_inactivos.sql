-- ======================================================================
-- ANALISIS DE 135 CASOS: CLIENTES INACTIVOS CON PRESTAMOS APROBADOS
-- ======================================================================
-- Objetivo: Identificar cuáles deben estar ACTIVOS (préstamos vigentes)
-- vs cuáles están correctamente FINALIZADOS
-- ======================================================================

-- ======================================================================
-- 1. RESUMEN GENERAL POR ESTADO DEL CLIENTE
-- ======================================================================

SELECT 
    c.estado AS estado_cliente,
    COUNT(DISTINCT c.id) AS total_clientes,
    COUNT(p.id) AS total_prestamos_aprobados,
    COUNT(DISTINCT CASE WHEN cu.id IS NOT NULL THEN p.id END) AS prestamos_con_cuotas,
    COUNT(DISTINCT CASE WHEN pag.id IS NOT NULL THEN p.id END) AS prestamos_con_pagos,
    COALESCE(SUM(pag.monto_pagado), 0) AS total_pagado
FROM clientes c
INNER JOIN prestamos p ON c.cedula = p.cedula
LEFT JOIN cuotas cu ON p.id = cu.prestamo_id
LEFT JOIN pagos pag ON p.cedula = pag.cedula AND pag.activo = TRUE
WHERE c.activo = FALSE
  AND p.estado = 'APROBADO'
GROUP BY c.estado
ORDER BY total_clientes DESC;

-- ======================================================================
-- 2. CLIENTES INACTIVOS (ESTADO='INACTIVO') CON PRESTAMOS APROBADOS
-- ======================================================================
-- Estos son los casos que requieren corrección (deben estar ACTIVOS)
-- ======================================================================

SELECT 
    c.id AS cliente_id,
    c.cedula,
    c.nombres,
    c.estado,
    c.activo,
    c.fecha_registro,
    c.fecha_actualizacion,
    COUNT(p.id) AS total_prestamos_aprobados,
    MIN(p.fecha_aprobacion) AS primera_aprobacion,
    MAX(p.fecha_aprobacion) AS ultima_aprobacion,
    COUNT(cu.id) AS total_cuotas_generadas,
    COALESCE(SUM(cu.total_pagado), 0) AS total_pagado_cuotas,
    COALESCE(SUM(cu.capital_pendiente), 0) AS capital_pendiente,
    COUNT(pag.id) AS total_pagos_registrados,
    COALESCE(SUM(pag.monto_pagado), 0) AS total_pagado_pagos,
    CASE 
        WHEN COALESCE(SUM(cu.capital_pendiente), 0) > 0 THEN 'PRESTAMO VIGENTE'
        WHEN COALESCE(SUM(cu.total_pagado), 0) > 0 THEN 'CON PAGOS'
        ELSE 'SIN PAGOS'
    END AS clasificacion
FROM clientes c
INNER JOIN prestamos p ON c.cedula = p.cedula
LEFT JOIN cuotas cu ON p.id = cu.prestamo_id
LEFT JOIN pagos pag ON p.cedula = pag.cedula AND pag.activo = TRUE
WHERE c.estado = 'INACTIVO'
  AND c.activo = FALSE
  AND p.estado = 'APROBADO'
GROUP BY c.id, c.cedula, c.nombres, c.estado, c.activo, 
         c.fecha_registro, c.fecha_actualizacion
ORDER BY total_pagado_cuotas DESC, capital_pendiente DESC;

-- ======================================================================
-- 3. CLIENTES FINALIZADOS CON PRESTAMOS APROBADOS
-- ======================================================================
-- Estos pueden estar correctamente FINALIZADOS si completaron su ciclo
-- ======================================================================

SELECT 
    c.id AS cliente_id,
    c.cedula,
    c.nombres,
    c.estado,
    c.activo,
    c.fecha_actualizacion,
    COUNT(p.id) AS total_prestamos_aprobados,
    COUNT(cu.id) AS total_cuotas_generadas,
    COALESCE(SUM(cu.total_pagado), 0) AS total_pagado_cuotas,
    COALESCE(SUM(cu.capital_pendiente), 0) AS capital_pendiente,
    COALESCE(SUM(cu.interes_pendiente), 0) AS interes_pendiente,
    COUNT(pag.id) AS total_pagos_registrados,
    COALESCE(SUM(pag.monto_pagado), 0) AS total_pagado_pagos,
    CASE 
        WHEN COALESCE(SUM(cu.capital_pendiente), 0) > 0 THEN 'TIENE SALDO PENDIENTE'
        WHEN COALESCE(SUM(cu.total_pagado), 0) > 0 THEN 'COMPLETO PAGOS'
        ELSE 'SIN PAGOS'
    END AS clasificacion
FROM clientes c
INNER JOIN prestamos p ON c.cedula = p.cedula
LEFT JOIN cuotas cu ON p.id = cu.prestamo_id
LEFT JOIN pagos pag ON p.cedula = pag.cedula AND pag.activo = TRUE
WHERE c.estado = 'FINALIZADO'
  AND c.activo = FALSE
  AND p.estado = 'APROBADO'
GROUP BY c.id, c.cedula, c.nombres, c.estado, c.activo, c.fecha_actualizacion
ORDER BY capital_pendiente DESC, total_pagado_cuotas DESC;

-- ======================================================================
-- 4. CLASIFICACION: PRESTAMOS VIGENTES VS FINALIZADOS
-- ======================================================================
-- Identificar cuáles tienen saldo pendiente (deben estar ACTIVOS)
-- ======================================================================

WITH resumen_clientes AS (
    SELECT 
        c.id AS cliente_id,
        c.estado AS estado_actual,
        COALESCE(SUM(cu.capital_pendiente), 0) AS capital_pendiente,
        COALESCE(SUM(cu.interes_pendiente), 0) AS interes_pendiente,
        COALESCE(SUM(cu.total_pagado), 0) AS total_pagado,
        COUNT(p.id) AS total_prestamos
    FROM clientes c
    INNER JOIN prestamos p ON c.cedula = p.cedula
    LEFT JOIN cuotas cu ON p.id = cu.prestamo_id
    WHERE c.activo = FALSE
      AND p.estado = 'APROBADO'
    GROUP BY c.id, c.estado
)
SELECT 
    CASE 
        WHEN capital_pendiente > 0 OR interes_pendiente > 0 
        THEN 'DEBE ESTAR ACTIVO (PRESTAMO VIGENTE)'
        WHEN total_pagado > 0 AND capital_pendiente = 0 AND interes_pendiente = 0
        THEN 'CORRECTO FINALIZADO (SALDO CERO)'
        ELSE 'SIN PAGOS (REVISAR)'
    END AS clasificacion,
    estado_actual,
    COUNT(*) AS total_clientes,
    SUM(total_prestamos) AS total_prestamos,
    SUM(capital_pendiente) AS total_capital_pendiente,
    SUM(interes_pendiente) AS total_interes_pendiente,
    SUM(total_pagado) AS total_pagado
FROM resumen_clientes
GROUP BY 
    CASE 
        WHEN capital_pendiente > 0 OR interes_pendiente > 0 
        THEN 'DEBE ESTAR ACTIVO (PRESTAMO VIGENTE)'
        WHEN total_pagado > 0 AND capital_pendiente = 0 AND interes_pendiente = 0
        THEN 'CORRECTO FINALIZADO (SALDO CERO)'
        ELSE 'SIN PAGOS (REVISAR)'
    END,
    estado_actual
ORDER BY total_clientes DESC;

-- ======================================================================
-- 5. DETALLE: CLIENTES QUE DEBEN ESTAR ACTIVOS (TIENEN SALDO PENDIENTE)
-- ======================================================================

SELECT 
    c.id AS cliente_id,
    c.cedula,
    c.nombres,
    c.estado AS estado_actual,
    c.activo,
    COUNT(p.id) AS total_prestamos_aprobados,
    COALESCE(SUM(cu.capital_pendiente), 0) AS capital_pendiente,
    COALESCE(SUM(cu.interes_pendiente), 0) AS interes_pendiente,
    COALESCE(SUM(cu.total_pagado), 0) AS total_pagado,
    COALESCE(SUM(cu.capital_pendiente), 0) + COALESCE(SUM(cu.interes_pendiente), 0) AS saldo_total_pendiente,
    MIN(p.fecha_aprobacion) AS primera_aprobacion,
    MAX(p.fecha_aprobacion) AS ultima_aprobacion
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
-- 6. ESTADISTICAS POR ESTADO Y CLASIFICACION
-- ======================================================================

WITH resumen_por_cliente AS (
    SELECT 
        c.id AS cliente_id,
        c.estado AS estado_cliente,
        COALESCE(SUM(cu.capital_pendiente), 0) AS capital_pendiente,
        COALESCE(SUM(cu.interes_pendiente), 0) AS interes_pendiente,
        COALESCE(SUM(cu.total_pagado), 0) AS total_pagado,
        COUNT(p.id) AS total_prestamos
    FROM clientes c
    INNER JOIN prestamos p ON c.cedula = p.cedula
    LEFT JOIN cuotas cu ON p.id = cu.prestamo_id
    WHERE c.activo = FALSE
      AND p.estado = 'APROBADO'
    GROUP BY c.id, c.estado
)
SELECT 
    estado_cliente,
    CASE 
        WHEN capital_pendiente > 0 OR interes_pendiente > 0 
        THEN 'TIENE SALDO PENDIENTE'
        ELSE 'SIN SALDO PENDIENTE'
    END AS tiene_saldo_pendiente,
    COUNT(*) AS total_clientes,
    SUM(total_prestamos) AS total_prestamos,
    SUM(capital_pendiente) AS total_capital_pendiente,
    SUM(interes_pendiente) AS total_interes_pendiente,
    SUM(total_pagado) AS total_pagado
FROM resumen_por_cliente
GROUP BY estado_cliente,
    CASE 
        WHEN capital_pendiente > 0 OR interes_pendiente > 0 
        THEN 'TIENE SALDO PENDIENTE'
        ELSE 'SIN SALDO PENDIENTE'
    END
ORDER BY estado_cliente, tiene_saldo_pendiente;

-- ======================================================================
-- 7. RESUMEN EJECUTIVO
-- ======================================================================

SELECT 
    'Total clientes inactivos con prestamos aprobados' AS metrica,
    COUNT(DISTINCT c.id) AS valor
FROM clientes c
INNER JOIN prestamos p ON c.cedula = p.cedula
WHERE c.activo = FALSE
  AND p.estado = 'APROBADO'

UNION ALL

SELECT 
    'Clientes INACTIVOS (estado) con prestamos aprobados' AS metrica,
    COUNT(DISTINCT c.id) AS valor
FROM clientes c
INNER JOIN prestamos p ON c.cedula = p.cedula
WHERE c.estado = 'INACTIVO'
  AND p.estado = 'APROBADO'

UNION ALL

SELECT 
    'Clientes FINALIZADOS con prestamos aprobados' AS metrica,
    COUNT(DISTINCT c.id) AS valor
FROM clientes c
INNER JOIN prestamos p ON c.cedula = p.cedula
WHERE c.estado = 'FINALIZADO'
  AND p.estado = 'APROBADO'

UNION ALL

SELECT 
    'Clientes con saldo pendiente (deben estar ACTIVOS)' AS metrica,
    COUNT(DISTINCT c.id) AS valor
FROM clientes c
INNER JOIN prestamos p ON c.cedula = p.cedula
LEFT JOIN cuotas cu ON p.id = cu.prestamo_id
WHERE c.activo = FALSE
  AND p.estado = 'APROBADO'
GROUP BY c.id
HAVING COALESCE(SUM(cu.capital_pendiente), 0) > 0 
    OR COALESCE(SUM(cu.interes_pendiente), 0) > 0

UNION ALL

SELECT 
    'Clientes sin saldo pendiente (correctamente FINALIZADOS)' AS metrica,
    COUNT(DISTINCT c.id) AS valor
FROM clientes c
INNER JOIN prestamos p ON c.cedula = p.cedula
LEFT JOIN cuotas cu ON p.id = cu.prestamo_id
WHERE c.activo = FALSE
  AND p.estado = 'APROBADO'
GROUP BY c.id
HAVING COALESCE(SUM(cu.capital_pendiente), 0) = 0 
    AND COALESCE(SUM(cu.interes_pendiente), 0) = 0
    AND COALESCE(SUM(cu.total_pagado), 0) > 0;

-- ======================================================================
-- 8. LISTA PARA CORRECCION: CLIENTES QUE DEBEN ESTAR ACTIVOS
-- ======================================================================
-- Esta consulta lista todos los clientes que tienen saldo pendiente
-- y deben ser cambiados a estado ACTIVO
-- ======================================================================

SELECT 
    c.id AS cliente_id,
    c.cedula,
    c.nombres,
    c.estado AS estado_actual,
    c.activo,
    COUNT(DISTINCT p.id) AS total_prestamos_aprobados,
    COALESCE(SUM(cu.capital_pendiente), 0) AS capital_pendiente,
    COALESCE(SUM(cu.interes_pendiente), 0) AS interes_pendiente,
    COALESCE(SUM(cu.total_pagado), 0) AS total_pagado,
    COALESCE(SUM(cu.capital_pendiente), 0) + COALESCE(SUM(cu.interes_pendiente), 0) AS saldo_total_pendiente
FROM clientes c
INNER JOIN prestamos p ON c.cedula = p.cedula
LEFT JOIN cuotas cu ON p.id = cu.prestamo_id
WHERE c.activo = FALSE
  AND p.estado = 'APROBADO'
GROUP BY c.id, c.cedula, c.nombres, c.estado, c.activo
HAVING COALESCE(SUM(cu.capital_pendiente), 0) > 0 
    OR COALESCE(SUM(cu.interes_pendiente), 0) > 0
ORDER BY saldo_total_pendiente DESC, c.cedula;

-- ======================================================================
-- NOTAS:
-- ======================================================================
-- 1. Clientes con saldo pendiente (capital_pendiente > 0 o interes_pendiente > 0)
--    deben estar en estado ACTIVO porque tienen préstamos vigentes
-- 
-- 2. Clientes sin saldo pendiente y con pagos registrados pueden estar
--    correctamente en estado FINALIZADO
--
-- 3. Clientes sin pagos y sin saldo pendiente requieren revisión manual
-- ======================================================================
