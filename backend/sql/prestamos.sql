-- Tabla prestamos. Conectada a clientes (cliente_id).
-- Ejecutar en la BD si no usas Base.metadata.create_all.

CREATE TABLE IF NOT EXISTS prestamos (
    id SERIAL PRIMARY KEY,
    cliente_id INTEGER NOT NULL REFERENCES clientes(id) ON DELETE CASCADE,
    total_financiamiento NUMERIC(14, 2) NOT NULL,
    monto_programado NUMERIC(14, 2),
    monto_pagado NUMERIC(14, 2),
    estado VARCHAR(20) NOT NULL DEFAULT 'PENDIENTE',
    fecha_creacion TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    fecha_actualizacion TIMESTAMP WITHOUT TIME ZONE
);

CREATE INDEX IF NOT EXISTS ix_prestamos_id ON prestamos (id);
CREATE INDEX IF NOT EXISTS ix_prestamos_cliente_id ON prestamos (cliente_id);
CREATE INDEX IF NOT EXISTS ix_prestamos_estado ON prestamos (estado);
