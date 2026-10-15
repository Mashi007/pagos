-- Pago 104967 (V18097271 / prestamo 2345): 96 USD en pagos, 0 en cuota_pagos.
-- Préstamo LIQUIDADO con 12 cuotas cubiertas; fila duplicada / carga de más (Binance 443804633778003968).
-- Ejecutar en Postgres (Render). Revisar una fila antes de COMMIT.

BEGIN;

SELECT id, prestamo_id, monto_pagado, numero_documento, estado
FROM pagos
WHERE id = 104967;

UPDATE pagos
SET
  estado = 'ANULADO_IMPORT',
  notas = trim(
    coalesce(notas, '')
    || ' [2026-10] Huérfano sin cuota_pagos; anulado para alinear resumen crédito (12 cuotas).'
  )
WHERE id = 104967
  AND prestamo_id = 2345
  AND NOT EXISTS (SELECT 1 FROM cuota_pagos cp WHERE cp.pago_id = 104967);

SELECT id, estado, notas FROM pagos WHERE id = 104967;

-- COMMIT;
-- ROLLBACK;
