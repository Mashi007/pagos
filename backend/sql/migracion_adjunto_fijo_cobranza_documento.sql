-- PDFs de "Documentos PDF anexos" (configuracion.adjuntos_fijos_por_caso): contenido en BD para Render/disco efimero.
-- Ejecutar en la BD de produccion si no usas alembic upgrade.

CREATE TABLE IF NOT EXISTS adjunto_fijo_cobranza_documento (
    id VARCHAR(36) NOT NULL PRIMARY KEY,
    tipo_caso VARCHAR(32) NOT NULL,
    nombre_archivo VARCHAR(512) NOT NULL,
    pdf_data BYTEA NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_adjunto_fijo_cobranza_documento_tipo_caso
    ON adjunto_fijo_cobranza_documento (tipo_caso);
