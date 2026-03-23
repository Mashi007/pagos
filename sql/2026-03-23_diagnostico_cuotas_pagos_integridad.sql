-- Diagnostico integral: amortizacion vs pagos (PostgreSQL)
-- Uso: reemplazar :prestamo_id o fijar WHERE prestamo_id = 983

-- 1) Cuotas donde total_pagado no coincide con la suma de cuota_pagos
SELECT
  c.id AS cuota_id,
  c.prestamo_id,
  c.numero_cuota,
  c.monto_cuota,
  c.total_pagado,
  COALESCE(SUM(cp.monto_aplicado), 0) AS sum_cuota_pagos,
  ROUND(
    COALESCE(c.total_pagado, 0)::numeric - COALESCE(SUM(cp.monto_aplicado), 0)::numeric,
    2
  ) AS diff_total_vs_cp
FROM cuotas c
LEFT JOIN cuota_pagos cp ON cp.cuota_id = c.id
WHERE c.prestamo_id = 983
GROUP BY c.id, c.prestamo_id, c.numero_cuota, c.monto_cuota, c.total_pagado
HAVING ABS(COALESCE(c.total_pagado, 0) - COALESCE(SUM(cp.monto_aplicado), 0)) > 0.02
ORDER BY c.numero_cuota;

-- 2) Pagos conciliados (o verificado SI) con monto > 0 y sin ninguna fila en cuota_pagos
SELECT
  p.id AS pago_id,
  p.prestamo_id,
  p.fecha_pago,
  p.monto_pagado,
  p.estado,
  p.conciliado
FROM pagos p
WHERE p.prestamo_id = 983
  AND p.monto_pagado > 0
  AND (
    p.conciliado = TRUE
    OR upper(trim(coalesce(p.verificado_concordancia, ''))) = 'SI'
  )
  AND NOT EXISTS (SELECT 1 FROM cuota_pagos cp WHERE cp.pago_id = p.id)
ORDER BY p.fecha_pago NULLS LAST, p.id;

-- 3) Detalle: cada fila de cuota_pagos del prestamo
SELECT
  cp.id AS cuota_pago_id,
  cp.cuota_id,
  c.numero_cuota,
  cp.pago_id,
  cp.monto_aplicado,
  cp.fecha_aplicacion,
  cp.es_pago_completo
FROM cuota_pagos cp
JOIN cuotas c ON c.id = cp.cuota_id
WHERE c.prestamo_id = 983
ORDER BY c.numero_cuota, cp.pago_id, cp.id;

-- 4) Mismo pago_id repetido en la misma cuota (no deberia)
SELECT cp.cuota_id, cp.pago_id, COUNT(*) AS veces, SUM(cp.monto_aplicado) AS suma_montos
FROM cuota_pagos cp
JOIN cuotas c ON c.id = cp.cuota_id
WHERE c.prestamo_id = 983
GROUP BY cp.cuota_id, cp.pago_id
HAVING COUNT(*) > 1;

-- 5) Balance global: pagos conciliados vs suma cuota_pagos
SELECT
  (SELECT COALESCE(SUM(p.monto_pagado), 0)
   FROM pagos p
   WHERE p.prestamo_id = 983
     AND p.monto_pagado > 0
     AND (
       p.conciliado = TRUE
       OR upper(trim(coalesce(p.verificado_concordancia, ''))) = 'SI'
     )
  ) AS sum_monto_pagos,
  (SELECT COALESCE(SUM(cp.monto_aplicado), 0)
   FROM cuota_pagos cp
   JOIN cuotas c ON c.id = cp.cuota_id
   WHERE c.prestamo_id = 983
  ) AS sum_monto_cuota_pagos;

/*
Interpretacion de diffs negativos grandes:
- total_pagado < sum(cuota_pagos): mas dinero en cuota_pagos que en la columna cuotas (doble registro o
  reaplicacion sin reset; o total_pagado no actualizado).
Correccion integral: POST /api/v1/prestamos/983/reaplicar-fifo-aplicacion (admin).
*/

