-- Historial de correos por cliente (idempotente).
-- Alternativa al ensure en startup: python no requerido si se aplica a mano.

CREATE TABLE IF NOT EXISTS cliente_emails_historial (
    id SERIAL PRIMARY KEY,
    cliente_id INTEGER NOT NULL REFERENCES clientes(id) ON DELETE CASCADE,
    cedula VARCHAR(20) NOT NULL,
    email VARCHAR(150) NOT NULL,
    email_norm VARCHAR(150) NOT NULL,
    rol VARCHAR(20) NOT NULL,
    registrado_en TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    usuario_cambio VARCHAR(50) NULL,
    CONSTRAINT uq_cliente_emails_historial_cliente_email
        UNIQUE (cliente_id, email_norm)
);

CREATE INDEX IF NOT EXISTS ix_cliente_emails_historial_cliente_id
    ON cliente_emails_historial (cliente_id);

CREATE INDEX IF NOT EXISTS ix_cliente_emails_historial_cedula
    ON cliente_emails_historial (cedula);

CREATE INDEX IF NOT EXISTS ix_cliente_emails_historial_email_norm
    ON cliente_emails_historial (email_norm);
