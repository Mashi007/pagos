-- =============================================================================
-- Paso 1 — Fechas sin tasa (reportes BS aprobados/importados con pago en cartera)
-- =============================================================================
-- Lista cada fecha_pago del reporte que NO tiene fila en tasas_cambio_diaria.
-- Cargar la tasa oficial (Bs. por 1 USD) para cada fecha antes del UPDATE masivo.
-- Mismo criterio de vínculo pago↔reporte que en backfill_pagos_bs_mal_importados_desde_cobros.sql (0a).
--
-- Tras obtener las fechas, registrar tasas con cualquiera de:
--   - POST /admin/tasas-cambio/guardar-por-fecha  (admin; JSON: fecha, tasa_oficial)
--   - backend/sql/upsert_tasas_por_fecha_manual.sql   (editar valores y ejecutar)
--   - python tools/cargar_tasas_fechas_pagos_bs.py 2026-03-12=3105.75 ...
-- =============================================================================

SELECT
    pr.fecha_pago AS fecha_sin_tasa,
    COUNT(DISTINCT pr.id) AS cantidad_reportes_bs
FROM pagos p
JOIN pagos_reportados pr
  ON (
        p.numero_documento = ('COB-' || pr.referencia_interna)
     OR TRIM(BOTH FROM p.numero_documento) = TRIM(BOTH FROM pr.referencia_interna)
  )
LEFT JOIN tasas_cambio_diaria tc ON tc.fecha = pr.fecha_pago
WHERE UPPER(TRIM(pr.moneda)) = 'BS'
  AND pr.estado IN ('aprobado', 'importado')
  AND tc.fecha IS NULL
GROUP BY pr.fecha_pago
ORDER BY pr.fecha_pago;
