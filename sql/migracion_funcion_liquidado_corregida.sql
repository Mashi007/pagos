-- =============================================================================
-- Correccion: funcion actualizar_prestamos_a_liquidado_automatico()
-- =============================================================================
-- Problema anterior: usaba SUM(monto_cuota) FILTER (WHERE estado = 'PAGADO'),
-- que puede marcar LIQUIDADO sin que todas las cuotas esten cubiertas por total_pagado.
--
-- Regla alineada con backend: app.api.v1.endpoints.pagos._marcar_prestamo_liquidado_si_corresponde
--   LIQUIDADO solo si NO existe cuota con total_pagado < monto_cuota - 0.01
--   y el prestamo tiene al menos una cuota.
--
-- Ejecutar en PostgreSQL como superusuario/owner de la BD.
-- =============================================================================

CREATE OR REPLACE FUNCTION actualizar_prestamos_a_liquidado_automatico()
RETURNS void
LANGUAGE plpgsql
AS $$
BEGIN
  WITH prestamos_a_liquidar AS (
    SELECT p.id
    FROM prestamos p
    WHERE p.estado = 'APROBADO'
      AND EXISTS (SELECT 1 FROM cuotas c WHERE c.prestamo_id = p.id)
      AND NOT EXISTS (
        SELECT 1
        FROM cuotas c2
        WHERE c2.prestamo_id = p.id
          AND COALESCE(c2.total_pagado, 0) < COALESCE(c2.monto_cuota, 0) - 0.01
      )
  ),
  upd AS (
    UPDATE prestamos p
    SET estado = 'LIQUIDADO'
    FROM prestamos_a_liquidar pal
    WHERE p.id = pal.id
      AND p.estado = 'APROBADO'
    RETURNING p.id
  )
  INSERT INTO auditoria_cambios_estado_prestamo (
    prestamo_id,
    estado_anterior,
    estado_nuevo,
    motivo,
    total_financiamiento,
    suma_pagado
  )
  SELECT
    p.id,
    'APROBADO',
    'LIQUIDADO',
    'Actualizacion automatica: todas las cuotas cubiertas (total_pagado vs monto_cuota)',
    p.total_financiamiento::numeric(14, 2),
    COALESCE(SUM(COALESCE(c.total_pagado, 0)), 0)::numeric(14, 2)
  FROM prestamos p
  JOIN upd u ON u.id = p.id
  JOIN cuotas c ON c.prestamo_id = p.id
  GROUP BY p.id, p.total_financiamiento;
END;
$$;
