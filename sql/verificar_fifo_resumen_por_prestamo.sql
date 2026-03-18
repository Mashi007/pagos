-- Resumen por préstamo de violaciones FIFO (para priorizar corrección)
-- Una fila por préstamo: primera cuota no completada y lista de cuotas posteriores con pago

SELECT
  c1.prestamo_id,
  MIN(c1.numero_cuota) AS primera_cuota_sin_completar,
  MIN(c1.id) AS cuota_anterior_id,
  MIN(c1.monto_cuota) AS monto_cuota,
  MIN(COALESCE(c1.total_pagado, 0)) AS total_pagado_esa_cuota,
  MIN(c1.monto_cuota) - MIN(COALESCE(c1.total_pagado, 0)) AS faltante,
  STRING_AGG(DISTINCT c2.numero_cuota::text, ',' ORDER BY c2.numero_cuota::text) AS numeros_cuotas_posteriores_con_pago
FROM cuotas c1
JOIN cuotas c2
  ON c1.prestamo_id = c2.prestamo_id
  AND c1.numero_cuota < c2.numero_cuota
WHERE (c2.total_pagado IS NOT NULL AND c2.total_pagado > 0)
  AND (c1.total_pagado IS NULL OR c1.total_pagado < c1.monto_cuota - 0.01)
GROUP BY c1.prestamo_id, c1.numero_cuota, c1.id, c1.monto_cuota, c1.total_pagado
ORDER BY c1.prestamo_id, c1.numero_cuota;
