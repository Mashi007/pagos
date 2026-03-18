-- Verificar si todos los pagos están conciliados
-- Ajusta nombre de tabla y columna según tu esquema (ej: pago.conciliado, pago.estado_conciliacion, etc.)

-- Opción 1: Si existe columna conciliado (boolean) o estado_conciliacion en la tabla de pagos
-- Resumen: total de pagos vs cuántos están conciliados
SELECT
    COUNT(*) AS total_pagos,
    COUNT(*) FILTER (WHERE conciliado = true)  AS conciliados,
    COUNT(*) FILTER (WHERE conciliado = false OR conciliado IS NULL) AS no_conciliados,
    COUNT(*) FILTER (WHERE conciliado = true) = COUNT(*) AS todos_conciliados
FROM pago;

-- Listado de pagos NO conciliados (para revisión)
SELECT id, created_at, monto, referencia, cliente_id, prestamo_id
FROM pago
WHERE conciliado = false OR conciliado IS NULL
ORDER BY created_at DESC;

-- Opción 2: Si la conciliación se guarda en otra tabla (ej: conciliacion_pago)
-- Todos conciliados = cada pago tiene al menos un registro en conciliacion_pago
SELECT
    (SELECT COUNT(*) FROM pago) AS total_pagos,
    (SELECT COUNT(DISTINCT pago_id) FROM conciliacion_pago) AS pagos_con_conciliacion,
    (SELECT COUNT(*) FROM pago p
     WHERE NOT EXISTS (SELECT 1 FROM conciliacion_pago c WHERE c.pago_id = p.id)
    ) AS pagos_sin_conciliar;

-- Pagos que aún no tienen conciliación
SELECT p.id, p.created_at, p.monto, p.referencia
FROM pago p
WHERE NOT EXISTS (SELECT 1 FROM conciliacion_pago c WHERE c.pago_id = p.id)
ORDER BY p.created_at DESC;

-- Opción 3: Si usas estado como texto (ej: estado = 'CONCILIADO')
-- SELECT
--     COUNT(*) AS total,
--     COUNT(*) FILTER (WHERE estado_conciliacion = 'CONCILIADO') AS conciliados,
--     COUNT(*) FILTER (WHERE COALESCE(estado_conciliacion, '') <> 'CONCILIADO') AS no_conciliados
-- FROM pago;
