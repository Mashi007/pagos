-- Borra TODOS los pagos del cliente V29723003, limpia cuotas de sus prestamos y deja prestamos en APROBADO.
-- Tambien borra filas en pagos_con_errores del mismo cliente (evita "documento duplicado" al recargar Excel).
-- PostgreSQL. Ejecutar en ventana de mantenimiento; revisar filas afectadas antes con SELECT.
--
-- Pre-chequeo (solo lectura):
-- SELECT id, fecha_pago, monto_pagado, numero_documento, prestamo_id
-- FROM pagos
-- WHERE UPPER(REPLACE(cedula, '-', '')) = UPPER(REPLACE('V29723003', '-', ''));

BEGIN;

DELETE FROM reporte_contable_cache rcc
WHERE rcc.cuota_id IN (
  SELECT cu.id
  FROM cuotas cu
  INNER JOIN prestamos pr ON pr.id = cu.prestamo_id
  INNER JOIN clientes cl ON cl.id = pr.cliente_id
  WHERE UPPER(REPLACE(cl.cedula, '-', '')) = UPPER(REPLACE('V29723003', '-', ''))
);

DELETE FROM pagos pg
WHERE UPPER(REPLACE(pg.cedula, '-', '')) = UPPER(REPLACE('V29723003', '-', ''))
   OR pg.prestamo_id IN (
        SELECT pr.id
        FROM prestamos pr
        INNER JOIN clientes cl ON cl.id = pr.cliente_id
        WHERE UPPER(REPLACE(cl.cedula, '-', '')) = UPPER(REPLACE('V29723003', '-', ''))
      );

DELETE FROM pagos_con_errores pce
WHERE UPPER(REPLACE(pce.cedula, '-', '')) = UPPER(REPLACE('V29723003', '-', ''))
   OR pce.prestamo_id IN (
        SELECT pr.id
        FROM prestamos pr
        INNER JOIN clientes cl ON cl.id = pr.cliente_id
        WHERE UPPER(REPLACE(cl.cedula, '-', '')) = UPPER(REPLACE('V29723003', '-', ''))
      );

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
WHERE EXISTS (
  SELECT 1
  FROM prestamos pr
  INNER JOIN clientes cl ON cl.id = pr.cliente_id
  WHERE pr.id = c.prestamo_id
    AND UPPER(REPLACE(cl.cedula, '-', '')) = UPPER(REPLACE('V29723003', '-', ''))
);

UPDATE prestamos pr
SET
  estado = 'APROBADO',
  fecha_liquidado = NULL
FROM clientes cl
WHERE cl.id = pr.cliente_id
  AND UPPER(REPLACE(cl.cedula, '-', '')) = UPPER(REPLACE('V29723003', '-', ''));

COMMIT;
