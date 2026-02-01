-- Tabla cuotas para notificaciones por fecha_vencimiento y mora.
-- Ejecutar en la BD si no usas Base.metadata.create_all.

CREATE TABLE IF NOT EXISTS cuotas (
    id SERIAL PRIMARY KEY,
    cliente_id INTEGER NOT NULL REFERENCES clientes(id) ON DELETE CASCADE,
    numero_cuota INTEGER NOT NULL,
    fecha_vencimiento DATE NOT NULL,
    monto NUMERIC(14, 2) NOT NULL,
    pagado BOOLEAN NOT NULL DEFAULT FALSE,
    fecha_pago TIMESTAMP WITHOUT TIME ZONE
);

CREATE INDEX IF NOT EXISTS ix_cuotas_id ON cuotas (id);
CREATE INDEX IF NOT EXISTS ix_cuotas_cliente_id ON cuotas (cliente_id);
CREATE INDEX IF NOT EXISTS ix_cuotas_fecha_vencimiento ON cuotas (fecha_vencimiento);
CREATE INDEX IF NOT EXISTS ix_cuotas_pagado ON cuotas (pagado);
