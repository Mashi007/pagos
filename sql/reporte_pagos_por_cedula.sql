-- =============================================================================
-- Reporte de pagos por cedula (PostgreSQL). Reutilizable: cambia solo params.
-- Ejecutar cada bloque por separado si el cliente SQL no admite varios SELECT.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- PARAMS: una sola linea a editar
-- -----------------------------------------------------------------------------
WITH params AS (
  SELECT 'V30319177'::text AS cedula_buscar  -- <-- cambiar cedula aqui (mayusculas recomendado)
),

-- Normaliza igual que en consultas habituales (sin guiones en comparacion)
norm AS (
  SELECT upper(btrim(cedula_buscar)) AS cedula_n
  FROM params
),

-- Pagos donde la cedula esta en el pago o en el prestamo vinculado
pagos_scope AS (
  SELECT p.*
  FROM pagos p
  LEFT JOIN prestamos pr ON pr.id = p.prestamo_id
  CROSS JOIN norm n
  WHERE upper(btrim(p.cedula)) = n.cedula_n
     OR upper(btrim(pr.cedula)) = n.cedula_n
),

-- Aplicacion a cuotas (si existe)
aplicado AS (
  SELECT
    cp.pago_id,
    SUM(cp.monto_aplicado) AS monto_aplicado_total
  FROM cuota_pagos cp
  WHERE cp.pago_id IN (SELECT id FROM pagos_scope)
  GROUP BY cp.pago_id
)

-- -----------------------------------------------------------------------------
-- A) Detalle de pagos (orden cronologico)
-- -----------------------------------------------------------------------------
SELECT
  ps.id AS pago_id,
  ps.prestamo_id,
  pr.cedula AS cedula_prestamo,
  ps.cedula AS cedula_en_pago,
  ps.fecha_pago,
  ps.fecha_registro,
  ps.monto_pagado,
  COALESCE(a.monto_aplicado_total, 0)::numeric(14, 2) AS monto_aplicado_cuotas,
  (ps.monto_pagado - COALESCE(a.monto_aplicado_total, 0))::numeric(14, 2) AS diferencia_sin_aplicar,
  ps.numero_documento,
  ps.referencia_pago,
  ps.estado,
  ps.conciliado,
  ps.moneda_registro
FROM pagos_scope ps
LEFT JOIN prestamos pr ON pr.id = ps.prestamo_id
LEFT JOIN aplicado a ON a.pago_id = ps.id
ORDER BY ps.fecha_pago DESC NULLS LAST, ps.id DESC;

/*
-- -----------------------------------------------------------------------------
-- B) Resumen por prestamo (mismo params: copiar CTE params + norm + pagos_scope arriba)
-- -----------------------------------------------------------------------------
WITH params AS ( SELECT 'V30319177'::text AS cedula_buscar ),
norm AS ( SELECT upper(btrim(cedula_buscar)) AS cedula_n FROM params ),
pagos_scope AS (
  SELECT p.*
  FROM pagos p
  LEFT JOIN prestamos pr ON pr.id = p.prestamo_id
  CROSS JOIN norm n
  WHERE upper(btrim(p.cedula)) = n.cedula_n OR upper(btrim(pr.cedula)) = n.cedula_n
)
SELECT
  ps.prestamo_id,
  MAX(pr.cedula) AS cedula_prestamo,
  COUNT(*)::bigint AS cantidad_pagos,
  COALESCE(SUM(ps.monto_pagado) FILTER (WHERE ps.estado = 'PAGADO'), 0)::numeric(14, 2) AS suma_pagado_usd,
  COALESCE(SUM(ps.monto_pagado) FILTER (WHERE ps.estado = 'PENDIENTE'), 0)::numeric(14, 2) AS suma_pendiente_usd
FROM pagos_scope ps
LEFT JOIN prestamos pr ON pr.id = ps.prestamo_id
GROUP BY ps.prestamo_id
ORDER BY ps.prestamo_id;

-- -----------------------------------------------------------------------------
-- C) Totales globales para la cedula
-- -----------------------------------------------------------------------------
WITH params AS ( SELECT 'V30319177'::text AS cedula_buscar ),
norm AS ( SELECT upper(btrim(cedula_buscar)) AS cedula_n FROM params ),
pagos_scope AS (
  SELECT p.*
  FROM pagos p
  LEFT JOIN prestamos pr ON pr.id = p.prestamo_id
  CROSS JOIN norm n
  WHERE upper(btrim(p.cedula)) = n.cedula_n OR upper(btrim(pr.cedula)) = n.cedula_n
)
SELECT
  COUNT(*)::bigint AS total_registros_pagos,
  COALESCE(SUM(monto_pagado), 0)::numeric(14, 2) AS suma_monto_todos_estados,
  COALESCE(SUM(monto_pagado) FILTER (WHERE estado = 'PAGADO'), 0)::numeric(14, 2) AS suma_solo_pagado
FROM pagos_scope;
*/
