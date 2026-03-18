-- =============================================================================
-- Verificación: cuotas actualizadas para cédula V17974792
-- Ejecutar contra la BD (PostgreSQL). Reemplaza 'V17974792' si usas otro formato.
-- =============================================================================

-- 1) Cliente(s) con esta cédula
SELECT id AS cliente_id, cedula, nombres, telefono, email, estado, fecha_registro, fecha_actualizacion
FROM clientes
WHERE TRIM(UPPER(cedula)) = TRIM(UPPER('V17974792'))
   OR cedula LIKE '%17974792%';

-- 2) Préstamos del cliente
SELECT p.id AS prestamo_id, p.cliente_id, p.cedula, p.nombres,
       p.total_financiamiento, p.numero_cuotas, p.estado,
       p.fecha_aprobacion::date AS fecha_aprobacion,
       p.fecha_registro::date AS fecha_registro
FROM prestamos p
WHERE p.cliente_id IN (SELECT id FROM clientes WHERE TRIM(UPPER(cedula)) = TRIM(UPPER('V17974792')) OR cedula LIKE '%17974792%')
   OR TRIM(UPPER(p.cedula)) = TRIM(UPPER('V17974792'))
   OR p.cedula LIKE '%17974792%'
ORDER BY p.id;

-- 3) Cuotas (tabla de amortización): total_pagado, pago_id, estado, fecha_pago
SELECT c.id AS cuota_id, c.prestamo_id, c.numero_cuota, c.fecha_vencimiento, c.fecha_pago,
       c.monto_cuota AS monto, c.total_pagado, c.pago_id, c.estado AS estado_cuota,
       c.dias_mora
FROM cuotas c
WHERE c.prestamo_id IN (
  SELECT p.id FROM prestamos p
  WHERE p.cliente_id IN (SELECT id FROM clientes WHERE TRIM(UPPER(cedula)) = TRIM(UPPER('V17974792')) OR cedula LIKE '%17974792%')
     OR TRIM(UPPER(p.cedula)) = TRIM(UPPER('V17974792'))
     OR p.cedula LIKE '%17974792%'
)
ORDER BY c.prestamo_id, c.numero_cuota;

-- 4) Pagos del préstamo (conciliado, monto, prestamo_id)
SELECT pg.id AS pago_id, pg.prestamo_id, pg.cedula, pg.fecha_pago, pg.monto_pagado,
       pg.numero_documento, pg.estado AS estado_pago, pg.conciliado, pg.fecha_conciliacion
FROM pagos pg
WHERE pg.prestamo_id IN (
  SELECT p.id FROM prestamos p
  WHERE p.cliente_id IN (SELECT id FROM clientes WHERE TRIM(UPPER(cedula)) = TRIM(UPPER('V17974792')) OR cedula LIKE '%17974792%')
     OR TRIM(UPPER(p.cedula)) = TRIM(UPPER('V17974792'))
     OR p.cedula LIKE '%17974792%'
)
   OR TRIM(UPPER(pg.cedula)) = TRIM(UPPER('V17974792'))
   OR pg.cedula LIKE '%17974792%'
ORDER BY pg.fecha_pago, pg.id;

-- 5) Enlaces pago → cuota (cuota_pagos): si hay filas = pago aplicado a cuotas
SELECT cp.id, cp.cuota_id, cp.pago_id, cp.monto_aplicado, cp.fecha_aplicacion, cp.es_pago_completo,
       c.prestamo_id, c.numero_cuota, pg.monto_pagado, pg.conciliado
FROM cuota_pagos cp
JOIN cuotas c ON c.id = cp.cuota_id
JOIN pagos pg ON pg.id = cp.pago_id
WHERE c.prestamo_id IN (
  SELECT p.id FROM prestamos p
  WHERE p.cliente_id IN (SELECT id FROM clientes WHERE TRIM(UPPER(cedula)) = TRIM(UPPER('V17974792')) OR cedula LIKE '%17974792%')
     OR TRIM(UPPER(p.cedula)) = TRIM(UPPER('V17974792'))
     OR p.cedula LIKE '%17974792%'
)
ORDER BY cp.pago_id, cp.cuota_id;

-- 6) Diagnóstico: pagos con prestamo_id y cuántos enlaces en cuota_pagos (0 = no aplicado)
SELECT pg.id AS pago_id, pg.prestamo_id, pg.monto_pagado, pg.conciliado,
       (SELECT COUNT(*) FROM cuota_pagos cp WHERE cp.pago_id = pg.id) AS enlaces_cuota_pagos
FROM pagos pg
WHERE pg.prestamo_id IN (
  SELECT p.id FROM prestamos p
  WHERE p.cliente_id IN (SELECT id FROM clientes WHERE TRIM(UPPER(cedula)) = TRIM(UPPER('V17974792')) OR cedula LIKE '%17974792%')
     OR TRIM(UPPER(p.cedula)) = TRIM(UPPER('V17974792'))
     OR p.cedula LIKE '%17974792%'
)
ORDER BY pg.id;
-- Si enlaces_cuota_pagos = 0 y conciliado = true → abrir Tabla de Amortización de ese préstamo y Refrescar para que se aplique.

-- 7) Resumen por préstamo (cuotas, cuotas con pago, total pagado en cuotas)
SELECT p.id AS prestamo_id, p.estado, p.total_financiamiento, p.numero_cuotas,
       (SELECT COUNT(*) FROM cuotas c WHERE c.prestamo_id = p.id) AS total_cuotas,
       (SELECT COUNT(*) FROM cuotas c WHERE c.prestamo_id = p.id AND (c.total_pagado IS NOT NULL AND c.total_pagado > 0)) AS cuotas_con_pago,
       (SELECT COALESCE(SUM(c.total_pagado), 0) FROM cuotas c WHERE c.prestamo_id = p.id) AS total_abonado_cuotas,
       (SELECT COALESCE(SUM(pg.monto_pagado), 0) FROM pagos pg WHERE pg.prestamo_id = p.id) AS total_pagado_prestamo
FROM prestamos p
WHERE p.cliente_id IN (SELECT id FROM clientes WHERE TRIM(UPPER(cedula)) = TRIM(UPPER('V17974792')) OR cedula LIKE '%17974792%')
   OR TRIM(UPPER(p.cedula)) = TRIM(UPPER('V17974792'))
   OR p.cedula LIKE '%17974792%'
ORDER BY p.id;
