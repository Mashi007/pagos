-- Historial de mensajes WhatsApp para mostrar copia de la conversación en Comunicaciones.
-- Ejecutar una vez.

CREATE TABLE IF NOT EXISTS mensaje_whatsapp (
    id SERIAL PRIMARY KEY,
    telefono VARCHAR(30) NOT NULL,
    direccion VARCHAR(10) NOT NULL,
    body TEXT,
    message_type VARCHAR(20) NOT NULL DEFAULT 'text',
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_mensaje_whatsapp_telefono ON mensaje_whatsapp(telefono);
CREATE INDEX IF NOT EXISTS ix_mensaje_whatsapp_timestamp ON mensaje_whatsapp(timestamp);
