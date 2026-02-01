-- Tabla pagos_whatsapp: imágenes recibidas por WhatsApp (fecha, cedula_cliente, imagen).
-- Ejecutar en la BD si no usas Base.metadata.create_all.

CREATE TABLE IF NOT EXISTS pagos_whatsapp (
    id SERIAL PRIMARY KEY,
    fecha TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    cedula_cliente VARCHAR(20),
    imagen BYTEA NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_pagos_whatsapp_id ON pagos_whatsapp (id);
CREATE INDEX IF NOT EXISTS ix_pagos_whatsapp_cedula_cliente ON pagos_whatsapp (cedula_cliente);
