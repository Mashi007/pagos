-- Plantilla: corrección masiva PAGADO sin cuota_pagos (NO ejecutar a ciegas)
-- Requisitos: backup de tabla pagos; criterio de negocio; revisar COUNT antes de UPDATE.

-- 1) Vista de control: cuántos entrarían (ejemplo: PAGADO, sin cuota_pagos, sin cupo en cuotas pendientes)
--    Ajusta el filtro NOT EXISTS al mismo que usaste en diagnóstico (saldo aplicable).

/*
SELECT COUNT(*) 
FROM pagos p
WHERE COALESCE(p.estado, '') = 'PAGADO'
  AND NOT EXISTS (SELECT 1 FROM cuota_pagos cp WHERE cp.pago_id = p.id)
  AND COALESCE(p.monto_pagado, 0) > 0
  AND COALESCE(p.estado, '') <> 'ANULADO_IMPORT'
  AND p.prestamo_id IS NOT NULL
  AND NOT EXISTS (
    SELECT 1
    FROM cuotas c
    WHERE c.prestamo_id = p.prestamo_id
      AND c.estado IN ('PENDIENTE', 'MORA', 'PARCIAL')
      AND (
        COALESCE(c.monto_cuota, 0)
        - COALESCE(
            (SELECT SUM(cp2.monto_aplicado) FROM cuota_pagos cp2 WHERE cp2.cuota_id = c.id),
            0
          )
      ) > 0.01
  );
*/

-- 2) Respaldo de los IDs a tocar (descomentar y ejecutar antes del UPDATE)
/*
CREATE TABLE IF NOT EXISTS backup_pagos_sin_aplicacion_20260320 AS
SELECT p.*
FROM pagos p
WHERE ... -- mismo WHERE que arriba
;
*/

-- 3) Opción A: pasar a PENDIENTE para reflejar "registrado pero no articulado"
--    Solo si negocio aprueba.

/*
BEGIN;
UPDATE pagos p
SET estado = 'PENDIENTE'
WHERE COALESCE(p.estado, '') = 'PAGADO'
  AND NOT EXISTS (SELECT 1 FROM cuota_pagos cp WHERE cp.pago_id = p.id)
  -- AND ... resto de filtros de cohorte
;
-- Verificar: SELECT COUNT(*) FROM pagos WHERE id IN (...);
COMMIT;
*/

-- 4) Opción B: anular import (ejemplo de estado; alinear con convención del proyecto)

/*
BEGIN;
UPDATE pagos p
SET estado = 'ANULADO_IMPORT',
    notas = left(coalesce(p.notas, '') || E'\n[2026-03-20] Anulado masivo: sin cupo / duplicado cohorte feb-2026', 10000)
WHERE ... ;
COMMIT;
*/
