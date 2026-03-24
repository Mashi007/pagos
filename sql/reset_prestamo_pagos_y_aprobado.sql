-- Reset de pagos de un prestamo: borra pagos, limpia cuotas y deja prestamo en APROBADO.
-- PostgreSQL. Reemplazar 837 en todas las apariciones si aplica otro prestamo_id.
-- Usar CAST(... AS date) en lugar de :: para ejecutar tambien con drivers que interpretan ":".

BEGIN;

DELETE FROM reporte_contable_cache rcc
WHERE rcc.cuota_id IN (
  SELECT cu.id FROM cuotas cu WHERE cu.prestamo_id = 837
);

DELETE FROM pagos pg WHERE pg.prestamo_id = 837;

UPDATE cuotas c
SET
  total_pagado = 0,
  fecha_pago = NULL,
  pago_id = NULL,
  dias_mora = NULL,
  dias_morosidad = NULL,
  estado = (
    CASE
      WHEN COALESCE((SELECT SUM(cp.monto_aplicado) FROM cuota_pagos cp WHERE cp.cuota_id = c.id), 0)
           >= COALESCE(c.monto_cuota, 0) - 0.01 THEN
        CASE
          WHEN c.fecha_vencimiento IS NOT NULL
            AND CAST(c.fecha_vencimiento AS date) > CAST((CURRENT_TIMESTAMP AT TIME ZONE 'America/Caracas') AS date)
          THEN 'PAGO_ADELANTADO'
          ELSE 'PAGADO'
        END
      WHEN COALESCE((SELECT SUM(cp.monto_aplicado) FROM cuota_pagos cp WHERE cp.cuota_id = c.id), 0) > 0.001 THEN
        CASE
          WHEN c.fecha_vencimiento IS NULL THEN 'PARCIAL'
          WHEN CAST((CURRENT_TIMESTAMP AT TIME ZONE 'America/Caracas') AS date) <= CAST(c.fecha_vencimiento AS date) THEN 'PARCIAL'
          WHEN (CAST((CURRENT_TIMESTAMP AT TIME ZONE 'America/Caracas') AS date) - CAST(c.fecha_vencimiento AS date)) >= 92 THEN 'MORA'
          ELSE 'VENCIDO'
        END
      ELSE
        CASE
          WHEN c.fecha_vencimiento IS NULL THEN 'PENDIENTE'
          WHEN CAST((CURRENT_TIMESTAMP AT TIME ZONE 'America/Caracas') AS date) <= CAST(c.fecha_vencimiento AS date) THEN 'PENDIENTE'
          WHEN (CAST((CURRENT_TIMESTAMP AT TIME ZONE 'America/Caracas') AS date) - CAST(c.fecha_vencimiento AS date)) >= 92 THEN 'MORA'
          ELSE 'VENCIDO'
        END
    END
  )
WHERE c.prestamo_id = 837;

UPDATE prestamos pr
SET estado = 'APROBADO',
    fecha_liquidado = NULL
WHERE pr.id = 837;

COMMIT;
