-- Borra pagos del cliente V29723003, cola pagos_con_errores, y cache contable de sus cuotas.
-- NO actualiza cuotas ni prestamos.
--
-- ADVERTENCIA: al borrar pagos, cuota_pagos se elimina en CASCADE por FK, pero
-- cuotas.total_pagado, fecha_pago, pago_id y estado NO se recalculan aqui.
-- Si necesitas cartera coherente, usa reset_cliente_*_pagos_y_aprobado.sql o
-- regulariza despues (ej. sql/regularizar_total_pagado_desde_cuota_pagos.sql).
--
-- PostgreSQL.

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

COMMIT;
