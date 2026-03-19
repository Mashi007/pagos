-- =============================================================================
-- Regularización: alinear cuotas.total_pagado con SUM(cuota_pagos.monto_aplicado)
--
-- Caso de uso: trazabilidad en cuota_pagos correcta pero total_pagado en cuotas
-- quedó en 0 o desfasado (legacy o regeneración de cuotas).
--
-- PASO 1 (solo lectura): revisar filas que cambiarían
-- PASO 2: ejecutar UPDATE en ventana de mantenimiento
-- =============================================================================

-- 1) Vista de desfase (misma lógica que verificar_trazabilidad sección 3, ampliada)
WITH aplicado AS (
    SELECT cuota_id, SUM(monto_aplicado)::numeric(14,2) AS sum_aplicado
    FROM cuota_pagos
    GROUP BY cuota_id
)
SELECT
    c.id AS cuota_id,
    c.prestamo_id,
    c.numero_cuota,
    c.monto_cuota,
    c.total_pagado AS total_pagado_actual,
    COALESCE(a.sum_aplicado, 0) AS sum_cuota_pagos,
    (COALESCE(a.sum_aplicado, 0) - COALESCE(c.total_pagado, 0)) AS ajuste_propuesto
FROM cuotas c
LEFT JOIN aplicado a ON a.cuota_id = c.id
WHERE EXISTS (SELECT 1 FROM cuota_pagos cp WHERE cp.cuota_id = c.id)
  AND (
    c.total_pagado IS NULL
    OR ABS(COALESCE(c.total_pagado, 0) - COALESCE(a.sum_aplicado, 0)) > 0.01
  )
ORDER BY c.prestamo_id, c.numero_cuota;

-- 2) UPDATE: copiar suma de cuota_pagos a total_pagado (solo cuotas con al menos un cuota_pago)
-- Descomentar para ejecutar:
/*
WITH aplicado AS (
    SELECT cuota_id, SUM(monto_aplicado)::numeric(14,2) AS sum_aplicado
    FROM cuota_pagos
    GROUP BY cuota_id
)
UPDATE cuotas c
SET total_pagado = a.sum_aplicado,
    actualizado_en = NOW()
FROM aplicado a
WHERE c.id = a.cuota_id
  AND (
    c.total_pagado IS NULL
    OR ABS(COALESCE(c.total_pagado, 0) - a.sum_aplicado) > 0.01
  );
*/
