-- Tabla tickets para CRM. Conectada a clientes (cliente_id).
-- Ejecutar en la BD si no usas Base.metadata.create_all.

CREATE TABLE IF NOT EXISTS tickets (
    id SERIAL PRIMARY KEY,
    titulo VARCHAR(255) NOT NULL,
    descripcion TEXT NOT NULL,
    cliente_id INTEGER REFERENCES clientes(id) ON DELETE SET NULL,
    estado VARCHAR(30) NOT NULL DEFAULT 'abierto',
    prioridad VARCHAR(20) NOT NULL DEFAULT 'media',
    tipo VARCHAR(30) NOT NULL DEFAULT 'consulta',
    asignado_a VARCHAR(255),
    asignado_a_id INTEGER,
    escalado_a_id INTEGER,
    escalado BOOLEAN NOT NULL DEFAULT FALSE,
    fecha_limite TIMESTAMP WITHOUT TIME ZONE,
    conversacion_whatsapp_id INTEGER,
    comunicacion_email_id INTEGER,
    creado_por_id INTEGER,
    fecha_creacion TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    fecha_actualizacion TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    archivos TEXT
);

CREATE INDEX IF NOT EXISTS ix_tickets_id ON tickets (id);
CREATE INDEX IF NOT EXISTS ix_tickets_cliente_id ON tickets (cliente_id);
CREATE INDEX IF NOT EXISTS ix_tickets_estado ON tickets (estado);
