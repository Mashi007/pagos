-- =============================================================================
-- Monitoreo Post-Regeneración: Alertas de Integridad
-- =============================================================================
-- Ejecutar mensualmente para detectar anomalías.
-- Guardar como vista o job en BD.

-- ============================================================================
-- Alert 1: Cuotas con fecha_vencimiento desalineada vs fecha_aprobacion
-- ============================================================================
-- Si resultado > 0: cuotas generadas incorrectamente o fecha_aprobacion cambió
CREATE OR REPLACE VIEW v_alert_cuota1_desalineada AS
WITH p AS (
  SELECT
    pr.id AS prestamo_id,
    UPPER(COALESCE(NULLIF(TRIM(pr.modalidad_pago), ''), 'MENSUAL')) AS modalidad,
    pr.fecha_aprobacion::date AS fecha_aprob,
    c.fecha_vencimiento AS venc_actual
  FROM prestamos pr
  JOIN cuotas c ON c.prestamo_id = pr.id AND c.numero_cuota = 1
  WHERE pr.fecha_aprobacion IS NOT NULL AND pr.numero_cuotas >= 1
),
esp AS (
  SELECT
    p.*,
    CASE
      WHEN p.modalidad = 'MENSUAL' THEN fn_add_months_keep_day(p.fecha_aprob, 1)
      WHEN p.modalidad = 'QUINCENAL' THEN (p.fecha_aprob + 14 * INTERVAL '1 day')::date
      WHEN p.modalidad = 'SEMANAL' THEN (p.fecha_aprob + 6 * INTERVAL '1 day')::date
      ELSE fn_add_months_keep_day(p.fecha_aprob, 1)
    END AS venc_esperado
  FROM p
)
SELECT
  prestamo_id,
  modalidad,
  fecha_aprob,
  venc_actual,
  venc_esperado,
  'ALERTA: Cuota 1 desalineada' AS alerta
FROM esp
WHERE esp.venc_actual IS DISTINCT FROM esp.venc_esperado;

-- ============================================================================
-- Alert 2: Préstamos con numero_cuotas inconsistente
-- ============================================================================
-- Si resultado > 0: cuotas se borraron/no generaron correctamente
CREATE OR REPLACE VIEW v_alert_numero_cuotas_inconsistente AS
SELECT
  pr.id AS prestamo_id,
  pr.numero_cuotas AS declarado,
  COUNT(c.id) AS en_tabla,
  ABS(pr.numero_cuotas - COUNT(c.id)) AS diferencia,
  'ALERTA: N cuotas inconsistente' AS alerta
FROM prestamos pr
LEFT JOIN cuotas c ON c.prestamo_id = pr.id
WHERE pr.numero_cuotas >= 1
GROUP BY pr.id, pr.numero_cuotas
HAVING COUNT(c.id) <> pr.numero_cuotas;

-- ============================================================================
-- Alert 3: Duplicados de numero_cuota por préstamo
-- ============================================================================
-- Si resultado > 0: error en generación de cuotas (debe ser único)
CREATE OR REPLACE VIEW v_alert_duplicados_numero_cuota AS
SELECT
  prestamo_id,
  numero_cuota,
  COUNT(*) AS veces,
  'ALERTA: Duplicado numero_cuota' AS alerta
FROM cuotas
GROUP BY prestamo_id, numero_cuota
HAVING COUNT(*) > 1;

-- ============================================================================
-- Alert 4: Cuotas sin estado válido
-- ============================================================================
-- Si resultado > 0: estado inválido o NULL (débil)
CREATE OR REPLACE VIEW v_alert_cuotas_estado_invalido AS
SELECT
  id,
  prestamo_id,
  numero_cuota,
  estado,
  'ALERTA: Estado inválido o NULL' AS alerta
FROM cuotas
WHERE estado NOT IN ('PENDIENTE', 'PAGADO', 'MORA', 'VENCIDO', 'CANCELADO')
  OR estado IS NULL;

