-- =============================================================================
-- Verificación Cascada: pagos aplicados a cuotas por orden de numero_cuota
-- =============================================================================
-- Regla: En cada préstamo, un pago debe aplicarse primero a la cuota más antigua
-- (numero_cuota menor). No puede haber una cuota N con pago si existe una
-- cuota M < N que no esté totalmente pagada.
--
-- Este script devuelve las filas donde se viola Cascada (cuota posterior con pago
-- mientras una cuota anterior no está completada).
-- =============================================================================

-- 1) Resumen: préstamos con al menos una violación Cascada
SELECT
  'Prestamos con violacion Cascada' AS tipo,
  COUNT(DISTINCT c1.prestamo_id) AS total_prestamos
FROM cuotas c1
JOIN cuotas c2
  ON c1.prestamo_id = c2.prestamo_id
  AND c1.numero_cuota < c2.numero_cuota
WHERE (c2.total_pagado IS NOT NULL AND c2.total_pagado > 0)
  AND (c1.total_pagado IS NULL OR c1.total_pagado < c1.monto_cuota - 0.01);

-- 2) Detalle: cada par (cuota anterior no completada, cuota posterior con pago)
SELECT
  c1.prestamo_id,
  c1.id AS cuota_anterior_id,
  c1.numero_cuota AS numero_cuota_anterior,
  c1.monto_cuota AS monto_anterior,
  COALESCE(c1.total_pagado, 0) AS total_pagado_anterior,
  c1.estado AS estado_anterior,
  c2.id AS cuota_posterior_id,
  c2.numero_cuota AS numero_cuota_posterior,
  c2.monto_cuota AS monto_posterior,
  COALESCE(c2.total_pagado, 0) AS total_pagado_posterior,
  c2.estado AS estado_posterior
FROM cuotas c1
JOIN cuotas c2
  ON c1.prestamo_id = c2.prestamo_id
  AND c1.numero_cuota < c2.numero_cuota
WHERE (c2.total_pagado IS NOT NULL AND c2.total_pagado > 0)
  AND (c1.total_pagado IS NULL OR c1.total_pagado < c1.monto_cuota - 0.01)
ORDER BY c1.prestamo_id, c1.numero_cuota, c2.numero_cuota;

-- 3) Verificación global: cumple o no la regla de cascada
WITH viola AS (
  SELECT EXISTS (
    SELECT 1
    FROM cuotas c1
    JOIN cuotas c2
      ON c1.prestamo_id = c2.prestamo_id
      AND c1.numero_cuota < c2.numero_cuota
    WHERE (c2.total_pagado IS NOT NULL AND c2.total_pagado > 0)
      AND (c1.total_pagado IS NULL OR c1.total_pagado < c1.monto_cuota - 0.01)
  ) AS hay_violacion
)
SELECT
  CASE WHEN hay_violacion THEN 'NO_CUMPLE_CASCADA' ELSE 'CUMPLE_CASCADA' END AS resultado_cascada,
  CASE WHEN hay_violacion THEN 'NO_CUMPLE_FIFO' ELSE 'CUMPLE_FIFO' END AS resultado_fifo
FROM viola;
