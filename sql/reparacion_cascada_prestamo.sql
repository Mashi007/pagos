-- Reparacion en CASCADA para un prestamo (PostgreSQL).
-- Politica: misma idea que POST /api/v1/prestamos/{id}/reaplicar-cascada-aplicacion
-- (ruta .../reaplicar-fifo-aplicacion es alias legacy).
--
-- Antes de ejecutar: cambie 2438 por el prestamo_id deseado en los 4 sitios marcados con <<<.
-- Ejecute el archivo COMPLETO en el cliente SQL (no por fragmentos), o use transaccion manual.
--
-- Columna de monto en tabla cuotas: monto_cuota (no usar alias Python "monto").

BEGIN;

-- <<< CAMBIAR prestamo_id AQUI (1/4)
DO $$
DECLARE
  v_prestamo_id integer := 2438;
  v_cuotas integer;
BEGIN
  SELECT COUNT(*) INTO v_cuotas FROM cuotas WHERE prestamo_id = v_prestamo_id;
  IF v_cuotas = 0 THEN
    RAISE EXCEPTION 'Prestamo % no tiene cuotas, abortando', v_prestamo_id;
  END IF;
END $$;

-- 1) Limpiar articulacion previa
DELETE FROM cuota_pagos cp
USING cuotas c
WHERE cp.cuota_id = c.id
  AND c.prestamo_id = 2438;

-- 2) Resetear acumulados de cuotas
UPDATE cuotas
SET
  total_pagado = 0,
  fecha_pago = NULL,
  pago_id = NULL,
  dias_mora = NULL
WHERE prestamo_id = 2438;

-- 3) Reaplicar pagos conciliados en cascada (orden cuotas: numero_cuota; pagos: fecha_pago, id)
DO $$
DECLARE
  v_prestamo_id integer := 2438;

  r_pago record;
  r_cuota record;

  v_monto_restante numeric(14, 2);
  v_monto_necesario numeric(14, 2);
  v_aplicar numeric(14, 2);
  v_nuevo_total numeric(14, 2);
  v_orden integer;
BEGIN
  FOR r_pago IN
    SELECT
      p.id,
      p.fecha_pago::date AS fecha_pago,
      COALESCE(p.monto_pagado, 0)::numeric(14, 2) AS monto_pagado
    FROM pagos p
    WHERE p.prestamo_id = v_prestamo_id
      AND COALESCE(p.monto_pagado, 0) > 0
      AND (
        p.conciliado = TRUE
        OR UPPER(TRIM(COALESCE(p.verificado_concordancia, ''))) = 'SI'
      )
    ORDER BY p.fecha_pago NULLS LAST, p.id
  LOOP
    v_monto_restante := r_pago.monto_pagado;
    v_orden := 0;

    FOR r_cuota IN
      SELECT
        c.id,
        c.numero_cuota,
        COALESCE(c.monto_cuota, 0)::numeric(14, 2) AS monto_cuota,
        COALESCE(c.total_pagado, 0)::numeric(14, 2) AS total_pagado
      FROM cuotas c
      WHERE c.prestamo_id = v_prestamo_id
        AND COALESCE(c.total_pagado, 0) < COALESCE(c.monto_cuota, 0) - 0.01
      ORDER BY c.numero_cuota
      FOR UPDATE
    LOOP
      EXIT WHEN v_monto_restante <= 0;

      v_monto_necesario := GREATEST(0, r_cuota.monto_cuota - r_cuota.total_pagado);
      CONTINUE WHEN v_monto_necesario <= 0;

      v_aplicar := LEAST(v_monto_restante, v_monto_necesario);
      CONTINUE WHEN v_aplicar <= 0;

      UPDATE cuotas c
      SET
        total_pagado = ROUND(COALESCE(c.total_pagado, 0) + v_aplicar, 2),
        pago_id = r_pago.id,
        fecha_pago = CASE
          WHEN ROUND(COALESCE(c.total_pagado, 0) + v_aplicar, 2) >= COALESCE(c.monto_cuota, 0) - 0.01
          THEN r_pago.fecha_pago
          ELSE c.fecha_pago
        END
      WHERE c.id = r_cuota.id
      RETURNING COALESCE(total_pagado, 0)::numeric(14, 2)
      INTO v_nuevo_total;

      INSERT INTO cuota_pagos (
        cuota_id,
        pago_id,
        monto_aplicado,
        fecha_aplicacion,
        orden_aplicacion,
        es_pago_completo
      )
      VALUES (
        r_cuota.id,
        r_pago.id,
        ROUND(v_aplicar, 2),
        NOW(),
        v_orden,
        (v_nuevo_total >= r_cuota.monto_cuota - 0.01)
      );

      v_monto_restante := ROUND(v_monto_restante - v_aplicar, 2);
      v_orden := v_orden + 1;
    END LOOP;
  END LOOP;
END $$;

-- 4) Estados alineados a la misma taxonomia que el backend (cuota_estado.clasificar_estado_cuota)
--    Usa CURRENT_DATE (SQL); la app usa America/Caracas. Para operacion de mantenimiento suele ser aceptable.
UPDATE cuotas c
SET estado = CASE
  WHEN COALESCE(c.monto_cuota, 0) > 0
       AND COALESCE(c.total_pagado, 0) >= COALESCE(c.monto_cuota, 0) - 0.01 THEN
    CASE
      WHEN c.fecha_vencimiento::date > CURRENT_DATE THEN 'PAGO_ADELANTADO'
      ELSE 'PAGADO'
    END
  WHEN GREATEST(0, (CURRENT_DATE - c.fecha_vencimiento::date)) = 0 THEN
    CASE
      WHEN COALESCE(c.total_pagado, 0) > 0.001 THEN 'PARCIAL'
      ELSE 'PENDIENTE'
    END
  WHEN GREATEST(0, (CURRENT_DATE - c.fecha_vencimiento::date)) >= 92 THEN 'MORA'
  ELSE 'VENCIDO'
END
WHERE c.prestamo_id = 2438;

COMMIT;

-- Verificacion rapida (opcional)
-- SELECT numero_cuota, monto_cuota, total_pagado, estado FROM cuotas WHERE prestamo_id = 2438 ORDER BY numero_cuota;
