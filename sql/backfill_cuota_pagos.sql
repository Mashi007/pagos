-- =============================================================================
-- BACKFILL de trazabilidad: cuota_pagos desde cuotas con pago aplicado (legacy)
-- =============================================================================
--
-- REGLAS:
-- 1. Origen: solo cuotas con total_pagado > 0, pago_id NOT NULL y sin ninguna
--    fila en cuota_pagos para esa cuota_id (dato legacy aplicado antes de cuota_pagos).
-- 2. Una fila por cuota: se inserta una fila en cuota_pagos por cuota elegible.
-- 3. Campos: monto_aplicado = cuota.total_pagado; orden_aplicacion = 0;
--    es_pago_completo = (total_pagado >= monto_cuota - 0.01);
--    fecha_aplicacion = COALESCE(pago.fecha_pago, cuota.fecha_pago::timestamp, now()).
-- 4. Idempotente: no se inserta si ya existe alguna fila en cuota_pagos para esa cuota_id.
-- 5. Solo INSERT: no se modifican tablas cuotas ni pagos.
--
-- POST-BACKFILL: ejecutar consulta 2 de verificar_trazabilidad_pagos_cuotas_prestamos.sql
-- para revisar pagos donde suma(monto_aplicado) != monto_pagado (ajuste manual si aplica).
--
-- Uso: ejecutar en una transacción y hacer COMMIT tras revisar el número de filas.
-- =============================================================================

-- Vista previa: cuántas filas se insertarían (ejecutar primero)
SELECT COUNT(*) AS filas_a_insertar
FROM cuotas c
JOIN pagos p ON p.id = c.pago_id
WHERE c.total_pagado IS NOT NULL AND c.total_pagado > 0
  AND c.pago_id IS NOT NULL
  AND NOT EXISTS (SELECT 1 FROM cuota_pagos cp WHERE cp.cuota_id = c.id);

-- Inserción (descomentar y ejecutar cuando apruebes)
/*
INSERT INTO cuota_pagos (
    cuota_id,
    pago_id,
    monto_aplicado,
    fecha_aplicacion,
    orden_aplicacion,
    es_pago_completo
)
SELECT
    c.id,
    c.pago_id,
    c.total_pagado,
    COALESCE(
        (p.fecha_pago AT TIME ZONE 'America/Caracas')::timestamptz,
        (c.fecha_pago::timestamp AT TIME ZONE 'America/Caracas')::timestamptz,
        current_timestamp
    ),
    0,
    (c.total_pagado >= (c.monto_cuota - 0.01))
FROM cuotas c
JOIN pagos p ON p.id = c.pago_id
WHERE c.total_pagado IS NOT NULL AND c.total_pagado > 0
  AND c.pago_id IS NOT NULL
  AND NOT EXISTS (SELECT 1 FROM cuota_pagos cp WHERE cp.cuota_id = c.id);
*/

-- =============================================================================
-- POST-BACKFILL: integridad por pago (desfase entre monto_pagado y suma aplicada)
-- =============================================================================
-- Copiar/ejecutar consulta 2 de verificar_trazabilidad_pagos_cuotas_prestamos.sql
-- para listar pagos donde SUM(monto_aplicado) <> monto_pagado (revisar manual si aplica).
