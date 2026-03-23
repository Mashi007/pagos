-- Prestamos en LIQUIDADO que aun tienen cuotas sin cubrir (inconsistente).
-- Regla: pendiente si COALESCE(total_pagado,0) < monto_cuota - 0.01

SELECT
  p.id AS prestamo_id,
  p.cedula,
  p.estado,
  COUNT(*) FILTER (
    WHERE COALESCE(c.total_pagado, 0) < COALESCE(c.monto_cuota, 0) - 0.01
  ) AS cuotas_pendientes,
  COALESCE(SUM(COALESCE(c.total_pagado, 0)), 0)::numeric(14, 2) AS sum_total_pagado,
  COALESCE(SUM(COALESCE(c.monto_cuota, 0)), 0)::numeric(14, 2) AS sum_monto_cuotas,
  p.total_financiamiento::numeric(14, 2) AS total_financiamiento
FROM prestamos p
JOIN cuotas c ON c.prestamo_id = p.id
WHERE p.estado = 'LIQUIDADO'
GROUP BY p.id, p.cedula, p.estado, p.total_financiamiento
HAVING COUNT(*) FILTER (
  WHERE COALESCE(c.total_pagado, 0) < COALESCE(c.monto_cuota, 0) - 0.01
) > 0
ORDER BY p.id;

-- Correccion masiva (revisar resultado del SELECT antes):
-- UPDATE prestamos p
-- SET estado = 'APROBADO'
-- WHERE p.estado = 'LIQUIDADO'
--   AND EXISTS (
--     SELECT 1
--     FROM cuotas c
--     WHERE c.prestamo_id = p.id
--       AND COALESCE(c.total_pagado, 0) < COALESCE(c.monto_cuota, 0) - 0.01
--   );
