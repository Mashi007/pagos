-- Diagnóstico: 3 BINANCE en bandeja sin observación (25/08/2026)
SELECT
  pr.id,
  pr.referencia_interna,
  pr.tipo_cedula || pr.numero_cedula AS cedula,
  pr.estado,
  pr.falla_validadores_manual,
  pr.monto,
  pr.moneda,
  pr.institucion_financiera,
  pr.numero_operacion,
  pr.gemini_coincide_exacto,
  LEFT(COALESCE(pr.gemini_comentario, ''), 300) AS gemini_comentario,
  COALESCE(pr.observacion, '') AS observacion,
  pr.canal_ingreso,
  pr.created_at,
  EXISTS (
    SELECT 1 FROM clientes c
    WHERE UPPER(REGEXP_REPLACE(COALESCE(c.cedula,''), '[^A-Za-z0-9]', '', 'g'))
      LIKE '%' || pr.numero_cedula || '%'
  ) AS cliente_existe,
  (
    SELECT p.id FROM prestamos p
    WHERE UPPER(REGEXP_REPLACE(COALESCE(p.cedula,''), '[^A-Za-z0-9]', '', 'g'))
      LIKE '%' || pr.numero_cedula || '%'
      AND UPPER(TRIM(COALESCE(p.estado,''))) = 'APROBADO'
    ORDER BY p.id DESC LIMIT 1
  ) AS prestamo_aprobado_id,
  EXISTS (
    SELECT 1 FROM pagos pg
    WHERE pg.numero_documento = pr.numero_operacion
       OR pg.numero_documento LIKE '%' || pr.numero_operacion || '%'
  ) AS serial_ya_en_pagos
FROM pagos_reportados pr
WHERE pr.numero_operacion IN (
    '450606131298197504',
    '450606146082562048',
    '450608158172143616'
  )
   OR (
    pr.numero_cedula IN ('18753729', '17118122', '32663006')
    AND pr.fecha_pago = DATE '2026-08-25'
  )
ORDER BY pr.id DESC;
