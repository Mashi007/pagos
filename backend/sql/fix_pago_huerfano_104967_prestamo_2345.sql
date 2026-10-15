-- V18097271 / prestamo 2345 — cuadre resumen crédito
--
-- CORRECTO: anular pago 57193 (135 USD, itmaster), NO 104967 (96 USD).
-- 57193 tenía cuota_pagos; tras anular hay que recalcular cuotas y/o cascada en UI.
--
-- Ejecutar en Postgres (Render). Revisar SELECTs antes de COMMIT.

BEGIN;

SELECT id, monto_pagado, numero_documento, estado,
       EXISTS (SELECT 1 FROM cuota_pagos cp WHERE cp.pago_id = pagos.id) AS tiene_cuota
FROM pagos
WHERE prestamo_id = 2345 AND id IN (57193, 104967)
ORDER BY id;

-- 1) Si antes anulaste 104967 por error, restáuralo
UPDATE pagos
SET estado = 'PAGADO'
WHERE id = 104967
  AND prestamo_id = 2345
  AND upper(coalesce(estado, '')) LIKE '%ANUL%';

-- 2) Anular el de 135 (57193): quitar aplicación y marcar no operativo
DELETE FROM cuota_pagos
WHERE pago_id = 57193;

UPDATE pagos
SET
  estado = 'ANULADO_IMPORT',
  notas = trim(
    coalesce(notas, '')
    || ' [2026-10-15] Anulado para cuadre; pago admin 135 USD (usar 96 + cascada).'
  )
WHERE id = 57193
  AND prestamo_id = 2345
  AND monto_pagado = 135.00;

-- 3) Recalcular total_pagado en cuotas desde cuota_pagos restantes
UPDATE cuotas c
SET total_pagado = COALESCE(
  (SELECT SUM(cp.monto_aplicado) FROM cuota_pagos cp WHERE cp.cuota_id = c.id),
  0
)
WHERE c.prestamo_id = 2345;

SELECT id, monto_pagado, estado FROM pagos WHERE id IN (57193, 104967);
SELECT numero_cuota, total_pagado, monto FROM cuotas WHERE prestamo_id = 2345 ORDER BY numero_cuota;

-- 4) En app: Revisión manual prestamo 2345 → «Aplicar a cuotas» / cascada
--    para rearticular 104967 y el resto si cuotas 9–10 quedaron desfasadas.

-- COMMIT;
-- ROLLBACK;
