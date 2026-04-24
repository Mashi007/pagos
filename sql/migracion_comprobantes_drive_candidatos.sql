-- Candidatos a migrar: comprobante aún como enlace Google Drive (no URL interna comprobante-imagen).
-- No modifica datos. Ejecutar en PostgreSQL para revisar volumen antes de
--   python backend/scripts/migrar_comprobantes_drive_a_bd.py --dry-run
--
-- Nota: no se requiere migración DDL; las tablas pagos y pago_comprobante_imagen ya existen.

SELECT
  p.id AS pago_id,
  p.prestamo_id,
  LEFT(p.link_comprobante, 140) AS link_preview,
  LENGTH(p.link_comprobante) AS link_len,
  p.estado,
  p.fecha_pago
FROM pagos p
WHERE p.link_comprobante IS NOT NULL
  AND TRIM(p.link_comprobante) <> ''
  AND p.link_comprobante NOT ILIKE '%comprobante-imagen%'
  AND (
    p.link_comprobante ILIKE '%drive.google%'
    OR (
      LENGTH(TRIM(p.link_comprobante)) >= 25
      AND TRIM(p.link_comprobante) NOT LIKE '%/%'
    )
  )
ORDER BY p.id;
