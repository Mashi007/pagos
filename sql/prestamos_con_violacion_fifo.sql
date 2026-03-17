-- Préstamos con posible violación FIFO (cuota posterior pagada y anterior no)
-- Una cuota "cubierta" = COALESCE(total_pagado,0) >= monto_cuota - 0.01
-- Violación: existe cuota N no cubierta y cuota N+1 cubierta (mismo préstamo)

-- 1) Lista de prestamo_id que conviene rearticular
SELECT DISTINCT a.prestamo_id
FROM cuotas a
JOIN cuotas b
  ON b.prestamo_id = a.prestamo_id
 AND b.numero_cuota = a.numero_cuota + 1
WHERE COALESCE(a.total_pagado, 0) < (a.monto_cuota - 0.01)
  AND COALESCE(b.total_pagado, 0) >= (b.monto_cuota - 0.01)
ORDER BY a.prestamo_id;


-- 2) Detalle: préstamo, número de cuota no cubierta, número de cuota cubierta (par violado)
SELECT
  a.prestamo_id,
  a.numero_cuota   AS cuota_no_cubierta,
  COALESCE(a.total_pagado::numeric(14,2), 0) AS pago_cuota_anterior,
  a.monto_cuota    AS monto_cuota_anterior,
  b.numero_cuota   AS cuota_cubierta_siguiente,
  COALESCE(b.total_pagado::numeric(14,2), 0) AS pago_cuota_siguiente,
  b.monto_cuota    AS monto_cuota_siguiente
FROM cuotas a
JOIN cuotas b
  ON b.prestamo_id = a.prestamo_id
 AND b.numero_cuota = a.numero_cuota + 1
WHERE COALESCE(a.total_pagado, 0) < (a.monto_cuota - 0.01)
  AND COALESCE(b.total_pagado, 0) >= (b.monto_cuota - 0.01)
ORDER BY a.prestamo_id, a.numero_cuota;


-- 3) Conteo por préstamo (cuántos pares violados tiene cada uno)
SELECT
  a.prestamo_id,
  COUNT(*) AS pares_violados
FROM cuotas a
JOIN cuotas b
  ON b.prestamo_id = a.prestamo_id
 AND b.numero_cuota = a.numero_cuota + 1
WHERE COALESCE(a.total_pagado, 0) < (a.monto_cuota - 0.01)
  AND COALESCE(b.total_pagado, 0) >= (b.monto_cuota - 0.01)
GROUP BY a.prestamo_id
ORDER BY a.prestamo_id;
