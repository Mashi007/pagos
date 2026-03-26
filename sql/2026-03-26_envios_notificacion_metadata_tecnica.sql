-- Metadatos SMTP/socket por envio (comprobante PDF legal).
-- PostgreSQL. Ejecutar una vez en produccion.

ALTER TABLE envios_notificacion
  ADD COLUMN IF NOT EXISTS metadata_tecnica JSONB;

COMMENT ON COLUMN envios_notificacion.metadata_tecnica IS
  'JSON: message_id, IPs socket SMTP, resultado sesion, etc. Capturado al enviar.';
