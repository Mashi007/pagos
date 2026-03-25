-- Historial de notificaciones: cuerpo del correo, adjuntos enviados y comprobante PDF.
-- Ejecutar en DBeaver / psql sobre la misma BD que usa la app (después de backup si aplica).

-- 1) Columnas en envios_notificacion
ALTER TABLE envios_notificacion
  ADD COLUMN IF NOT EXISTS mensaje_html TEXT NULL,
  ADD COLUMN IF NOT EXISTS mensaje_texto TEXT NULL,
  ADD COLUMN IF NOT EXISTS comprobante_pdf BYTEA NULL;

COMMENT ON COLUMN envios_notificacion.mensaje_html IS 'Cuerpo HTML del correo tal como se envió (snapshot).';
COMMENT ON COLUMN envios_notificacion.mensaje_texto IS 'Cuerpo texto del correo tal como se envió (snapshot).';
COMMENT ON COLUMN envios_notificacion.comprobante_pdf IS 'Comprobante de envío en PDF (generado al persistir el registro).';

-- 2) Adjuntos por envío
CREATE TABLE IF NOT EXISTS envios_notificacion_adjuntos (
  id SERIAL PRIMARY KEY,
  envio_notificacion_id INTEGER NOT NULL REFERENCES envios_notificacion (id) ON DELETE CASCADE,
  nombre_archivo VARCHAR(255) NOT NULL,
  contenido BYTEA NOT NULL,
  orden INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS ix_envios_notif_adjuntos_envio_id
  ON envios_notificacion_adjuntos (envio_notificacion_id);

COMMENT ON TABLE envios_notificacion_adjuntos IS 'PDFs u otros adjuntos enviados en el correo (bytes en el momento del envío).';