-- ============================================================================
-- Alert 5: Préstamos con cuotas pero sin fecha_aprobacion
-- ============================================================================
-- Si resultado > 0: anomalía (debería regenerarse sin fecha_aprobacion)
CREATE OR REPLACE VIEW v_alert_cuotas_sin_fecha_aprobacion AS
SELECT
  p.id,
  p.estado,
  p.numero_cuotas,
  COUNT(c.id) AS cuotas_asociadas,
  'ALERTA: Cuotas sin fecha_aprobacion origen' AS alerta
FROM prestamos p
JOIN cuotas c ON c.prestamo_id = p.id
WHERE p.fecha_aprobacion IS NULL
GROUP BY p.id, p.estado, p.numero_cuotas;

-- ============================================================================
-- Alert 6: Inconsistencia estado vs total_pagado
-- ============================================================================
-- Si resultado > 0: estado no refleja pago real (ej. PAGADO pero total_pagado < monto_cuota)
CREATE OR REPLACE VIEW v_alert_inconsistencia_estado_pago AS
SELECT
  prestamo_id,
  numero_cuota,
  estado,
  monto_cuota,
  total_pagado,
  (monto_cuota - COALESCE(total_pagado, 0))::numeric(14,2) AS saldo,
  'ALERTA: Estado inconsistente con pago' AS alerta
FROM cuotas
WHERE
  (estado = 'PAGADO' AND COALESCE(total_pagado, 0) + 0.01 < monto_cuota)
  OR (estado = 'PENDIENTE' AND COALESCE(total_pagado, 0) >= monto_cuota)
  OR (COALESCE(total_pagado, 0) < 0);

-- ============================================================================
-- Alert 7: Violación Cascada (cuota posterior pagada, anterior impaga)
-- ============================================================================
-- Si resultado > 0: aplicación de pagos no respeta Cascada
CREATE OR REPLACE VIEW v_alert_fifo_violacion AS
WITH q AS (
  SELECT
    c.prestamo_id,
    c.numero_cuota,
    c.monto_cuota,
    COALESCE(c.total_pagado, 0) AS total_pagado,
    (COALESCE(c.total_pagado, 0) >= c.monto_cuota - 0.01) AS esta_cubierta
  FROM cuotas c
),
primera_impaga AS (
  SELECT
    prestamo_id,
    MIN(numero_cuota) AS primera_impaga
  FROM q
  WHERE NOT esta_cubierta
  GROUP BY prestamo_id
)
SELECT
  q.prestamo_id,
  pi.primera_impaga,
  q.numero_cuota AS cuota_posterior_pagada,
  q.total_pagado,
  q.monto_cuota,
  'ALERTA: Violación Cascada' AS alerta
FROM q
JOIN primera_impaga pi ON pi.prestamo_id = q.prestamo_id
WHERE q.numero_cuota > pi.primera_impaga AND q.total_pagado > 0;

-- ============================================================================
-- Dashboard: Resumen de Alertas
-- ============================================================================
CREATE OR REPLACE VIEW v_alert_resumen AS
SELECT
  'Cuota1 Desalineada' AS tipo_alerta,
  (SELECT COUNT(*) FROM v_alert_cuota1_desalineada) AS cantidad
UNION ALL
SELECT 'Número Cuotas Inconsistente', (SELECT COUNT(*) FROM v_alert_numero_cuotas_inconsistente)
UNION ALL
SELECT 'Duplicados Numero_Cuota', (SELECT COUNT(*) FROM v_alert_duplicados_numero_cuota)
UNION ALL
SELECT 'Estado Inválido', (SELECT COUNT(*) FROM v_alert_cuotas_estado_invalido)
UNION ALL
SELECT 'Cuotas Sin Fecha_Aprobacion', (SELECT COUNT(*) FROM v_alert_cuotas_sin_fecha_aprobacion)
UNION ALL
SELECT 'Inconsistencia Estado/Pago', (SELECT COUNT(*) FROM v_alert_inconsistencia_estado_pago)
UNION ALL
SELECT 'Violación Cascada', (SELECT COUNT(*) FROM v_alert_fifo_violacion)
ORDER BY cantidad DESC;

-- ============================================================================
-- Consulta: Ver todas las alertas activas
-- ============================================================================
-- SELECT * FROM v_alert_resumen WHERE cantidad > 0;
