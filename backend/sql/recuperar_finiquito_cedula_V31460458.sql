-- Recuperacion finiquito: cedula V31460458 (casos borrados por bug Visto / refresh).
-- Ejecutar en la BD de produccion (misma que DATABASE_URL).

-- 1) Estado actual de prestamos y elegibilidad finiquito
SELECT
  p.id AS prestamo_id,
  UPPER(TRIM(p.estado)) AS estado,
  p.total_financiamiento,
  COALESCE(SUM(COALESCE(c.total_pagado, 0)), 0) AS sum_cuotas_pagado,
  ROUND(
    ABS(
      COALESCE(SUM(COALESCE(c.total_pagado, 0)), 0) - COALESCE(p.total_financiamiento, 0)
    )::numeric,
    4
  ) AS diff_abs,
  (SELECT COUNT(*) FROM pagos pg WHERE pg.prestamo_id = p.id) AS n_pagos,
  fc.id AS caso_id,
  fc.estado AS caso_estado
FROM prestamos p
LEFT JOIN cuotas c ON c.prestamo_id = p.id
LEFT JOIN finiquito_casos fc ON fc.prestamo_id = p.id
WHERE UPPER(TRIM(p.cedula)) = 'V31460458'
GROUP BY p.id, p.estado, p.total_financiamiento, fc.id, fc.estado
ORDER BY p.id;

-- Elegibles para materializar (misma regla que el job):
--   estado LIQUIDADO o FINIQUITO y |sum(cuotas)-total_fin| <= 0.02

-- 2) Historial finiquito (si quedo algo)
SELECT h.caso_id, h.estado_anterior, h.estado_nuevo, h.creado_en
FROM finiquito_estado_historial h
JOIN finiquito_casos fc ON fc.id = h.caso_id
WHERE UPPER(TRIM(fc.cedula)) = 'V31460458'
ORDER BY h.creado_en DESC
LIMIT 20;

-- 3) Si diff_abs > 0.02 o estado = APROBADO con cuotas en cero:
--    restaurar pagos/cascada en revision manual ANTES del paso 4.

-- 4) Marcar liquidados efectivos (funcion del sistema) y luego refrescar desde la app:
--    POST /api/v1/finiquito/admin/refresh-materializado  (admin logueado)
--    o en backend: python scripts/diagnostico_finiquito_cedula.py V31460458 --recuperar

SELECT actualizar_prestamos_a_liquidado_automatico();

-- 5) Verificar casos creados (deben aparecer en REVISION)
SELECT id, prestamo_id, estado, sum_total_pagado, total_financiamiento, creado_en
FROM finiquito_casos
WHERE UPPER(TRIM(cedula)) = 'V31460458'
ORDER BY id;
