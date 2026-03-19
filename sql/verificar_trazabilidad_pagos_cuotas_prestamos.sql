-- =============================================================================
-- Verificación del mecanismo de trazabilidad: orden e integración
--   pagos → cuota_pagos → cuotas → préstamos
--
-- Trazabilidad en BD:
--   - Tabla cuota_pagos: cada fila = aplicación de un pago a una cuota
--     (cuota_id, pago_id, monto_aplicado, fecha_aplicacion, orden_aplicacion, es_pago_completo).
--   - Orden de aplicación: FIFO por numero_cuota (cuotas más antiguas primero);
--     orden_aplicacion en cuota_pagos indica la secuencia dentro de un mismo pago.
-- =============================================================================

-- =============================================================================
-- 1. Resumen de trazabilidad: cuántos pagos tienen historial en cuota_pagos
-- =============================================================================
SELECT
    (SELECT COUNT(*) FROM pagos WHERE prestamo_id IS NOT NULL AND monto_pagado > 0) AS pagos_con_prestamo_y_monto,
    (SELECT COUNT(DISTINCT pago_id) FROM cuota_pagos) AS pagos_con_trazabilidad,
    (SELECT COUNT(*) FROM cuota_pagos) AS total_registros_trazabilidad;

-- =============================================================================
-- 2. Integridad por PAGO: suma(monto_aplicado) por pago debe = monto_pagado
-- =============================================================================
WITH aplicado_por_pago AS (
    SELECT
        pago_id,
        SUM(monto_aplicado) AS total_aplicado,
        COUNT(*) AS num_registros
    FROM cuota_pagos
    GROUP BY pago_id
)
SELECT
    p.id AS pago_id,
    p.prestamo_id,
    p.monto_pagado,
    COALESCE(a.total_aplicado, 0) AS total_aplicado_trazabilidad,
    (p.monto_pagado - COALESCE(a.total_aplicado, 0)) AS desfase,
    a.num_registros AS filas_en_cuota_pagos
FROM pagos p
LEFT JOIN aplicado_por_pago a ON a.pago_id = p.id
WHERE p.prestamo_id IS NOT NULL
  AND p.monto_pagado > 0
  AND (ABS(COALESCE(a.total_aplicado, 0) - p.monto_pagado) > 0.01)
ORDER BY p.id;

-- Si la consulta anterior devuelve 0 filas → integridad pago ↔ cuota_pagos OK.

-- =============================================================================
-- 3. Integridad por CUOTA: suma(monto_aplicado) por cuota debe = cuota.total_pagado
-- =============================================================================
WITH aplicado_por_cuota AS (
    SELECT
        cuota_id,
        SUM(monto_aplicado) AS total_aplicado_trazabilidad
    FROM cuota_pagos
    GROUP BY cuota_id
)
SELECT
    c.id AS cuota_id,
    c.prestamo_id,
    c.numero_cuota,
    c.monto_cuota AS monto,
    c.total_pagado AS total_pagado_cuota,
    COALESCE(a.total_aplicado_trazabilidad, 0) AS total_aplicado_trazabilidad,
    (COALESCE(c.total_pagado, 0) - COALESCE(a.total_aplicado_trazabilidad, 0)) AS desfase
FROM cuotas c
LEFT JOIN aplicado_por_cuota a ON a.cuota_id = c.id
WHERE c.total_pagado IS NOT NULL AND c.total_pagado > 0
  AND (ABS(COALESCE(c.total_pagado, 0) - COALESCE(a.total_aplicado_trazabilidad, 0)) > 0.01)
ORDER BY c.prestamo_id, c.numero_cuota;

-- Si devuelve 0 filas → integridad cuota ↔ cuota_pagos OK.

-- =============================================================================
-- 4. Orden FIFO por pago: secuencia orden_aplicacion debe ser 0, 1, 2, ...
--    y cuotas aplicadas en orden de numero_cuota creciente
-- =============================================================================
-- 4a. Pagos con registros en cuota_pagos donde orden_aplicacion no es consecutivo (posible inconsistencia)
WITH ord AS (
    SELECT
        pago_id,
        orden_aplicacion,
        cuota_id,
        LAG(orden_aplicacion) OVER (PARTITION BY pago_id ORDER BY orden_aplicacion) AS prev_orden
    FROM cuota_pagos
)
SELECT
    pago_id,
    orden_aplicacion,
    prev_orden,
    orden_aplicacion - COALESCE(prev_orden, -1) - 1 AS hueco
FROM ord
WHERE prev_orden IS NOT NULL AND orden_aplicacion <> prev_orden + 1
ORDER BY pago_id, orden_aplicacion;

-- 4b. Por cada pago: cuotas tocadas en orden de numero_cuota (debe ser creciente si FIFO correcto)
WITH secuencia AS (
    SELECT
        cp.pago_id,
        cp.orden_aplicacion,
        cp.cuota_id,
        c.numero_cuota,
        LAG(c.numero_cuota) OVER (PARTITION BY cp.pago_id ORDER BY cp.orden_aplicacion) AS numero_cuota_anterior
    FROM cuota_pagos cp
    JOIN cuotas c ON c.id = cp.cuota_id
)
SELECT
    pago_id,
    orden_aplicacion,
    cuota_id,
    numero_cuota,
    numero_cuota_anterior,
    CASE WHEN numero_cuota_anterior IS NOT NULL AND numero_cuota < numero_cuota_anterior THEN 'NO_FIFO' END AS alerta
FROM secuencia
WHERE numero_cuota_anterior IS NOT NULL AND numero_cuota < numero_cuota_anterior
ORDER BY pago_id, orden_aplicacion;

-- Si ambas 4a y 4b devuelven 0 filas → orden de trazabilidad consistente con FIFO.

-- =============================================================================
-- 5. Cadena completa pago → cuota_pagos → cuota → préstamo (muestra de trazabilidad)
-- =============================================================================
SELECT
    p.id AS pago_id,
    p.prestamo_id,
    p.fecha_pago,
    p.monto_pagado,
    cp.orden_aplicacion,
    c.id AS cuota_id,
    c.numero_cuota,
    c.fecha_vencimiento,
    cp.monto_aplicado,
    cp.es_pago_completo,
    cp.fecha_aplicacion
FROM pagos p
JOIN cuota_pagos cp ON cp.pago_id = p.id
JOIN cuotas c ON c.id = cp.cuota_id
WHERE p.prestamo_id IS NOT NULL
ORDER BY p.prestamo_id, p.id, cp.orden_aplicacion
LIMIT 200;

-- =============================================================================
-- 6. Préstamos con al menos un pago integrado (trazabilidad presente)
-- =============================================================================
SELECT
    pr.id AS prestamo_id,
    COUNT(DISTINCT p.id) AS num_pagos,
    COUNT(DISTINCT cp.pago_id) AS pagos_con_trazabilidad,
    COUNT(cp.id) AS total_registros_cuota_pagos
FROM prestamos pr
JOIN pagos p ON p.prestamo_id = pr.id AND p.monto_pagado > 0
LEFT JOIN cuota_pagos cp ON cp.pago_id = p.id
GROUP BY pr.id
HAVING COUNT(DISTINCT p.id) > 0
ORDER BY pr.id
LIMIT 100;
