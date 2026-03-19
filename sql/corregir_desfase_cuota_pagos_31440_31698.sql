-- Corrige los 2 pagos con doble asignación en cuota_pagos (suma > monto_pagado).
-- pago_id 31440: monto_pagado 57, suma 114 (2 filas).
-- pago_id 31698: monto_pagado 100, suma 200 (2 filas).
-- Se deja una fila con el monto del pago y la otra se pone en 0 (la de mayor id).

UPDATE cuota_pagos
SET monto_aplicado = 0
WHERE pago_id = 31440
  AND id = (SELECT id FROM cuota_pagos WHERE pago_id = 31440 ORDER BY id DESC LIMIT 1);

UPDATE cuota_pagos
SET monto_aplicado = 0
WHERE pago_id = 31698
  AND id = (SELECT id FROM cuota_pagos WHERE pago_id = 31698 ORDER BY id DESC LIMIT 1);

-- Verificación: ejecutar consulta 2 de verificar_trazabilidad_pagos_cuotas_prestamos.sql
-- filtrando por pago_id IN (31440, 31698); debe devolver 0 filas.
